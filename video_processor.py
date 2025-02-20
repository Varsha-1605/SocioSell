import cv2
import numpy as np
import torch
from transformers import Wav2Vec2ForCTC, Wav2Vec2Processor
import google.generativeai as genai
import librosa
from PIL import Image
import os
from tqdm import tqdm
import subprocess
import soundfile as sf
from pathlib import Path
import asyncio
import logging
import time
import yt_dlp as youtube_dl
import backoff
from functools import wraps
import imageio_ffmpeg
import tempfile

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def handle_rate_limit(max_tries=5, initial_wait=5):
    def decorator(func):
        @wraps(func)
        @backoff.on_exception(
            backoff.expo,
            Exception,
            max_tries=max_tries,
            giveup=lambda e: not (isinstance(e, Exception) and "429" in str(e)),
            base=2,
            factor=5
        )
        async def wrapper(*args, **kwargs):
            return await func(*args, **kwargs)
        return wrapper
    return decorator

class TokenBucket:
    def __init__(self, tokens_per_second=0.05, max_tokens=10):
        self.tokens_per_second = tokens_per_second
        self.max_tokens = max_tokens
        self.tokens = max_tokens
        self.last_update = time.time()
        self.lock = asyncio.Lock()
        self.waiting = False
    
    async def acquire(self):
        async with self.lock:
            now = time.time()
            time_passed = now - self.last_update
            self.tokens = min(self.max_tokens, self.tokens + time_passed * self.tokens_per_second)
            self.last_update = now
            
            if self.tokens >= 1:
                self.tokens -= 1
                return True
            return False
    
    async def wait(self):
        while not await self.acquire():
            self.waiting = True
            await asyncio.sleep(20)
        self.waiting = False

class VideoProcessor:
    def __init__(self, google_api_key):
        self.api_key = google_api_key
        self.rate_limiter = TokenBucket(tokens_per_second=0.05)
        
        genai.configure(api_key=google_api_key)
        self.model = genai.GenerativeModel('gemini-1.5-pro-latest')
        
        self.ffmpeg_path = imageio_ffmpeg.get_ffmpeg_exe()  # Get the bundled FFmpeg path
        if not os.path.exists(self.ffmpeg_path):
            raise RuntimeError(f"FFmpeg not found at: {self.ffmpeg_path}")
        print(f"Using FFmpeg from: {self.ffmpeg_path}")
        
        self.audio_processor = Wav2Vec2Processor.from_pretrained("facebook/wav2vec2-base-960h")
        self.audio_model = Wav2Vec2ForCTC.from_pretrained("facebook/wav2vec2-base-960h")
        
        self.temp_dir = Path("temp")
        self.temp_dir.mkdir(exist_ok=True)
        
        self.MAX_FRAMES_PER_VIDEO = 3
        self.MAX_API_RETRIES = 3
        self.API_RETRY_DELAY = 10
        self.FRAME_ANALYSIS_DELAY = 5

    async def download_video(self, video_url):
        try:
            temp_path = self.temp_dir / f"{abs(hash(video_url))}.mp4"
            ydl_opts = {
                'format': 'best',
                'outtmpl': str(temp_path),
                'quiet': True,
                'no_warnings': True,
                'extract_flat': True
            }
            
            loop = asyncio.get_event_loop()
            success = await loop.run_in_executor(None, 
                lambda: self._download_with_ytdl(ydl_opts, video_url))
            
            if success and temp_path.exists():
                return temp_path
            return None
            
        except Exception as e:
            logger.error(f"Error downloading video: {str(e)}")
            return None

    def _download_with_ytdl(self, ydl_opts, url):
        with youtube_dl.YoutubeDL(ydl_opts) as ydl:
            try:
                ydl.download([url])
                return True
            except Exception as e:
                logger.error(f"YouTube-DL error: {str(e)}")
                return False

    async def _extract_audio(self, video_path):
        try:
            if not os.path.exists(str(video_path)):
                raise FileNotFoundError(f"Video file not found: {video_path}")
                
            temp_audio_path = self.temp_dir / "temp_audio.wav"
            command = [
                str(self.ffmpeg_path),
                '-i', str(video_path),
                '-ab', '160k',
                '-ac', '2',
                '-ar', '16000',
                '-vn', str(temp_audio_path),
                '-y'
            ]
            
            process = await asyncio.create_subprocess_exec(
                *command,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            await process.communicate()
            
            if not os.path.exists(str(temp_audio_path)):
                return None, None
                
            waveform, sample_rate = librosa.load(str(temp_audio_path), sr=16000)
            os.remove(str(temp_audio_path))
            return waveform, sample_rate
            
        except Exception as e:
            logger.error(f"Error extracting audio: {str(e)}")
            return None, None

    async def _transcribe_audio(self, waveform):
        try:
            inputs = self.audio_processor(waveform, sampling_rate=16000, return_tensors="pt", padding=True)
            with torch.no_grad():
                logits = self.audio_model(inputs.input_values).logits
            predicted_ids = torch.argmax(logits, dim=-1)
            return self.audio_processor.batch_decode(predicted_ids)[0]
        except Exception as e:
            logger.error(f"Error transcribing audio: {str(e)}")
            return ""

    async def _extract_frames(self, video_path, num_frames=5):
        frames = []
        try:
            cap = cv2.VideoCapture(str(video_path))
            total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
            
            if total_frames > 0:
                frame_indices = np.linspace(0, total_frames-1, num_frames, dtype=int)
                for idx in frame_indices:
                    cap.set(cv2.CAP_PROP_POS_FRAMES, idx)
                    ret, frame = cap.read()
                    if ret:
                        frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                        frames.append(Image.fromarray(frame))
                        
        except Exception as e:
            logger.error(f"Error extracting frames: {str(e)}")
            
        finally:
            if 'cap' in locals():
                cap.release()
                
        return frames

    @handle_rate_limit(max_tries=3, initial_wait=2)
    async def _analyze_frame(self, frame):
        await self.rate_limiter.wait()
        prompt = """Analyze this product image and provide a detailed e-commerce style description.
Include:
1. Visual characteristics
2. Notable features
3. Potential uses
4. Any visible technical specifications
Keep the description professional and engaging."""
        response = self.model.generate_content([prompt, frame])
        return response.text

    async def _analyze_frames(self, frames):
        descriptions = []
        frames = frames[:self.MAX_FRAMES_PER_VIDEO]
        
        for frame in tqdm(frames, desc="Analyzing frames"):
            try:
                for attempt in range(self.MAX_API_RETRIES):
                    try:
                        await self.rate_limiter.wait()
                        description = await self._analyze_frame(frame)
                        if description:
                            descriptions.append(description)
                            break
                        await asyncio.sleep(2)
                    except Exception as e:
                        if "429" in str(e):
                            await asyncio.sleep(self.API_RETRY_DELAY * (attempt + 1))
                            continue
                        raise e
                        
            except Exception as e:
                logger.error(f"Error analyzing frame: {str(e)}")
                
            await asyncio.sleep(self.FRAME_ANALYSIS_DELAY)
        
        return descriptions

    @handle_rate_limit(max_tries=3, initial_wait=2)
    async def _generate_description(self, frame_descriptions, audio_transcription=""):
        await self.rate_limiter.wait()
        prompt = f"""Analyze this product video and provide detailed information in the following format exactly. If any value is not found, write N/A.

BEGIN_ANALYSIS
Product Name: [exact product name of visible product in video]
Category: [main category of visible product in video]
Subcategory: [sub category of visible product in video]
Platform: [platform where similar video is available, only name]
Duration: [Duration of video on that platform]
Views: [visible views of video on that platform]
Transcript Summary: [2-3 sentences about the product]
Price: [visible pricing information]
Key Timestamps: [visible timestamps information]
Visual Descriptions:
{chr(10).join(frame_descriptions)}
Highlights: 
- [highlight 1]
- [highlight 2]
- [highlight 3]
Key Features:
- [feature 1]
- [feature 2]
- [feature 3]
Search Keywords:
- [keyword 1]
- [keyword 2]
- [keyword 3]
Product links:
- [Product link 1, Price on that platform]
- [Product link 2, Price on that platform]
- [Product link 3, Price on that platform]
END_ANALYSIS"""
        
        response = self.model.generate_content(prompt)
        return response.text

    async def process_video(self, video_file):
        try:
            
            try:
                with tempfile.NamedTemporaryFile(delete=False, suffix=".mp4") as temp_video:
                    temp_video.write(await video_file.read())
                    temp_video_path = temp_video.name
                waveform, sr = await self._extract_audio(temp_video_path)
                audio_transcription = await self._transcribe_audio(waveform) if waveform is not None else ""
                
                frames = await self._extract_frames(temp_video_path)
                if not frames:
                    return {'status': 'error', 'message': 'Failed to extract frames from video'}
                
                frame_descriptions = await self._analyze_frames(frames)
                final_description = await self._generate_description(frame_descriptions, audio_transcription)
                analysis_dict = self._parse_analysis(final_description)
                analysis_dict['status'] = 'success'
                
                return analysis_dict
                
            finally:
                print("Video analyzed successfully")
                    
        except Exception as e:
            return {'status': 'error', 'message': str(e)}
        
    def _parse_analysis(self, text):
        """Parse the analysis text into structured format"""
        analysis_dict = {
            'product_name': "Not Available",
            'category': "Not Available",
            'subcategory': "Not Available",
            'price': "Not Available",
            'key_features': [],
            'search_keywords': [],
            'highlights': [],
            'key_timestamps': {},
            'product_links': [],
            'platform': "Not Available",
            'duration': "Not Available",
            'views': "Not Available",
            'transcript_summary': "Not Available",
        }

        try:
            # Extract only content between BEGIN_ANALYSIS and END_ANALYSIS
            if 'BEGIN_ANALYSIS' in text and 'END_ANALYSIS' in text:
                content = text.split('BEGIN_ANALYSIS')[-1].split('END_ANALYSIS')[0].strip()
            else:
                content = text.strip()

            lines = content.split('\n')
            current_section = None

            for line in lines:
                line = line.strip()
                if not line:
                    continue

                # Direct assignments for labeled fields
                if line.startswith('Product Name:'):
                    analysis_dict['product_name'] = line.split(':', 1)[1].strip()
                elif line.startswith('Category:'):
                    analysis_dict['category'] = line.split(':', 1)[1].strip()
                elif line.startswith('Subcategory:'):
                    analysis_dict['subcategory'] = line.split(':', 1)[1].strip()
                elif line.startswith('Platform:'):
                    analysis_dict['platform'] = line.split(':', 1)[1].strip()
                elif line.startswith('Duration:'):
                    analysis_dict['duration'] = line.split(':', 1)[1].strip()
                elif line.startswith('Views:'):
                    analysis_dict['views'] = line.split(':', 1)[1].strip()
                elif line.startswith('Transcript Summary:'):
                    analysis_dict['transcript_summary'] = line.split(':', 1)[1].strip()
                elif line.startswith('Price:'):
                    analysis_dict['price'] = line.split(':', 1)[1].strip()

                # Handle Sections Based on Headers
                elif line.startswith('Key Features:'):
                    current_section = 'features'
                elif line.startswith('Search Keywords:'):
                    current_section = 'keywords'
                elif line.startswith('Highlights:'):
                    current_section = 'highlights'
                elif line.startswith('Key Timestamps:'):
                    current_section = 'timestamps'
                elif line.startswith('Product links:'):
                    current_section = 'links'

                # Parse Lists
                elif line.startswith('- '):
                    item = line.strip('- ').strip()
                    if current_section == 'features':
                        analysis_dict['key_features'].append(item)
                    elif current_section == 'keywords':
                        analysis_dict['search_keywords'].append(item)
                    elif current_section == 'highlights':
                        analysis_dict['highlights'].append(item)
                    elif current_section == 'links':
                        # Parse links (e.g., '- [Product link 1, $29.99]')
                        if ',' in item:
                            link, price = item.rsplit(',', 1)
                            analysis_dict['product_links'].append({
                                "store": link.strip(),
                                "price": price.strip()
                            })
                        else:
                            analysis_dict['product_links'].append({
                                "store": item.strip(),
                                "price": "Not Available"
                            })

                # Parse Timestamps (e.g., '00:15: Intro scene')
                elif current_section == 'timestamps' and ':' in line:
                    timestamp, desc = line.split(':', 1)
                    analysis_dict['key_timestamps'][timestamp.strip()] = desc.strip()

            return analysis_dict

        except Exception as e:
            logger.error(f"Error parsing analysis: {str(e)}")
            return analysis_dict