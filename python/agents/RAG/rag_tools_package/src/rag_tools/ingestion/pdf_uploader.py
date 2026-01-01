from google.auth import default
from google.api_core.exceptions import ResourceExhausted
import vertexai
from vertexai.preview import rag
import os
import requests
import tempfile
from ..config import PROJECT_ID, LOCATION

class PDFUploader:
    def __init__(self, corpus_display_name="RAG_Corpus", corpus_description="RAG Corpus"):
        self.corpus_display_name = corpus_display_name
        self.corpus_description = corpus_description
        self.initialize_vertex_ai()

    def initialize_vertex_ai(self):
        credentials, _ = default()
        vertexai.init(
            project=PROJECT_ID, location=LOCATION, credentials=credentials
        )

    def create_corpus(self):
        # Check if corpus exists
        # Note: This is a simplified check. In production, you might want to list corpora and match by name.
        # For now, we try to create and catch duplication errors if the API throws them, 
        # or just create a new one every time (which is the default behavior of create_corpus).
        print(f"Creating RAG Corpus: {self.corpus_display_name}")
        corpus = rag.create_corpus(
            display_name=self.corpus_display_name,
            description=self.corpus_description,
        )
        print(f"Corpus created: {corpus.name}")
        return corpus

    def upload_file(self, corpus_name, file_path, display_name=None):
        print(f"Uploading {file_path} to {corpus_name}...")
        try:
            rag_file = rag.upload_file(
                corpus_name=corpus_name,
                path=file_path,
                display_name=display_name or os.path.basename(file_path),
                description="Uploaded via RAG Tools"
            )
            print(f"File uploaded successfully: {rag_file.name}")
            return rag_file
        except Exception as e:
            print(f"Error uploading file: {e}")
            return None

    def upload_from_url(self, corpus_name, url, filename):
        print(f"Downloading {url}...")
        response = requests.get(url)
        if response.status_code == 200:
            with tempfile.TemporaryDirectory() as temp_dir:
                file_path = os.path.join(temp_dir, filename)
                with open(file_path, "wb") as f:
                    f.write(response.content)
                return self.upload_file(corpus_name, file_path)
        else:
            print(f"Failed to download file: Status {response.status_code}")
            return None
