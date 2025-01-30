from fastapi import APIRouter, File, UploadFile, Form
from typing import Optional, List
from fastapi import File, UploadFile, Form
from schemas.video import (
    upload_video,
    search_videos,
    get_video_listings,
    get_comparable_videos,
    get_video_analytics
)
import logging
from video_processor import VideoProcessor

logger = logging.getLogger(__name__)
router = APIRouter()
video_processor = VideoProcessor()
@router.post("/", 
    summary="Upload Product Video",
    description="Upload and analyze a product video for listing generation."
)
async def upload_video_route(
    files: List[UploadFile] = File(...),
    title: str = Form(...),
    caption: Optional[str] = Form(None)
):
    try:
        # Process first uploaded video
        video = files[0]
        
        # Save video temporarily 
        with open(f"temp_{video.filename}", "wb") as buffer:
            buffer.write(await video.read())
        
        # Analyze video using Gemini
        analysis = await video_processor.analyze_video(f"temp_{video.filename}")
        
        # If using existing upload_video schema function, pass the analysis
        return await upload_video(files, title, caption, analysis)
    
    except Exception as e:
        logger.error(f"Video upload error: {str(e)}")
        return {
            "status": "error",
            "message": str(e)
        }
@router.get("/search/{title}",
    summary="Search Videos",
    description="Search for product videos by title."
)
async def search_videos_route(title: str):
    return await search_videos(title)

@router.get("/listings/{video_id}",
    summary="Get Video Listings",
    description="Get all listings and platforms for a specific video."
)
async def get_video_listings_route(video_id: str):
    return await get_video_listings(video_id)

@router.get("/compare/{video_id}",
    summary="Get Comparable Videos",
    description="Get comparable videos for comparison."
)
async def get_comparable_videos_route(video_id: str, limit: int = 3):
    return await get_comparable_videos(video_id, limit)

@router.get("/analytics/{video_id}",
    summary="Get Video Analytics",
    description="Get detailed analytics for a specific video."
)
async def get_video_analytics_route(video_id: str):
    return await get_video_analytics(video_id)