from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from collections import deque
#from core import Core
from cache import CacheBlockState
from enum import Enum

class BusRequestType(Enum):
    BusRd = 1,
    BusRdX = 2,
    Flush = 3,

@dataclass
class BusRequest:
    req_type: BusRequestType
    core: "Core"
    address: int
    curr_block_state: CacheBlockState

    def __str__(self):
        return f"BusRequest - Type: {self.req_type}, core: {self.core.id}, address: {self.address}"

@dataclass
class BusResponse:
    req: BusRequest
    is_in_other_cache: bool = False # Only used for BusRd

class BusState(Enum):
    READY = 1,
    BUSY = 2,

@dataclass
class Bus:
    # requests: deque[BusRequest] = field(default_factory=deque)
    # core_to_resp: dict[int, BusResponse] = field(default_factory=dict)
    # state: BusState = BusState.READY

    def execute_cycle(self):
        pass

    def queue_request(self, req: BusRequest):
        pass
    
    def get_traffic(self):
        pass

    def get_invalidations_or_updates(self):
        pass