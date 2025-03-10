"""
Path and URL utilities for ZIM to EPUB conversion.
"""

import os
import re
from urllib.parse import urljoin, urlparse, unquote

def sanitize_filename(filename):
    """
    Sanitize a filename to be safe for file systems.
    
    Args:
        filename (str): The filename to sanitize
        
    Returns:
        str: Sanitized filename
    """
    # Replace invalid characters with underscores
    filename = re.sub(r'[\\/*?:"<>|]', '_', filename)
    # Remove leading/trailing spaces and dots
    filename = filename.strip('. ')
    # Ensure the filename is not empty
    if not filename:
        filename = 'unnamed'
    return filename

def get_extension(path):
    """
    Get the file extension from a path.
    
    Args:
        path (str): The file path
        
    Returns:
        str: The file extension (without the dot) or empty string if no extension
    """
    # Extract the extension
    _, ext = os.path.splitext(path)
    # Remove the dot and return
    return ext[1:] if ext else ""

def get_unique_filename(base_name, extension, existing_files):
    """
    Generate a unique filename that doesn't exist in the given set.
    
    Args:
        base_name (str): The base filename
        extension (str): The file extension
        existing_files (set): Set of existing filenames
        
    Returns:
        str: A unique filename
    """
    counter = 1
    filename = f"{base_name}.{extension}" if extension else base_name
    
    while filename in existing_files:
        filename = f"{base_name}_{counter}.{extension}" if extension else f"{base_name}_{counter}"
        counter += 1
    
    return filename 