import google.generativeai as genai
import os
from dotenv import load_dotenv
import logging
from PIL import Image

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class ImageProcessor:
    def __init__(self):
        load_dotenv()
        api_key = os.getenv('GOOGLE_API_KEY')
        if not api_key:
            raise ValueError("GOOGLE_API_KEY not found in environment variables")
        
        genai.configure(api_key=api_key)
        self.model = genai.GenerativeModel("gemini-1.5-pro-latest")

    async def product_listing(self, image: Image.Image, title: str, caption: str):
        """Analyze product image and return structured data"""
        try:
            analysis_prompt = [
                """Analyze this product image and provide detailed information in the following format exactly:

    BEGIN_ANALYSIS
    Product Name: [exact product name]
    Category: [main category]
    Subcategory: [sub category]
    Description: [2-3 sentences about the product]
    Price: [visible pricing information]
    Key Features:
    - [feature 1]
    - [feature 2]
    - [feature 3]
    Search Keywords:
    - [keyword 1]
    - [keyword 2]
    - [keyword 3]
    END_ANALYSIS""",
                image,
                title,
                caption
            ]

            response = self.model.generate_content(analysis_prompt)
            analysis_dict = self._parse_analysis(response.text)
            analysis_dict['status'] = 'success'

            return analysis_dict

        except Exception as e:
            logger.error(f"Error in analyze_product: {str(e)}")
            return {
                'status': 'error',
                'message': str(e)
            }

    async def analyze_product(self, image: Image.Image):
        """Analyze product image and return structured data"""
        try:
            analysis_prompt = [
                """Analyze this product image and provide detailed information in the following format exactly:

BEGIN_ANALYSIS
Product Name: [exact product name]
Category: [main category]
Subcategory: [sub category]
Description: [2-3 sentences about the product]
Price: [visible pricing information]
Key Features:
- [feature 1]
- [feature 2]
- [feature 3]
Search Keywords:
- [keyword 1]
- [keyword 2]
- [keyword 3]
END_ANALYSIS""",
                image
            ]

            response = self.model.generate_content(analysis_prompt)
            analysis_dict = self._parse_analysis(response.text)
            analysis_dict['status'] = 'success'

            return analysis_dict

        except Exception as e:
            logger.error(f"Error in analyze_product: {str(e)}")
            return {
                'status': 'error',
                'message': str(e)
            }

    def _parse_analysis(self, text):
        """Parse the analysis text into structured format"""
        analysis_dict = {
            'product_name': '',
            'category': '',
            'subcategory': '',
            'description': '',
            'price': '',
            'key_features': [],
            'search_keywords': []
        }

        try:
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

                if line.startswith('Product Name:'):
                    analysis_dict['product_name'] = line.split(':', 1)[1].strip()
                elif line.startswith('Category:'):
                    analysis_dict['category'] = line.split(':', 1)[1].strip()
                elif line.startswith('Subcategory:'):
                    analysis_dict['subcategory'] = line.split(':', 1)[1].strip()
                elif line.startswith('Description:'):
                    analysis_dict['description'] = line.split(':', 1)[1].strip()
                elif line.startswith('Price:'):
                    analysis_dict['price'] = line.split(':', 1)[1].strip()
                elif line.startswith('Key Features:'):
                    current_section = 'features'
                elif line.startswith('Search Keywords:'):
                    current_section = 'keywords'
                elif line.startswith('- '):
                    if current_section == 'features':
                        analysis_dict['key_features'].append(line.strip('- '))
                    elif current_section == 'keywords':
                        analysis_dict['search_keywords'].append(line.strip('- '))

            return analysis_dict

        except Exception as e:
            logger.error(f"Error parsing analysis: {str(e)}")
            return analysis_dict

