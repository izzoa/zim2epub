#!/usr/bin/env python3
"""
Setup script for pyzim2epub.
"""

from setuptools import setup, find_packages

with open("README.md", "r", encoding="utf-8") as fh:
    long_description = fh.read()

setup(
    name="zim2epub",
    version="0.1.4",
    author="Anthony Izzo",
    author_email="izzo.anthony@gmail.com",
    description="Convert ZIM files to EPUB format",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/izzoa/zim2epub",
    packages=find_packages(),
    py_modules=[],
    classifiers=[
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
        "Development Status :: 3 - Alpha",
        "Intended Audience :: End Users/Desktop",
        "Topic :: Text Processing :: Markup :: XML",
    ],
    python_requires=">=3.6",
    install_requires=[
        "libzim>=3.0.0",
        "ebooklib>=0.17.1",
        "beautifulsoup4>=4.9.0",
        "argparse>=1.4.0",
        "tqdm>=4.45.0",
        "lxml>=4.5.0",
    ],
    entry_points={
        "console_scripts": [
            "zim2epub=zim2epub.cli:main",
        ],
    },
) 