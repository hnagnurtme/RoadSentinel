"""
Common helper functions.
"""
import hashlib
import secrets
from datetime import datetime, timedelta
from typing import Any, Dict


def generate_random_string(length: int = 32) -> str:
    """
    Generate a secure random string.
    
    Args:
        length: Length of the string to generate
        
    Returns:
        Random string
    """
    return secrets.token_urlsafe(length)


def hash_string(text: str) -> str:
    """
    Hash a string using SHA256.
    
    Args:
        text: String to hash
        
    Returns:
        Hashed string
    """
    return hashlib.sha256(text.encode()).hexdigest()


def get_client_ip(request) -> str:
    """
    Get client IP address from request.
    
    Args:
        request: Django request object
        
    Returns:
        Client IP address
    """
    x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
    if x_forwarded_for:
        ip = x_forwarded_for.split(',')[0]
    else:
        ip = request.META.get('REMOTE_ADDR')
    return ip


def format_datetime(dt: datetime, format_str: str = '%Y-%m-%d %H:%M:%S') -> str:
    """
    Format datetime object to string.
    
    Args:
        dt: Datetime object
        format_str: Format string
        
    Returns:
        Formatted datetime string
    """
    return dt.strftime(format_str)


def parse_datetime(date_string: str, format_str: str = '%Y-%m-%d %H:%M:%S') -> datetime:
    """
    Parse string to datetime object.
    
    Args:
        date_string: Date string
        format_str: Format string
        
    Returns:
        Datetime object
    """
    return datetime.strptime(date_string, format_str)


def days_from_now(days: int) -> datetime:
    """
    Calculate datetime X days from now.
    
    Args:
        days: Number of days
        
    Returns:
        Datetime object
    """
    return datetime.now() + timedelta(days=days)


def sanitize_filename(filename: str) -> str:
    """
    Sanitize filename to prevent security issues.
    
    Args:
        filename: Original filename
        
    Returns:
        Sanitized filename
    """
    import re
    # Remove any non-alphanumeric characters except dots, dashes, and underscores
    sanitized = re.sub(r'[^\w\s\-\.]', '', filename)
    # Replace spaces with underscores
    sanitized = sanitized.replace(' ', '_')
    return sanitized
