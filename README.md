# ZIM to EPUB Converter

A Python command-line tool to convert ZIM files (used by Kiwix and others for offline content) to EPUB format for e-readers.

## Features

- Convert ZIM files to EPUB format with robust error handling
- Option to include or exclude images
- Automatic table of contents generation based on article names
- Limit the number of articles to include
- Preserves metadata from the ZIM file
- Clean, readable formatting for e-readers
- Handles URL-encoded paths and special characters
- Supports various ZIM file structures and formats
- Extracts content from main entry when standard article paths aren't available
- Avoids duplicate images in the output EPUB

## Recent Updates

- **Improved URL handling**: Added support for URL-encoded paths and special characters
- **Enhanced image processing**: Fixed issues with duplicate images and improved mimetype detection
- **Better article extraction**: Added multiple methods to extract articles from different ZIM file structures
- **Robust error handling**: Added comprehensive error handling and fallback mechanisms
- **Detailed logging**: Added verbose logging to help diagnose issues

## Installation

### Prerequisites

- Python 3.6 or higher
- C++ libzim library (required for the Python bindings)

### Installing C++ libzim

#### macOS
```bash
brew install libzim
```

#### Debian/Ubuntu
```bash
apt-get install libzim-dev
```

#### Fedora
```bash
dnf install libzim-devel
```

### Installing the Python package

1. Clone this repository:
   ```bash
   git clone https://github.com/yourusername/pyzim2epub.git
   cd pyzim2epub
   ```

2. Install the required dependencies:
   ```bash
   USE_SYSTEM_LIBZIM=1 pip install -r requirements.txt
   ```

3. (Optional) Install the package in development mode:
   ```bash
   pip install -e .
   ```

## Usage

### Basic usage

```bash
python zim2epub.py path/to/your/file.zim
```

This will create an EPUB file with the same name as the input file in the current directory.

### Command-line Options

```
usage: zim2epub.py [-h] [-o OUTPUT] [--no-images] [--no-toc] [--max-articles MAX_ARTICLES] [-v] zim_file

Convert ZIM files to EPUB format

positional arguments:
  zim_file              Path to the ZIM file to convert

optional arguments:
  -h, --help            show this help message and exit
  -o OUTPUT, --output OUTPUT
                        Path for the output EPUB file (default: same as input with .epub extension)
  --no-images           Do not include images in the EPUB (default: False)
  --no-toc              Do not generate a table of contents (default: False)
  --max-articles MAX_ARTICLES
                        Maximum number of articles to include (default: None)
  -v, --verbose         Show verbose output (default: False)
```

### Examples

Convert a ZIM file without images (useful for smaller file size):
```bash
python zim2epub.py wikipedia.zim --no-images
```

Convert a ZIM file with a custom output path:
```bash
python zim2epub.py wikipedia.zim -o my-wikipedia.epub
```

Convert only the first 100 articles of a ZIM file:
```bash
python zim2epub.py wikipedia.zim --max-articles 100
```

Enable verbose output for debugging:
```bash
python zim2epub.py wikipedia.zim -v
```

### Using as a Library

You can also use the `ZimToEpub` class directly in your Python code:

```python
from zim2epub import ZimToEpub

converter = ZimToEpub(
    zim_path="path/to/file.zim",
    output_path="output.epub",
    include_images=True,
    generate_toc=True,
    max_articles=None,
    verbose=True
)

output_path = converter.convert()
print(f"EPUB created at: {output_path}")
```

## Troubleshooting

If you encounter issues:

1. Try running with the `-v` flag to see detailed logs
2. Make sure you have the C++ libzim library installed
3. Check that your ZIM file is valid and not corrupted
4. For image issues, try using the `--no-images` flag

## Requirements

- Python 3.6 or higher
- libzim (Python bindings for the ZIM file format)
- EbookLib (for EPUB creation)
- BeautifulSoup4 (for HTML parsing)
- tqdm (for progress bars)
- lxml (for XML processing)

## License

This project is licensed under the MIT License - see the LICENSE file for details.

## Acknowledgments

- The [OpenZIM](https://github.com/openzim) project for the libzim library
- [EbookLib](https://github.com/aerkalov/ebooklib) for EPUB creation functionality 