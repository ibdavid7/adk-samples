# Reading Agent Specification Document

**Version:** 1.0  
**Status:** Draft  
**Date:** December 29, 2025  
**Based on:** [READING_AGENT_PLAN.MD](READING_AGENT_PLAN.MD)

---

## 1. Executive Summary

The **Reading Agent** is a specialized AI agent designed to perform high-fidelity transcription, visual reasoning, and question answering over complex documents. Unlike traditional OCR-based RAG systems, this agent leverages **Gemini 3's Visual Reasoning** capabilities to understand spatial relationships, indentation, and non-linear text layouts (e.g., "scrambled" notes, curved text).

The system supports **PDF** (native multimodal) and **EPUB** (via conversion) formats, utilizing Google Cloud's Vertex AI RAG Engine for storage and retrieval.

## 2. User Personas & Use Cases

### 2.1 Personas
*   **The Researcher:** Needs to extract data from old, messy, or handwritten manuscripts where layout implies meaning.
*   **The Analyst:** Reviews financial reports or forms where indentation levels strictly define data hierarchy.
*   **The Archivist:** Digitizing non-standard documents (posters, mind maps) that standard OCR fails to capture correctly.

### 2.2 User Stories
*   **As a user**, I want to upload a PDF with complex indentation so that the resulting markdown preserves the exact hierarchy.
*   **As a user**, I want to query an EPUB book so that I can find specific passages and their context.
*   **As a user**, I want the agent to "read" a page with scrambled/handwritten notes and reconstruct them into a logical order.
*   **As a Medical Data Analyst**, I want to process the **CPT Professional 2024** EPUB to extract a structured dataset of codes, where child codes inherit descriptions from parents based on the "semicolon rule" and all codes are tagged with their active Section, Subsection, and Subheading.

## 3. Functional Requirements

### 3.1 Input Handling
*   **FR-01: PDF Support**: The system MUST accept PDF files. These shall be processed as visual inputs (images) to preserve layout fidelity.
*   **FR-02: EPUB Support**: The system MUST accept EPUB files. These shall be pre-processed (unzipped/converted) into a text/markdown format suitable for RAG ingestion.

### 3.2 Processing & Transcription
*   **FR-03: Visual Reasoning**: The agent MUST use Gemini 3's Vision Language Model (VLM) capabilities.
*   **FR-04: Indentation Preservation**: The transcription output MUST use markdown spacing/indentation to mirror the visual layout of the source.
*   **FR-05: Scrambled Text Handling**: The agent MUST be capable of logically ordering non-linear text blocks (e.g., marginalia, curved text).
*   **FR-06: Media Resolution**: The system MUST allow configuration of `media_resolution` to "High" for fine-grained detail capture.

### 3.3 Domain-Specific Logic (CPT Rules)
*   **FR-CPT-01: Semicolon Inheritance**: The agent MUST apply the CPT "semicolon rule": Child codes (indented) MUST inherit the portion of the parent code's description preceding the semicolon.
    *   *Example*: Parent `10000 Procedure; simple` + Child `10001 complicated` -> `10001 Procedure; complicated`.
*   **FR-CPT-02: Context Propagation**: The agent MUST identify and propagate hierarchical headers (Section, Subsection, Subheading) to every extracted code object within that hierarchy.
*   **FR-CPT-03: Structured Output**: The agent MUST output data in a specific JSON schema containing: `code`, `code_desc`, `code_type`, `section`, `subsection`, `subheading`, `topic`, and `code_version`.

### 3.4 Retrieval & Generation (RAG)
*   **FR-07: Context Retrieval**: The system MUST retrieve relevant document chunks via Vertex AI RAG Engine.
*   **FR-08: Citation**: Responses MUST include citations pointing to the source document.
*   **FR-09: Thinking Mode**: The agent SHOULD utilize Gemini 3's "Thinking Mode" (High) for complex reasoning tasks to reduce hallucinations.

## 4. Technical Architecture

### 4.1 High-Level Components

1.  **Ingestion Service (The "Reader")**
    *   *Role*: Prepares documents for the RAG Corpus.
    *   *Tools*: Python scripts (`prepare_corpus_and_data.py`, `prepare_epub.py`).
    *   *Logic*:
        *   PDFs -> Direct upload to Vertex RAG (Multimodal).
        *   EPUBs -> `ZipFile`/`BeautifulSoup` -> Markdown -> Vertex RAG (Text).

2.  **Knowledge Base (Vertex AI RAG)**
    *   *Role*: Stores vector embeddings and raw document content.
    *   *Config*: `VertexAiRagRetrieval` tool.

3.  **Reasoning Engine (Gemini 3 Agent)**
    *   *Role*: The "Brain" that processes user queries and retrieved context.
    *   *Model*: `gemini-3.0-pro-preview` (or equivalent).
    *   *Framework*: Google ADK (`Agent`, `VertexAiRagRetrieval`).

### 4.2 Data Flow

1.  **Ingestion Phase**:
    *   User provides File (PDF/EPUB).
    *   Script determines type.
    *   If EPUB: Convert to Markdown.
    *   Upload to Vertex AI RAG Corpus.

2.  **Query Phase**:
    *   User asks question (e.g., "Transcribe page 5 preserving indentation").
    *   Agent calls `VertexAiRagRetrieval`.
    *   RAG Engine returns relevant chunks (Images/Text).
    *   Gemini 3 processes chunks with **Visual Reasoning**.
    *   Agent returns formatted Markdown response.

## 5. Configuration Specifications

### 5.1 Model Configuration
The `Agent` initialization in `rag/agent.py` requires specific tuning for this use case:

```python
model_config = {
    "model_name": "gemini-3.0-pro-preview",
    "generation_config": {
        "media_resolution": "high",  # Critical for small text/details
        "thinking_level": "high",    # Critical for logical reconstruction
        "temperature": 0.1           # Low temp for faithful transcription
    }
}
```

### 5.2 System Prompts
The system instruction must enforce the "High Fidelity" persona and CPT-specific rules:

> "You are an expert Medical Data Analyst and high-fidelity transcription engine. Your goal is to extract structured CPT code data from the provided document.
>
> **Visual & Structural Rules:**
> 1.  **Indentation**: Use visual indentation to determine parent/child relationships between codes.
> 2.  **Headers**: Identify Section (e.g., 'Surgery'), Subsection (e.g., 'Musculoskeletal System'), and Subheading (e.g., 'Endoscopy') headers. These apply to all subsequent codes until a new header of the same level appears.
>
> **CPT Logic Rules:**
> 1.  **Semicolon Rule**: If a code description starts with a lowercase letter or is indented under a parent, it is a child code. Its full description is: [Parent Description before ';'] + ';' + [Child Description].
>
> **Output Format:**
> Return a JSON list of objects with this schema:
> ```json
> {
>   "code": "string",
>   "code_desc": "string (full reconstructed description)",
>   "code_type": "CPT",
>   "section": "string",
>   "subsection": "string",
>   "subheading": "string",
>   "topic": "string (optional)",
>   "code_version": "CPT 2024 AMA"
> }
> ```"

## 6. Dependencies & Environment

*   **Language**: Python 3.10+
*   **Package Manager**: `uv`
*   **Key Libraries**:
    *   `google-adk`
    *   `vertexai` (Preview)
    *   `beautifulsoup4` (for EPUB parsing)
    *   `markitdown` (optional, for advanced conversion)

## 7. Future Scope
*   **Handwriting Recognition**: Fine-tuning specifically for cursive or historical scripts.
*   **Multi-Page Stitching**: Logic to handle text that flows across page boundaries in PDFs.
*   **Structured Data Extraction**: Converting visual tables directly into JSON/CSV formats.
