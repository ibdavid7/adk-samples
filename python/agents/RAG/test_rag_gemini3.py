from vertexai.preview import rag
from vertexai.generative_models import GenerativeModel, Tool
import vertexai
import os
from dotenv import load_dotenv

load_dotenv()

PROJECT_ID = os.getenv("GOOGLE_CLOUD_PROJECT")
# The model is in us-central1
LOCATION = "us-east4" 
# The corpus is in us-west1
RAG_CORPUS_ID = os.getenv("RAG_CORPUS")

print(f"Project: {PROJECT_ID}")
print(f"Location: {LOCATION}")
print(f"Corpus: {RAG_CORPUS_ID}")

# Initialize Vertex AI API
vertexai.init(project=PROJECT_ID, location=LOCATION)

# Direct context retrieval config
rag_retrieval_config = rag.RagRetrievalConfig(
    top_k=3,
    filter=rag.Filter(vector_distance_threshold=0.5),
)

# Create a RAG retrieval tool
# Note: We are referencing a corpus in us-west1 from a client in us-central1.
# This should work if the resource ID is full.
rag_retrieval_tool = Tool.from_retrieval(
    retrieval=rag.Retrieval(
        source=rag.VertexRagStore(
            rag_resources=[
                rag.RagResource(
                    rag_corpus=RAG_CORPUS_ID
                )
            ],
            rag_retrieval_config=rag_retrieval_config,
        ),
    )
)

# Create a Gemini model instance
# Trying the exact name listed in the previous step
model_name = "gemini-3-pro-preview" 

print(f"Initializing model: {model_name}")
try:
    rag_model = GenerativeModel(
        model_name=model_name, 
        tools=[rag_retrieval_tool]
    )

    # Generate response
    print("Generating content...")
    response = rag_model.generate_content("What is the code for a psychiatric diagnostic evaluation?")
    print("Response received:")
    print(response.text)

except Exception as e:
    print(f"Error: {e}")
