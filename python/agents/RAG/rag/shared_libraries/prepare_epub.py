# Copyright 2025 Google LLC
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import os
import zipfile
from bs4 import BeautifulSoup
from google.auth import default
import vertexai
from vertexai.preview import rag
from dotenv import load_dotenv, set_key
import tempfile

# Load environment variables
load_dotenv()

PROJECT_ID = os.getenv("GOOGLE_CLOUD_PROJECT")
LOCATION = os.getenv("GOOGLE_CLOUD_LOCATION")
CORPUS_DISPLAY_NAME = "CPT_Professional_2024_Corpus"
CORPUS_DESCRIPTION = "Corpus containing CPT Professional 2024 EPUB content"
ENV_FILE_PATH = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", ".env"))

def initialize_vertex_ai():
    credentials, _ = default()
    vertexai.init(project=PROJECT_ID, location=LOCATION, credentials=credentials)

def create_or_get_corpus():
    """Creates a new corpus or retrieves an existing one."""
    embedding_model_config = rag.EmbeddingModelConfig(
        publisher_model="publishers/google/models/text-embedding-004"
    )
    existing_corpora = rag.list_corpora()
    corpus = None
    for existing_corpus in existing_corpora:
        if existing_corpus.display_name == CORPUS_DISPLAY_NAME:
            corpus = existing_corpus
            print(f"Found existing corpus: {CORPUS_DISPLAY_NAME}")
            break
    if corpus is None:
        corpus = rag.create_corpus(
            display_name=CORPUS_DISPLAY_NAME,
            description=CORPUS_DESCRIPTION,
            embedding_model_config=embedding_model_config,
        )
        print(f"Created new corpus: {CORPUS_DISPLAY_NAME}")
    return corpus

def epub_to_markdown(epub_path, limit=None):
    """
    Converts an EPUB file to a single Markdown string, preserving indentation.
    Args:
        epub_path: Path to the EPUB file.
        limit: Optional integer to limit the number of chapters/sections processed.
    """
    markdown_output = ""
    
    with zipfile.ZipFile(epub_path, 'r') as z:
        # Find the OPF file to get the reading order (spine)
        try:
            container_xml = z.read('META-INF/container.xml')
            soup_container = BeautifulSoup(container_xml, 'xml')
            rootfile = soup_container.find('rootfile')
            if not rootfile:
                print("Error: Could not find rootfile in container.xml")
                return ""
            opf_path = rootfile['full-path']
            
            opf_content = z.read(opf_path)
            soup_opf = BeautifulSoup(opf_content, 'xml')
        except Exception as e:
            print(f"Error reading OPF: {e}")
            return ""
        
        # Get the manifest (id -> href)
        manifest = {}
        for item in soup_opf.find_all('item'):
            manifest[item['id']] = item['href']
            
        # Iterate through the spine to process files in order
        spine = soup_opf.find('spine')
        opf_dir = os.path.dirname(opf_path)
        
        count = 0
        for itemref in spine.find_all('itemref'):
            if limit and count >= limit:
                print(f"Reached limit of {limit} sections. Stopping.")
                break
                
            item_id = itemref['idref']
            href = manifest.get(item_id)
            
            if href:
                # Resolve relative path inside the zip
                full_path = os.path.join(opf_dir, href) if opf_dir else href
                
                try:
                    html_content = z.read(full_path).decode('utf-8')
                    soup = BeautifulSoup(html_content, 'html.parser')
                    
                    # Iterate over divs and ps with specific classes
                    # We use a recursive search but filter for specific "content" classes
                    # to avoid duplicating text from container divs.
                    
                    for element in soup.find_all(['div', 'p']):
                        text = element.get_text(strip=True)
                        if not text:
                            continue
                            
                        classes = element.get('class', [])
                        
                        # Map classes to Markdown
                        if 'h1' in classes:
                            markdown_output += f"# {text}\n\n"
                        elif 'h2' in classes:
                            markdown_output += f"## {text}\n\n"
                        elif 'h3' in classes:
                            markdown_output += f"### {text}\n\n"
                        elif 'h4' in classes:
                            markdown_output += f"#### {text}\n\n"
                        elif 'noindent' in classes:
                            markdown_output += f"{text}\n\n"
                        elif 'nlist' in classes:
                            markdown_output += f"{text}\n\n"
                        elif any(c.startswith('table-para') for c in classes):
                            markdown_output += f"> {text}\n\n"
                        elif element.name == 'p':
                            markdown_output += f"{text}\n\n"
                    
                    count += 1

                except KeyError:
                    print(f"Warning: Could not find file {full_path} in archive.")
                except Exception as e:
                    print(f"Error processing {full_path}: {e}")
                    
    return markdown_output

def upload_text_to_corpus(corpus_name, text_content, display_name):
    """Uploads text content as a file to the corpus."""
    # Vertex RAG accepts local files. We'll write the markdown to a temp file.
    with tempfile.NamedTemporaryFile(mode='w+', suffix='.md', delete=False) as temp_file:
        temp_file.write(text_content)
        temp_file_path = temp_file.name
        
    print(f"Uploading {display_name} to corpus...")
    try:
        rag.upload_file(
            corpus_name=corpus_name,
            path=temp_file_path,
            display_name=display_name,
            description="CPT 2024 Markdown Content"
        )
        print(f"Successfully uploaded {display_name}")
    except Exception as e:
        print(f"Error uploading file: {e}")
    finally:
        os.remove(temp_file_path)

def update_env_file(corpus_name, env_file_path):
    try:
        set_key(env_file_path, "RAG_CORPUS", corpus_name)
        print(f"Updated RAG_CORPUS in {env_file_path} to {corpus_name}")
    except Exception as e:
        print(f"Error updating .env file: {e}")

def main():
    # --- Configuration ---
    # Set this to your local EPUB file path
    LOCAL_EPUB_PATH = "/workspaces/adk-samples/python/agents/RAG/source/CPT Professional 2024 American Medical Association.epub"
    
    if not os.path.exists(LOCAL_EPUB_PATH):
        print(f"Please set LOCAL_EPUB_PATH to a valid file. Current: {LOCAL_EPUB_PATH}")
        return

    initialize_vertex_ai()
    corpus = create_or_get_corpus()
    update_env_file(corpus.name, ENV_FILE_PATH)

    print("Converting EPUB to Markdown...")
    # Set limit=100 for a trial run of 100 sections/chapters
    markdown_content = epub_to_markdown(LOCAL_EPUB_PATH, limit=100)
    
    print("Uploading to RAG Corpus...")
    upload_text_to_corpus(corpus.name, markdown_content, "CPT_2024.md")

if __name__ == "__main__":
    main()
