"""
Command-line interface for ZIM to EPUB conversion.
"""

import os
import sys
import argparse
import logging
from zim2epub.converter.zim_to_epub import ZimToEpub

logger = logging.getLogger('zim2epub')

def parse_args():
    """
    Parse command-line arguments.
    
    Returns:
        argparse.Namespace: Parsed arguments
    """
    parser = argparse.ArgumentParser(
        description="Convert ZIM files to EPUB format",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter
    )
    
    parser.add_argument(
        "zim_file",
        help="Path to the ZIM file to convert"
    )
    
    parser.add_argument(
        "-o", "--output",
        help="Path for the output EPUB file (default: same as input with .epub extension)"
    )
    
    parser.add_argument(
        "--no-images",
        action="store_true",
        help="Do not include images in the EPUB"
    )
    
    parser.add_argument(
        "--no-toc",
        action="store_true",
        help="Do not generate a table of contents"
    )
    
    parser.add_argument(
        "--max-articles",
        type=int,
        help="Maximum number of articles to include"
    )
    
    parser.add_argument(
        "-v", "--verbose",
        action="store_true",
        help="Show verbose output"
    )
    
    parser.add_argument(
        "--full-crawl",
        action="store_true",
        help="Use full crawl mode to extract all articles"
    )
    
    return parser.parse_args()

def main():
    """
    Main function to handle command-line arguments and run the conversion.
    
    Returns:
        int: Exit code
    """
    args = parse_args()
    
    # Check if the ZIM file exists
    if not os.path.isfile(args.zim_file):
        logger.error(f"ZIM file not found: {args.zim_file}")
        return 1
    
    try:
        # Create the converter
        converter = ZimToEpub(
            zim_path=args.zim_file,
            output_path=args.output,
            include_images=not args.no_images,
            generate_toc=not args.no_toc,
            max_articles=args.max_articles,
            verbose=args.verbose,
            full_crawl=args.full_crawl
        )
        
        # Run the conversion
        output_path = converter.convert()
        
        print(f"Conversion completed successfully. EPUB file created at: {output_path}")
        return 0
    
    except Exception as e:
        logger.error(f"Conversion failed: {e}")
        return 1

if __name__ == "__main__":
    sys.exit(main()) 