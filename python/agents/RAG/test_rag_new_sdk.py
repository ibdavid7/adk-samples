from google import genai
from google.genai import types
import os
from dotenv import load_dotenv

load_dotenv()

PROJECT_ID = os.getenv("GOOGLE_CLOUD_PROJECT")
LOCATION = "us-central1" # Model location
RAG_CORPUS_ID = os.getenv("RAG_CORPUS") # Full resource name (in us-west1)

print(f"Using google-genai SDK")
print(f"Project: {PROJECT_ID}")
print(f"Location: {LOCATION}")
print(f"Corpus: {RAG_CORPUS_ID}")

client = genai.Client(
    vertexai=True,
    project=PROJECT_ID,
    location=LOCATION
)

# Configure RAG Tool
rag_tool = types.Tool(
    retrieval=types.Retrieval(
        vertex_rag_store=types.VertexRagStore(
            rag_corpora=[RAG_CORPUS_ID],
            vector_distance_threshold=0.5,
        )
    )
)

# Try Gemini 2.5 Pro first
model_id = "gemini-2.5-pro"

print(f"\nAttempting to generate with {model_id}...")

try:
    response = client.models.generate_content(
        model=model_id,
        contents="What is the code for a psychiatric diagnostic evaluation?",
        config=types.GenerateContentConfig(
            tools=[rag_tool],
            response_mime_type="application/json" 
        )
    )
    print("Response received:")
    print(response.text)

except Exception as e:
    print(f"Error with {model_id}: {e}")
    
    # Fallback to Gemini 2.0 Flash
    fallback_model = "gemini-2.0-flash-001"
    print(f"\nFalling back to {fallback_model}...")
    try:
        response = client.models.generate_content(
            model=fallback_model,
            contents="What is the code for a psychiatric diagnostic evaluation?",
            config=types.GenerateContentConfig(
                tools=[rag_tool]
            )
        )
        print("Response received:")
        print(response.text)
    except Exception as e2:
        print(f"Error with {fallback_model}: {e2}")
