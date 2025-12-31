import os
import json
import csv
import argparse
import glob

def json_to_csv(input_path, output_file):
    # Determine list of files to process
    files_to_process = []
    if os.path.isfile(input_path):
        files_to_process.append(input_path)
    elif os.path.isdir(input_path):
        # Find all json files in the directory
        # We look for files ending in .json
        files_to_process = glob.glob(os.path.join(input_path, "*.json"))
    else:
        print(f"Error: Input path '{input_path}' not found.")
        return

    if not files_to_process:
        print("No JSON files found to process.")
        return

    print(f"Found {len(files_to_process)} JSON files.")

    # Define the standard fieldnames based on the CPT extractor schema
    fieldnames = [
        "code",
        "code_description",
        "code_type",
        "section",
        "section_text",
        "subsection",
        "subsection_text",
        "subheading",
        "subheading_text",
        "topic",
        "topic_text",
        "code_version"
    ]

    total_records = 0
    
    # Open output CSV file
    with open(output_file, 'w', newline='', encoding='utf-8') as csvfile:
        writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
        writer.writeheader()

        for json_file in sorted(files_to_process):
            print(f"Processing {json_file}...", end=" ")
            try:
                with open(json_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                
                if isinstance(data, list):
                    count = 0
                    for entry in data:
                        # Filter out keys that are not in our standard fieldnames to avoid errors
                        # or fill missing keys with empty strings
                        row = {k: entry.get(k, "") for k in fieldnames}
                        writer.writerow(row)
                        count += 1
                    print(f"Added {count} records.")
                    total_records += count
                else:
                    print("Skipped (not a list of records).")
            except Exception as e:
                print(f"Error: {e}")

    print(f"\nSuccessfully converted {len(files_to_process)} files to {output_file}.")
    print(f"Total records: {total_records}")

def main():
    parser = argparse.ArgumentParser(description="Convert CPT JSON chunks to a single CSV file.")
    parser.add_argument("input_path", help="Path to a JSON file or a directory containing JSON files.")
    parser.add_argument("--output", "-o", default="cpt_codes.csv", help="Output CSV file path.")
    
    args = parser.parse_args()
    
    json_to_csv(args.input_path, args.output)

if __name__ == "__main__":
    main()


EXAMPLE_USAGE = """

SINGLE FILE:
uv run rag/shared_libraries/json_to_csv.py 
/workspaces/adk-samples/python/agents/RAG/cpt_39_62_chapter.json --output single_chapter.csv

DIRECTORY OF FILES:
uv run rag/shared_libraries/json_to_csv.py /workspaces/adk-samples/python/agents/RAG/ \
--output all_cpt_codes.csv

"""