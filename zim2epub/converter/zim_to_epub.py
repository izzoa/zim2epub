"""
Main ZIM to EPUB converter class.
"""

import os
import logging
from ebooklib import epub
from libzim.reader import Archive
from zim2epub.utils.logging_utils import setup_logger
from zim2epub.converter.metadata import MetadataExtractor
from zim2epub.converter.image_processor import ImageProcessor
from zim2epub.converter.toc_generator import TocGenerator
from zim2epub.converter.article_extractor import StandardExtractor
from zim2epub.converter.full_crawl_extractor import FullCrawlExtractor

logger = logging.getLogger('zim2epub')

class ZimToEpub:
    """
    Class to handle the conversion from ZIM to EPUB format.
    """
    
    def __init__(self, zim_path, output_path=None, include_images=True, 
                 generate_toc=True, max_articles=None, verbose=False, full_crawl=False):
        """
        Initialize the converter with the given parameters.
        
        Args:
            zim_path (str): Path to the ZIM file
            output_path (str, optional): Path for the output EPUB file
            include_images (bool): Whether to include images in the EPUB
            generate_toc (bool): Whether to generate a table of contents
            max_articles (int, optional): Maximum number of articles to include
            verbose (bool): Whether to show verbose output
            full_crawl (bool): Whether to use full crawl mode to extract all articles
        """
        # Set up logger
        self.logger = setup_logger(verbose)
        
        self.zim_path = zim_path
        self.include_images = include_images
        self.generate_toc = generate_toc
        self.max_articles = max_articles
        self.verbose = verbose
        self.full_crawl = full_crawl
        
        # Set output path if not provided
        if output_path is None:
            base_name = os.path.basename(zim_path)
            name_without_ext = os.path.splitext(base_name)[0]
            self.output_path = f"{name_without_ext}.epub"
        else:
            self.output_path = output_path
        
        # Initialize the EPUB book
        self.book = epub.EpubBook()
        
        # Open the ZIM file
        try:
            self.zim = Archive(zim_path)
            logger.info(f"Successfully opened ZIM file: {zim_path}")
        except Exception as e:
            logger.error(f"Failed to open ZIM file: {e}")
            raise
    
    def convert(self):
        """
        Convert the ZIM file to EPUB format.
        
        Returns:
            str: Path to the created EPUB file
        """
        try:
            # Set metadata
            self._set_metadata()
            
            # Process articles
            self._process_articles()
            
            # Process images if needed
            if self.include_images:
                self._process_images()
            
            # Generate table of contents if needed
            if self.generate_toc:
                self._generate_toc()
            
            # Add default NCX and Nav files
            self.book.add_item(epub.EpubNcx())
            self.book.add_item(epub.EpubNav())
            
            # Add CSS
            self._add_css()
            
            # Write the EPUB file
            epub.write_epub(self.output_path, self.book, {})
            logger.info(f"Successfully created EPUB file: {self.output_path}")
            
            return self.output_path
        
        except Exception as e:
            logger.error(f"Error during conversion: {e}")
            raise
    
    def _set_metadata(self):
        """Set metadata for the EPUB file from the ZIM metadata."""
        try:
            # Create metadata extractor
            metadata_extractor = MetadataExtractor(self.zim, self.zim_path)
            
            # Extract metadata
            metadata = metadata_extractor.extract_metadata()
            
            # Set EPUB metadata
            self.book.set_title(metadata['title'])
            self.book.set_language(metadata['language'])
            self.book.add_author(metadata['creator'])
            self.book.add_metadata('DC', 'publisher', metadata['publisher'])
            self.book.add_metadata('DC', 'description', metadata['description'])
            self.book.add_metadata('DC', 'date', metadata['date'])
            self.book.add_metadata('DC', 'source', metadata['source'])
            
            # Set identifier
            self.book.set_identifier(metadata['identifier'])
            
            logger.info("Metadata set successfully")
        
        except Exception as e:
            logger.error(f"Error setting metadata: {e}")
            raise
    
    def _process_articles(self):
        """Process articles from the ZIM file and add them to the EPUB."""
        try:
            # Create image processor if needed
            image_processor = ImageProcessor(self.zim, self.book) if self.include_images else None
            
            # Create article extractor
            if self.full_crawl:
                logger.info("Using full crawl mode to extract all articles")
                extractor = FullCrawlExtractor(self.zim, image_processor)
            else:
                extractor = StandardExtractor(self.zim, image_processor)
            
            # Extract articles
            self.articles = extractor.extract_articles()
            
            # Add articles to the book
            for filename, article_info in self.articles.items():
                # Create the article
                article = epub.EpubHtml(
                    title=article_info['title'],
                    file_name=f"{filename}.xhtml",
                    lang=self.book.language
                )
                
                # Set the content
                article.content = f"<h1>{article_info['title']}</h1>"
                
                # Add the article to the book
                self.book.add_item(article)
            
            logger.info(f"Added {len(self.articles)} articles to the book")
        
        except Exception as e:
            logger.error(f"Error processing articles: {e}")
            raise
    
    def _process_images(self):
        """Process images from the ZIM file and add them to the EPUB."""
        try:
            # Create image processor
            image_processor = ImageProcessor(self.zim, self.book)
            
            # Process images
            image_processor.process_images()
        
        except Exception as e:
            logger.error(f"Error processing images: {e}")
            raise
    
    def _generate_toc(self):
        """Generate a table of contents for the EPUB."""
        try:
            # Create TOC generator
            toc_generator = TocGenerator(self.book)
            
            # Generate TOC
            toc_generator.generate_toc(self.articles)
        
        except Exception as e:
            logger.error(f"Error generating table of contents: {e}")
            raise
    
    def _add_css(self):
        """Add CSS to the EPUB."""
        try:
            # Create CSS
            style = """
            body {
                font-family: serif;
                margin: 5%;
                text-align: justify;
            }
            h1, h2, h3, h4, h5, h6 {
                font-family: sans-serif;
                margin-top: 1em;
                margin-bottom: 0.5em;
            }
            img {
                max-width: 100%;
                height: auto;
            }
            table {
                border-collapse: collapse;
                margin: 1em 0;
            }
            th, td {
                border: 1px solid #ccc;
                padding: 0.5em;
            }
            """
            
            # Add CSS file
            css = epub.EpubItem(
                uid="style_default",
                file_name="style/default.css",
                media_type="text/css",
                content=style
            )
            self.book.add_item(css)
            
            # Add CSS to all HTML files
            for item in self.book.items:
                if isinstance(item, epub.EpubHtml):
                    item.add_item(css)
            
            logger.info("CSS added successfully")
        
        except Exception as e:
            logger.error(f"Error adding CSS: {e}")
            raise 