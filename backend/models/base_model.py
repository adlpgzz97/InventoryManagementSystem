"""
Base model class for Inventory Management System
Provides common functionality for all model classes
"""

from typing import Dict, Any, Optional
from abc import ABC, abstractmethod


class BaseModel(ABC):
    """Base model class with common functionality"""
    
    @classmethod
    @abstractmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'BaseModel':
        """Create model instance from dictionary - must be implemented by subclasses"""
        pass
    
    @abstractmethod
    def to_dict(self) -> Dict[str, Any]:
        """Convert model to dictionary - must be implemented by subclasses"""
        pass
    
    def __repr__(self) -> str:
        """Default string representation"""
        return f"<{self.__class__.__name__} {getattr(self, 'id', 'unknown')}>"
    
    def __eq__(self, other: Any) -> bool:
        """Default equality comparison based on ID"""
        if not isinstance(other, self.__class__):
            return False
        return getattr(self, 'id', None) == getattr(other, 'id', None)
    
    def __hash__(self) -> int:
        """Default hash based on ID"""
        return hash(getattr(self, 'id', None))
