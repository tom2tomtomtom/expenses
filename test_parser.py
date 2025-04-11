#!/usr/bin/env python3
"""
Test script for receipt parser functionality
"""

import os
import sys
import json
import argparse
from src.receipt_parser import ReceiptParserFactory

def main():
    """Main entry point for the test script"""
    parser = argparse.ArgumentParser(description='Receipt Parser Test')
    parser.add_argument('--input', help='Input file or directory with email data in JSON format')
    parser.add_argument('--output-dir', default='test_results', help='Output directory for parsed receipt data')
    
    args = parser.parse_args()
    
    if not args.input:
        print("Error: --input argument is required")
        return 1
    
    # Create output directory if it doesn't exist
    if not os.path.exists(args.output_dir):
        os.makedirs(args.output_dir)
    
    # Create receipt parser
    receipt_parser = ReceiptParserFactory.create_parser()
    
    # Process input file or directory
    if os.path.isdir(args.input):
        # Process all JSON files in directory
        files = [f for f in os.listdir(args.input) if f.endswith('.json')]
        for filename in files:
            input_path = os.path.join(args.input, filename)
            process_file(input_path, args.output_dir, receipt_parser)
    else:
        # Process single file
        process_file(args.input, args.output_dir, receipt_parser)
    
    return 0

def process_file(input_path, output_dir, receipt_parser):
    """Process a single input file"""
    try:
        print(f"Processing {input_path}...")
        
        # Load email data
        with open(input_path, 'r') as f:
            email_data = json.load(f)
        
        # Parse receipt data
        receipt_data = receipt_parser.parse(email_data)
        
        # Generate output filename
        base_name = os.path.basename(input_path)
        output_path = os.path.join(output_dir, f"parsed_{base_name}")
        
        # Save parsed data
        with open(output_path, 'w') as f:
            json.dump(receipt_data, f, indent=2, default=str)
        
        print(f"Parsed receipt data saved to {output_path}")
        print(f"Vendor: {receipt_data.get('vendor')}")
        print(f"Date: {receipt_data.get('date')}")
        print(f"Total: {receipt_data.get('total')}")
        print(f"Confidence: {receipt_data.get('confidence')}")
        print()
        
    except Exception as e:
        print(f"Error processing {input_path}: {str(e)}")

if __name__ == "__main__":
    sys.exit(main())
