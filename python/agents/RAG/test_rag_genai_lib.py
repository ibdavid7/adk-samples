from google import genai
from google.genai import types
import os
from dotenv import load_dotenv

load_dotenv()

PROJECT_ID = os.getenv("GOOGLE_CLOUD_PROJECT")
LOCATION = "us-central1"
RAG_CORPUS_ID = os.getenv("RAG_CORPUS")

print(f"Using google-genai library")
print(f"Project: {PROJECT_ID}")
print(f"Location: {LOCATION}")
print(f"Corpus: {RAG_CORPUS_ID}")

client = genai.Client(
    vertexai=True,
    project=PROJECT_ID,
    location=LOCATION
)

# Define the tool
rag_tool = types.Tool(
    retrieval=types.Retrieval(
        vertex_rag_store=types.VertexRagStore(
            rag_corpora=[RAG_CORPUS_ID],
            vector_distance_threshold=0.5,
        )
    )
)

model_name = "gemini-3.0-pro-preview"

print(f"Generating with {model_name}...")
try:
    response = client.models.generate_content(
        model=model_name,
        contents="What is the code for a psychiatric diagnostic evaluation?",
        config=types.GenerateContentConfig(
            tools=[rag_tool]
        )
    )
    print("Response received:")
    print(response.text)
except Exception as e:
    print(f"Error: {e}")
