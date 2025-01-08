

from fastapi import FastAPI, Request
from motor.motor_asyncio import AsyncIOMotorClient
import logging
import os
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.responses import HTMLResponse, JSONResponse
from routers import image, video, combined
from dotenv import load_dotenv
from time import time

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

app = FastAPI(
    title="Social Media Product Listing Generator",
    description="""
    Product listing generator supporting both images and videos.
    
    Sample testing guide:
    
    1. Image Upload (/upload/):
       Categories:
       - Electronics: "Sony WH-1000XM4 Headphones"
       - Fashion: "Nike Air Max 270"
       - Home Decor: "Scandinavian Floor Lamp"
       
    2. Video Upload (/upload/video/):
       Categories:
       - Electronics: "iPhone 15 Review", "MacBook Pro Review"
       - Fashion: "Nike Collection", "Adidas Shoes"
       - Beauty: "Makeup Tutorial", "Skincare Routine"
    """
)

# Load .env file
load_dotenv()

# MongoDB setup
MONGODB_URL = os.getenv("MONGODB_URL")
client = AsyncIOMotorClient(MONGODB_URL)
db = client.social_media_products

# Image Collections
product_collection = db["products"]
listing_collection = db["listings"]
analytics_collection = db["analytics"]
review_collection = db["reviews"]
# Video Collections
video_collection = db["videos"]
video_listings_collection = db["video_listings"]
video_analytics_collection = db["video_analytics"]

# Include Routers
app.include_router(image.router, prefix="/upload/image", tags=["Image"])
app.include_router(video.router, prefix="/upload/video", tags=["Video"])
app.include_router(combined.router, prefix="/search/all", tags=["Combined"])

# Static files and templates setup
app.mount("/static", StaticFiles(directory="static"), name="static")
templates = Jinja2Templates(directory="templates")

@app.get("/", response_class=HTMLResponse)
async def home(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})

@app.get("/health",tags=["Monitoring"])
async def health_check():
    """
        Health check endpoint to monitor MongoDB connection and response time.
    """

    start_time = time()
    try:
        await db.command("ping")
        db_status = "connected"
    except Exception as e:
        db_status = f"disconnected: {str(e)}"

    response_time = round((time() - start_time) * 1000, 2)
    status_code = 200 if db_status == "connected" else 500

    # Log status
    logger.info(f"Health Check: DB status - {db_status}, Response Time - {response_time}ms")

    return JSONResponse(
        content={
            "status": "healthy" if db_status == "connected" else "unhealthy",
            "db_status": db_status,
            "response_time_ms": response_time
        },
        status_code=status_code
    )

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="127.0.0.2", port=8002, reload=True)