"""
Article extraction for ZIM to EPUB conversion.
"""

import os
import re
import logging
from tqdm import tqdm
from urllib.parse import unquote
from bs4 import BeautifulSoup
from abc import ABC, abstractmethod
from zim2epub.utils.html_utils import parse_html, sanitize_text

logger = logging.getLogger('zim2epub')

class ArticleExtractor(ABC):
    """
    Base class for article extraction strategies.
    """
    
    def __init__(self, zim_archive, image_processor=None):
        """
        Initialize the article extractor.
        
        Args:
            zim_archive: The ZIM archive
            image_processor: Optional image processor
        """
        self.zim = zim_archive
        self.image_processor = image_processor
        self.articles = {}  # Dictionary to store article entries for TOC generation
        self.counter = 0  # Counter for file naming
    
    @abstractmethod
    def extract_articles(self):
        """
        Extract articles from the ZIM file.
        
        Returns:
            dict: Dictionary of articles
        """
        pass
    
    def process_entry(self, entry, is_main=False):
        """
        Process a ZIM entry and add it to the articles.
        
        Args:
            entry: ZIM entry
            is_main (bool): Whether this is the main entry
            
        Returns:
            bool: True if the entry was processed successfully
        """
        try:
            # Skip redirects
            if entry.is_redirect:
                return False
            
            # Get the item
            item = entry.get_item()
            
            # Skip non-HTML entries
            if not item.mimetype.startswith('text/html'):
                return False
            
            # Get the content
            content_bytes = item.content.tobytes()
            
            # Parse the HTML
            soup = parse_html(content_bytes)
            
            # Extract the title
            title = sanitize_text(entry.title) or "Untitled"
            
            # Generate a filename
            filename_base = f"article_{self.counter}"
            self.counter += 1
            
            # Process images if needed
            if self.image_processor:
                soup = self.image_processor.extract_images_from_html(soup, entry.path)
            
            # Add the article to the book
            self._add_html_as_article(soup, filename_base, title, is_main)
            
            if is_main:
                logger.info(f"Added main entry as article: {title}")
            else:
                logger.info(f"Added article: {title}")
            
            return True
        
        except Exception as e:
            logger.warning(f"Error processing entry {entry.path}: {e}")
            return False
    
    def _add_html_as_article(self, soup, filename_base, title, is_main=False):
        """
        Add HTML content as an article to the book.
        
        Args:
            soup: BeautifulSoup object
            filename_base: Base filename
            title: Article title
            is_main (bool): Whether this is the main entry
            
        Returns:
            bool: True if the article was added successfully
        """
        try:
            # Store for TOC generation
            self.articles[filename_base] = {
                'title': title,
                'chapter': None
            }
            
            return True
        
        except Exception as e:
            logger.warning(f"Error adding HTML as article: {e}")
            return False


class StandardExtractor(ArticleExtractor):
    """
    Standard article extraction strategy.
    """
    
    def extract_articles(self):
        """
        Extract articles using the standard method.
        
        Returns:
            dict: Dictionary of articles
        """
        try:
            # Get main page if available
            main_entry = None
            try:
                if self.zim.has_main_entry:
                    main_entry = self.zim.main_entry
                    logger.info(f"Main entry found at: {main_entry.path}")
            except Exception as e:
                logger.warning(f"No main entry found: {e}")
            
            # Process the main entry first if available
            if main_entry:
                self.process_entry(main_entry, is_main=True)
            
            # Process other entries
            entries = []
            
            # Get article paths
            article_paths = self._get_article_paths()
            logger.info(f"Found {len(article_paths)} potential article paths")
            
            # Track skipped entries
            skipped_reasons = {
                "not_found": 0,
                "redirect": 0,
                "non_html": 0,
                "duplicate": 0,
                "error": 0
            }
            
            # Process each path
            for path in article_paths:
                try:
                    # Try with and without namespace prefix, and with URL decoding
                    paths_to_try = [
                        path,
                        unquote(path),
                        f"A/{path}",
                        f"A/{unquote(path)}",
                        path[2:] if path.startswith('A/') else path,
                        unquote(path[2:]) if path.startswith('A/') else unquote(path)
                    ]
                    
                    entry = None
                    for p in paths_to_try:
                        try:
                            if self.zim.has_entry_by_path(p):
                                entry = self.zim.get_entry_by_path(p)
                                if logger.level == logging.DEBUG:
                                    logger.debug(f"Found entry using path: {p}")
                                break
                        except Exception:
                            continue
                    
                    if not entry:
                        if logger.level == logging.DEBUG:
                            logger.debug(f"Path not found: {path}")
                        skipped_reasons["not_found"] += 1
                        continue
                    
                    # Skip if this is the main entry (already processed)
                    if main_entry and entry.path == main_entry.path:
                        if logger.level == logging.DEBUG:
                            logger.debug(f"Skipping main entry: {path}")
                        skipped_reasons["duplicate"] += 1
                        continue
                    
                    # Skip redirects
                    if entry.is_redirect:
                        if logger.level == logging.DEBUG:
                            logger.debug(f"Skipping redirect: {path}")
                        skipped_reasons["redirect"] += 1
                        continue
                    
                    # Skip non-HTML entries
                    try:
                        item = entry.get_item()
                        if not item.mimetype.startswith('text/html'):
                            if logger.level == logging.DEBUG:
                                logger.debug(f"Skipping non-HTML entry: {path} (mimetype: {item.mimetype})")
                            skipped_reasons["non_html"] += 1
                            continue
                    except Exception as e:
                        if logger.level == logging.DEBUG:
                            logger.debug(f"Error checking mimetype for {path}: {e}")
                        skipped_reasons["error"] += 1
                        continue
                    
                    entries.append(entry)
                except Exception as e:
                    if logger.level == logging.DEBUG:
                        logger.debug(f"Error processing path {path}: {e}")
                    skipped_reasons["error"] += 1
            
            # Log skipped reasons
            if logger.level == logging.INFO:
                for reason, count in skipped_reasons.items():
                    if count > 0:
                        logger.info(f"Skipped {count} entries due to: {reason}")
            
            # Process each entry
            for entry in tqdm(entries, desc="Processing articles", disable=logger.level != logging.INFO):
                self.process_entry(entry)
            
            # If no articles were processed but we have a main entry, try to extract content from it
            if not self.articles and main_entry and main_entry.path not in self.articles:
                logger.warning("No articles were processed. Trying to extract content from main entry.")
                self._extract_content_from_main_entry(main_entry)
            
            logger.info(f"Processed {len(self.articles)} articles")
            
            return self.articles
        
        except Exception as e:
            logger.error(f"Error extracting articles: {e}")
            raise
    
    def _get_article_paths(self):
        """
        Get all article paths from the ZIM file.
        
        Returns:
            list: List of article paths
        """
        paths = []
        
        # Debug: Print some basic ZIM file information
        if logger.level == logging.DEBUG:
            try:
                logger.debug(f"ZIM file info: entry_count={self.zim.entry_count}, article_count={self.zim.article_count}")
                logger.debug(f"ZIM file has_new_namespace_scheme: {self.zim.has_new_namespace_scheme}")
                if self.zim.has_main_entry:
                    logger.debug(f"Main entry path: {self.zim.main_entry.path}")
            except Exception as e:
                logger.warning(f"Error getting ZIM file info: {e}")
        
        # Try to access entries directly by URL
        direct_paths = self._try_direct_url_access()
        if direct_paths:
            paths.extend(direct_paths)
            if logger.level == logging.INFO:
                logger.info(f"Found {len(direct_paths)} paths by direct URL access")
        
        # Try to find a list of articles from the main page or table of contents
        if self.zim.has_main_entry:
            try:
                main_entry = self.zim.main_entry
                item = main_entry.get_item()
                content_bytes = item.content.tobytes()
                
                # Parse the HTML
                soup = parse_html(content_bytes)
                
                # Find all links
                for link in soup.find_all('a'):
                    href = link.get('href')
                    if href and not href.startswith(('http://', 'https://')):
                        # Clean up the path
                        path = href.split('#')[0]  # Remove fragment
                        if path and path not in paths:
                            paths.append(path)
            except Exception as e:
                logger.warning(f"Error extracting links from main entry: {e}")
        
        # If we couldn't find any articles, try some common paths
        if not paths:
            # Try common article paths
            common_paths = [
                'A/index', 'A/main', 'A/home', 'A/welcome', 'A/start',
                'index', 'main', 'home', 'welcome', 'start',
                'wiki/Main_Page', 'wiki/index', 'wiki/home',
                'wikipedia/Main_Page', 'wikipedia/index',
                'A/Main_Page', 'Main_Page',
                'A', 'C', 'M', 'I', 'W'
            ]
            
            for path in common_paths:
                try:
                    if self.zim.has_entry_by_path(path):
                        paths.append(path)
                except Exception as e:
                    logger.warning(f"Error checking path {path}: {e}")
        
        return paths
    
    def _try_direct_url_access(self):
        """
        Try to access entries directly by URL.
        
        Returns:
            list: List of paths
        """
        paths = []
        
        # Try common URL patterns
        url_patterns = [
            # Try to find articles by iterating through indices
            lambda i: f"A/{i}",
            lambda i: f"A/article_{i}",
            lambda i: f"A/page_{i}",
            lambda i: f"{i}",
            lambda i: f"article_{i}",
            lambda i: f"page_{i}"
        ]
        
        # Try each pattern
        for pattern in url_patterns:
            # Try a reasonable number of indices
            for i in range(100):
                try:
                    path = pattern(i)
                    if self.zim.has_entry_by_path(path):
                        paths.append(path)
                except Exception:
                    continue
        
        return paths
    
    def _extract_content_from_main_entry(self, main_entry):
        """
        Extract content from the main entry when no articles are found.
        
        Args:
            main_entry: Main ZIM entry
        """
        try:
            # Get the main entry content
            item = main_entry.get_item()
            content_bytes = item.content.tobytes()
            
            # Parse the HTML
            soup = parse_html(content_bytes)
            
            # Extract the title
            title = sanitize_text(main_entry.title) or "Main Page"
            
            # Add the main entry as an article
            filename_base = "main"
            self._add_html_as_article(soup, filename_base, title, is_main=True)
            
            # Extract sections
            sections_count = 0
            for section in soup.find_all(['h1', 'h2', 'h3']):
                # Get the section title
                section_title = section.get_text().strip()
                if not section_title:
                    continue
                
                # Get the section content
                section_content = []
                for sibling in section.find_next_siblings():
                    if sibling.name in ['h1', 'h2', 'h3']:
                        break
                    section_content.append(str(sibling))
                
                if not section_content:
                    continue
                
                # Create a new soup for the section
                section_soup = BeautifulSoup(f"<h1>{section_title}</h1>{''.join(section_content)}", 'lxml')
                
                # Add the section as an article
                section_filename = f"section_{sections_count}"
                self._add_html_as_article(section_soup, section_filename, section_title)
                
                sections_count += 1
            
            logger.info(f"Extracted main entry and {sections_count} sections")
        
        except Exception as e:
            logger.warning(f"Error extracting content from main entry: {e}") 