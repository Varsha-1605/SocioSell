import google.generativeai as genai
from fastapi import FastAPI, Request, UploadFile, HTTPException, File, Form
from flask import request
from motor.motor_asyncio import AsyncIOMotorClient
import logging
import io
import os
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.responses import HTMLResponse, JSONResponse
from PIL import Image
from dotenv import load_dotenv
from time import time
from image_processor import ImageProcessor
from routers import image, video, combined
from pymongo import MongoClient
from pymongo.server_api import ServerApi


# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

app = FastAPI(
    title="Social Media Product Listing Generator")

# Load .env file
load_dotenv()

# MongoDB setup
MONGODB_URL = os.getenv("MONGODB_URL")
try:
    client = AsyncIOMotorClient(
        MONGODB_URL,
        maxPoolSize=20,
        minPoolSize=5,
        connectTimeoutMS=10000   
    )
    db = client.social_media_products
    logger.info("MongoDB client initialized with connection pooling")
except Exception as e:
    logger.error(f"Failed to initialize MongoDB client: {str(e)}")
    raise

# Image Collections
product_collection = db["products"]
listing_collection = db["listings"]
analytics_collection = db["analytics"]
review_collection = db["reviews"]
# Video Collections
video_collection = db["videos"]
video_listings_collection = db["video_listings"]
video_analytics_collection = db["video_analytics"]

# Static files and templates setup
app.mount("/static", StaticFiles(directory="static"), name="static")
templates = Jinja2Templates(directory="templates")

# Initialize Image Processor
image_processor = ImageProcessor()

# Include Routers
app.include_router(image.router, prefix="/upload/image", tags=["Image"])
app.include_router(video.router, prefix="/upload/video", tags=["Video"])
app.include_router(combined.router, prefix="/search/all", tags=["Combined"])


@app.get("/", response_class=HTMLResponse)
async def home(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})


@app.get("/health", tags=["Monitoring"])
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

    try:
        stats = await client.admin.command('serverStatus')
        connection_stats = stats.get('connections', {})
        logger.info(f"Connection Pool Stats: {connection_stats}")
    except Exception as pool_exception:
        logger.error(f"Failed to retrieve pool stats: {pool_exception}")


    return JSONResponse(
        content={
            "status": "healthy" if db_status == "connected" else "unhealthy",
            "db_status": db_status,
            "response_time_ms": response_time,
        },
        status_code=status_code,
    )


@app.get("/pool-stats", tags=["Monitoring"])
async def pool_stats():
    """
    Endpoint to retrieve and log MongoDB connection pool stats.
    """
    try:
        stats = await client.admin.command('serverStatus')
        connection_stats = stats.get('connections', {})
        logger.info(f"Connection Pool Stats: {connection_stats}")
        return JSONResponse(content={"pool_stats": connection_stats}, status_code=200)
    except Exception as e:
        logger.error(f"Error fetching pool stats: {e}")
        return JSONResponse(content={"error": str(e)}, status_code=500)


@app.post("/generate_listings")
async def generate_listings(request: Request, file: UploadFile = Form(...), productTitle: str = Form(...), caption: str = Form(None)):
    try:
        # Read the uploaded image file directly using file.file
        image = Image.open(file.file)

        # Call your product_listing function
        raw_response = await image_processor.product_listing(image=image, title=productTitle, caption=caption)

        if raw_response.get("status") == "error":
            raise HTTPException(status_code=500, detail=raw_response.get("message"))

            # Generate dynamic recommendations (you'll need to define this function elsewhere)
        recommendations = await generate_recommendations(raw_response)

        # Combine analysis and recommendations
        result = {**raw_response, "recommendations": recommendations}

        # Return the response based on client request
        accept_header = request.headers.get("accept", "").lower()
        if "application/json" in accept_header:
            return JSONResponse(content=result, status_code=200)
        else:
            return templates.TemplateResponse(
                "result.html",
                {"request": request, "result": result}
            )
    except Exception as e:
        logger.error(f"Error processing image: {str(e)}")
        return JSONResponse(
            content={"status": "error", "message": "Failed to process image"},
            status_code=500
        )



@app.post("/upload_image")
async def upload_image(request: Request, file: UploadFile):
    """
    Handle image upload, analyze the product, and generate personalized recommendations.
    """
    try:
        # Open the uploaded image
        image = Image.open(file.file)

        # Analyze the image using ImageProcessor
        raw_response = await image_processor.analyze_product(image)
        
        if raw_response.get("status") == "error":
            raise HTTPException(status_code=500, detail=raw_response.get("message"))

        # Generate dynamic recommendations
        recommendations = await generate_recommendations(raw_response)

        # Combine analysis and recommendations
        result = {**raw_response, "recommendations": recommendations}

        # Return the response based on client request
        accept_header = request.headers.get("accept", "").lower()
        if "application/json" in accept_header:
            return JSONResponse(content=result, status_code=200)
        else:
            return templates.TemplateResponse(
                "result.html",
                {"request": request, "result": result}
            )
    except Exception as e:
        logger.error(f"Error processing image: {str(e)}")
        return JSONResponse(
            content={"status": "error", "message": "Failed to process image"},
            status_code=500
        )


async def generate_recommendations(data):
    """
    Generate personalized recommendations based on the product's category and features using MongoDB.
    Ensures at least 3-5 recommendations.
    """
    try:
        # Establish MongoDB connection
        uri = os.getenv("MONGODB_URL")
        client = MongoClient(uri, server_api=ServerApi('1'))
        db = client.social_media_products
        product_collection = db["products"]

        category = data.get("category", None)
        subcategory = data.get("subcategory", None)
        key_features = data.get("key_features", [])

        if not category:
            logger.warning("No category provided for recommendation. Returning default response.")
            return [{"name": "No recommendations available", "price": "N/A", "url": "#"}]

        # Primary query: match category and at least one key feature
        primary_query = {
            "category": category,
            "subcategory": subcategory,
            "common_features": {"$in": key_features}
        }

        # Fallback query: match only the category if primary query has insufficient results
        fallback_query = {"category": category,
                          "subcategory": subcategory}

        # Fetch recommendations
        recommendations = list(product_collection.find(primary_query).limit(5))
        if len(recommendations) < 3:
            additional_recommendations = list(
                product_collection.find(fallback_query).limit(5 - len(recommendations))
            )
            recommendations.extend(additional_recommendations)

        # Format recommendations
        formatted_recommendations = [
            {
                "name": product.get("brand_options", ["Unknown Product"])[0],
                "price": product.get("price_ranges", {}).get("mid_range", {}).get("min", "N/A"),
                "features": product.get("common_features", []),
            }
            for product in recommendations
        ]

        # Return default if still insufficient recommendations
        if not formatted_recommendations:
            formatted_recommendations = [{"name": "No recommendations available", "price": "N/A", "url": "#"}]

        return formatted_recommendations

    except Exception as e:
        logger.error(f"Error generating recommendations: {str(e)}")
        return [{"name": "Error generating recommendations", "price": "N/A", "url": "#"}]
    finally:
        client.close()


# def _parse_recommendations(response_text):
#     """
#     Parse the raw response from GenAI and extract recommendations in structured format.
#     """
#     recommendations = []

#     try:
#         # Extract the text between BEGIN_RECOMMENDATIONS and END_RECOMMENDATIONS
#         if "BEGIN_RECOMMENDATIONS" in response_text and "END_RECOMMENDATIONS" in response_text:
#             content = response_text.split("BEGIN_RECOMMENDATIONS")[-1].split("END_RECOMMENDATIONS")[0].strip()
#         else:
#             content = response_text.strip()

#         # Process each line as a separate product recommendation
#         lines = content.split("\n")
#         for line in lines:
#             if line.strip().startswith("-"):
#                 # Parse product details from the line
#                 product_details = line.strip("- ").split(", ")
#                 if len(product_details) >= 2:
#                     recommendations.append({
#                         "name": product_details[0],
#                         "price": product_details[1],
#                         "url": "#",  # Placeholder for product URLs
#                         "description": ", ".join(product_details[2:]) if len(product_details) > 2 else "No description available."
#                     })

#         return recommendations

#     except Exception as e:
#         logger.error(f"Error parsing recommendations: {str(e)}")
#         return []


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="127.0.0.2", port=8002, reload=True)