#!/usr/bin/env python3
"""
Example script demonstrating how to use the ZimToEpub class programmatically.
"""

import sys
from zim2epub import ZimToEpub

def main():
    """
    Example usage of the ZimToEpub class.
    """
    if len(sys.argv) < 2:
        print("Usage: python example.py <path_to_zim_file>")
        return 1
    
    zim_path = sys.argv[1]
    
    # Example 1: Basic conversion
    print("Example 1: Basic conversion")
    converter = ZimToEpub(
        zim_path=zim_path,
        output_path="example_basic.epub",
        verbose=True
    )
    converter.convert()
    
    # Example 2: Conversion without images
    print("\nExample 2: Conversion without images")
    converter = ZimToEpub(
        zim_path=zim_path,
        output_path="example_no_images.epub",
        include_images=False,
        verbose=True
    )
    converter.convert()
    
    # Example 3: Conversion with limited articles
    print("\nExample 3: Conversion with limited articles")
    converter = ZimToEpub(
        zim_path=zim_path,
        output_path="example_limited.epub",
        max_articles=10,
        verbose=True
    )
    converter.convert()
    
    print("\nAll examples completed successfully!")
    return 0

if __name__ == "__main__":
    sys.exit(main()) 