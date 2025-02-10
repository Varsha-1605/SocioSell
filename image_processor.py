import google.generativeai as genai
import os
from dotenv import load_dotenv
import logging
from PIL import Image
import json

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
    
    async def analyze_product(self, image: Image.Image):
        """Analyze product image and return structured data with recommendations"""
        try:
            analysis_prompt = [
                """Analyze this product image. Provide a detailed analysis and 5 product recommendations following this exact format:

BEGIN_ANALYSIS
Product Name: [exact product name]
Category: [main category]
Subcategory: [sub category]
Description: [2-3 sentences about the product]
Price Range: [estimated price range]
Key Features:
- [feature 1]
- [feature 2]
- [feature 3]

Recommendations:
1. [Product 1 Name]
   - Price: [Price]
   - Key Similarities: [2-3 key matching features]
2. [Product 2 Name]
   - Price: [Price]
   - Key Similarities: [2-3 key matching features]
3. [Product 3 Name]
   - Price: [Price]
   - Key Similarities: [2-3 key matching features]
4. [Product 4 Name]
   - Price: [Price]
   - Key Similarities: [2-3 key matching features]
5. [Product 5 Name]
   - Price: [Price]
   - Key Similarities: [2-3 key matching features]
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
            'price_range': '',
            'key_features': [],
            'recommendations': []
        }
        
        try:
            if 'BEGIN_ANALYSIS' in text and 'END_ANALYSIS' in text:
                content = text.split('BEGIN_ANALYSIS')[-1].split('END_ANALYSIS')[0].strip()
            else:
                content = text.strip()
            
            lines = content.split('\n')
            current_section = None
            recommendation_index = 0
            
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
                elif line.startswith('Price Range:'):
                    analysis_dict['price_range'] = line.split(':', 1)[1].strip()
                elif line.startswith('Key Features:'):
                    current_section = 'features'
                elif line.startswith('Recommendations:'):
                    current_section = 'recommendations'
                    recommendation_index = 0
                elif line.startswith('1.') or line.startswith('2.') or line.startswith('3.') or line.startswith('4.') or line.startswith('5.'):
                    recommendation_index += 1
                    current_recommendation = {'name': line.split('.', 1)[1].strip()}
                    analysis_dict['recommendations'].append(current_recommendation)
                elif line.startswith('- Price:') and current_section == 'recommendations':
                    analysis_dict['recommendations'][recommendation_index-1]['price'] = line.split(':', 1)[1].strip()
                elif line.startswith('- Key Similarities:') and current_section == 'recommendations':
                    analysis_dict['recommendations'][recommendation_index-1]['similarities'] = line.split(':', 1)[1].strip()
                elif line.startswith('- '):
                    if current_section == 'features':
                        analysis_dict['key_features'].append(line.strip('- '))
            
            return analysis_dict
            
        except Exception as e:
            logger.error(f"Error parsing analysis: {str(e)}")
            return analysis_dict