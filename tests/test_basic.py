import unittest
import os
import sys
from unittest.mock import patch, MagicMock

# Add the parent directory to the path so we can import the module
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from zim2epub import ZimToEpub

class TestBasic(unittest.TestCase):
    @patch('zim2epub.Archive')
    def test_initialization(self, mock_archive):
        """Test that the ZimToEpub class can be initialized with a mocked Archive."""
        # Set up the mock
        mock_instance = MagicMock()
        mock_archive.return_value = mock_instance
        
        # Configure the mock to have the necessary attributes and methods
        mock_instance.metadata_keys = ['Title', 'Language', 'Creator']
        mock_instance.get_metadata.return_value = 'Test Value'
        mock_instance.has_main_entry = True
        mock_instance.main_entry = MagicMock()
        
        # Now initialize ZimToEpub with our mocked Archive
        converter = ZimToEpub(
            zim_path="dummy.zim",
            output_path="dummy.epub",
            include_images=False,
            generate_toc=False,
            max_articles=10,
            verbose=True
        )
        
        # Verify the initialization worked
        self.assertEqual(converter.zim_path, "dummy.zim")
        self.assertEqual(converter.output_path, "dummy.epub")
        self.assertEqual(converter.include_images, False)
        self.assertEqual(converter.generate_toc, False)
        self.assertEqual(converter.max_articles, 10)
        self.assertEqual(converter.verbose, True)
        
        # Verify the mock was called
        mock_archive.assert_called_once_with("dummy.zim")
    
    def test_sanitize_text(self):
        """Test the _sanitize_text method."""
        # Create a dummy instance without initializing the ZIM file
        converter = ZimToEpub.__new__(ZimToEpub)
        
        # Test with a normal string
        self.assertEqual(converter._sanitize_text("Hello World"), "Hello World")
        
        # Test with None
        self.assertIsNone(converter._sanitize_text(None))
        
        # Test with control characters
        self.assertEqual(converter._sanitize_text("Hello\nWorld"), "Hello World")
        self.assertEqual(converter._sanitize_text("Hello\rWorld"), "Hello World")
        self.assertEqual(converter._sanitize_text("Hello\r\nWorld"), "Hello World")
        
        # Test with bytes
        self.assertEqual(converter._sanitize_text(b"Hello World"), "Hello World")
    
    def test_get_extension(self):
        """Test the _get_extension method."""
        # Create a dummy instance without initializing the ZIM file
        converter = ZimToEpub.__new__(ZimToEpub)
        
        # Test with various file paths
        self.assertEqual(converter._get_extension("image.jpg"), "jpg")
        self.assertEqual(converter._get_extension("image.png"), "png")
        self.assertEqual(converter._get_extension("path/to/image.gif"), "gif")
        self.assertEqual(converter._get_extension("image"), "jpg")  # Default
        self.assertEqual(converter._get_extension("image."), "")  # Empty extension
    
    def test_get_unique_image_filename(self):
        """Test the _get_unique_image_filename method."""
        # Create a dummy instance and initialize necessary attributes
        converter = ZimToEpub.__new__(ZimToEpub)
        converter.processed_images = {}
        
        # Test generating unique filenames
        filename1 = converter._get_unique_image_filename("image1.jpg")
        self.assertTrue(filename1.endswith(".jpg"))
        self.assertIn(filename1, converter.processed_images.values())
        
        # Test with the same path should return the same filename
        filename2 = converter._get_unique_image_filename("image1.jpg")
        self.assertEqual(filename1, filename2)
        
        # Test with a different path should return a different filename
        filename3 = converter._get_unique_image_filename("image2.jpg")
        self.assertNotEqual(filename1, filename3)

if __name__ == '__main__':
    unittest.main() 