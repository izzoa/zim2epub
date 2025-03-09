import unittest
import os
import sys

# Add the parent directory to the path so we can import the module
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from zim2epub import ZimToEpub

class TestBasic(unittest.TestCase):
    def test_initialization(self):
        """Test that the ZimToEpub class can be initialized."""
        # This test doesn't require an actual ZIM file
        try:
            converter = ZimToEpub(
                zim_path="dummy.zim",
                output_path="dummy.epub",
                include_images=False,
                generate_toc=False,
                max_articles=10,
                verbose=True
            )
            # If we get here without an error, the initialization worked
            self.assertTrue(True)
        except Exception as e:
            self.fail(f"ZimToEpub initialization raised an exception: {e}")
    
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

if __name__ == '__main__':
    unittest.main() 