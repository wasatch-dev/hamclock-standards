#!/usr/bin/python3
# Copyright 2026 Open HamClock Standards
# SPDX-License-Identifier: Apache-2.0
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may find a copy of the License in the LICENSE file at the repo root.

"""
convert api-doc.md (markdown table) to api-doc.txt (plain text table)
"""
import sys

def analyze_md(filename):
    entries = []
    
    try:
        with open(filename, 'r') as f:
            lines = f.readlines()
        
        # Find the table start after ---
        table_start = False
        header_skipped = False
        for line in lines:
            line = line.strip()
            if line == '---':
                table_start = True
                continue
            if table_start and line.startswith('|'):
                if not header_skipped:
                    header_skipped = True
                    continue  # skip the header row
                if line.find(':---') != -1:
                    continue  # skip the separator row
                # Parse table row
                parts = [p.strip() for p in line.split('|')[1:-1]]  # skip first and last empty
                if len(parts) == 9:
                    path, arg, units, min_, max_, default, required, samples, proposal = parts
                    entries.append({
                        'path': path,
                        'arg': arg,
                        'units': units,
                        'min': min_,
                        'max': max_,
                        'default': default,
                        'required': required,
                        'samples': samples,
                        'proposal': proposal
                    })

        # Print License Header
        print("# API Documentation")
        print("This work is licensed under a [Creative Commons Attribution-NoDerivatives 4.0 International License](https://creativecommons.org/licenses/by-nd/4.0/).")
        print("\n---\n")

        # Print the Report Header
        header = f"{'path':<30} | {'Argument':<20} | {'Units':<8} | {'Min':<6} | {'Max':<6} | {'Default':<8} | {'required':<9} | {'sample values':<30} | {'Proposal'}"
        print(header)
        print("-" * len(header))

        # Group by path
        current_path = None
        for entry in entries:
            if entry['path']:
                if current_path:
                    print("-" * len(header))
                current_path = entry['path']
                # Print path row
                print(f"{entry['path']:<30} | {'':<20} | {'':<8} | {'':<6} | {'':<6} | {'':<8} | {'':<9} | {'':<30} |")
            # Print arg row if arg exists
            if entry['arg']:
                print(f"{'':<30} | {entry['arg']:<20} | {entry['units']:<8} | {entry['min']:<6} | {entry['max']:<6} | {entry['default']:<8} | {entry['required']:<9} | {entry['samples']:<30} | {entry['proposal']}")
        
        if current_path:
            print("-" * len(header))

    except FileNotFoundError:
        print(f"Error: The file '{filename}' was not found.")

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python3 script_name.py <filename>")
        sys.exit(1)

    target_file = sys.argv[1]
    analyze_md(target_file)
