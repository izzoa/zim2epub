import pytest
import os
import sys
import tempfile
from unittest.mock import patch

# Add the parent directory to the path so we can import the module
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from zim2epub import ZimToEpub

@pytest.mark.parametrize("include_images,generate_toc", [
    (True, True),
    (False, True),
    (True, False),
    (False, False)
])
def test_conversion_with_mock(mock_zim_archive, include_images, generate_toc):
    """Test the conversion process with a mock ZIM archive."""
    with patch('zim2epub.Archive', return_value=mock_zim_archive):
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
                max_articles=2,  # Limit to 2 articles for faster testing
                verbose=True
            )
            
            # Run the conversion
            result_path = converter.convert()
            
            # Check that the output file exists
            assert os.path.exists(result_path)
            assert os.path.getsize(result_path) > 0
            
            # Check that the result path matches the expected output path
            assert result_path == output_path
            
            # Check that articles were processed
            assert len(converter.articles) > 0
        
        finally:
            # Clean up the temporary file
            if os.path.exists(output_path):
                os.unlink(output_path)

def test_metadata_extraction(mock_zim_archive):
    """Test metadata extraction from the ZIM file."""
    with patch('zim2epub.Archive', return_value=mock_zim_archive):
        # Initialize the converter
        converter = ZimToEpub(
            zim_path="dummy.zim",
            output_path="dummy.epub",
            include_images=False,
            generate_toc=False,
            verbose=True
        )
        
        # Test getting metadata
        for field in ['Title', 'Language', 'Creator', 'Publisher', 'Description']:
            value = converter._get_metadata(field)
            assert value == 'Test Value'
        
        # Test getting non-existent metadata
        value = converter._get_metadata('NonExistent')
        assert value is None

def test_article_paths(mock_zim_archive):
    """Test getting article paths from the ZIM file."""
    with patch('zim2epub.Archive', return_value=mock_zim_archive):
        # Initialize the converter
        converter = ZimToEpub(
            zim_path="dummy.zim",
            output_path="dummy.epub",
            include_images=False,
            generate_toc=False,
            verbose=True
        )
        
        # Get article paths
        paths = converter._get_article_paths()
        
        # Check that we got some paths
        assert len(paths) > 0
        
        # Check that the main entry path is included
        assert 'mainPage' in paths or any(p.endswith('mainPage') for p in paths) 