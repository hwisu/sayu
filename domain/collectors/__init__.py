"""Collectors package"""

from .cli import CliCollector
from .git import GitCollector
from .manager import CollectorManager

__all__ = ['CliCollector', 'GitCollector', 'CollectorManager']
