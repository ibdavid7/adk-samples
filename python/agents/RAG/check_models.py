
import os
from google import genai
from dotenv import load_dotenv

load_dotenv()

PROJECT_ID = os.getenv("GOOGLE_CLOUD_PROJECT")
LOCATION = "us-central1"

client = genai.Client(
    vertexai=True,
    project=PROJECT_ID,
    location=LOCATION
)

print(f"Listing models in {PROJECT_ID} / {LOCATION}...")
try:
    # The SDK might not have a direct list_models for Vertex in the same way, 
    # but let's try the standard list method if available or just try to invoke a few common ones.
    # Actually, the genai SDK usually has models.list()
    
    # Note: The google-genai SDK structure might differ slightly, but let's try the standard pattern.
    # If this fails, we'll know.
    
    # For Vertex AI, we often use the vertexai SDK to list models, but let's see if genai client supports it.
    # If not, I'll use vertexai SDK.
    pass
except Exception as e:
    print(e)

# Let's try using vertexai SDK directly to list models as it is more standard for this.
import vertexai
from vertexai.preview import generative_models

vertexai.init(project=PROJECT_ID, location=LOCATION)

print("Checking common model names...")
candidates = [
    "gemini-2.5-pro",
    "gemini-2.5-pro-001",
    "gemini-2.5-flash"
]

for model_id in candidates:
    try:
        model = generative_models.GenerativeModel(model_id)
        # Just trying to instantiate doesn't always fail, need to try a dummy generation or check existence
        # But listing is better.
        print(f"Checking {model_id}...", end=" ")
        response = model.generate_content("Hello", stream=False)
        print("OK")
    except Exception as e:
        if "404" in str(e):
            print("NOT FOUND")
        else:
            print(f"Error: {e}")

