"""
Logging utilities for ZIM to EPUB conversion.
"""

import logging

def setup_logger(verbose=False):
    """
    Set up and configure the logger.
    
    Args:
        verbose (bool): Whether to show verbose output
        
    Returns:
        logging.Logger: Configured logger
    """
    # Configure logging
    level = logging.INFO if verbose else logging.WARNING
    logging.basicConfig(
        level=level,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    return logging.getLogger('zim2epub') 