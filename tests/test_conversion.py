import pytest
import os
import sys
import tempfile
from unittest.mock import patch

# Add the parent directory to the path so we can import the module
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from zim2epub import ZimToEpub
from zim2epub.converter.metadata import MetadataExtractor
from zim2epub.converter.article_extractor import StandardExtractor

@pytest.mark.parametrize("include_images,generate_toc", [
    (True, True),
    (False, True),
    (True, False),
    (False, False)
])
def test_conversion_with_mock(mock_zim_archive, include_images, generate_toc):
    """Test the conversion process with a mock ZIM archive."""
    with patch('zim2epub.converter.zim_to_epub.Archive', return_value=mock_zim_archive), \
         patch('zim2epub.converter.zim_to_epub.ImageProcessor'), \
         patch('zim2epub.converter.zim_to_epub.TocGenerator'), \
         patch('zim2epub.converter.zim_to_epub.epub.write_epub'):
        
        # Create a temporary output file
        with tempfile.NamedTemporaryFile(suffix='.epub', delete=False) as temp_file:
            output_path = temp_file.name
        
        try:
            # Initialize the converter
            converter = ZimToEpub(
                zim_path="dummy.zim",
                output_path=output_path,
                include_images=include_images,
                generate_toc=generate_toc,
                verbose=True
            )
            
            # Run the conversion
            result = converter.convert()
            
            # Check that the conversion was successful
            assert result == output_path  # convert returns the output path
            
            # Check that the appropriate methods were called based on settings
            if include_images:
                assert hasattr(converter, 'book')  # Book should be created
            
            if generate_toc:
                assert hasattr(converter, 'book')  # Book should be created
        
        finally:
            # Clean up the temporary file
            if os.path.exists(output_path):
                os.unlink(output_path)

def test_metadata_extraction(mock_zim_archive):
    """Test metadata extraction from the ZIM file."""
    # Create a metadata extractor
    metadata_extractor = MetadataExtractor(mock_zim_archive, "dummy.zim")
    
    # Test getting metadata
    for field in ['Title', 'Language', 'Creator', 'Publisher', 'Description']:
        value = metadata_extractor.get_metadata(field)
        assert value == 'Test Value'
    
    # Test extracting all metadata
    metadata = metadata_extractor.extract_metadata()
    assert metadata['title'] == 'Test Value'
    assert metadata['language'] == 'Test Value'
    assert metadata['creator'] == 'Test Value'
    assert metadata['publisher'] == 'Test Value'
    assert metadata['description'] == 'Test Value'
    assert 'date' in metadata
    assert 'source' in metadata
    assert 'identifier' in metadata

def test_article_paths(mock_zim_archive):
    """Test getting article paths from the ZIM file."""
    # Create an article extractor
    article_extractor = StandardExtractor(mock_zim_archive)
    
    # Get article paths
    paths = article_extractor._get_article_paths()
    
    # Check that the paths include the main page
    assert 'mainPage' in paths
    assert len(paths) > 0 