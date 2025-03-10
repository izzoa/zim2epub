import pytest
import os
from unittest.mock import MagicMock

@pytest.fixture
def mock_zim_archive():
    """Create a mock ZIM archive for testing."""
    mock = MagicMock()
    
    # Configure basic properties
    mock.metadata_keys = ['Title', 'Language', 'Creator', 'Publisher', 'Description']
    mock.get_metadata.return_value = 'Test Value'
    mock.has_main_entry = True
    mock.main_entry = MagicMock()
    mock.main_entry.path = 'mainPage'
    mock.main_entry.title = 'Main Page'
    mock.main_entry.is_redirect = False
    
    # Configure item for main entry
    mock_item = MagicMock()
    mock_item.content = MagicMock()
    mock_item.content.tobytes.return_value = b'<html><head><title>Test Page</title></head><body><h1>Test</h1><a href="A/1">Link 1</a><a href="A/2">Link 2</a><a href="mainPage">Main Page</a></body></html>'
    mock_item.mimetype = 'text/html'
    mock.main_entry.get_item.return_value = mock_item
    
    # Configure entry count
    mock.entry_count = 100
    mock.article_count = 50
    
    # Configure has_entry_by_path
    def has_entry_by_path(path):
        return path in ['mainPage', 'A/1', 'A/2', 'A/3']
    mock.has_entry_by_path = has_entry_by_path
    
    # Configure get_entry_by_path
    def get_entry_by_path(path):
        if path not in ['mainPage', 'A/1', 'A/2', 'A/3']:
            raise ValueError(f"Entry not found: {path}")
        
        entry = MagicMock()
        entry.path = path
        entry.title = f"Page {path}"
        entry.is_redirect = False
        
        item = MagicMock()
        item.content = MagicMock()
        item.content.tobytes.return_value = f'<html><head><title>Page {path}</title></head><body><h1>Test {path}</h1></body></html>'.encode('utf-8')
        item.mimetype = 'text/html'
        entry.get_item.return_value = item
        
        return entry
    
    mock.get_entry_by_path = get_entry_by_path
    
    return mock 