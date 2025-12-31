import os
import json
import csv
import argparse
import glob

def jsonl_to_csv(input_path, output_file):
    # Determine list of files to process
    files_to_process = []
    if os.path.isfile(input_path):
        files_to_process.append(input_path)
    elif os.path.isdir(input_path):
        # Find all jsonl files in the directory
        files_to_process = glob.glob(os.path.join(input_path, "*.jsonl"))
    else:
        print(f"Error: Input path '{input_path}' not found.")
        return

    if not files_to_process:
        print("No JSONL files found to process.")
        return

    print(f"Found {len(files_to_process)} JSONL files.")

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

        for jsonl_file in sorted(files_to_process):
            print(f"Processing {jsonl_file}...", end=" ")
            file_count = 0
            try:
                with open(jsonl_file, 'r', encoding='utf-8') as f:
                    for line_num, line in enumerate(f, 1):
                        line = line.strip()
                        if not line:
                            continue
                        try:
                            entry = json.loads(line)
                            # Filter out keys that are not in our standard fieldnames to avoid errors
                            # or fill missing keys with empty strings
                            row = {k: entry.get(k, "") for k in fieldnames}
                            writer.writerow(row)
                            file_count += 1
                        except json.JSONDecodeError:
                            print(f"\n  [Warning] Skipping invalid JSON on line {line_num} of {jsonl_file}")
                
                print(f"Added {file_count} records.")
                total_records += file_count
            except Exception as e:
                print(f"\nError reading file {jsonl_file}: {e}")

    print(f"\nSuccessfully converted {len(files_to_process)} files to {output_file}.")
    print(f"Total records: {total_records}")

def main():
    parser = argparse.ArgumentParser(description="Convert CPT JSONL chunks to a single CSV file.")
    parser.add_argument("input_path", help="Path to a JSONL file or a directory containing JSONL files.")
    parser.add_argument("--output", "-o", default="cpt_codes.csv", help="Output CSV file path.")
    
    args = parser.parse_args()
    
    jsonl_to_csv(args.input_path, args.output)

if __name__ == "__main__":
    main()
