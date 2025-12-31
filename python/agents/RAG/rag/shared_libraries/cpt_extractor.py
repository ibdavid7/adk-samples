import os
import json
import argparse
import time
from google import genai
from google.genai import types
from dotenv import load_dotenv
from epub_navigator import EPUBNavigator

load_dotenv()

PROJECT_ID = os.getenv("GOOGLE_CLOUD_PROJECT")
LOCATION = "us-central1" 
MODEL_ID = "gemini-2.5-pro" # Fallback to 2.0 Flash as 3.0 Pro Preview is unstable/404

# If the user specifically requested Gemini 3 Pro, we can try to use it if available
# But based on previous errors, we default to the working one for reliability.
# We will add a flag to override.

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
                for chunk in response_stream:
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
                return cleaned_text.strip()
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
                return cleaned_text.strip()
        except Exception as e:
            print(f"\nError calling model: {e}")
            return "[]"

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
{text[:300000]} 
(Note: Text truncated to fit context window if necessary)
"""

def main():
    parser = argparse.ArgumentParser(description="Extract CPT codes from EPUB")
    parser.add_argument("--start", type=int, required=True, help="Start page number")
    parser.add_argument("--end", type=int, required=True, help="End page number")
    parser.add_argument("--output", type=str, default="cpt_output.json", help="Output JSON file")
    parser.add_argument("--model", type=str, default="gemini-2.5-pro", help="Model ID to use")
    parser.add_argument("--chunk-size", type=int, default=5, help="Number of pages per chunk")
    parser.add_argument("--no-hierarchy", action="store_true", help="Disable hierarchy context retrieval")
    parser.add_argument("--by-chapter", action="store_true", help="Process by chapter boundaries instead of fixed page chunks")
    parser.add_argument("--stream", action="store_true", help="Stream response to show progress (useful for Gemini 3)")
    parser.add_argument("--skip-combined-output", action="store_true", help="Do not save the combined output file, only individual chunks")
    parser.add_argument("--simple-schema", action="store_true", help="Use a simplified JSON schema (code and description only) to reduce parsing errors")
    
    args = parser.parse_args()
    
    epub_path = "/workspaces/adk-samples/python/agents/RAG/source/CPT Professional 2024 American Medical Association.epub"
    extractor = CPTExtractor(epub_path, model_id=args.model, use_hierarchy=not args.no_hierarchy)
    
    all_codes = []
    last_code_context = None
    
    chunks = []
    if args.by_chapter:
        print("Calculating chapter boundaries...")
        boundaries = extractor.navigator.get_chapter_boundaries()
        for b in boundaries:
            # Check overlap with requested range
            if max(b['start_page'], args.start) <= min(b['end_page'], args.end):
                chunks.append((b['start_page'], b['end_page']))
        print(f"Found {len(chunks)} chapters overlapping with pages {args.start}-{args.end}")
    else:
        for current_start in range(args.start, args.end + 1, args.chunk_size):
            current_end = min(current_start + args.chunk_size - 1, args.end)
            chunks.append((current_start, current_end))
    
    # Loop through chunks
    for current_start, current_end in chunks:
        print(f"\n--- Processing Chunk: Pages {current_start} to {current_end} ---")
        
        chunk_start_time = time.time()
        
        # Pass the last code from the previous chunk as context
        json_response_text = extractor.extract_pages(current_start, current_end, previous_code_context=last_code_context, stream=args.stream, simple_schema=args.simple_schema)
        
        chunk_elapsed = time.time() - chunk_start_time
        print(f"  -> Chunk processed in {chunk_elapsed:.2f} seconds")
        
        chunk_codes = []
        try:
            # Try parsing as JSONL (line by line)
            for line in json_response_text.strip().split('\n'):
                line = line.strip()
                if not line: continue
                try:
                    obj = json.loads(line)
                    chunk_codes.append(obj)
                except json.JSONDecodeError:
                    # If a line fails, it might be because the model output a standard JSON array despite instructions
                    # We will try to parse the whole text as a fallback below
                    pass
            
            # Fallback: If no codes found via JSONL, try parsing as standard JSON array
            if not chunk_codes:
                 try:
                     parsed = json.loads(json_response_text)
                     if isinstance(parsed, list):
                         chunk_codes = parsed
                     elif isinstance(parsed, dict):
                         chunk_codes = [parsed]
                 except:
                     pass

            if chunk_codes:
                all_codes.extend(chunk_codes)
                # Update context for the next chunk
                last_code_context = chunk_codes[-1]
                print(f"  -> Extracted {len(chunk_codes)} codes. Last code: {last_code_context.get('code', 'N/A')}")
                
                # Save individual chapter/chunk file
                # Determine output directory from args.output or current dir
                output_dir = os.path.dirname(args.output)
                chapter_filename = os.path.join(output_dir, f"cpt_{current_start}_{current_end}_chapter.jsonl")
                
                with open(chapter_filename, "w") as f:
                    for code in chunk_codes:
                        f.write(json.dumps(code) + "\n")
                print(f"  -> Saved chunk results to {chapter_filename}")
            else:
                print("  -> No codes found in this chunk (or parsing failed).")
                # Trigger error handling to save raw text
                raise json.JSONDecodeError("No valid JSON found", json_response_text, 0)

        except json.JSONDecodeError:
            print(f"  -> Error: Failed to parse JSON response for pages {current_start}-{current_end}")
            # Save the raw response for debugging/manual recovery
            output_dir = os.path.dirname(args.output)
            debug_filename = os.path.join(output_dir, f"cpt_{current_start}_{current_end}_raw_error.txt")
            with open(debug_filename, "w") as f:
                f.write(json_response_text)
            print(f"  -> Saved raw response to {debug_filename}. You can inspect it and manually fix the JSON.")
            
    # Determine final filename based on actual processed range
    final_output = args.output
    if chunks:
        actual_start = chunks[0][0]
        actual_end = chunks[-1][1]
        
        dirname = os.path.dirname(args.output)
        basename = os.path.basename(args.output)
        name, ext = os.path.splitext(basename)
        
        # Avoid double stamping if the user manually typed the range
        if f"_{actual_start}_{actual_end}" not in name:
            new_basename = f"{name}_{actual_start}_{actual_end}{ext}"
            final_output = os.path.join(dirname, new_basename)

    # Ensure extension is .jsonl
    if final_output.endswith('.json'):
        final_output = final_output[:-5] + '.jsonl'
    elif not final_output.endswith('.jsonl'):
        final_output += '.jsonl'

    if not args.skip_combined_output:
        # Save combined results
        with open(final_output, "w") as f:
            for code in all_codes:
                f.write(json.dumps(code) + "\n")
        
        print(f"\nFull extraction complete. Total codes: {len(all_codes)}. Saved to {final_output}")
    else:
        print(f"\nFull extraction complete. Total codes: {len(all_codes)}. Skipped saving combined output.")

if __name__ == "__main__":
    main()


EXAMPLE_USAGE = """

uv run rag/shared_libraries/cpt_extractor.py --start 64 --end 65 --output cpt_64_65_chapter.json --model gemini-3-flash-preview --no-hierarchy --by-chapter

uv run rag/shared_libraries/cpt_extractor.py --start 66 --end 70 --output cpt_66_70_chapter.json --model gemini-3-flash-preview --no-hierarchy --by-chapter

USING GEMINI 3 PRO STREAMING:
uv run rag/shared_libraries/cpt_extractor.py --start 119 --end 130 \
 --model gemini-3-pro-preview --no-hierarchy --by-chapter --stream --skip-combined-output

USING GEMINI 3 PRO WITH SIMPLE SCHEMA:
uv run rag/shared_libraries/cpt_extractor.py --start 95 --end 100 \
 --model gemini-3-pro-preview --no-hierarchy --by-chapter --stream \
 --skip-combined-output --simple-schema

USING GEMINI 3 FLASH STREAMING:
uv run rag/shared_libraries/cpt_extractor.py --start 66 --end 74 --model gemini-3-flash-preview --no-hierarchy --by-chapter --stream --skip-combined-output
uv run rag/shared_libraries/cpt_extractor.py --start 66 --end 74 --model gemini-3-flash-preview --no-hierarchy --by-chapter --skip-combined-output

"""
