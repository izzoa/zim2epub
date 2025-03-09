#!/usr/bin/env python3
"""
ZIM to EPUB Converter

This script converts ZIM files (used by Kiwix and others for offline content)
to EPUB format for e-readers.
"""

import os
import sys
import argparse
import re
import tempfile
import logging
from pathlib import Path
from urllib.parse import urljoin, urlparse, unquote
import mimetypes
from datetime import datetime

from bs4 import BeautifulSoup
from tqdm import tqdm
from libzim.reader import Archive
from ebooklib import epub

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger('zim2epub')

class ZimToEpub:
    """
    Class to handle the conversion from ZIM to EPUB format.
    """
    
    def __init__(self, zim_path, output_path=None, include_images=True, 
                 generate_toc=True, max_articles=None, verbose=False):
        """
        Initialize the converter with the given parameters.
        
        Args:
            zim_path (str): Path to the ZIM file
            output_path (str, optional): Path for the output EPUB file
            include_images (bool): Whether to include images in the EPUB
            generate_toc (bool): Whether to generate a table of contents
            max_articles (int, optional): Maximum number of articles to include
            verbose (bool): Whether to show verbose output
        """
        self.zim_path = zim_path
        self.include_images = include_images
        self.generate_toc = generate_toc
        self.max_articles = max_articles
        self.verbose = verbose
        
        # Set output path if not provided
        if output_path is None:
            base_name = os.path.basename(zim_path)
            name_without_ext = os.path.splitext(base_name)[0]
            self.output_path = f"{name_without_ext}.epub"
        else:
            self.output_path = output_path
        
        # Initialize the EPUB book
        self.book = epub.EpubBook()
        
        # Dictionary to store image references for later processing
        self.images = {}
        
        # Dictionary to store processed images to avoid duplicates
        self.processed_images = {}
        
        # Dictionary to store article entries for TOC generation
        self.articles = {}
        
        # Counter for file naming
        self.counter = 0
        
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
            
            # Add a fallback page if no articles were processed
            if not self.articles:
                self._add_fallback_page()
            
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
            # Get metadata from ZIM file
            title = self._sanitize_text(self._get_metadata("Title")) or os.path.basename(self.zim_path)
            language = self._sanitize_text(self._get_metadata("Language")) or "en"
            creator = self._sanitize_text(self._get_metadata("Creator")) or "ZIM2EPUB Converter"
            publisher = self._sanitize_text(self._get_metadata("Publisher")) or "ZIM2EPUB"
            description = self._sanitize_text(self._get_metadata("Description")) or f"Converted from {os.path.basename(self.zim_path)}"
            
            # Set EPUB metadata
            self.book.set_title(title)
            self.book.set_language(language)
            self.book.add_author(creator)
            self.book.add_metadata('DC', 'publisher', publisher)
            self.book.add_metadata('DC', 'description', description)
            self.book.add_metadata('DC', 'date', datetime.now().strftime("%Y-%m-%d"))
            self.book.add_metadata('DC', 'source', f"Converted from ZIM file: {os.path.basename(self.zim_path)}")
            
            # Set identifier
            self.book.set_identifier(f"zim2epub-{os.path.basename(self.zim_path)}-{datetime.now().strftime('%Y%m%d%H%M%S')}")
            
            logger.info("Metadata set successfully")
        
        except Exception as e:
            logger.error(f"Error setting metadata: {e}")
            raise
    
    def _sanitize_text(self, text):
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
            except Exception as e:
                logger.warning(f"Error decoding bytes to string: {e}")
                return "Unknown text"
        
        # Ensure we have a string
        if not isinstance(text, str):
            try:
                text = str(text)
            except Exception as e:
                logger.warning(f"Error converting to string: {e}")
                return "Unknown text"
        
        # Remove control characters
        text = re.sub(r'[\x00-\x08\x0B\x0C\x0E-\x1F\x7F]', '', text)
        
        # Replace problematic characters
        text = text.replace('\r\n', ' ').replace('\n', ' ').replace('\r', ' ')
        
        return text
    
    def _get_metadata(self, name):
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
    
    def _process_articles(self):
        """Process articles from the ZIM file and add them to the EPUB."""
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
                self._process_entry(main_entry, is_main=True)
            
            # Process other entries
            entries = []
            # Iterate through all entries
            article_paths = self._get_article_paths()
            logger.info(f"Found {len(article_paths)} potential article paths")
            
            skipped_reasons = {
                "not_found": 0,
                "redirect": 0,
                "non_html": 0,
                "duplicate": 0,
                "error": 0
            }
            
            # Debug: Try to access entries directly by URL
            if self.verbose and article_paths:
                logger.info("Debugging path access:")
                # Try a few sample paths
                sample_paths = article_paths[:5] if len(article_paths) > 5 else article_paths
                for path in sample_paths:
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
                        
                        for p in paths_to_try:
                            try:
                                has_entry = self.zim.has_entry_by_path(p)
                                logger.info(f"Path '{p}': has_entry={has_entry}")
                                if has_entry:
                                    entry = self.zim.get_entry_by_path(p)
                                    logger.info(f"  Entry found: path={entry.path}, title={entry.title}, is_redirect={entry.is_redirect}")
                                    break
                            except Exception as e:
                                logger.info(f"  Error checking path '{p}': {e}")
                    except Exception as e:
                        logger.info(f"Error debugging path '{path}': {e}")
            
            # Try to access entries by title
            if self.verbose and len(article_paths) > 0 and skipped_reasons["not_found"] > 0:
                logger.info("Trying to access entries by title:")
                try:
                    # Try a few common titles
                    common_titles = ["Main Page", "Index", "Home", "Welcome", "Start"]
                    for title in common_titles:
                        try:
                            if self.zim.has_entry_by_title(title):
                                entry = self.zim.get_entry_by_title(title)
                                logger.info(f"Entry found by title '{title}': path={entry.path}, is_redirect={entry.is_redirect}")
                        except Exception as e:
                            logger.info(f"Error checking title '{title}': {e}")
                except Exception as e:
                    logger.info(f"Error trying to access entries by title: {e}")
            
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
                                if self.verbose:
                                    logger.debug(f"Found entry using path: {p}")
                                break
                        except Exception:
                            continue
                    
                    if not entry:
                        if self.verbose:
                            logger.debug(f"Path not found: {path}")
                        skipped_reasons["not_found"] += 1
                        continue
                    
                    # Skip if this is the main entry (already processed)
                    if main_entry and entry.path == main_entry.path:
                        if self.verbose:
                            logger.debug(f"Skipping main entry: {path}")
                        skipped_reasons["duplicate"] += 1
                        continue
                    
                    # Skip redirects
                    if entry.is_redirect:
                        if self.verbose:
                            logger.debug(f"Skipping redirect: {path}")
                        skipped_reasons["redirect"] += 1
                        continue
                    
                    # Skip non-HTML entries
                    try:
                        item = entry.get_item()
                        if not item.mimetype.startswith('text/html'):
                            if self.verbose:
                                logger.debug(f"Skipping non-HTML entry: {path} (mimetype: {item.mimetype})")
                            skipped_reasons["non_html"] += 1
                            continue
                    except Exception as e:
                        if self.verbose:
                            logger.debug(f"Error checking mimetype for {path}: {e}")
                        skipped_reasons["error"] += 1
                        continue
                    
                    entries.append(entry)
                except Exception as e:
                    if self.verbose:
                        logger.debug(f"Error processing path {path}: {e}")
                    skipped_reasons["error"] += 1
            
            # Log skipped reasons
            if self.verbose:
                for reason, count in skipped_reasons.items():
                    if count > 0:
                        logger.info(f"Skipped {count} entries due to: {reason}")
            
            # Limit the number of articles if specified
            if self.max_articles and len(entries) > self.max_articles:
                entries = entries[:self.max_articles]
                logger.info(f"Limited to {self.max_articles} articles")
            
            # Process each entry
            for entry in tqdm(entries, desc="Processing articles", disable=not self.verbose):
                self._process_entry(entry)
            
            # If no articles were processed but we have a main entry, try to extract content from it
            if not self.articles and main_entry and main_entry.path not in self.articles:
                logger.warning("No articles were processed. Trying to extract content from main entry.")
                self._extract_content_from_main_entry(main_entry)
            
            # If still no articles, try a direct extraction as a last resort
            if not self.articles and not entries:
                logger.warning("No articles were processed. Trying direct extraction as a last resort.")
                self._extract_content_directly()
            
            logger.info(f"Processed {len(self.articles)} articles")
        
        except Exception as e:
            logger.error(f"Error processing articles: {e}")
            raise
    
    def _get_article_paths(self):
        """
        Get all article paths from the ZIM file.
        
        Returns:
            list: List of article paths
        """
        paths = []
        
        # Debug: Print some basic ZIM file information
        if self.verbose:
            try:
                logger.info(f"ZIM file info: entry_count={self.zim.entry_count}, article_count={self.zim.article_count}")
                logger.info(f"ZIM file has_new_namespace_scheme: {self.zim.has_new_namespace_scheme}")
                if self.zim.has_main_entry:
                    logger.info(f"Main entry path: {self.zim.main_entry.path}")
            except Exception as e:
                logger.warning(f"Error getting ZIM file info: {e}")
        
        # Try to access entries directly by URL
        direct_paths = self._try_direct_url_access()
        if direct_paths:
            paths.extend(direct_paths)
            if self.verbose:
                logger.info(f"Found {len(direct_paths)} paths by direct URL access")
        
        # We need to manually find articles since get_entries_by_namespace is not available
        # This is a simple approach that checks common article paths
        
        # Try to find a list of articles from the main page or table of contents
        if self.zim.has_main_entry:
            try:
                main_entry = self.zim.main_entry
                item = main_entry.get_item()
                content_bytes = item.content.tobytes()
                
                # Try different encodings
                for encoding in ['utf-8', 'latin-1', 'cp1252']:
                    try:
                        content = content_bytes.decode(encoding, errors='replace')
                        break
                    except UnicodeDecodeError:
                        continue
                else:
                    # If all encodings fail, use utf-8 with replace
                    content = content_bytes.decode('utf-8', errors='replace')
                
                # Parse the HTML content to find links
                soup = BeautifulSoup(content, 'lxml')
                for link in soup.find_all('a'):
                    href = link.get('href')
                    if href and not href.startswith(('http://', 'https://')):
                        # Clean up the path
                        path = href.split('#')[0]  # Remove fragment
                        if path and path not in paths:
                            paths.append(path)
                
                # Debug: Print some sample paths
                if self.verbose and paths:
                    sample_paths = paths[:5] if len(paths) > 5 else paths
                    logger.info(f"Sample paths from main entry: {sample_paths}")
                    
                    # Try to access a few sample paths with URL decoding
                    if sample_paths:
                        logger.info("Testing sample paths with URL decoding:")
                        for path in sample_paths:
                            decoded_path = unquote(path)
                            if decoded_path != path:
                                logger.info(f"Original: '{path}', Decoded: '{decoded_path}'")
                                try:
                                    has_entry = self.zim.has_entry_by_path(decoded_path)
                                    logger.info(f"  Decoded path '{decoded_path}': has_entry={has_entry}")
                                except Exception as e:
                                    logger.info(f"  Error checking decoded path '{decoded_path}': {e}")
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
        
        # If we still don't have any articles, try to extract articles from metadata
        if not paths:
            try:
                if 'Title' in self.zim.metadata_keys:
                    logger.info("Trying to extract articles from metadata")
                    # Some ZIM files store article information in metadata
                    for key in self.zim.metadata_keys:
                        if key.startswith('Article/'):
                            article_path = key.split('/', 1)[1]
                            if article_path and article_path not in paths:
                                paths.append(article_path)
            except Exception as e:
                logger.warning(f"Error extracting articles from metadata: {e}")
        
        # If we still don't have any articles, we'll need to scan the ZIM file
        # This is a fallback and might be slow for large ZIM files
        if not paths:
            logger.warning("Could not find articles through common paths. Using a fallback method.")
            
            # Try to find articles by scanning entry count
            try:
                # Get the total entry count
                entry_count = self.zim.entry_count
                logger.info(f"ZIM file has {entry_count} entries")
                
                # If there are too many entries, limit the scan
                max_scan = min(entry_count, 1000)
                
                # Try to find articles by checking paths with common patterns
                for prefix in ['A/', '', 'wiki/', 'wikipedia/']:
                    for i in range(1, max_scan // 4):  # Divide by 4 for the prefixes
                        try:
                            path = f"{prefix}{i}"
                            if self.zim.has_entry_by_path(path):
                                paths.append(path)
                        except Exception as e:
                            if self.verbose:
                                logger.debug(f"Error checking path {path}: {e}")
            except Exception as e:
                logger.warning(f"Error scanning ZIM file: {e}")
        
        logger.info(f"Found {len(paths)} potential article paths")
        return paths
    
    def _try_direct_url_access(self):
        """
        Try to access entries directly by URL.
        
        Returns:
            list: List of valid article paths
        """
        paths = []
        
        # Common URL patterns in ZIM files
        url_patterns = [
            "A/index.html", "A/main.html", "A/home.html", "A/welcome.html",
            "index.html", "main.html", "home.html", "welcome.html",
            "A/index.htm", "A/main.htm", "A/home.htm", "A/welcome.htm",
            "index.htm", "main.htm", "home.htm", "welcome.htm",
            "A/index", "A/main", "A/home", "A/welcome",
            "index", "main", "home", "welcome",
            "A", "C", "M", "I", "W"
        ]
        
        # Add numeric patterns
        for i in range(1, 20):
            url_patterns.append(f"A/{i}")
            url_patterns.append(f"{i}")
        
        # Try each pattern
        for pattern in url_patterns:
            try:
                if self.zim.has_entry_by_path(pattern):
                    entry = self.zim.get_entry_by_path(pattern)
                    if not entry.is_redirect:
                        try:
                            item = entry.get_item()
                            if item.mimetype.startswith('text/html'):
                                paths.append(pattern)
                                if self.verbose:
                                    logger.info(f"Found valid article path: {pattern}")
                        except Exception as e:
                            if self.verbose:
                                logger.debug(f"Error checking mimetype for pattern '{pattern}': {e}")
            except Exception as e:
                if self.verbose:
                    logger.debug(f"Error checking pattern '{pattern}': {e}")
        
        # Try to access entries by title
        try:
            # Common titles in various formats
            common_titles = [
                "Main Page", "Index", "Home", "Welcome", "Start",
                "MainPage", "HomePage", "WelcomePage", "StartPage",
                "Main_Page", "Home_Page", "Welcome_Page", "Start_Page",
                "main", "home", "welcome", "start",
                "main page", "home page", "welcome page", "start page",
                "Main", "Home", "Welcome", "Start"
            ]
            
            # Try to get the ZIM file title as a potential entry title
            if 'Title' in self.zim.metadata_keys:
                try:
                    zim_title = self.zim.get_metadata('Title')
                    if isinstance(zim_title, bytes):
                        zim_title = zim_title.decode('utf-8', errors='replace')
                    common_titles.append(zim_title)
                    if self.verbose:
                        logger.info(f"Added ZIM title as potential entry title: '{zim_title}'")
                except Exception as e:
                    if self.verbose:
                        logger.debug(f"Error getting ZIM title: {e}")
            
            # Try each title
            for title in common_titles:
                try:
                    # Try with original title
                    if self.zim.has_entry_by_title(title):
                        entry = self.zim.get_entry_by_title(title)
                        if not entry.is_redirect and entry.path not in paths:
                            paths.append(entry.path)
                            if self.verbose:
                                logger.info(f"Found valid article path by title '{title}': {entry.path}")
                    
                    # Try with title case
                    title_case = title.title()
                    if title_case != title and self.zim.has_entry_by_title(title_case):
                        entry = self.zim.get_entry_by_title(title_case)
                        if not entry.is_redirect and entry.path not in paths:
                            paths.append(entry.path)
                            if self.verbose:
                                logger.info(f"Found valid article path by title case '{title_case}': {entry.path}")
                    
                    # Try with uppercase
                    upper_case = title.upper()
                    if upper_case != title and self.zim.has_entry_by_title(upper_case):
                        entry = self.zim.get_entry_by_title(upper_case)
                        if not entry.is_redirect and entry.path not in paths:
                            paths.append(entry.path)
                            if self.verbose:
                                logger.info(f"Found valid article path by uppercase '{upper_case}': {entry.path}")
                    
                    # Try with lowercase
                    lower_case = title.lower()
                    if lower_case != title and self.zim.has_entry_by_title(lower_case):
                        entry = self.zim.get_entry_by_title(lower_case)
                        if not entry.is_redirect and entry.path not in paths:
                            paths.append(entry.path)
                            if self.verbose:
                                logger.info(f"Found valid article path by lowercase '{lower_case}': {entry.path}")
                
                except Exception as e:
                    if self.verbose:
                        logger.debug(f"Error checking title '{title}': {e}")
        except Exception as e:
            if self.verbose:
                logger.debug(f"Error trying to access entries by title: {e}")
        
        # Try to access entries by iterating through the ZIM file
        if not paths and self.verbose:
            logger.info("Trying to access entries by iterating through the ZIM file")
            try:
                # Get a sample of entries from the ZIM file
                article_count = min(self.zim.article_count, 10)
                if article_count > 0:
                    logger.info(f"Trying to access {article_count} articles directly")
                    
                    # Try to access the main entry
                    if self.zim.has_main_entry:
                        main_entry = self.zim.main_entry
                        logger.info(f"Main entry: path={main_entry.path}, title={main_entry.title}")
                        
                        # Try to get entries by URL-decoding the main entry path
                        if '%' in main_entry.path:
                            decoded_path = unquote(main_entry.path)
                            logger.info(f"Decoded main entry path: {decoded_path}")
                            try:
                                if self.zim.has_entry_by_path(decoded_path):
                                    logger.info(f"Found entry using decoded main entry path: {decoded_path}")
                            except Exception as e:
                                logger.info(f"Error checking decoded main entry path: {e}")
            except Exception as e:
                logger.warning(f"Error accessing entries directly: {e}")
        
        return paths
    
    def _process_entry(self, entry, is_main=False):
        """
        Process a single ZIM entry and add it to the EPUB.
        
        Args:
            entry: ZIM entry object
            is_main (bool): Whether this is the main entry
        """
        try:
            # Skip redirects
            if entry.is_redirect:
                return
            
            # Get the item and check mimetype
            try:
                item = entry.get_item()
                # Check if it's HTML content
                mimetype = self._get_mimetype_from_item(item, entry.path)
                if not mimetype.startswith('text/html'):
                    if self.verbose:
                        logger.debug(f"Skipping non-HTML entry: {entry.path} (mimetype: {mimetype})")
                    return
            except Exception as e:
                logger.warning(f"Error getting item or mimetype for entry {entry.path}: {e}")
                return
            
            # Get the content
            try:
                content_bytes = item.content.tobytes()
                # Try different encodings
                for encoding in ['utf-8', 'latin-1', 'cp1252']:
                    try:
                        content = content_bytes.decode(encoding, errors='replace')
                        break
                    except UnicodeDecodeError:
                        continue
                else:
                    # If all encodings fail, use utf-8 with replace
                    content = content_bytes.decode('utf-8', errors='replace')
            except Exception as e:
                logger.warning(f"Error getting content for entry {entry.path}: {e}")
                return
            
            # Create a unique filename for the article
            filename = f"article_{self.counter}.xhtml"
            self.counter += 1
            
            # Parse the HTML content
            try:
                soup = BeautifulSoup(content, 'lxml')
            except Exception as e:
                logger.warning(f"Error parsing HTML for entry {entry.path}: {e}")
                # Create a simple HTML with the raw content
                content = f"<html><head><title>Article {self.counter}</title></head><body><pre>{self._sanitize_text(content)}</pre></body></html>"
                soup = BeautifulSoup(content, 'lxml')
            
            # Extract the title
            try:
                if soup.title and soup.title.string:
                    title = self._sanitize_text(soup.title.string)
                else:
                    title = self._sanitize_text(entry.title) or f"Article {self.counter}"
            except Exception as e:
                logger.warning(f"Error extracting title for entry {entry.path}: {e}")
                title = f"Article {self.counter}"
            
            # Process images if needed
            if self.include_images:
                try:
                    self._extract_images(soup, entry.path)
                except Exception as e:
                    logger.warning(f"Error extracting images for entry {entry.path}: {e}")
            else:
                # Remove all images if not including them
                for img in soup.find_all('img'):
                    img.decompose()
            
            # Create the EPUB chapter
            try:
                chapter = epub.EpubHtml(
                    title=title,
                    file_name=filename,
                    lang=self._sanitize_text(self._get_metadata("Language") or "en")
                )
                chapter.content = str(soup)
                
                # Add the chapter to the book
                self.book.add_item(chapter)
                
                # Add to spine
                if is_main:
                    self.book.spine = ['nav', chapter]
                else:
                    self.book.spine.append(chapter)
                
                # Store for TOC generation
                self.articles[entry.path] = {
                    'title': title,
                    'chapter': chapter
                }
                
                if is_main:
                    logger.info(f"Processed main entry: {title}")
            except Exception as e:
                logger.warning(f"Error creating EPUB chapter for entry {entry.path}: {e}")
        
        except Exception as e:
            logger.warning(f"Error processing entry {entry.path}: {e}")
    
    def _extract_images(self, soup, article_path):
        """
        Extract image references from HTML content.
        
        Args:
            soup (BeautifulSoup): Parsed HTML content
            article_path (str): Path of the article
        """
        for img in soup.find_all('img'):
            src = img.get('src')
            if not src:
                continue
            
            # Handle relative URLs
            if not src.startswith(('http://', 'https://')):
                # Resolve relative path
                base_path = os.path.dirname(article_path)
                img_path = urljoin(f"{base_path}/", src)
                
                # Clean up path
                img_path = urlparse(img_path).path
                
                # Try both the original and URL-decoded paths
                img_paths = [img_path]
                if '%' in img_path:
                    img_paths.append(unquote(img_path))
                
                # Generate a unique image filename based on the path
                img_filename = self._get_unique_image_filename(img_path)
                
                # Update the src attribute to point to the EPUB image
                img['src'] = f"images/{img_filename}"
                
                # Store the mapping for later processing
                for path in img_paths:
                    if path not in self.images:
                        self.images[path] = []
                    self.images[path].append(img_filename)
    
    def _get_unique_image_filename(self, img_path):
        """
        Generate a unique filename for an image.
        
        Args:
            img_path (str): Path of the image
            
        Returns:
            str: Unique filename
        """
        # Check if we've already processed this image path
        if img_path in self.processed_images:
            return self.processed_images[img_path]
        
        # Generate a hash of the path to ensure uniqueness
        path_hash = str(abs(hash(img_path)) % 10000)
        ext = self._get_extension(img_path)
        
        # Create a unique filename
        filename = f"image_{path_hash}.{ext}"
        
        # Check if this filename is already used
        counter = 1
        while filename in self.processed_images.values():
            filename = f"image_{path_hash}_{counter}.{ext}"
            counter += 1
        
        # Store the mapping
        self.processed_images[img_path] = filename
        
        return filename
    
    def _get_extension(self, path):
        """
        Get the file extension from a path.
        
        Args:
            path (str): File path
            
        Returns:
            str: File extension
        """
        ext = os.path.splitext(path)[1].lower()
        if ext:
            return ext[1:]  # Remove the dot
        
        # Default to jpg if no extension
        return "jpg"
    
    def _process_images(self):
        """Process images and add them to the EPUB."""
        try:
            if not self.images:
                logger.info("No images to process")
                return
            
            # Create a set to track processed image filenames
            processed_filenames = set()
            
            logger.info(f"Processing {len(self.images)} images")
            
            for img_path, filenames in tqdm(self.images.items(), desc="Processing images", disable=not self.verbose):
                try:
                    # Skip if we've already processed all filenames for this path
                    if all(filename in processed_filenames for filename in filenames):
                        continue
                    
                    # Try to get the image from the ZIM file
                    entry = None
                    
                    # Try with the original path
                    try:
                        if self.zim.has_entry_by_path(img_path):
                            entry = self.zim.get_entry_by_path(img_path)
                    except Exception:
                        pass
                    
                    # If not found, try with URL-decoded path
                    if not entry and '%' in img_path:
                        try:
                            decoded_path = unquote(img_path)
                            if self.zim.has_entry_by_path(decoded_path):
                                entry = self.zim.get_entry_by_path(decoded_path)
                        except Exception:
                            pass
                    
                    # If not found, try with 'I/' prefix (image namespace)
                    if not entry:
                        try:
                            prefixed_path = f"I/{img_path}"
                            if self.zim.has_entry_by_path(prefixed_path):
                                entry = self.zim.get_entry_by_path(prefixed_path)
                        except Exception:
                            pass
                    
                    # If not found, try with 'I/' prefix and URL-decoded path
                    if not entry and '%' in img_path:
                        try:
                            prefixed_decoded_path = f"I/{unquote(img_path)}"
                            if self.zim.has_entry_by_path(prefixed_decoded_path):
                                entry = self.zim.get_entry_by_path(prefixed_decoded_path)
                        except Exception:
                            pass
                    
                    if entry and not entry.is_redirect:
                        try:
                            item = entry.get_item()
                            content = item.content.tobytes()
                            
                            # Determine the mimetype
                            mimetype = self._get_mimetype_from_item(item, img_path)
                            
                            # Add the image to the EPUB, but only if we haven't processed it yet
                            for img_filename in filenames:
                                if img_filename not in processed_filenames:
                                    epub_image = epub.EpubImage(
                                        uid=f"image_{img_filename}",
                                        file_name=f"images/{img_filename}",
                                        media_type=mimetype,
                                        content=content
                                    )
                                    self.book.add_item(epub_image)
                                    processed_filenames.add(img_filename)
                        except Exception as e:
                            logger.warning(f"Error processing image content for {img_path}: {e}")
                    else:
                        logger.warning(f"Error processing image {img_path}: 'Cannot find entry'")
                
                except Exception as e:
                    logger.warning(f"Error processing image {img_path}: {e}")
            
            logger.info(f"Successfully processed {len(processed_filenames)} unique images")
        
        except Exception as e:
            logger.error(f"Error processing images: {e}")
            raise
    
    def _get_mimetype_from_item(self, item, path):
        """
        Get the mimetype from an item, with fallbacks.
        
        Args:
            item: The ZIM item
            path (str): The path of the item
            
        Returns:
            str: The mimetype
        """
        # First try to get the mimetype from the item
        try:
            return item.mimetype
        except AttributeError:
            pass
        
        # If that fails, try to get it from the entry
        try:
            return item.entry.mimetype
        except (AttributeError, TypeError):
            pass
        
        # If that fails, try to guess from the path
        ext = self._get_extension(path)
        if ext:
            mime_type = mimetypes.guess_type(f"file.{ext}")[0]
            if mime_type:
                return mime_type
        
        # Default mimetypes based on extension
        ext_to_mime = {
            'jpg': 'image/jpeg',
            'jpeg': 'image/jpeg',
            'png': 'image/png',
            'gif': 'image/gif',
            'svg': 'image/svg+xml',
            'webp': 'image/webp',
            'ico': 'image/x-icon',
            'bmp': 'image/bmp',
            'tiff': 'image/tiff',
            'tif': 'image/tiff'
        }
        
        if ext.lower() in ext_to_mime:
            return ext_to_mime[ext.lower()]
        
        # Last resort fallback
        return 'image/jpeg'
    
    def _generate_toc(self):
        """Generate a table of contents for the EPUB."""
        try:
            if not self.articles:
                logger.warning("No articles to generate TOC")
                return
            
            logger.info("Generating table of contents")
            
            # Create TOC entries
            toc = []
            for path, article in self.articles.items():
                try:
                    # Ensure the title is XML compatible
                    title = self._sanitize_text(article['title'])
                    if not title:
                        title = f"Article {path}"
                    
                    # Create a safe ID
                    article_id = re.sub(r'[^a-zA-Z0-9]', '_', path)
                    if not article_id:
                        article_id = f"article_{len(toc)}"
                    
                    toc.append(epub.Link(
                        article['chapter'].file_name, 
                        title, 
                        article_id
                    ))
                except Exception as e:
                    logger.warning(f"Error adding TOC entry for {path}: {e}")
            
            # Set the TOC
            if toc:
                self.book.toc = toc
                logger.info("Table of contents generated successfully")
            else:
                logger.warning("No valid TOC entries could be created")
        
        except Exception as e:
            logger.error(f"Error generating TOC: {e}")
            raise
    
    def _add_css(self):
        """Add CSS styling to the EPUB."""
        try:
            # Define CSS style
            style = """
            body {
                font-family: serif;
                margin: 5%;
                text-align: justify;
            }
            h1, h2, h3, h4, h5, h6 {
                font-family: sans-serif;
                margin-top: 2em;
                margin-bottom: 1em;
            }
            img {
                max-width: 100%;
                height: auto;
            }
            a {
                color: #0066cc;
                text-decoration: none;
            }
            """
            
            # Create CSS item
            css = epub.EpubItem(
                uid="style_default",
                file_name="style/default.css",
                media_type="text/css",
                content=style
            )
            
            # Add CSS to the book
            self.book.add_item(css)
            
            # Add CSS to all HTML files
            for article in self.articles.values():
                article['chapter'].add_item(css)
            
            logger.info("CSS added successfully")
        
        except Exception as e:
            logger.error(f"Error adding CSS: {e}")
            raise
    
    def _add_fallback_page(self):
        """Add a fallback page to the EPUB if no articles were processed."""
        try:
            logger.warning("No articles were processed, adding a fallback page")
            
            # Create a fallback page
            title = f"Content from {os.path.basename(self.zim_path)}"
            filename = "fallback.xhtml"
            
            # Create simple HTML content
            content = f"""
            <html>
                <head>
                    <title>{title}</title>
                </head>
                <body>
                    <h1>{title}</h1>
                    <p>This EPUB was created from the ZIM file: {os.path.basename(self.zim_path)}</p>
                    <p>However, no articles could be processed from the ZIM file.</p>
                    <p>This could be due to one of the following reasons:</p>
                    <ul>
                        <li>The ZIM file has a non-standard structure</li>
                        <li>The ZIM file does not contain any HTML articles</li>
                        <li>There was an error processing the ZIM file</li>
                    </ul>
                </body>
            </html>
            """
            
            # Create the EPUB chapter
            chapter = epub.EpubHtml(
                title=title,
                file_name=filename,
                lang="en"
            )
            chapter.content = content
            
            # Add the chapter to the book
            self.book.add_item(chapter)
            
            # Add to spine
            self.book.spine = ['nav', chapter]
            
            # Store for TOC generation
            self.articles["fallback"] = {
                'title': title,
                'chapter': chapter
            }
            
            logger.info("Fallback page added successfully")
        
        except Exception as e:
            logger.error(f"Error adding fallback page: {e}")
            raise
    
    def _extract_content_directly(self):
        """
        Try to extract content directly from the ZIM file as a last resort.
        This method attempts to find any HTML content in the ZIM file.
        """
        try:
            # Get the total entry count
            entry_count = self.zim.entry_count
            logger.info(f"Attempting direct extraction from {entry_count} entries")
            
            # Try to access entries by URL pattern
            html_entries = self._try_url_patterns()
            
            # If we still don't have any entries, try by index
            if not html_entries:
                # Limit the number of entries to check
                max_entries = min(entry_count, 1000)
                
                # Try to find HTML content
                html_entries = []
                
                # Check the first max_entries entries
                for i in range(max_entries):
                    try:
                        # Try to get an entry by index
                        # This is a hack and might not work for all ZIM files
                        path = f"{i}"
                        if self.zim.has_entry_by_path(path):
                            entry = self.zim.get_entry_by_path(path)
                            
                            # Skip redirects
                            if entry.is_redirect:
                                continue
                            
                            # Check if it's HTML
                            try:
                                item = entry.get_item()
                                if item.mimetype.startswith('text/html'):
                                    html_entries.append(entry)
                                    if len(html_entries) >= 10:  # Limit to 10 entries
                                        break
                            except Exception:
                                continue
                    except Exception:
                        continue
            
            # Process the HTML entries
            for entry in html_entries:
                self._process_entry(entry)
            
            logger.info(f"Direct extraction found {len(html_entries)} HTML entries")
        
        except Exception as e:
            logger.warning(f"Error during direct extraction: {e}")
            # This is a last resort, so we don't want to raise an exception
    
    def _try_url_patterns(self):
        """
        Try to access entries by URL pattern.
        
        Returns:
            list: List of entry objects
        """
        entries = []
        
        # Common URL patterns in ZIM files
        url_patterns = [
            "A/index.html", "A/main.html", "A/home.html", "A/welcome.html",
            "index.html", "main.html", "home.html", "welcome.html",
            "A/index.htm", "A/main.htm", "A/home.htm", "A/welcome.htm",
            "index.htm", "main.htm", "home.htm", "welcome.htm",
            "A/index", "A/main", "A/home", "A/welcome",
            "index", "main", "home", "welcome",
            "A", "C", "M", "I", "W",
            "wiki/Main_Page", "wiki/index", "wiki/home",
            "wikipedia/Main_Page", "wikipedia/index",
            "A/Main_Page", "Main_Page"
        ]
        
        # Add numeric patterns
        for i in range(1, 20):
            url_patterns.append(f"A/{i}")
            url_patterns.append(f"{i}")
        
        # Try each pattern
        if self.verbose:
            logger.info("Trying direct URL patterns:")
        
        for pattern in url_patterns:
            try:
                # Try with original pattern
                if self.zim.has_entry_by_path(pattern):
                    entry = self.zim.get_entry_by_path(pattern)
                    if not entry.is_redirect:
                        try:
                            item = entry.get_item()
                            mimetype = self._get_mimetype_from_item(item, pattern)
                            if mimetype.startswith('text/html'):
                                entries.append(entry)
                                if self.verbose:
                                    logger.info(f"Found HTML entry with pattern '{pattern}': {entry.path}")
                                    if len(entries) >= 10:  # Limit to 10 entries
                                        break
                        except Exception as e:
                            if self.verbose:
                                logger.debug(f"Error checking mimetype for pattern '{pattern}': {e}")
                
                # Try with URL-decoded pattern
                if '%' in pattern:
                    decoded_pattern = unquote(pattern)
                    if self.zim.has_entry_by_path(decoded_pattern):
                        entry = self.zim.get_entry_by_path(decoded_pattern)
                        if not entry.is_redirect:
                            try:
                                item = entry.get_item()
                                mimetype = self._get_mimetype_from_item(item, decoded_pattern)
                                if mimetype.startswith('text/html'):
                                    entries.append(entry)
                                    if self.verbose:
                                        logger.info(f"Found HTML entry with decoded pattern '{decoded_pattern}': {entry.path}")
                                        if len(entries) >= 10:  # Limit to 10 entries
                                            break
                            except Exception as e:
                                if self.verbose:
                                    logger.debug(f"Error checking mimetype for decoded pattern '{decoded_pattern}': {e}")
            except Exception as e:
                if self.verbose:
                    logger.debug(f"Error checking pattern '{pattern}': {e}")
        
        # Try to access entries by title
        try:
            # Common titles in various formats
            common_titles = [
                "Main Page", "Index", "Home", "Welcome", "Start",
                "MainPage", "HomePage", "WelcomePage", "StartPage",
                "Main_Page", "Home_Page", "Welcome_Page", "Start_Page",
                "main", "home", "welcome", "start",
                "main page", "home page", "welcome page", "start page",
                "Main", "Home", "Welcome", "Start"
            ]
            
            # Try to get the ZIM file title as a potential entry title
            if 'Title' in self.zim.metadata_keys:
                try:
                    zim_title = self.zim.get_metadata('Title')
                    if isinstance(zim_title, bytes):
                        zim_title = zim_title.decode('utf-8', errors='replace')
                    common_titles.append(zim_title)
                except Exception:
                    pass
            
            # Try each title
            for title in common_titles:
                try:
                    if self.zim.has_entry_by_title(title):
                        entry = self.zim.get_entry_by_title(title)
                        if not entry.is_redirect:
                            try:
                                item = entry.get_item()
                                mimetype = self._get_mimetype_from_item(item, entry.path)
                                if mimetype.startswith('text/html'):
                                    entries.append(entry)
                                    if self.verbose:
                                        logger.info(f"Found HTML entry with title '{title}': {entry.path}")
                                        if len(entries) >= 10:  # Limit to 10 entries
                                            break
                            except Exception:
                                continue
                except Exception:
                    continue
        except Exception:
            pass
        
        return entries
    
    def _extract_content_from_main_entry(self, main_entry):
        """
        Try to extract content from the main entry by parsing its HTML and creating
        separate articles for each section.
        
        Args:
            main_entry: The main entry from the ZIM file
        """
        try:
            # Get the content of the main entry
            item = main_entry.get_item()
            content_bytes = item.content.tobytes()
            
            # Try different encodings
            for encoding in ['utf-8', 'latin-1', 'cp1252']:
                try:
                    content = content_bytes.decode(encoding, errors='replace')
                    break
                except UnicodeDecodeError:
                    continue
            else:
                # If all encodings fail, use utf-8 with replace
                content = content_bytes.decode('utf-8', errors='replace')
            
            # Parse the HTML content
            soup = BeautifulSoup(content, 'lxml')
            
            # Extract the title
            main_title = self._sanitize_text(soup.title.string if soup.title else main_entry.title or "Main Page")
            
            # First, add the main entry as a whole
            self._add_html_as_article(
                soup, 
                f"main_page", 
                main_title,
                is_main=True
            )
            
            # Then try to extract sections as separate articles
            sections = []
            
            # Look for headings that might indicate sections
            for heading in soup.find_all(['h1', 'h2', 'h3']):
                # Skip empty headings
                if not heading.get_text(strip=True):
                    continue
                
                # Get the section title
                section_title = self._sanitize_text(heading.get_text(strip=True))
                
                # Find the content of this section (everything until the next heading of same or higher level)
                section_content = []
                current = heading.next_sibling
                
                while current and not (current.name in ['h1', 'h2', 'h3'] and 
                                      (current.name == heading.name or 
                                       current.name < heading.name)):
                    if current.name:  # Skip NavigableString
                        section_content.append(str(current))
                    current = current.next_sibling
                
                if section_content:
                    # Create a new soup for this section
                    section_html = f"<html><head><title>{section_title}</title></head><body><h1>{section_title}</h1>{''.join(section_content)}</body></html>"
                    section_soup = BeautifulSoup(section_html, 'lxml')
                    
                    # Add this section as an article
                    sections.append((section_soup, section_title))
            
            # Add each section as a separate article
            for i, (section_soup, section_title) in enumerate(sections):
                self._add_html_as_article(
                    section_soup,
                    f"section_{i}",
                    section_title
                )
            
            logger.info(f"Extracted main entry and {len(sections)} sections")
        
        except Exception as e:
            logger.warning(f"Error extracting content from main entry: {e}")
    
    def _add_html_as_article(self, soup, filename_base, title, is_main=False):
        """
        Add HTML content as an article to the EPUB.
        
        Args:
            soup (BeautifulSoup): Parsed HTML content
            filename_base (str): Base filename for the article
            title (str): Title for the article
            is_main (bool): Whether this is the main article
        """
        try:
            # Create a unique filename for the article
            filename = f"{filename_base}_{self.counter}.xhtml"
            self.counter += 1
            
            # Process images if needed
            if self.include_images:
                try:
                    self._extract_images(soup, filename_base)
                except Exception as e:
                    logger.warning(f"Error extracting images for {filename_base}: {e}")
            else:
                # Remove all images if not including them
                for img in soup.find_all('img'):
                    img.decompose()
            
            # Create the EPUB chapter
            chapter = epub.EpubHtml(
                title=title,
                file_name=filename,
                lang=self._sanitize_text(self._get_metadata("Language") or "en")
            )
            chapter.content = str(soup)
            
            # Add the chapter to the book
            self.book.add_item(chapter)
            
            # Add to spine
            if is_main:
                self.book.spine = ['nav', chapter]
            else:
                self.book.spine.append(chapter)
            
            # Store for TOC generation
            self.articles[filename_base] = {
                'title': title,
                'chapter': chapter
            }
            
            if is_main:
                logger.info(f"Added main entry as article: {title}")
            else:
                logger.info(f"Added section as article: {title}")
            
            return True
        
        except Exception as e:
            logger.warning(f"Error adding HTML as article: {e}")
            return False


def main():
    """Main function to handle command-line arguments and run the conversion."""
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
    
    args = parser.parse_args()
    
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
            verbose=args.verbose
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