from datetime import datetime

def parse_date(date_str: str, fmt: str = '%d-%m-%Y') -> datetime:
    """Parse date string to datetime object"""
    return datetime.strptime(date_str, fmt) if date_str else None

def format_date(date: datetime, fmt: str = '%d-%m-%Y') -> str:
    """Format datetime object to date string"""
    return date.strftime(fmt) if date else None


def parse_iso_date(date_str: str) -> datetime:
    """Parse ISO 8601 date string to datetime object"""
    return datetime.fromisoformat(date_str) if date_str else None

def format_iso_date(date: datetime) -> str:
    """Format datetime object to ISO 8601 string"""
    return date.isoformat() if date else None