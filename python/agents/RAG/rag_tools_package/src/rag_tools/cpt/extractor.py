import os
import json
import time
from google import genai
from google.genai import types
from ..config import PROJECT_ID, LOCATION, MODEL_ID
from .navigator import EPUBNavigator

class CPTExtractor:
    def __init__(self, epub_path, model_id=MODEL_ID, use_hierarchy=True):
        self.navigator = EPUBNavigator(epub_path)
        self.use_hierarchy = use_hierarchy
        
        # Gemini 3 Pro Preview is currently only available in the "global" region for some projects
        # or requires specific location handling.
        current_location = LOCATION
        if "gemini-3" in model_id:
            current_location = "us-central1" # Try us-central1 first, but user docs say global might be needed.
            # Actually, the user docs explicitly say: location="global" for the Python example.
            current_location = "global"
            
        print(f"Initializing GenAI client for {model_id} in {current_location}...")
        self.client = genai.Client(
            vertexai=True,
            project=PROJECT_ID,
            location=current_location
        )
        self.model_id = model_id

    def extract_pages(self, start_page, end_page, previous_code_context=None, stream=False, simple_schema=False):
        print(f"Extracting content from pages {start_page} to {end_page}...")
        raw_text = self.navigator.get_content_by_page_range(start_page, end_page)
        
        context = {}
        if self.use_hierarchy:
            print("Retrieving hierarchy context...")
            context = self.navigator.get_hierarchy_context(start_page)
            print(f"Context found: {context}")
        else:
            print("Skipping hierarchy context retrieval.")
        
        prompt = self._construct_prompt(raw_text, context, previous_code_context, simple_schema)
        
        print(f"Prompt size: {len(prompt)} characters")
        print(f"Sending request to {self.model_id}...")
        try:
            config = types.GenerateContentConfig(
                response_mime_type="application/json",
                temperature=0.1
            )

            if stream:
                print("Streaming response (receiving chunks)...")
                response_stream = self.client.models.generate_content_stream(
                    model=self.model_id,
                    contents=prompt,
                    config=config
                )
                
                full_text = ""
                usage_metadata = None
                for chunk in response_stream:
                    if hasattr(chunk, 'usage_metadata') and chunk.usage_metadata:
                        usage_metadata = chunk.usage_metadata

                    if hasattr(chunk, 'candidates') and chunk.candidates and chunk.candidates[0].content and chunk.candidates[0].content.parts:
                        for part in chunk.candidates[0].content.parts:
                            # Check for explicit 'thought' field
                            if hasattr(part, 'thought') and part.thought:
                                print(f"\n\033[90m[Thinking]: {part.thought}\033[0m", end="", flush=True)
                            
                            # Check for text field - only append actual text to the result
                            if hasattr(part, 'text') and part.text:
                                full_text += part.text
                                print(".", end="", flush=True)
                    elif hasattr(chunk, 'text') and chunk.text:
                         # Fallback for models/chunks without parts structure
                         full_text += chunk.text
                         print(".", end="", flush=True)

                print("\nStreaming complete.")
                
                # Clean up markdown code blocks if present
                cleaned_text = full_text.strip()
                if cleaned_text.startswith("```json"):
                    cleaned_text = cleaned_text[7:]
                if cleaned_text.startswith("```"):
                    cleaned_text = cleaned_text[3:]
                if cleaned_text.endswith("```"):
                    cleaned_text = cleaned_text[:-3]
                return cleaned_text.strip(), usage_metadata
            else:
                response = self.client.models.generate_content(
                    model=self.model_id,
                    contents=prompt,
                    config=config
                )
                text = response.text
                # Clean up markdown code blocks if present
                cleaned_text = text.strip()
                if cleaned_text.startswith("```json"):
                    cleaned_text = cleaned_text[7:]
                if cleaned_text.startswith("```"):
                    cleaned_text = cleaned_text[3:]
                if cleaned_text.endswith("```"):
                    cleaned_text = cleaned_text[:-3]
                return cleaned_text.strip(), response.usage_metadata
        except Exception as e:
            print(f"\nError calling model: {e}")
            return "[]", None

    def _construct_prompt(self, text, context, previous_code_context=None, simple_schema=False):
        prev_context_str = ""
        if previous_code_context:
            prev_context_str = f"""
**Previous Code Context**:
The last CPT code extracted from the previous page range was:
{json.dumps(previous_code_context, indent=2)}
If the FIRST code in the current text is a child code (starts with a semicolon or is indented), use the description from this previous code as the PARENT.
"""

        schema_instruction = """
4. **Output Format**:
   Return the data as **JSON Lines** (ndjson).
   - Each line must be a valid, independent JSON object.
   - Do NOT wrap the output in a list `[...]`.
   - Do NOT use commas between lines.
   - Schema for each object:
   {{
    "code": "string",
    "code_description": "string (resolved full description)",
    "code_type": "CPT",
    "section": "string",
    "section_text": "string",
    "subsection": "string",
    "subsection_text": "string",
    "subheading": "string",
    "subheading_text": "string",
    "topic": "string",
    "topic_text": "string",
    "code_version": "CPT 2024 AMA"
   }}
"""
        if simple_schema:
            schema_instruction = """
4. **Output Format**:
   Return the data as **JSON Lines** (ndjson).
   - Each line must be a valid, independent JSON object.
   - Do NOT wrap the output in a list `[...]`.
   - Do NOT use commas between lines.
   - Schema for each object:
   {{
    "code": "string",
    "code_description": "string (resolved full description)"
   }}
   Do NOT include any other fields like section, subsection, etc.
"""

        return f"""
You are an expert Medical Coder and Data Analyst.
Your task is to extract CPT codes from the provided text and format them into a structured JSON array.

**Context (Hierarchy from previous pages)**:
- Current Section: {context.get('section', 'Unknown')}
- Current Subsection: {context.get('subsection', 'Unknown')}
- Current Subheading: {context.get('subheading', 'Unknown')}
- Current Topic: {context.get('topic', 'Unknown')}
{prev_context_str}

**Rules**:
1. **Semicolon Rule**: This is CRITICAL. CPT codes often use a parent-child relationship.
   - If a code description starts with a semicolon (e.g., "; surgical") or is indented and lowercase, it is a CHILD code.
   - You must find the immediately preceding PARENT code (which usually ends with a semicolon).
   - The full description for the child is: [Parent Description up to semicolon] + [Child Description].
   - Example:
     - Parent: "29800 Arthroscopy, temporomandibular joint; diagnostic, with or without synovial biopsy (separate procedure)"
     - Child: "29804 ; surgical"
     - Result for 29804: "Arthroscopy, temporomandibular joint, surgical"
2. **Hierarchy Inheritance**:
   - For every code extracted, fill in the "section", "subsection", "subheading", and "topic" fields.
   - If the text explicitly introduces a new header (e.g., "Respiratory System"), update the context for subsequent codes.
   - If no new header is found, use the **Context** provided above.
3. **Text Extraction**:
   - "section_text", "subsection_text", etc. should contain the introductory text paragraphs that appear under those headers.
   - If the text is not present in this chunk, use "See previous pages" or leave empty. Do not hallucinate.
{schema_instruction}

**Input Text**:
{text[:350000]} 
(Note: Text truncated to fit context window if necessary)
"""
