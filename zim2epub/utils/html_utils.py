"""
HTML utilities for ZIM to EPUB conversion.
"""

import re
from bs4 import BeautifulSoup

def sanitize_text(text):
    """
    Sanitize text to be XML compatible.
    
    Args:
        text (str or bytes): Text to sanitize
        
    Returns:
        str: Sanitized text
    """
    if text is None:
        return None
    
    # Convert bytes to string if needed
    if isinstance(text, bytes):
        try:
            text = text.decode('utf-8', errors='replace')
        except Exception:
            return "Unknown text"
    
    # Ensure we have a string
    if not isinstance(text, str):
        try:
            text = str(text)
        except Exception:
            return "Unknown text"
    
    # Remove control characters
    text = re.sub(r'[\x00-\x08\x0B\x0C\x0E-\x1F\x7F]', '', text)
    
    # Replace problematic characters
    text = text.replace('\r\n', ' ').replace('\n', ' ').replace('\r', ' ')
    
    return text

def parse_html(content, parser='lxml'):
    """
    Parse HTML content into a BeautifulSoup object.
    
    Args:
        content (str or bytes): HTML content to parse
        parser (str): Parser to use
        
    Returns:
        BeautifulSoup: Parsed HTML
    """
    # Convert bytes to string if needed
    if isinstance(content, bytes):
        # Try different encodings
        for encoding in ['utf-8', 'latin-1', 'cp1252']:
            try:
                content = content.decode(encoding, errors='replace')
                break
            except UnicodeDecodeError:
                continue
        else:
            # If all encodings fail, use utf-8 with replace
            content = content.decode('utf-8', errors='replace')
    
    # Parse the HTML
    return BeautifulSoup(content, parser) 