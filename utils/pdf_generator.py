import pdfkit
import os
from datetime import datetime
import subprocess
import shutil
import sys

def find_wkhtmltopdf():
    """Find wkhtmltopdf executable in common installation paths"""
    possible_paths = [
        'C:\\Program Files\\wkhtmltopdf\\bin\\wkhtmltopdf.exe',
        'C:\\Program Files (x86)\\wkhtmltopdf\\bin\\wkhtmltopdf.exe',
        '/usr/local/bin/wkhtmltopdf',
        '/usr/bin/wkhtmltopdf'
    ]
    
    for path in possible_paths:
        if os.path.exists(path):
            return path
            
    # If not found in common paths, try to find in PATH
    wkhtmltopdf = shutil.which('wkhtmltopdf')
    if wkhtmltopdf:
        return wkhtmltopdf
        
    return None

def create_pdf(html_content, name):
    """Convert HTML resume to PDF"""
    temp_html = None
    try:
        # Create output directory if not exists
        output_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "output")
        os.makedirs(output_dir, exist_ok=True)
        
        # Generate filename
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = os.path.join(output_dir, f"{name.replace(' ', '_')}_Resume_{timestamp}.pdf")
        
        # Create a temporary HTML file
        temp_html = os.path.join(output_dir, f"temp_{timestamp}.html")
        with open(temp_html, 'w', encoding='utf-8') as f:
            f.write(html_content)
        
        # Find wkhtmltopdf executable
        wkhtmltopdf_path = find_wkhtmltopdf()
        if not wkhtmltopdf_path:
            raise Exception("wkhtmltopdf not found. Please install wkhtmltopdf from https://wkhtmltopdf.org/downloads.html")

        try:
            # Configure pdfkit options with proper margin settings
            options = {
                'page-size': 'A4',
                'margin-top': '0.5in',
                'margin-right': '0.5in',
                'margin-bottom': '0.5in',
                'margin-left': '0.5in',
                'encoding': 'UTF-8',
                'quiet': None,
                'print-media-type': None,
                'enable-local-file-access': None
            }
            
            # Configure pdfkit to use the found wkhtmltopdf path
            config = pdfkit.configuration(wkhtmltopdf=wkhtmltopdf_path)
            
            # Generate PDF using pdfkit with string input
            pdfkit.from_string(
                html_content,
                filename,
                options=options,
                configuration=config
            )
            
            if not os.path.exists(filename):
                raise Exception("PDF file was not created successfully")
                
            return filename
            
        except Exception as pdf_error:
            raise Exception(f"PDF generation failed: {str(pdf_error)}")
            
    except Exception as e:
        print(f"Error generating PDF: {str(e)}")
        if temp_html and os.path.exists(temp_html):
            try:
                os.remove(temp_html)
            except:
                pass
        raise
        
    finally:
        # Clean up temporary HTML file
        if temp_html and os.path.exists(temp_html):
            try:
                os.remove(temp_html)
            except:
                pass