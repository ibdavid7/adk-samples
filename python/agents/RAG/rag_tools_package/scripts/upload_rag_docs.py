import argparse
import os
import sys

# Add the src directory to the python path so we can import the package
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "src")))

from rag_tools.ingestion.pdf_uploader import PDFUploader

def main():
    parser = argparse.ArgumentParser(description="Upload documents to Vertex AI RAG Corpus")
    parser.add_argument("--file", type=str, help="Local path to PDF file")
    parser.add_argument("--url", type=str, help="URL to PDF file")
    parser.add_argument("--corpus-name", type=str, default="RAG_Corpus", help="Display name for the corpus")
    
    args = parser.parse_args()
    
    if not args.file and not args.url:
        print("Error: Must provide either --file or --url")
        return

    uploader = PDFUploader(corpus_display_name=args.corpus_name)
    corpus = uploader.create_corpus()
    
    if args.file:
        uploader.upload_file(corpus.name, args.file)
    elif args.url:
        filename = os.path.basename(args.url) or "downloaded.pdf"
        uploader.upload_from_url(corpus.name, args.url, filename)

if __name__ == "__main__":
    main()
