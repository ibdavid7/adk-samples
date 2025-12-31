
import os
from google.cloud import aiplatform

PROJECT_ID = os.getenv("GOOGLE_CLOUD_PROJECT")
LOCATION = "us-central1"

aiplatform.init(project=PROJECT_ID, location=LOCATION)

print(f"Listing Publisher Models in {LOCATION}...")

# Publisher models are resources.
# We can try to list them using the API directly or the SDK.
# The SDK has `aiplatform.Model.list`, but that lists *user* models.
# Publisher models are usually accessed via `aiplatform.get_publisher_model` or similar, 
# but listing them is tricky in the SDK.

# Let's try to use the gapic client to list publisher models.
from google.cloud import aiplatform_v1

def list_publisher_models():
    client = aiplatform_v1.ModelGardenServiceClient(
        client_options={"api_endpoint": f"{LOCATION}-aiplatform.googleapis.com"}
    )
    parent = f"projects/{PROJECT_ID}/locations/{LOCATION}/publishers/google"
    
    print(f"Querying {parent}...")
    try:
        # Note: The method is list_publisher_models
        request = aiplatform_v1.ListPublisherModelsRequest(parent=parent)
        response = client.list_publisher_models(request=request)
        
        found_gemini = False
        for model in response:
            if "gemini" in model.name.lower():
                print(f"Found: {model.name} ({model.version_id})")
                found_gemini = True
        
        if not found_gemini:
            print("No Gemini models found in the publisher list (this is unexpected).")
            
    except Exception as e:
        print(f"Error listing publisher models: {e}")

if __name__ == "__main__":
    list_publisher_models()
