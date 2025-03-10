"""
Full crawl article extraction for ZIM to EPUB conversion.
"""

import re
import logging
from tqdm import tqdm
from urllib.parse import unquote
from bs4 import BeautifulSoup
from zim2epub.utils.html_utils import parse_html
from zim2epub.converter.article_extractor import ArticleExtractor

logger = logging.getLogger('zim2epub')

class FullCrawlExtractor(ArticleExtractor):
    """
    Full crawl article extraction strategy.
    """
    
    def extract_articles(self):
        """
        Extract articles using the full crawl method.
        
        Returns:
            dict: Dictionary of articles
        """
        try:
            logger.info("Starting full crawl of all entries in the ZIM file")
            
            # Track statistics
            stats = {
                "total": 0,
                "processed": 0,
                "skipped": {
                    "redirect": 0,
                    "non_html": 0,
                    "duplicate": 0,
                    "error": 0,
                    "binary": 0
                }
            }
            
            # Get main page if available
            main_entry = None
            try:
                if self.zim.has_main_entry:
                    main_entry = self.zim.main_entry
                    logger.info(f"Main entry found at: {main_entry.path}")
                    
                    # Process the main entry first
                    if self.process_entry(main_entry, is_main=True):
                        stats["processed"] += 1
            except Exception as e:
                logger.warning(f"No main entry found: {e}")
            
            # Get all entries by iterating through the ZIM file
            entries = []
            
            # Method 1: Try to use get_entry_by_index
            try:
                # Use a progress bar if verbose
                with tqdm(total=self.zim.entry_count, desc="Scanning entries by index", disable=logger.level != logging.INFO) as pbar:
                    for entry_idx in range(self.zim.entry_count):
                        try:
                            # Get the entry by index
                            entry = self.zim.get_entry_by_index(entry_idx)
                            stats["total"] += 1
                            
                            # Skip if this is the main entry (already processed)
                            if main_entry and entry.path == main_entry.path:
                                stats["skipped"]["duplicate"] += 1
                                pbar.update(1)
                                continue
                            
                            # Skip redirects
                            if entry.is_redirect:
                                stats["skipped"]["redirect"] += 1
                                pbar.update(1)
                                continue
                            
                            # Skip non-article entries (those without a title)
                            if not entry.title:
                                stats["skipped"]["non_html"] += 1
                                pbar.update(1)
                                continue
                            
                            # Skip non-HTML entries
                            try:
                                item = entry.get_item()
                                if not item.mimetype.startswith('text/html'):
                                    stats["skipped"]["non_html"] += 1
                                    pbar.update(1)
                                    continue
                                    
                                # Skip binary content
                                if 'image/' in item.mimetype or 'application/' in item.mimetype:
                                    stats["skipped"]["binary"] += 1
                                    pbar.update(1)
                                    continue
                            except Exception as e:
                                if logger.level == logging.DEBUG:
                                    logger.debug(f"Error checking mimetype for entry {entry_idx}: {e}")
                                stats["skipped"]["error"] += 1
                                pbar.update(1)
                                continue
                            
                            # Add to entries list
                            entries.append(entry)
                            
                            pbar.update(1)
                        except Exception as e:
                            if logger.level == logging.DEBUG:
                                logger.debug(f"Error processing entry {entry_idx}: {e}")
                            stats["skipped"]["error"] += 1
                            pbar.update(1)
            except Exception as e:
                logger.warning(f"Error using get_entry_by_index method: {e}")
            
            # Method 2: Try to find entries by namespace
            if not entries:
                logger.info("No entries found using index method. Trying namespace method...")
                try:
                    # Try to get entries by namespace
                    namespaces = ['A', 'C', '-', 'W', 'M', 'I', 'J', 'S', 'T', 'V', 'X', 'U', 'Z', '']
                    for ns in namespaces:
                        try:
                            with tqdm(desc=f"Scanning namespace '{ns}'", disable=logger.level != logging.INFO) as pbar:
                                # This is a workaround since get_entries_by_namespace is not directly available
                                # We'll try to access entries with common patterns in each namespace
                                for i in range(1000):  # Try a reasonable number of entries
                                    try:
                                        # Try different patterns
                                        patterns = [
                                            f"{ns}/{i}",
                                            f"{ns}/article_{i}",
                                            f"{ns}/page_{i}",
                                            f"{ns}/entry_{i}"
                                        ]
                                        
                                        for pattern in patterns:
                                            try:
                                                if self.zim.has_entry_by_path(pattern):
                                                    entry = self.zim.get_entry_by_path(pattern)
                                                    stats["total"] += 1
                                                    
                                                    # Skip if this is the main entry (already processed)
                                                    if main_entry and entry.path == main_entry.path:
                                                        stats["skipped"]["duplicate"] += 1
                                                        continue
                                                    
                                                    # Skip redirects
                                                    if entry.is_redirect:
                                                        stats["skipped"]["redirect"] += 1
                                                        continue
                                                    
                                                    # Skip non-article entries (those without a title)
                                                    if not entry.title:
                                                        stats["skipped"]["non_html"] += 1
                                                        continue
                                                    
                                                    # Skip non-HTML entries
                                                    try:
                                                        item = entry.get_item()
                                                        if not item.mimetype.startswith('text/html'):
                                                            stats["skipped"]["non_html"] += 1
                                                            continue
                                                            
                                                        # Skip binary content
                                                        if 'image/' in item.mimetype or 'application/' in item.mimetype:
                                                            stats["skipped"]["binary"] += 1
                                                            continue
                                                    except Exception as e:
                                                        if logger.level == logging.DEBUG:
                                                            logger.debug(f"Error checking mimetype for entry {pattern}: {e}")
                                                        stats["skipped"]["error"] += 1
                                                        continue
                                                    
                                                    # Add to entries list
                                                    entries.append(entry)
                                            except Exception:
                                                pass
                                        
                                        pbar.update(1)
                                    except Exception:
                                        pbar.update(1)
                        except Exception as e:
                            logger.warning(f"Error scanning namespace '{ns}': {e}")
                except Exception as e:
                    logger.warning(f"Error using namespace method: {e}")
            
            # Method 3: Try to extract entries from the main page
            if not entries and main_entry:
                logger.info("No entries found using previous methods. Trying to extract from main page...")
                try:
                    # Get the main entry content
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
                            if path:
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
                                            if self.zim.has_entry_by_path(p):
                                                entry = self.zim.get_entry_by_path(p)
                                                stats["total"] += 1
                                                
                                                # Skip if this is the main entry (already processed)
                                                if main_entry and entry.path == main_entry.path:
                                                    stats["skipped"]["duplicate"] += 1
                                                    continue
                                                
                                                # Skip redirects
                                                if entry.is_redirect:
                                                    stats["skipped"]["redirect"] += 1
                                                    continue
                                                
                                                # Skip non-article entries (those without a title)
                                                if not entry.title:
                                                    stats["skipped"]["non_html"] += 1
                                                    continue
                                                
                                                # Skip non-HTML entries
                                                try:
                                                    item = entry.get_item()
                                                    if not item.mimetype.startswith('text/html'):
                                                        stats["skipped"]["non_html"] += 1
                                                        continue
                                                        
                                                    # Skip binary content
                                                    if 'image/' in item.mimetype or 'application/' in item.mimetype:
                                                        stats["skipped"]["binary"] += 1
                                                        continue
                                                except Exception as e:
                                                    if logger.level == logging.DEBUG:
                                                        logger.debug(f"Error checking mimetype for entry {p}: {e}")
                                                    stats["skipped"]["error"] += 1
                                                    continue
                                                
                                                # Add to entries list
                                                entries.append(entry)
                                                break
                                        except Exception:
                                            continue
                                except Exception as e:
                                    if logger.level == logging.DEBUG:
                                        logger.debug(f"Error processing path {path}: {e}")
                except Exception as e:
                    logger.warning(f"Error extracting entries from main page: {e}")
            
            # Method 4: Enhanced Compatibility Mode - Investigate ZIM structure
            if not entries:
                logger.info("No entries found using previous methods. Activating compatibility mode...")
                try:
                    # Step 1: Get ZIM metadata to find the main page
                    main_page_path = None
                    try:
                        # Try different metadata keys for main page
                        for key in ['mainPage', 'Main-Page', 'main_page', 'main-page']:
                            if key in self.zim.metadata_keys:
                                main_page_path = self.zim.get_metadata(key).decode('utf-8', errors='replace')
                                logger.info(f"Found main page path in metadata: {main_page_path}")
                                break
                        
                        # Try to access the main page directly
                        if main_page_path and not main_entry:
                            try:
                                if self.zim.has_entry_by_path(main_page_path):
                                    main_entry = self.zim.get_entry_by_path(main_page_path)
                                    if self.process_entry(main_entry, is_main=True):
                                        stats["processed"] += 1
                                    logger.info(f"Found and processed main page at {main_page_path}")
                            except Exception as e:
                                logger.warning(f"Error accessing main page at {main_page_path}: {e}")
                    except Exception as e:
                        logger.warning(f"Error getting main page from metadata: {e}")
                    
                    # Step 2: Analyze entry paths to find patterns
                    path_patterns = {}
                    domain_patterns = {}
                    file_extensions = {}
                    
                    logger.info("Analyzing ZIM structure to find patterns...")
                    with tqdm(total=min(10000, self.zim.entry_count), desc="Analyzing ZIM structure", disable=logger.level != logging.INFO) as pbar:
                        # Sample a subset of entries to find patterns
                        sample_size = min(10000, self.zim.entry_count)
                        step = max(1, self.zim.entry_count // sample_size)
                        
                        for entry_idx in range(0, self.zim.entry_count, step):
                            try:
                                entry = self.zim.get_entry_by_index(entry_idx)
                                
                                # Skip redirects
                                if entry.is_redirect:
                                    pbar.update(1)
                                    continue
                                
                                # Analyze the path even if it's not HTML
                                # This helps us find patterns in all types of content
                                path = entry.path
                                
                                # Extract domain pattern (e.g., "example.com/")
                                domain_match = re.match(r'^([a-zA-Z0-9.-]+\.[a-zA-Z]{2,})/.*', path)
                                if domain_match:
                                    domain = domain_match.group(1)
                                    domain_patterns[domain] = domain_patterns.get(domain, 0) + 1
                                
                                # Extract path pattern (e.g., "A/article_")
                                path_match = re.match(r'^([A-Za-z]*/[a-zA-Z0-9_-]+).*', path)
                                if path_match:
                                    pattern = path_match.group(1)
                                    path_patterns[pattern] = path_patterns.get(pattern, 0) + 1
                                
                                # Extract the first part of the path
                                parts = path.split('/')
                                if len(parts) > 0:
                                    first_part = parts[0]
                                    path_patterns[first_part] = path_patterns.get(first_part, 0) + 1
                                
                                # Extract file extensions
                                ext_match = re.search(r'\.([a-zA-Z0-9]+)$', path)
                                if ext_match:
                                    ext = ext_match.group(1).lower()
                                    file_extensions[ext] = file_extensions.get(ext, 0) + 1
                                
                                # Try to get mimetype
                                try:
                                    item = entry.get_item()
                                    if item.mimetype.startswith('text/html'):
                                        # This is an HTML entry, add it to our patterns with higher weight
                                        if domain_match:
                                            domain_patterns[domain] = domain_patterns.get(domain, 0) + 10
                                        if path_match:
                                            path_patterns[pattern] = path_patterns.get(pattern, 0) + 10
                                        if len(parts) > 0:
                                            path_patterns[first_part] = path_patterns.get(first_part, 0) + 10
                                except Exception:
                                    pass
                                
                                pbar.update(1)
                            except Exception:
                                pbar.update(1)
                                continue
                    
                    # Step 3: Find the most common patterns
                    common_domains = sorted(domain_patterns.items(), key=lambda x: x[1], reverse=True)
                    common_paths = sorted(path_patterns.items(), key=lambda x: x[1], reverse=True)
                    common_extensions = sorted(file_extensions.items(), key=lambda x: x[1], reverse=True)
                    
                    logger.info("Most common domain patterns found:")
                    for domain, count in common_domains[:5]:
                        logger.info(f"  - {domain}: {count} occurrences")
                    
                    logger.info("Most common path patterns found:")
                    for pattern, count in common_paths[:5]:
                        logger.info(f"  - {pattern}: {count} occurrences")
                    
                    logger.info("Most common file extensions found:")
                    for ext, count in common_extensions[:5]:
                        logger.info(f"  - .{ext}: {count} occurrences")
                    
                    # Step 4: Try to find articles using the most common patterns
                    article_count = 0
                    
                    # Try domain patterns first
                    if common_domains:
                        for domain_pattern, _ in common_domains[:3]:  # Try top 3 domain patterns
                            if article_count > 0:
                                break
                                
                            logger.info(f"Trying to find articles with domain pattern: {domain_pattern}/")
                            
                            with tqdm(total=self.zim.entry_count, desc=f"Scanning for {domain_pattern} articles", disable=logger.level != logging.INFO) as pbar:
                                for entry_idx in range(self.zim.entry_count):
                                    try:
                                        entry = self.zim.get_entry_by_index(entry_idx)
                                        
                                        # Check if this matches the domain pattern
                                        if entry.path.startswith(f"{domain_pattern}/") and (not main_page_path or entry.path != main_page_path):
                                            # Skip redirects
                                            if entry.is_redirect:
                                                stats["skipped"]["redirect"] += 1
                                                pbar.update(1)
                                                continue
                                            
                                            # Skip non-HTML entries
                                            try:
                                                item = entry.get_item()
                                                if not item.mimetype.startswith('text/html'):
                                                    stats["skipped"]["non_html"] += 1
                                                    pbar.update(1)
                                                    continue
                                            except Exception as e:
                                                if logger.level == logging.DEBUG:
                                                    logger.debug(f"Error checking mimetype for entry {entry.path}: {e}")
                                                stats["skipped"]["error"] += 1
                                                pbar.update(1)
                                                continue
                                            
                                            # Process the article
                                            if self.process_entry(entry):
                                                article_count += 1
                                                stats["processed"] += 1
                                                
                                                # Add to entries list for statistics
                                                entries.append(entry)
                                            
                                            # Limit the number of articles if specified
                                            if self.max_articles and article_count >= self.max_articles:
                                                logger.info(f"Reached maximum number of articles: {self.max_articles}")
                                                break
                                        
                                        pbar.update(1)
                                    except Exception as e:
                                        if logger.level == logging.DEBUG:
                                            logger.debug(f"Error processing entry {entry_idx}: {e}")
                                        stats["skipped"]["error"] += 1
                                        pbar.update(1)
                            
                            logger.info(f"Found and processed {article_count} articles using domain pattern {domain_pattern}")
                    
                    # If domain patterns didn't work, try path patterns
                    if common_paths and not article_count:
                        for path_pattern, _ in common_paths[:3]:  # Try top 3 path patterns
                            if article_count > 0:
                                break
                                
                            logger.info(f"Trying to find articles with path pattern: {path_pattern}")
                            
                            with tqdm(total=self.zim.entry_count, desc=f"Scanning for {path_pattern} articles", disable=logger.level != logging.INFO) as pbar:
                                for entry_idx in range(self.zim.entry_count):
                                    try:
                                        entry = self.zim.get_entry_by_index(entry_idx)
                                        
                                        # Check if this matches the path pattern
                                        if entry.path.startswith(path_pattern) and (not main_page_path or entry.path != main_page_path):
                                            # Skip redirects
                                            if entry.is_redirect:
                                                stats["skipped"]["redirect"] += 1
                                                pbar.update(1)
                                                continue
                                            
                                            # Skip non-HTML entries
                                            try:
                                                item = entry.get_item()
                                                if not item.mimetype.startswith('text/html'):
                                                    stats["skipped"]["non_html"] += 1
                                                    pbar.update(1)
                                                    continue
                                            except Exception as e:
                                                if logger.level == logging.DEBUG:
                                                    logger.debug(f"Error checking mimetype for entry {entry.path}: {e}")
                                                stats["skipped"]["error"] += 1
                                                pbar.update(1)
                                                continue
                                            
                                            # Process the article
                                            if self.process_entry(entry):
                                                article_count += 1
                                                stats["processed"] += 1
                                                
                                                # Add to entries list for statistics
                                                entries.append(entry)
                                            
                                            # Limit the number of articles if specified
                                            if self.max_articles and article_count >= self.max_articles:
                                                logger.info(f"Reached maximum number of articles: {self.max_articles}")
                                                break
                                        
                                        pbar.update(1)
                                    except Exception as e:
                                        if logger.level == logging.DEBUG:
                                            logger.debug(f"Error processing entry {entry_idx}: {e}")
                                        stats["skipped"]["error"] += 1
                                        pbar.update(1)
                            
                            logger.info(f"Found and processed {article_count} articles using path pattern {path_pattern}")
                    
                    # Step 5: If no articles found, try direct HTML detection
                    if not article_count:
                        logger.info("No articles found using patterns. Trying direct HTML detection...")
                        
                        with tqdm(total=self.zim.entry_count, desc="Scanning for HTML content", disable=logger.level != logging.INFO) as pbar:
                            for entry_idx in range(self.zim.entry_count):
                                try:
                                    entry = self.zim.get_entry_by_index(entry_idx)
                                    
                                    # Skip if this is the main entry (already processed)
                                    if main_entry and entry.path == main_entry.path:
                                        pbar.update(1)
                                        continue
                                    
                                    # Skip redirects
                                    if entry.is_redirect:
                                        pbar.update(1)
                                        continue
                                    
                                    # Check if this is an HTML entry with a title
                                    if entry.title:
                                        try:
                                            item = entry.get_item()
                                            if item.mimetype.startswith('text/html'):
                                                # Process the article
                                                if self.process_entry(entry):
                                                    article_count += 1
                                                    stats["processed"] += 1
                                                    
                                                    # Add to entries list for statistics
                                                    entries.append(entry)
                                                
                                                # Limit the number of articles if specified
                                                if self.max_articles and article_count >= self.max_articles:
                                                    logger.info(f"Reached maximum number of articles: {self.max_articles}")
                                                    break
                                        except Exception:
                                            pass
                                    
                                    pbar.update(1)
                                except Exception:
                                    pbar.update(1)
                                    continue
                        
                        logger.info(f"Found and processed {article_count} articles using direct HTML detection")
                
                except Exception as e:
                    logger.warning(f"Error in compatibility mode: {e}")
            
            logger.info(f"Found {len(entries)} HTML articles out of {stats['total']} total entries")
            
            # Process each entry
            for entry in tqdm(entries, desc="Processing articles", disable=logger.level != logging.INFO):
                if self.process_entry(entry):
                    stats["processed"] += 1
            
            # Log statistics
            logger.info(f"Full crawl statistics:")
            logger.info(f"  Total entries: {stats['total']}")
            logger.info(f"  Processed articles: {stats['processed']}")
            logger.info(f"  Skipped entries:")
            for reason, count in stats["skipped"].items():
                if count > 0:
                    logger.info(f"    - {reason}: {count}")
            
            # If no articles were processed but we have a main entry, try to extract content from it
            if not self.articles and main_entry and main_entry.path not in self.articles:
                logger.warning("No articles were processed. Trying to extract content from main entry.")
                self._extract_content_from_main_entry(main_entry)
            
            return self.articles
        
        except Exception as e:
            logger.error(f"Error during full crawl: {e}")
            raise
    
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
            title = main_entry.title or "Main Page"
            
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