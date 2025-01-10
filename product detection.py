pip install google-cloud-vision

export GOOGLE_APPLICATION_CREDENTIALS="path/to/your/service-account-file.json"

from google.cloud import vision
from google.cloud.vision import types
import io

# Initialize a Vision API client
client = vision.ImageAnnotatorClient()

def detect_product(image_path):
    """Detects labels (products) in the image and outputs the confidence score."""
    # Load the image into memory
    with io.open(image_path, 'rb') as image_file:
        content = image_file.read()

    # Create an image object from the file content
    image = types.Image(content=content)

    # Perform label detection on the image
    response = client.label_detection(image=image)
    labels = response.label_annotations

    # Print the detected labels and their confidence scores
    print("Detected Products and Confidence Scores:")
    
    # Iterate over the results and display label and confidence
    for label in labels:
        print(f"Product: {label.description}, Confidence: {label.score:.2f}")

    # Handle potential errors
    if response.error.message:
        raise Exception(f"Error during detection: {response.error.message}")

    return labels

# Example usage
image_path = 'path_to_your_image.jpg'  # Replace with the path to your product image
labels = detect_product(image_path)

