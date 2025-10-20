#!/usr/bin/env python3
"""
Script to create a complete HTML file for manual mapping of Church Slavonic character codes.
Handles both char/26526 and char/26528 URL patterns.
"""

import os
from pathlib import Path

def read_hex_chunks(filename):
    """Read hex chunks from the text file."""
    chunks = []
    try:
        with open(filename, 'r', encoding='utf-8') as f:
            for line in f:
                chunk = line.strip()
                if chunk:
                    chunks.append(chunk)
        return chunks
    except Exception as e:
        print(f"Error reading {filename}: {e}")
        return []

def generate_html_mapping(all_chunks, char_26526_chunks, char_26528_chunks, output_file):
    """Generate HTML file with Church Slavonic codes and their images."""
    
    html_content = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Complete Church Slavonic Character Code Mapping</title>
    <style>
        body {{
            font-family: Arial, sans-serif;
            margin: 20px;
            background-color: #f5f5f5;
        }}
        .container {{
            max-width: 1200px;
            margin: 0 auto;
            background-color: white;
            padding: 20px;
            border-radius: 8px;
            box-shadow: 0 2px 10px rgba(0,0,0,0.1);
        }}
        h1 {{
            color: #333;
            text-align: center;
            margin-bottom: 30px;
        }}
        .stats {{
            background-color: #e8f4f8;
            padding: 15px;
            border-radius: 5px;
            margin-bottom: 30px;
            text-align: center;
        }}
        .character-grid {{
            display: grid;
            grid-template-columns: repeat(auto-fill, minmax(300px, 1fr));
            gap: 20px;
            margin-top: 20px;
        }}
        .character-item {{
            border: 1px solid #ddd;
            border-radius: 8px;
            padding: 15px;
            background-color: #fafafa;
            text-align: center;
            transition: box-shadow 0.3s ease;
        }}
        .character-item:hover {{
            box-shadow: 0 4px 12px rgba(0,0,0,0.15);
        }}
        .code {{
            font-family: 'Courier New', monospace;
            font-size: 18px;
            font-weight: bold;
            color: #2c3e50;
            margin-bottom: 10px;
            background-color: #ecf0f1;
            padding: 8px;
            border-radius: 4px;
        }}
        .image-container {{
            margin: 10px 0;
            min-height: 60px;
            display: flex;
            align-items: center;
            justify-content: center;
        }}
        .character-image {{
            max-width: 100%;
            max-height: 80px;
            border: 1px solid #bdc3c7;
            border-radius: 4px;
            background-color: white;
        }}
        .url {{
            font-family: 'Courier New', monospace;
            font-size: 10px;
            color: #7f8c8d;
            word-break: break-all;
            margin-top: 8px;
        }}
        .unicode-input {{
            width: 100%;
            padding: 8px;
            margin-top: 10px;
            border: 1px solid #bdc3c7;
            border-radius: 4px;
            font-family: 'Courier New', monospace;
            font-size: 14px;
        }}
        .unicode-input:focus {{
            outline: none;
            border-color: #3498db;
            box-shadow: 0 0 5px rgba(52, 152, 219, 0.3);
        }}
        .instructions {{
            background-color: #fff3cd;
            border: 1px solid #ffeaa7;
            border-radius: 5px;
            padding: 15px;
            margin-bottom: 20px;
        }}
        .instructions h3 {{
            margin-top: 0;
            color: #856404;
        }}
        .instructions ul {{
            margin-bottom: 0;
        }}
        .instructions li {{
            margin-bottom: 5px;
        }}
        .url-type {{
            font-size: 12px;
            color: #e67e22;
            font-weight: bold;
            margin-bottom: 5px;
        }}
    </style>
</head>
<body>
    <div class="container">
        <h1>Complete Church Slavonic Character Code Mapping</h1>
        
        <div class="stats">
            <strong>Total Characters to Map:</strong> {len(all_chunks)}<br>
            <strong>char/26526 characters:</strong> {len(char_26526_chunks)}<br>
            <strong>char/26528 characters:</strong> {len(char_26528_chunks)}<br>
            <strong>Overlapping characters:</strong> {len(char_26526_chunks & char_26528_chunks)}
        </div>
        
        <div class="instructions">
            <h3>Instructions for Manual Mapping:</h3>
            <ul>
                <li>Each character code is displayed with its corresponding image from pravenc.ru</li>
                <li>Look at the image and identify what Church Slavonic character it represents</li>
                <li>Enter the Unicode character or code in the input field below each image</li>
                <li>You can use either the actual Unicode character (e.g., Ѣ) or the Unicode code (e.g., U+0462)</li>
                <li>Save this file after completing the mapping for the next step</li>
            </ul>
        </div>
        
        <div class="character-grid">
"""

    # Add each character code with its image
    for i, chunk in enumerate(sorted(all_chunks), 1):
        # Determine which URL pattern to use
        if chunk in char_26526_chunks and chunk in char_26528_chunks:
            # If chunk exists in both, use char/26526 as primary
            image_url = f"https://pravenc.ru/char/26526/{chunk}/image.png"
            url_type = "char/26526 (also in char/26528)"
        elif chunk in char_26526_chunks:
            image_url = f"https://pravenc.ru/char/26526/{chunk}/image.png"
            url_type = "char/26526"
        else:
            image_url = f"https://pravenc.ru/char/26528/{chunk}/image.png"
            url_type = "char/26528"
        
        html_content += f"""
            <div class="character-item">
                <div class="url-type">{url_type}</div>
                <div class="code">{chunk}</div>
                <div class="image-container">
                    <img src="{image_url}" alt="Church Slavonic character {chunk}" class="character-image" 
                         onerror="this.style.display='none'; this.nextElementSibling.style.display='block';">
                    <div style="display:none; color:#e74c3c; font-size:12px;">Image not found</div>
                </div>
                <input type="text" class="unicode-input" placeholder="Enter Unicode character or code (e.g., Ѣ or U+0462)" 
                       data-code="{chunk}" data-url="{image_url}">
                <div class="url">{image_url}</div>
            </div>
"""

    html_content += """
        </div>
        
        <div style="margin-top: 40px; padding: 20px; background-color: #e8f5e8; border-radius: 5px;">
            <h3>Mapping Progress</h3>
            <p>After completing the mapping, you can extract the mappings using JavaScript:</p>
            <pre style="background-color: #f8f9fa; padding: 10px; border-radius: 4px; overflow-x: auto;">
// Run this in the browser console to extract mappings:
const mappings = {};
document.querySelectorAll('.unicode-input').forEach(input => {
    if (input.value.trim()) {
        mappings[input.dataset.code] = input.value.trim();
    }
});
console.log(JSON.stringify(mappings, null, 2));
            </pre>
        </div>
    </div>
    
    <script>
        // Add some helpful functionality
        document.addEventListener('DOMContentLoaded', function() {
            // Add progress tracking
            function updateProgress() {
                const total = document.querySelectorAll('.unicode-input').length;
                const filled = document.querySelectorAll('.unicode-input[value]').length;
                const progress = Math.round((filled / total) * 100);
                console.log(`Mapping progress: ${filled}/${total} (${progress}%)`);
            }
            
            // Update progress on input
            document.querySelectorAll('.unicode-input').forEach(input => {
                input.addEventListener('input', updateProgress);
            });
        });
    </script>
</body>
</html>
"""

    try:
        with open(output_file, 'w', encoding='utf-8') as f:
            f.write(html_content)
        print(f"Complete HTML mapping file created: {output_file}")
        return True
    except Exception as e:
        print(f"Error creating HTML file: {e}")
        return False

def main():
    """Main function to create the complete HTML mapping file."""
    print("Creating Complete Church Slavonic Character Mapping HTML")
    print("=" * 60)
    
    # Read hex chunks from all files
    all_chunks = read_hex_chunks("all_church_slavonic_hex_chunks.txt")
    char_26526_chunks = set(read_hex_chunks("char_26526_hex_chunks.txt"))
    char_26528_chunks = set(read_hex_chunks("char_26528_hex_chunks.txt"))
    
    if not all_chunks:
        print("No hex chunks found!")
        return
    
    print(f"Found {len(all_chunks)} total character codes to map")
    print(f"char/26526: {len(char_26526_chunks)} codes")
    print(f"char/26528: {len(char_26528_chunks)} codes")
    print(f"Overlapping: {len(char_26526_chunks & char_26528_chunks)} codes")
    
    # Generate HTML file
    output_file = "complete_church_slavonic_mapping.html"
    if generate_html_mapping(all_chunks, char_26526_chunks, char_26528_chunks, output_file):
        print(f"\n✅ Complete HTML mapping file created successfully!")
        print(f"📁 File: {output_file}")
        print(f"📊 Total characters: {len(all_chunks)}")
        print(f"\n🌐 Open the HTML file in your browser to start mapping:")
        print(f"   file://{Path(output_file).absolute()}")
        print(f"\n💡 Instructions:")
        print(f"   - Each character code is displayed with its image")
        print(f"   - Enter the Unicode character in the input field")
        print(f"   - Save the file after completing the mapping")
    else:
        print("❌ Failed to create HTML mapping file")

if __name__ == "__main__":
    main()
