"""
Logging utilities for conditional output based on verbosity settings.
"""

import logging
import sys
from typing import Optional
from tqdm import tqdm

logger = logging.getLogger(__name__)


class ConditionalLogger:
    """
    Logger wrapper that provides conditional output based on verbosity settings.
    """
    
    def __init__(self, name: str, verbose: bool = False):
        """
        Initialize conditional logger.
        
        Args:
            name: Logger name
            verbose: Whether to show verbose output
        """
        self.logger = logging.getLogger(name)
        self.verbose = verbose
    
    def info(self, message: str, force: bool = False):
        """
        Log info message, only if verbose or forced.
        
        Args:
            message: Message to log
            force: Force logging even in non-verbose mode
        """
        if self.verbose or force:
            self.logger.info(message)
    
    def debug(self, message: str):
        """
        Log debug message (always conditional on verbose).
        
        Args:
            message: Message to log
        """
        if self.verbose:
            self.logger.debug(message)
    
    def warning(self, message: str):
        """
        Log warning message (always shown).
        
        Args:
            message: Message to log
        """
        self.logger.warning(message)
    
    def error(self, message: str):
        """
        Log error message (always shown).
        
        Args:
            message: Message to log
        """
        self.logger.error(message)
    
    def success(self, message: str, force: bool = True):
        """
        Log success message with checkmark.
        
        Args:
            message: Message to log
            force: Force logging even in non-verbose mode (default True)
        """
        if self.verbose or force:
            self.logger.info(f"✓ {message}")
    
    def progress_write(self, message: str, pbar: Optional[tqdm] = None):
        """
        Write message safely without interfering with progress bars.
        
        Args:
            message: Message to write
            pbar: Progress bar instance (optional)
        """
        # Always use tqdm.write when available to avoid interference
        if pbar:
            tqdm.write(message)
        elif self.verbose:
            print(message, file=sys.stdout, flush=True)


def create_progress_bar(total: int, desc: str, unit: str = "it", leave: bool = True) -> tqdm:
    """
    Create a standardized progress bar.
    
    Args:
        total: Total number of items
        desc: Description for the progress bar
        unit: Unit name for progress bar
        leave: Whether to keep progress bar after completion
        
    Returns:
        Configured tqdm progress bar
    """
    return tqdm(
        total=total,
        desc=desc,
        unit=unit,
        ncols=80,
        leave=leave,
        file=sys.stdout,
        position=0,
        bar_format='{desc}: {percentage:3.0f}%|{bar}| {n_fmt}/{total_fmt} {unit} [{elapsed}<{remaining}]'
    )


def format_completion_message(operation: str, duration: float, success_count: int, 
                            total_count: int, extra_info: str = "") -> str:
    """
    Format a standardized completion message.
    
    Args:
        operation: Name of the operation
        duration: Duration in seconds
        success_count: Number of successful items
        total_count: Total number of items
        extra_info: Additional information to include
        
    Returns:
        Formatted completion message
    """
    success_rate = f"({success_count}/{total_count})" if success_count != total_count else ""
    extra = f" {extra_info}" if extra_info else ""
    return f"{operation} completed in {duration:.2f} seconds {success_rate}{extra}"


def print_module_header(module_name: str):
    """
    Print a standardized module header.
    
    Args:
        module_name: Name of the module
    """
    header = f"  {module_name.upper()}  "
    border = "=" * 60
    padding = (60 - len(header)) // 2
    centered_header = " " * padding + header + " " * (60 - len(header) - padding)
    
    print(border)
    print(centered_header)
    print(border)