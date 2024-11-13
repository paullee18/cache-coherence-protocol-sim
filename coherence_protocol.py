from abc import ABC, abstractmethod
from enum import Enum

class CoherenceProtocolResult(Enum):
    CACHE_HIT = 1,
    CACHE_MISS = 2,

class CoherenceProtocol(ABC):
    @abstractmethod
    def on_read(self, core: "Core", address: int) -> CoherenceProtocolResult:
        pass

    @abstractmethod
    def on_write(self, core: "Core", address: int) -> CoherenceProtocolResult:
        pass

    @abstractmethod
    def on_bus_resp(self, core: "Core", resp):
        pass