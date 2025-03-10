"""
Metadata extraction for ZIM to EPUB conversion.
"""

import os
import logging
from datetime import datetime
from zim2epub.utils.html_utils import sanitize_text

logger = logging.getLogger('zim2epub')

class MetadataExtractor:
    """
    Class to handle metadata extraction from ZIM files.
    """
    
    def __init__(self, zim_archive, zim_filename):
        """
        Initialize the metadata extractor.
        
        Args:
            zim_archive: The ZIM archive
            zim_filename: The path to the ZIM file
        """
        self.zim = zim_archive
        self.zim_filename = zim_filename
    
    def extract_metadata(self):
        """
        Extract metadata from the ZIM file.
        
        Returns:
            dict: Dictionary of metadata
        """
        try:
            # Get metadata from ZIM file
            title = self.get_metadata("Title") or os.path.basename(self.zim_filename)
            language = self.get_metadata("Language") or "en"
            creator = self.get_metadata("Creator") or "ZIM2EPUB Converter"
            publisher = self.get_metadata("Publisher") or "ZIM2EPUB"
            description = self.get_metadata("Description") or f"Converted from {os.path.basename(self.zim_filename)}"
            
            # Create metadata dictionary
            metadata = {
                'title': title,
                'language': language,
                'creator': creator,
                'publisher': publisher,
                'description': description,
                'date': datetime.now().strftime("%Y-%m-%d"),
                'source': f"Converted from ZIM file: {os.path.basename(self.zim_filename)}",
                'identifier': f"zim2epub-{os.path.basename(self.zim_filename)}-{datetime.now().strftime('%Y%m%d%H%M%S')}"
            }
            
            logger.info("Metadata extracted successfully")
            return metadata
        
        except Exception as e:
            logger.error(f"Error extracting metadata: {e}")
            raise
    
    def get_metadata(self, name):
        """
        Get metadata from the ZIM file.
        
        Args:
            name (str): Name of the metadata field
            
        Returns:
            str: Value of the metadata field or None if not found
        """
        try:
            if name in self.zim.metadata_keys:
                metadata_value = self.zim.get_metadata(name)
                # Handle bytes objects
                if isinstance(metadata_value, bytes):
                    try:
                        return metadata_value.decode('utf-8', errors='replace')
                    except Exception as e:
                        logger.warning(f"Error decoding metadata {name}: {e}")
                        return None
                return metadata_value
            return None
        except Exception as e:
            logger.warning(f"Error getting metadata {name}: {e}")
            return None
    
    def get_main_page_path(self):
        """
        Get the main page path from metadata.
        
        Returns:
            str: Main page path or None if not found
        """
        try:
            # Try different metadata keys for main page
            for key in ['mainPage', 'Main-Page', 'main_page', 'main-page']:
                if key in self.zim.metadata_keys:
                    main_page_path = self.zim.get_metadata(key).decode('utf-8', errors='replace')
                    logger.info(f"Found main page path in metadata: {main_page_path}")
                    return main_page_path
            return None
        except Exception as e:
            logger.warning(f"Error getting main page from metadata: {e}")
            return None 