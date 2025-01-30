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
from dotenv import load_dotenv
from typing import Optional

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
    def __init__(self):
        load_dotenv()
        self.api_key = os.getenv('GOOGLE_API_KEY')
        self.rate_limiter = TokenBucket(tokens_per_second=0.05)
        
        genai.configure(api_key= os.getenv('GOOGLE_API_KEY'))
        self.model = genai.GenerativeModel('gemini-1.5-pro-latest')
        
        self.ffmpeg_path = r"C:/ProgramData/chocolatey/lib/ffmpeg/tools/ffmpeg/bin/ffmpeg.exe"
        if not os.path.exists(self.ffmpeg_path):
            raise RuntimeError(f"FFmpeg not found at: {self.ffmpeg_path}")
        self.ffmpeg_path = "ffmpeg"  
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
        prompt = f"""Based on the following frame descriptions and audio transcription, create a comprehensive 
e-commerce product description:

Visual Descriptions:
{chr(10).join(frame_descriptions)}

Audio Transcription:
{audio_transcription}

Please provide a well-structured description that includes:
1. Product overview
2. Key features and benefits
3. Technical specifications
4. Recommended uses
5. Notable information from the audio narration"""
        
        response = self.model.generate_content(prompt)
        return response.text

    async def process_video(self, video_url):
        try:
            video_path = await self.download_video(video_url)
            if not video_path:
                return {'status': 'error', 'message': 'Failed to download video'}
            
            try:
                waveform, sr = await self._extract_audio(video_path)
                audio_transcription = await self._transcribe_audio(waveform) if waveform is not None else ""
                
                frames = await self._extract_frames(video_path)
                if not frames:
                    return {'status': 'error', 'message': 'Failed to extract frames from video'}
                
                frame_descriptions = await self._analyze_frames(frames)
                final_description = await self._generate_description(frame_descriptions, audio_transcription)
                
                return {
                    'status': 'success',
                    'frame_descriptions': frame_descriptions,
                    'audio_transcription': audio_transcription,
                    'final_description': final_description
                }
                
            finally:
                if os.path.exists(str(video_path)):
                    os.remove(str(video_path))
                    
        except Exception as e:
            return {'status': 'error', 'message': str(e)}

    async def analyze_video(self, video_path: str, thumbnail_image: Optional[bytes] = None):
        """Analyze video content and generate recommendations"""
        try:
            # Prepare analysis prompt
            analysis_prompt = f"""Analyze the video/thumbnail and provide detailed product recommendations. 
            Format your response exactly like this:

BEGIN_ANALYSIS
Video Product: [main product or theme in the video]
Category: [main category]
Description: [2-3 sentence description of the product/video theme]

Recommendations:
1. [Product 1 Name]
   - Price: [Price]
   - Key Similarities: [2-3 matching features]
2. [Product 2 Name]
   - Price: [Price]
   - Key Similarities: [2-3 matching features]
3. [Product 3 Name]
   - Price: [Price]
   - Key Similarities: [2-3 matching features]
4. [Product 4 Name]
   - Price: [Price]
   - Key Similarities: [2-3 matching features]
5. [Product 5 Name]
   - Price: [Price]
   - Key Similarities: [2-3 matching features]
END_ANALYSIS"""

            # Prepare inputs
            inputs = [analysis_prompt]
            if thumbnail_image:
                inputs.append(thumbnail_image)

            # Generate content
            response = self.model.generate_content(inputs)
            analysis_dict = self._parse_analysis(response.text)
            analysis_dict['status'] = 'success'
            
            return analysis_dict
            
        except Exception as e:
            logger.error(f"Error in analyze_video: {str(e)}")
            return {
                'status': 'error',
                'message': str(e)
            }
    
    def _parse_analysis(self, text):
        """Parse the analysis text into structured format"""
        # Use similar parsing logic as in ImageProcessor
        analysis_dict = {
            'video_product': '',
            'category': '',
            'description': '',
            'recommendations': []
        }
        
        # Implement similar parsing logic as in image_processor.py
        # This method would extract recommendations and details 
        # using similar techniques to the ImageProcessor
        
        return analysis_dict