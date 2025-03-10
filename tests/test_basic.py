import unittest
import os
from unittest.mock import patch, MagicMock

from zim2epub import ZimToEpub
from zim2epub.utils.html_utils import sanitize_text
from zim2epub.utils.path_utils import get_extension
from zim2epub.converter.image_processor import ImageProcessor

class TestBasic(unittest.TestCase):
    @patch('zim2epub.converter.zim_to_epub.Archive')
    def test_initialization(self, mock_archive):
        """Test that the ZimToEpub class can be initialized with a mocked Archive."""
        # Set up the mock
        mock_instance = MagicMock()
        mock_archive.return_value = mock_instance
        
        # Configure the mock to have the necessary attributes and methods
        mock_instance.metadata_keys = ['Title', 'Language', 'Creator']
        mock_instance.get_metadata = MagicMock(return_value="Test Value")
        mock_instance.has_main_entry = True
        mock_instance.main_entry = MagicMock()
        mock_instance.main_entry.path = "A/Main_Page"
        mock_instance.main_entry.title = "Main Page"
        
        # Initialize the converter
        converter = ZimToEpub(
            zim_path="dummy.zim",
            output_path="dummy.epub",
            include_images=True,
            generate_toc=True,
            verbose=True
        )
        
        # Check that the converter was initialized correctly
        self.assertEqual(converter.zim_path, "dummy.zim")
        self.assertEqual(converter.include_images, True)
        self.assertEqual(converter.generate_toc, True)
        self.assertEqual(converter.verbose, True)
    
    def test_sanitize_text(self):
        """Test the sanitize_text function."""
        # Test with a normal string
        self.assertEqual(sanitize_text("Hello World"), "Hello World")
        
        # Test with special characters
        self.assertEqual(sanitize_text("Line1\nLine2"), "Line1 Line2")
        
        # Test with control characters
        self.assertEqual(sanitize_text("Text\x00with\x01control\x02chars"), "Textwithcontrolchars")
        
        # Test with bytes
        self.assertEqual(sanitize_text(b"Bytes string"), "Bytes string")
        
        # Test with None
        self.assertIsNone(sanitize_text(None))
    
    def test_get_extension(self):
        """Test the get_extension function."""
        # Test with various file paths
        self.assertEqual(get_extension("image.jpg"), "jpg")
        self.assertEqual(get_extension("path/to/image.png"), "png")
        self.assertEqual(get_extension("no_extension"), "")
        self.assertEqual(get_extension("image."), "")
        self.assertEqual(get_extension(".htaccess"), "")  # Files starting with a dot have no extension
    
    def test_get_unique_image_filename(self):
        """Test the _get_unique_image_filename method."""
        # Create an ImageProcessor instance
        image_processor = ImageProcessor(MagicMock(), MagicMock())
        image_processor.processed_images = {}
        
        # Test generating unique filenames
        filename1 = image_processor._get_unique_image_filename("image1.jpg")
        self.assertEqual(filename1, "image1.jpg")
        
        # Add the filename to processed_images to simulate it being used
        image_processor.processed_images[filename1] = True
        
        # Test generating a unique filename for the same base name
        filename2 = image_processor._get_unique_image_filename("image1.jpg")
        self.assertNotEqual(filename1, filename2)
        self.assertTrue(filename2.startswith("image1_"))
        self.assertTrue(filename2.endswith(".jpg"))

if __name__ == '__main__':
    unittest.main() 