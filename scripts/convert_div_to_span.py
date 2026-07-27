#!/usr/bin/env python3
"""
Script to change <div class="cu">[text]</div> to <span class="cu">[text]</span> in all Markdown files.
"""

import re
from pathlib import Path

from _paths import ARTICLES_DIR

def convert_div_to_span(content):
    """Convert <div class="cu">[text]</div> to <span class="cu">[text]</span>."""
    # Pattern to match <div class="cu">[text]</div>
    pattern = r'<div class="cu">([^<]*)</div>'
    
    def replace_div(match):
        text = match.group(1)
        return f'<span class="cu">{text}</span>'
    
    # Replace all div tags with span tags
    converted_content = re.sub(pattern, replace_div, content)
    
    return converted_content

def process_markdown_files(articles_dir):
    """Process all Markdown files to convert div tags to span tags."""
    
    articles_path = Path(articles_dir)
    if not articles_path.exists():
        print(f"❌ Articles directory not found: {articles_dir}")
        return
    
    # Find all Markdown files
    md_files = list(articles_path.glob('*.md'))
    print(f"📁 Found {len(md_files)} Markdown files to process")
    
    total_conversions = 0
    files_processed = 0
    
    for md_file in md_files:
        try:
            # Read the file
            with open(md_file, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # Count original div tags
            original_divs = len(re.findall(r'<div class="cu">[^<]*</div>', content))
            
            if original_divs > 0:
                # Convert div tags to span tags
                converted_content = convert_div_to_span(content)
                
                # Count conversions
                converted_spans = len(re.findall(r'<span class="cu">[^<]*</span>', converted_content))
                
                if converted_spans > 0:
                    # Write the converted content back to the file
                    with open(md_file, 'w', encoding='utf-8') as f:
                        f.write(converted_content)
                    
                    total_conversions += original_divs
                    files_processed += 1
                    
                    if files_processed % 100 == 0:
                        print(f"📝 Processed {files_processed} files, {total_conversions} conversions so far...")
        
        except Exception as e:
            print(f"❌ Error processing {md_file}: {e}")
    
    print(f"\n📊 Conversion Summary:")
    print(f"   Files processed: {files_processed}")
    print(f"   Total conversions: {total_conversions}")
    print(f"   ✅ Conversion completed successfully!")

def main():
    """Main function to run the conversion."""
    print("Div to Span Converter for Church Slavonic Text")
    print("=" * 50)
    print("This script converts <div class='cu'>[text]</div> to <span class='cu'>[text]</span>")
    print("in all Markdown files in the articles directory.")
    print()
    
    # Process all Markdown files
    process_markdown_files(ARTICLES_DIR)

if __name__ == "__main__":
    main()
