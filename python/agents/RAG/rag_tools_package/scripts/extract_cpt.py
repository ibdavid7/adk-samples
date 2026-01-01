import os
import json
import argparse
import time
import sys

# Add the src directory to the python path so we can import the package
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "src")))

from rag_tools.cpt.extractor import CPTExtractor
from rag_tools.utils.pricing import calculate_cost

def main():
    parser = argparse.ArgumentParser(description="Extract CPT codes from EPUB")
    parser.add_argument("--start", type=int, required=True, help="Start page number")
    parser.add_argument("--end", type=int, required=True, help="End page number")
    parser.add_argument("--epub", type=str, required=True, help="Path to the input EPUB file")
    parser.add_argument("--output-dir", type=str, default="cpt_output", help="Directory to save output JSONL files")
    parser.add_argument("--model", type=str, default="gemini-2.5-pro", help="Model ID to use")
    parser.add_argument("--chunk-size", type=int, default=5, help="Number of pages per chunk")
    parser.add_argument("--no-hierarchy", action="store_true", help="Disable hierarchy context retrieval")
    parser.add_argument("--by-chapter", action="store_true", help="Process by chapter boundaries instead of fixed page chunks")
    parser.add_argument("--stream", action="store_true", help="Stream response to show progress (useful for Gemini 3)")
    parser.add_argument("--simple-schema", action="store_true", help="Use a simplified JSON schema (code and description only) to reduce parsing errors")
    
    args = parser.parse_args()
    
    # Create output directory if it doesn't exist
    if not os.path.exists(args.output_dir):
        os.makedirs(args.output_dir)
        print(f"Created output directory: {args.output_dir}")
    
    extractor = CPTExtractor(args.epub, model_id=args.model, use_hierarchy=not args.no_hierarchy)
    
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
        json_response_text, usage_metadata = extractor.extract_pages(current_start, current_end, previous_code_context=last_code_context, stream=args.stream, simple_schema=args.simple_schema)
        
        chunk_elapsed = time.time() - chunk_start_time
        print(f"  -> Chunk processed in {chunk_elapsed:.2f} seconds")
        
        if usage_metadata:
            cost = calculate_cost(args.model, usage_metadata.prompt_token_count, usage_metadata.candidates_token_count)
            print(f"  -> Token Usage: Prompt: {usage_metadata.prompt_token_count}, Candidates: {usage_metadata.candidates_token_count}, Total: {usage_metadata.total_token_count}")
            print(f"  -> Estimated Cost: ${cost:.6f}")
        
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
                chapter_filename = os.path.join(args.output_dir, f"cpt_{current_start}_{current_end}_chapter.jsonl")
                
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
            debug_filename = os.path.join(args.output_dir, f"cpt_{current_start}_{current_end}_raw_error.txt")
            with open(debug_filename, "w") as f:
                f.write(json_response_text)
            print(f"  -> Saved raw response to {debug_filename}. You can inspect it and manually fix the JSON.")
            
    # Save combined results
    final_output = os.path.join(args.output_dir, "all_extracted_codes.jsonl")
    with open(final_output, "w") as f:
        for code in all_codes:
            f.write(json.dumps(code) + "\n")
    
    print(f"\nFull extraction complete. Total codes: {len(all_codes)}. Saved to {final_output}")

if __name__ == "__main__":
    main()


EXAMPLE_USAGE = """

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