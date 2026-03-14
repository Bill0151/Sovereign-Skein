import html2text
import os

def convert_html_to_md(input_html_path, output_md_path):
    print(f"Reading {input_html_path}...")
    
    # Check if the file exists before attempting to open it
    if not os.path.exists(input_html_path):
        print(f"Error: Could not find '{input_html_path}'. Please check the file name.")
        return

    with open(input_html_path, "r", encoding="utf-8") as html_file:
        html_content = html_file.read()

    print("Stripping images and converting to Markdown...")
    
    # Configure the html2text parser
    parser = html2text.HTML2Text()
    parser.ignore_images = True       # This strips all the images to save space
    parser.ignore_links = False       # Keeps any URLs we shared intact
    parser.body_width = 0             # Prevents awkward line wrapping
    parser.bypass_tables = False      # Preserves any markdown tables we generated

    # Process the conversion
    markdown_content = parser.handle(html_content)

    print(f"Saving output to {output_md_path}...")
    with open(output_md_path, "w", encoding="utf-8") as md_file:
        md_file.write(markdown_content)
        
    print("Conversion complete! You can now edit the .md file.")

if __name__ == "__main__":
    # Ensure your downloaded Gemini HTML file is in the same folder, 
    # or update this string with the exact file path.
    INPUT_FILE = "Google Gemini.html" 
    OUTPUT_FILE = "sovereign_skein_master_history.md"
    
    convert_html_to_md(INPUT_FILE, OUTPUT_FILE)