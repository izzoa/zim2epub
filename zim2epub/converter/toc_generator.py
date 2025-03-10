"""
Table of contents generation for ZIM to EPUB conversion.
"""

import logging
from ebooklib import epub

logger = logging.getLogger('zim2epub')

class TocGenerator:
    """
    Class to handle table of contents generation for ZIM to EPUB conversion.
    """
    
    def __init__(self, book):
        """
        Initialize the TOC generator.
        
        Args:
            book: The EPUB book
        """
        self.book = book
    
    def generate_toc(self, articles):
        """
        Generate a table of contents for the EPUB.
        
        Args:
            articles (dict): Dictionary of articles
        """
        try:
            if not articles:
                logger.warning("No articles to generate TOC from")
                return
            
            logger.info("Generating table of contents")
            
            # Create the TOC
            toc = []
            chapters = {}
            
            # First pass: collect all chapters
            for filename, article_info in articles.items():
                chapter = article_info.get('chapter')
                if chapter and chapter not in chapters:
                    chapters[chapter] = []
            
            # Second pass: add articles to chapters
            for filename, article_info in articles.items():
                title = article_info.get('title', 'Untitled')
                chapter = article_info.get('chapter')
                
                # Create the TOC entry
                section = epub.Link(f"{filename}.xhtml", title, filename)
                
                if chapter and chapter in chapters:
                    # Add to chapter
                    chapters[chapter].append(section)
                else:
                    # Add directly to TOC
                    toc.append(section)
            
            # Add chapters to TOC
            for chapter, sections in chapters.items():
                if sections:
                    toc.append((chapter, sections))
            
            # Set the TOC
            self.book.toc = toc
            
            # Set the spine
            self.book.spine = ['nav']
            for filename in articles.keys():
                self.book.spine.append(f"{filename}.xhtml")
            
            logger.info("Table of contents generated successfully")
        
        except Exception as e:
            logger.error(f"Error generating table of contents: {e}")
            raise 