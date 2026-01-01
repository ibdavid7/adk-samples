# CPT 2024 Structured Data Extraction Agent - Specification & Implementation Plan

## 1. Objective
Develop an AI-driven extraction agent capable of reading the "CPT Professional 2024" EPUB file and converting a user-specified page range (e.g., pages 50-200) into a structured JSON format. The agent must intelligently handle CPT-specific logic, including the "semicolon rule" for code descriptions and the inheritance of hierarchical section headers.

## 2. Input & Output

### Input
*   **Source File**: `CPT Professional 2024 American Medical Association.epub`
*   **Parameters**:
    *   `start_page` (int): The starting page number (based on EPUB page markers).
    *   `end_page` (int): The ending page number.

### Output
A JSON array containing objects with the following schema:
```json
[
  {
    "code": "29800",
    "code_description": "Arthroscopy, temporomandibular joint, diagnostic, with or without synovial biopsy (separate procedure)",
    "code_type": "CPT",
    "section": "Surgery",
    "section_text": "All services that appear in the Musculoskeletal System section...",
    "subsection": "Musculoskeletal System",
    "subsection_text": "Endoscopy/Arthroscopy",
    "subheading": "Surgical endoscopy/arthroscopy always includes...",
    "subheading_text": "...",
    "topic": "...",
    "topic_text": "...",
    "code_version": "CPT 2024 AMA"
  }
]
```

## 3. Technical Architecture

### 3.1. Component Diagram
1.  **EPUB Page Processor**: A Python module to traverse the EPUB structure, locate specific page markers (e.g., `<span id="page_50"/>`), and extract the raw HTML content between the start and end markers.
2.  **Context Manager**: A state tracking mechanism to identify the "active" Section, Subsection, and Subheading at the beginning of the requested page range (by scanning backwards if necessary).
3.  **Gemini Extraction Engine**: A prompt-engineered interface using **Gemini 2.5 Pro**. It will receive chunks of text/HTML and the "Current Context" and return structured JSON.
4.  **Aggregator**: Combines the JSON outputs from multiple model calls into a single coherent list.

### 3.2. Key Logic Handling

#### A. Page Selection
EPUBs are flowable text. "Pages" are marked by anchor tags (e.g., `<span id="page_757"/>`).
*   **Logic**:
    1.  Iterate through the EPUB `spine` (reading order).
    2.  Search for `id="page_{start_page}"`.
    3.  Capture all content until `id="page_{end_page + 1}"` is found.
    4.  Handle cases where a page range spans multiple internal HTML files.

#### B. Hierarchy Inheritance (The "Context" Problem)
A page might start in the middle of a list of codes, far below the `<h1>` or `<h2>` that defines the section.
*   **Solution**: The `EPUB Page Processor` must maintain a running state of the last seen headers (`h1`...`h6`). When extraction starts at Page 50, the prompt will be initialized with: *"Context: You are in Section 'Surgery', Subsection 'Musculoskeletal System'..."*.

#### C. The "Semicolon Rule"
CPT codes often use a parent-child relationship:
*   Parent: `29800 Arthroscopy, temporomandibular joint, diagnostic, with or without synovial biopsy (separate procedure)`
*   Child (indented): `29804 ; surgical`
*   **AI Task**: The LLM is best suited to resolve this. The prompt will explicitly instruct the model to:
    *   Identify indented codes.
    *   Look for the preceding parent code (which ends in a semicolon or is the logical root).
    *   Combine the parent string (up to the semicolon) with the child string.

## 4. Implementation Plan

### Step 1: `EPUBNavigator` Class
Create a Python class `rag/shared_libraries/epub_navigator.py` to:
*   Open the EPUB zip.
*   Parse the OPF (spine).
*   Implement `get_content_by_page_range(start, end)`.
*   Implement `get_hierarchy_context(page_number)`: Scans backwards from the start page to find the active headers.

### Step 2: `CPTExtractor` Agent
Create a script `rag/shared_libraries/cpt_extractor.py` that:
*   Uses `EPUBNavigator` to get the raw text for the requested pages.
*   Constructs a prompt for Gemini 2.5 Pro.
*   **Prompt Strategy**:
    *   **Role**: Medical Coding Data Analyst.
    *   **Task**: Extract CPT codes to JSON.
    *   **Input**: Raw text + Hierarchy Context.
    *   **Constraints**: Strict JSON output, handle semicolons, fill missing fields from context.

### Step 3: Execution Script
Create a runner script `extract_cpt_data.py` that:
*   Accepts CLI arguments: `--start`, `--end`, `--output`.
*   Runs the extraction.
*   Saves the result to a JSON file.

## 5. Prompt Design (Draft)

```text
You are an expert Medical Coder and Data Analyst.
Your task is to extract CPT codes from the provided text and format them into a structured JSON array.

**Context**:
Current Section: {current_section}
Current Subsection: {current_subsection}
...

**Rules**:
1. **Semicolon Rule**: If a code description starts with a semicolon or is indented/lowercase implying a continuation, find the parent code's description. Take the parent description up to the semicolon, and append the child description.
   - Example Parent: "Procedure on knee; diagnostic"
   - Example Child: "surgical"
   - Result: "Procedure on knee; surgical"
2. **Hierarchy**: Fill "section", "subsection", etc., for EVERY code. If the text doesn't explicitly state a new section, use the current active one.
3. **Text Extraction**: Capture "section_text" or "subsection_text" only when it appears as a preamble to a group of codes.

**Input Text**:
{chunk_of_text}

**Output Format**:
JSON Array of objects.
```

## 6. Next Steps
1.  Implement `EPUBNavigator` to prove we can extract specific pages.
2.  Implement the Gemini integration.
3.  Run a test on a small range (e.g., 5 pages).
