"""
CLI utility functions for the voice scam dataset generator.
"""

import logging
import sys
from datetime import datetime
from pathlib import Path


def setup_logging(level: str = 'INFO'):
    """
    Set up logging configuration.
    
    Args:
        level: Logging level (DEBUG, INFO, WARNING, ERROR)
    """
    logging.basicConfig(
        level=getattr(logging, level),
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    
    # Set httpx logger to DEBUG level to prevent INFO logs from interfering with tqdm
    httpx_logger = logging.getLogger('httpx')
    httpx_logger.setLevel(logging.WARNING)


def print_banner():
    """Print the application banner."""
    banner = """
╔══════════════════════════════════════════════════════════╗
║        Voice Scam Dataset Generator                      ║
║        Multilingual Synthetic Conversation Generation    ║
╚══════════════════════════════════════════════════════════╝
"""
    print(banner)


def print_step_header(step_name: str):
    """
    Print a formatted header for a pipeline step.
    
    Args:
        step_name: Name of the step
    """
    print(f"\n{'='*60}")
    print(f"  {step_name.upper()}")
    print(f"{'='*60}\n")


def print_step_complete(step_name: str, duration: float = None):
    """
    Print completion message for a pipeline step.
    
    Args:
        step_name: Name of the step
        duration: Duration in seconds (optional)
    """
    if duration:
        print(f"\n✓ {step_name} completed in {duration:.2f} seconds")
    else:
        print(f"\n✓ {step_name} completed")


def format_file_size(size_bytes: int) -> str:
    """
    Format file size in human-readable format.
    
    Args:
        size_bytes: Size in bytes
        
    Returns:
        Formatted string (e.g., "1.5 MB")
    """
    for unit in ['B', 'KB', 'MB', 'GB']:
        if size_bytes < 1024.0:
            return f"{size_bytes:.1f} {unit}"
        size_bytes /= 1024.0
    return f"{size_bytes:.1f} TB"


def confirm_action(message: str, default_yes: bool = False) -> bool:
    """
    Ask user for confirmation.
    
    Args:
        message: Confirmation message
        default_yes: If True, 'y' is the default (Y/n), otherwise 'n' is default (y/N)
        
    Returns:
        True if user confirms, False otherwise
    """
    if default_yes:
        prompt = f"{message} (Y/n): "
        response = input(prompt).strip().lower()
        return response != 'n'
    else:
        prompt = f"{message} (y/N): "
        response = input(prompt).strip().lower()
        return response == 'y'


def create_timestamp() -> str:
    """
    Create a timestamp string for file naming.
    
    Returns:
        Timestamp in format YYYY-MM-DD_HHMMSS
    """
    return datetime.now().strftime("%Y-%m-%d_%H%M%S")


def ensure_directory(path: Path) -> Path:
    """
    Ensure a directory exists, creating it if necessary.
    
    Args:
        path: Directory path
        
    Returns:
        The path object
    """
    path.mkdir(parents=True, exist_ok=True)
    return path


def print_error(message: str):
    """
    Print an error message to stderr.
    
    Args:
        message: Error message
    """
    print(f"ERROR: {message}", file=sys.stderr)


def print_warning(message: str):
    """
    Print a warning message.
    
    Args:
        message: Warning message
    """
    print(f"WARNING: {message}")


def print_info(message: str):
    """
    Print an info message.
    
    Args:
        message: Info message
    """
    print(f"INFO: {message}")


class ProgressTracker:
    """Simple progress tracker for pipeline steps."""
    
    def __init__(self, total_steps: int):
        """
        Initialize progress tracker.
        
        Args:
            total_steps: Total number of steps
        """
        self.total_steps = total_steps
        self.current_step = 0
        self.start_time = datetime.now()
    
    def update(self, step_name: str):
        """
        Update progress with current step.
        
        Args:
            step_name: Name of the current step
        """
        self.current_step += 1
        elapsed = (datetime.now() - self.start_time).total_seconds()
        
        progress = self.current_step / self.total_steps * 100
        print(f"\n[{self.current_step}/{self.total_steps}] {progress:.0f}% - {step_name}")
        print(f"Elapsed time: {elapsed:.1f}s")
    
    def complete(self):
        """Mark progress as complete."""
        total_time = (datetime.now() - self.start_time).total_seconds()
        print(f"\n✓ Pipeline completed in {total_time:.1f} seconds")


def format_language_info(config) -> str:
    """
    Format language configuration information for display.
    
    Args:
        config: Config object
        
    Returns:
        Formatted string
    """
    info = f"""
Language: {config.language_name} ({config.language_code})
Region: {config.region}
Translation: {config.translation_from_code} → {config.translation_intermediate_code} → {config.translation_to_code}
Voice IDs: {len(config.voice_ids[config.language_code])} voices available
Categories: {len(config.legit_call_categories)} conversation types
"""
    return info