from abc import ABC, abstractmethod
from typing import Dict, Any, Optional

class BaseRepository(ABC):
    @abstractmethod
    def create(self, key: str, data: Dict[str, Any]) -> Dict[str, Any]:
        pass

    @abstractmethod
    def get(self, key: str) -> Optional[Dict[str, Any]]:
        pass

    @abstractmethod
    def update(self, key: str, data: Dict[str, Any]) -> Dict[str, Any]:
        pass