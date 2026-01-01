import os
from dotenv import load_dotenv

# Load environment variables from .env file
# We assume the .env file is in the root of the project or passed explicitly
load_dotenv()

PROJECT_ID = os.getenv("GOOGLE_CLOUD_PROJECT")
LOCATION = os.getenv("GOOGLE_CLOUD_LOCATION", "us-central1")
MODEL_ID = os.getenv("MODEL_ID", "gemini-2.5-pro")

if not PROJECT_ID:
    # Warn or raise, but for a library, maybe just warn
    print("Warning: GOOGLE_CLOUD_PROJECT not set in environment.")
