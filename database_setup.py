from pymongo import MongoClient, ASCENDING
from pymongo.server_api import ServerApi
import logging
from datetime import datetime
import os
from dotenv import load_dotenv

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def setup_product_database():
    """Setup product reference database with sample data"""
    load_dotenv()
    uri = os.getenv("MONGODB_URL")
    
    try:
        client = MongoClient(uri, server_api=ServerApi('1'))
        db = client.social_media_products
        
        # Create collections
        product_references = db.product_references
        listings = db.listings
        
        # Create indexes
        product_references.create_index([("category", ASCENDING)])
        product_references.create_index([("subcategory", ASCENDING)])
        product_references.create_index([("keywords", ASCENDING)])
        product_references.create_index([("brand_options", ASCENDING)])
        
        listings.create_index([("product_id", ASCENDING)])
        listings.create_index([("created_at", ASCENDING)])
        
        # Sample product reference data
        sample_products = [
            {
                "category": "Electronics",
                "subcategory": "Smartphones",
                "brand_options": ["Samsung Galaxy S24", "iPhone 15", "Google Pixel 8"],
                "price_ranges": {
                    "budget": {"min": 299, "max": 499},
                    "mid_range": {"min": 500, "max": 799},
                    "premium": {"min": 800, "max": 1299}
                },
                "common_features": [
                    "5G Connectivity",
                    "AI-Enhanced Camera",
                    "AMOLED Display",
                    "Fast Charging",
                    "Wireless Charging"
                ],
                "keywords": ["smartphone", "mobile phone", "cell phone", "android", "ios"]
            },
            {
                "category": "Electronics",
                "subcategory": "Wireless Earbuds",
                "brand_options": ["Apple AirPods Pro", "Samsung Galaxy Buds", "Google Pixel Buds"],
                "price_ranges": {
                    "budget": {"min": 49, "max": 99},
                    "mid_range": {"min": 100, "max": 199},
                    "premium": {"min": 200, "max": 299}
                },
                "common_features": [
                    "Active Noise Cancellation",
                    "Touch Controls",
                    "Wireless Charging Case",
                    "Water Resistance",
                    "Voice Assistant Support"
                ],
                "keywords": ["earbuds", "wireless earphones", "tws", "headphones"]
            },
            {
                "category": "Electronics",
                "subcategory": "Smartwatches",
                "brand_options": ["Apple Watch Series 9", "Samsung Galaxy Watch 6", "Google Pixel Watch"],
                "price_ranges": {
                    "budget": {"min": 149, "max": 249},
                    "mid_range": {"min": 250, "max": 399},
                    "premium": {"min": 400, "max": 799}
                },
                "common_features": [
                    "Health Monitoring",
                    "Fitness Tracking",
                    "GPS",
                    "Always-On Display",
                    "Water Resistance"
                ],
                "keywords": ["smartwatch", "fitness tracker", "smart watch", "wearable"]
            }
        ]
        
        # Clear existing data
        product_references.delete_many({})
        listings.delete_many({})
        
        # Insert sample data
        product_references.insert_many(sample_products)
        logger.info("Sample product references inserted successfully")
        
        # Insert sample listings
        sample_listings = [
            {
                "product_id": str(product_references.find_one({"brand_options": "iPhone 15"})["_id"]),
                "title": "iPhone 15 Pro Max",
                "category": "Electronics",
                "subcategory": "Smartphones",
                "description": "Latest iPhone with A17 Pro chip and titanium design",
                "price": "$999",
                "features": [
                    "48MP Main Camera",
                    "Titanium Design",
                    "Action Button"
                ],
                "keywords": ["iphone", "smartphone", "apple"],
                "original_caption": "Just got the new iPhone 15 Pro! Amazing camera system!",
                "created_at": datetime.utcnow(),
                "status": "active"
            }
        ]
        
        listings.insert_many(sample_listings)
        logger.info("Sample listings inserted successfully")
        
    except Exception as e:
        logger.error(f"Error setting up database: {e}")
    finally:
        client.close()

if __name__ == "__main__":
    setup_product_database()