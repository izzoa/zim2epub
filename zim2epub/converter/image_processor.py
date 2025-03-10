"""
Image processing for ZIM to EPUB conversion.
"""

import os
import logging
import mimetypes
from tqdm import tqdm
from ebooklib import epub
from urllib.parse import unquote
from zim2epub.utils.path_utils import get_extension, get_unique_filename

logger = logging.getLogger('zim2epub')

class ImageProcessor:
    """
    Class to handle image processing for ZIM to EPUB conversion.
    """
    
    def __init__(self, zim_archive, book):
        """
        Initialize the image processor.
        
        Args:
            zim_archive: The ZIM archive
            book: The EPUB book
        """
        self.zim = zim_archive
        self.book = book
        self.images = {}  # Dictionary to store image references for later processing
        self.processed_images = {}  # Dictionary to store processed images to avoid duplicates
    
    def extract_images_from_html(self, soup, article_path):
        """
        Extract image references from HTML content.
        
        Args:
            soup: BeautifulSoup object
            article_path: Path of the article
            
        Returns:
            BeautifulSoup: Updated soup object
        """
        try:
            # Find all images in the HTML
            for img in soup.find_all('img'):
                src = img.get('src')
                if not src:
                    continue
                
                # Skip external images
                if src.startswith(('http://', 'https://')):
                    continue
                
                # Resolve the image path
                img_path = src
                if not img_path.startswith('/'):
                    # Relative path, resolve against the article path
                    base_dir = os.path.dirname(article_path)
                    img_path = os.path.normpath(os.path.join(base_dir, img_path))
                
                # Store the image reference for later processing
                self.images[img_path] = self.images.get(img_path, [])
                self.images[img_path].append(img)
            
            return soup
        
        except Exception as e:
            logger.warning(f"Error extracting images from {article_path}: {e}")
            return soup
    
    def process_images(self):
        """
        Process all collected image references.
        """
        try:
            if not self.images:
                logger.info("No images to process")
                return
            
            logger.info(f"Processing {len(self.images)} unique images")
            
            # Process each image
            for img_path, img_tags in tqdm(self.images.items(), desc="Processing images", disable=not logger.level == logging.INFO):
                try:
                    # Try to get the image from the ZIM file
                    paths_to_try = [
                        img_path,
                        unquote(img_path),
                        f"I/{img_path}",
                        f"I/{unquote(img_path)}",
                        img_path[2:] if img_path.startswith('I/') else img_path,
                        unquote(img_path[2:]) if img_path.startswith('I/') else unquote(img_path)
                    ]
                    
                    image_found = False
                    for p in paths_to_try:
                        try:
                            if self.zim.has_entry_by_path(p):
                                entry = self.zim.get_entry_by_path(p)
                                if entry.is_redirect:
                                    continue
                                
                                item = entry.get_item()
                                
                                # Get the image content
                                content = item.content.tobytes()
                                
                                # Get the mimetype
                                mimetype = self._get_mimetype(item, p)
                                
                                # Get a unique filename for the image
                                filename = self._get_unique_image_filename(p)
                                
                                # Add the image to the EPUB
                                image = epub.EpubImage()
                                image.file_name = filename
                                image.media_type = mimetype
                                image.content = content
                                self.book.add_item(image)
                                
                                # Update all references to this image
                                for img_tag in img_tags:
                                    img_tag['src'] = filename
                                
                                image_found = True
                                break
                        except Exception as e:
                            if logger.level == logging.DEBUG:
                                logger.debug(f"Error processing image path {p}: {e}")
                    
                    if not image_found and logger.level == logging.DEBUG:
                        logger.debug(f"Image not found: {img_path}")
                
                except Exception as e:
                    logger.warning(f"Error processing image {img_path}: {e}")
            
            logger.info("Images processed successfully")
        
        except Exception as e:
            logger.error(f"Error processing images: {e}")
    
    def _get_mimetype(self, item, path):
        """
        Get the mimetype for an image.
        
        Args:
            item: ZIM item
            path: Image path
            
        Returns:
            str: Mimetype
        """
        # Try to get the mimetype from the item
        if hasattr(item, 'mimetype') and item.mimetype:
            return item.mimetype
        
        # Try to guess the mimetype from the path
        ext = get_extension(path).lower()
        if ext:
            # Map common image extensions to mimetypes
            mimetype_map = {
                'jpg': 'image/jpeg',
                'jpeg': 'image/jpeg',
                'png': 'image/png',
                'gif': 'image/gif',
                'svg': 'image/svg+xml',
                'webp': 'image/webp'
            }
            
            if ext in mimetype_map:
                return mimetype_map[ext]
            
            # Try to guess from the extension
            guessed_type = mimetypes.guess_type(f"file.{ext}")[0]
            if guessed_type:
                return guessed_type
        
        # Default to JPEG
        return 'image/jpeg'
    
    def _get_unique_image_filename(self, img_path):
        """
        Get a unique filename for an image.
        
        Args:
            img_path: Image path
            
        Returns:
            str: Unique filename
        """
        # Extract the base name and extension
        base_name = os.path.basename(img_path)
        base_name = os.path.splitext(base_name)[0]
        
        # Clean up the base name
        base_name = base_name.replace('/', '_').replace('\\', '_')
        base_name = base_name.replace('%20', '_').replace(' ', '_')
        
        # Get the extension
        ext = get_extension(img_path)
        if not ext:
            # Default to jpg if no extension
            ext = 'jpg'
        
        # Generate a unique filename
        return get_unique_filename(base_name, ext, self.processed_images) 