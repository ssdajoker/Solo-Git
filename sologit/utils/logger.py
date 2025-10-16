
"""
Logging utilities for Solo Git.

Provides structured logging with different levels and formatters.
"""

import logging
import sys
from pathlib import Path
from typing import Optional


# Color codes for terminal output
class Colors:
    RESET = '\033[0m'
    BOLD = '\033[1m'
    RED = '\033[31m'
    GREEN = '\033[32m'
    YELLOW = '\033[33m'
    BLUE = '\033[34m'
    MAGENTA = '\033[35m'
    CYAN = '\033[36m'
    WHITE = '\033[37m'


class ColoredFormatter(logging.Formatter):
    """Custom formatter with colors for console output."""
    
    LEVEL_COLORS = {
        'DEBUG': Colors.CYAN,
        'INFO': Colors.GREEN,
        'WARNING': Colors.YELLOW,
        'ERROR': Colors.RED,
        'CRITICAL': Colors.RED + Colors.BOLD
    }
    
    def __init__(self, fmt: Optional[str] = None, use_colors: bool = True):
        super().__init__(fmt)
        self.use_colors = use_colors and sys.stderr.isatty()
    
    def format(self, record):
        if self.use_colors:
            levelname = record.levelname
            if levelname in self.LEVEL_COLORS:
                record.levelname = (
                    f"{self.LEVEL_COLORS[levelname]}{levelname}{Colors.RESET}"
                )
        return super().format(record)


def setup_logging(verbose: bool = False, log_file: Optional[Path] = None):
    """
    Setup logging configuration.
    
    Args:
        verbose: Enable verbose (DEBUG) logging
        log_file: Optional path to log file
    """
    # Determine log level
    level = logging.DEBUG if verbose else logging.INFO
    
    # Create root logger
    root_logger = logging.getLogger('sologit')
    root_logger.setLevel(level)
    
    # Remove existing handlers
    root_logger.handlers.clear()
    
    # Console handler with colors
    console_handler = logging.StreamHandler(sys.stderr)
    console_handler.setLevel(level)
    
    console_format = '%(levelname)s: %(message)s'
    if verbose:
        console_format = '%(levelname)s [%(name)s]: %(message)s'
    
    console_formatter = ColoredFormatter(console_format)
    console_handler.setFormatter(console_formatter)
    root_logger.addHandler(console_handler)
    
    # File handler (if specified)
    if log_file:
        log_file.parent.mkdir(parents=True, exist_ok=True)
        file_handler = logging.FileHandler(log_file)
        file_handler.setLevel(logging.DEBUG)
        
        file_format = '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        file_formatter = logging.Formatter(file_format)
        file_handler.setFormatter(file_formatter)
        root_logger.addHandler(file_handler)
    
    # Suppress noisy third-party loggers
    logging.getLogger('urllib3').setLevel(logging.WARNING)
    logging.getLogger('requests').setLevel(logging.WARNING)


def get_logger(name: str) -> logging.Logger:
    """
    Get a logger for the given name.
    
    Args:
        name: Logger name (typically __name__)
    
    Returns:
        Configured logger instance
    """
    # Ensure the logger is under the sologit namespace
    if not name.startswith('sologit.'):
        name = f'sologit.{name}'
    
    return logging.getLogger(name)


class LogContext:
    """Context manager for temporary log level changes."""
    
    def __init__(self, logger: logging.Logger, level: int):
        self.logger = logger
        self.level = level
        self.old_level = None
    
    def __enter__(self):
        self.old_level = self.logger.level
        self.logger.setLevel(self.level)
        return self.logger
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        self.logger.setLevel(self.old_level)

