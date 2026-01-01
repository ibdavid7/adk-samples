# RAG Tools Package

This package contains tools for:
1.  **CPT Extraction**: Extracting CPT codes from EPUB files using Gemini models.
2.  **RAG Ingestion**: Uploading documents (PDFs) to Vertex AI RAG Corpora.
3.  **Utilities**: Converting extraction results to CSV.

## Installation

You can install this package in editable mode:

```bash
pip install -e .
```

## Configuration

Create a `.env` file in the root of your project (or copy `.env.example`):

```bash
GOOGLE_CLOUD_PROJECT=your-project-id
GOOGLE_CLOUD_LOCATION=us-central1
MODEL_ID=gemini-2.5-pro
```

## Usage

### 1. Extract CPT Codes

```bash
# Run extraction (example)
python scripts/extract_cpt.py \
  --epub "./source/CPT Professional 2024 American Medical Association.epub" \
  --start 63 --end 63 \
  --output-dir "cpt_output" \
  --model gemini-3-pro-preview \
  --no-hierarchy --by-chapter --stream

[OPTIONAL]
  --simple-schema
```

### 2. Convert Results to CSV

```bash
python scripts/convert_results.py cpt_output/ --output final_codes.csv
```

### 3. Upload Documents to RAG

```bash
python scripts/upload_rag_docs.py --file "/path/to/doc.pdf" --corpus-name "My_Corpus"
```
