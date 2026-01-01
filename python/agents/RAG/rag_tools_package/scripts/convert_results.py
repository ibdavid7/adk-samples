import argparse
import os
import sys

# Add the src directory to the python path so we can import the package
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "src")))

from rag_tools.utils.converters import jsonl_to_csv

def main():
    parser = argparse.ArgumentParser(description="Convert CPT JSONL chunks to a single CSV file.")
    parser.add_argument("input_path", help="Path to a JSONL file or a directory containing JSONL files.")
    parser.add_argument("--output", "-o", default="cpt_codes.csv", help="Output CSV file path.")
    
    args = parser.parse_args()
    
    jsonl_to_csv(args.input_path, args.output)

if __name__ == "__main__":
    main()
