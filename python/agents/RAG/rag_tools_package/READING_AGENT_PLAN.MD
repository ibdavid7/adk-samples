# Reading Agent Implementation Plan

This document outlines the plan to build a "Reading Agent" using Google Cloud Platform (GCP) and Gemini 3. The agent leverages **Visual Reasoning** to handle complex transcriptions, indentation preservation, and "scrambled" text, supporting both PDF and EPUB formats.

## 1. Project Overview

*   **Goal**: Create an agent capable of high-fidelity transcription and question answering from complex documents, specifically targeting **CPT Professional 2024** extraction.
*   **Key Technologies**:
    *   **Model**: Gemini 3 (Visual Reasoning, Media Resolution Control, Thinking Mode).
    *   **Platform**: Vertex AI (Agent Engine, RAG Engine).
    *   **Framework**: Google ADK (Agent Development Kit).
*   **Input Formats**:
    *   **PDF**: Native support via Vertex AI RAG / Gemini Multimodal.
    *   **EPUB**: Requires preprocessing (EPUB -> Markdown/PDF) with layout preservation.

## 2. Architecture

### Components
1.  **Ingestion Pipeline**:
    *   **PDF**: Direct upload to Vertex AI RAG Corpus.
    *   **EPUB**: Preprocessing script to unzip and convert to **Layout-Preserving Markdown** (using `MarkItDown` or custom `BeautifulSoup` logic) before ingestion.
2.  **RAG Engine**: Vertex AI RAG for storing and retrieving document chunks.
3.  **Agent Core**:
    *   **Model**: `gemini-3.0-pro` (or latest preview).
    *   **Configuration**: High `media_resolution`, High `thinking_level`.
    *   **Tools**: `VertexAiRagRetrieval` for accessing the corpus.
    *   **Output**: Structured JSON for CPT codes.

## 3. Implementation Steps

### Step 1: Environment & Dependencies
*   Reuse the existing `pyproject.toml` from `python/agents/RAG`.
*   Add dependencies for EPUB handling: `beautifulsoup4`, `ebooklib`, `markitdown`.

### Step 2: Data Ingestion (The "Reader")

#### PDF Handling (Reuse Existing)
We can reuse `rag/shared_libraries/prepare_corpus_and_data.py` with minor modifications to support local file uploads more easily.

#### EPUB Handling (New)
Create a script `rag/shared_libraries/prepare_epub.py` to:
1.  Extract text/images from EPUB.
2.  **Critical**: Convert HTML to Markdown while preserving indentation (using `&nbsp;` or blockquotes `>`) to ensure Gemini can "see" the hierarchy.
3.  Upload to the RAG Corpus.

**Code Snippet (EPUB to Layout-Aware Markdown):**
```python
from bs4 import BeautifulSoup

def html_to_layout_markdown(html_content):
    soup = BeautifulSoup(html_content, 'html.parser')
    # Custom logic to map CSS 'margin-left' or classes to Markdown indentation
    # e.g., <p style="margin-left: 20px"> -> "> Text"
    # ...
    return markdown_content
```

### Step 3: Agent Configuration (Gemini 3)

Update `rag/agent.py` to use the Gemini 3 model and configure specific parameters for visual reasoning.

**Configuration:**
*   **Model Name**: Update `model='gemini-2.0-flash-001'` to `gemini-3.0-pro-preview` (check availability).
*   **System Instructions**:
    > "You are an expert Medical Data Analyst. Extract CPT codes into a JSON list.
    > Rules:
    > 1. **Semicolon Rule**: Child codes (indented) inherit parent description before ';'.
    > 2. **Context**: Track 'Section', 'Subsection', 'Subheading' from headers.
    > 3. **Output**: JSON list with fields: code, code_desc, code_type, section, subsection, subheading, topic, code_version."

**Thinking Mode & Media Resolution:**
*   These parameters are typically set in the generation config.
*   *Note: Check ADK support for passing `generation_config` parameters like `media_resolution` and `thinking_level`.*

### Step 4: RAG Integration
The `VertexAiRagRetrieval` tool in `rag/agent.py` is already set up to query the corpus. We just need to ensure the corpus is populated with our high-fidelity processed documents.

## 4. Refined Code Structure

### `rag/shared_libraries/prepare_corpus_and_data.py`
*   **Status**: **Reusable**.
*   **Action**: Keep as is for PDF support. Can be imported by other scripts.

### `rag/agent.py`
*   **Status**: **Modify**.
*   **Action**:
    *   Change model to Gemini 3.
    *   Update system instructions in `rag/prompts.py`.

### `rag/prompts.py`
*   **Status**: **Modify**.
*   **Action**: Add the "Visual Reasoning" system prompt.

## 5. Next Steps
1.  **Verify Gemini 3 Access**: Ensure the GCP project has access to the Gemini 3 preview models.
2.  **Develop EPUB Converter**: Write the script to convert EPUBs to a RAG-friendly format.
3.  **Update Agent**: Modify `agent.py` and `prompts.py` with the new model and instructions.
4.  **Test**: Run the agent against a "scrambled" PDF and an EPUB to verify performance.