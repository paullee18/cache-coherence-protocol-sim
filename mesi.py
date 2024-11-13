from coherence_protocol import CoherenceProtocol, CoherenceProtocolResult
from dataclasses import dataclass, field
from bus import Bus, BusRequest, BusRequestType, BusState, BusResponse
from constants import MEM_FETCH_CC, BUS_UPDATE_WORD_CC, WORD_SIZE_BITS
from core import Core, CoreState
from cache import Cache, CacheSet, CacheBlock, MemAddressCacheInfo, CacheBlockState
from collections import deque
import logging
logging.basicConfig(level=logging.INFO)
LOGGER = logging.getLogger("coherence")

@dataclass
class MESI(CoherenceProtocol):
    bus: Bus
    private_accesses: int = 0
    shared_accesses: int = 0

    def update_access_type(self, core: Core, address: int):
        state = core.cache.get_block_state(address)
        if state == CacheBlockState.EXCLUSIVE or state == CacheBlockState.MODIFIED:
            self.private_accesses += 1
        if state == CacheBlockState.SHARED:
            self.shared_accesses += 1

    def on_read(self, core: Core, address: int) -> CoherenceProtocolResult:
        self.update_access_type(core, address)

        # If cache hit, can complete in this cycle, else, issue a Bus request
        if core.cache.is_valid(address):
            # cache hit
            return CoherenceProtocolResult.CACHE_HIT
        else:
            request: BusRequest = BusRequest(
                req_type=BusRequestType.BusRd,
                core=core,
                address=address,
                curr_block_state=CacheBlockState.INVALID
            )
            self.bus.queue_request(request)
            return CoherenceProtocolResult.CACHE_MISS

    def on_write(self, core: Core, address: int) -> CoherenceProtocolResult:
        self.update_access_type(core, address)

        # If cache hit, can complete in this cycle, else, issue a Bus request
        state = core.cache.get_block_state(address)
        match state:
            case CacheBlockState.MODIFIED:
                # cache hit and nothing needs to be done
                return CoherenceProtocolResult.CACHE_HIT
            case CacheBlockState.EXCLUSIVE:
                # cache hit but need to update to M
                core.cache.set_block_state(address, CacheBlockState.MODIFIED)
                return CoherenceProtocolResult.CACHE_HIT
            case _:
                # Shared or Invalid
                request: BusRequest = BusRequest(
                    req_type=BusRequestType.BusRdX,
                    core=core,
                    address=address,
                    curr_block_state=state,
                )
                self.bus.queue_request(request)
                return CoherenceProtocolResult.CACHE_MISS
            
    def on_bus_resp(self, core: "Core", resp):
        match resp.req.req_type:
            case BusRequestType.BusRd:
                if resp.is_in_other_cache:
                    core.cache.set_block_state(resp.req.address, CacheBlockState.SHARED)
                else:
                    core.cache.set_block_state(resp.req.address, CacheBlockState.EXCLUSIVE)
            case BusRequestType.BusRdX:
                core.cache.set_block_state(resp.req.address, CacheBlockState.MODIFIED)

    def print_final_outputs(self):
        print(f"MESI protocol: {self.private_accesses} private accesses, {self.shared_accesses} shared accesses")

@dataclass
class MESIBus(Bus):
    caches: list[Cache]
    block_size_bytes: int
    requests: deque[BusRequest] = field(default_factory=deque)
    core_to_resp: dict[int, BusResponse] = field(default_factory=dict)
    state: BusState = BusState.READY
    curr_req: BusRequest = None
    clock_cycles_rem: int = 0 # for the curr request
    traffic: int = 0# bytes
    invalidations_or_updates: int = 0

    def execute_cycle(self):
        self.log("Executing cycle")
        if self.state == BusState.READY:
            if self.requests:
                self.curr_req = self.requests.popleft()
                self.state = BusState.BUSY

                # do invalidations and add clock cycles ?
                self.process_request(self.curr_req)

        match self.state:
            case BusState.READY:
                pass
            case _:
                self.log(f"Executing request {self.curr_req} with {self.clock_cycles_rem} cc remaining")
                self.clock_cycles_rem -= 1
                if self.clock_cycles_rem<0:
                    self.clock_cycles_rem = 0
                    # Generate response
                    resp = BusResponse(self.curr_req)
                    match self.curr_req.req_type:
                        case BusRequestType.BusRd:
                            # check if any other cache has copy
                            resp.is_in_other_cache = self.is_addr_in_other_cache(self.curr_req.core.id, self.curr_req.address)
                            pass
                        case BusRequestType.BusRdX:
                            pass
                        case BusRequestType.Flush:
                            pass
                    self.state = BusState.READY
                    self.core_to_resp[self.curr_req.core.id] = resp
                    self.curr_req = None
    
    def queue_request(self, request: BusRequest):
        self.requests.append(request)
        # clear any old response to this core
        self.core_to_resp.pop(request.core.id, None)

    def process_flush(self):
        self.traffic += self.block_size_bytes
        self.clock_cycles_rem += BUS_UPDATE_WORD_CC * (self.block_size_bytes * 8 // WORD_SIZE_BITS)

    def process_transfer(self):
        self.traffic += self.block_size_bytes
        self.clock_cycles_rem += BUS_UPDATE_WORD_CC * (self.block_size_bytes * 8 // WORD_SIZE_BITS)

    def process_request(self, request: BusRequest):
        # do invalidations and add clock cycles ?
        match request.req_type:
            case BusRequestType.BusRd:
                is_transferred = False
                for other_core_id in range(4):
                    if request.core.id == other_core_id:
                        continue
                    other_state = self.caches[other_core_id].get_block_state(request.address)
                    if other_state == CacheBlockState.MODIFIED or other_state == CacheBlockState.EXCLUSIVE :
                        # Cache-to-cache transfer and change state to shared
                        is_transferred = True
                        self.process_transfer()
                        self.process_flush()
                        self.caches[other_core_id].set_block_state(request.address, CacheBlockState.SHARED) # Optimisation, set to invalid instead?
                    if not is_transferred and other_state == CacheBlockState.SHARED:
                        is_transferred = True
                        self.process_transfer()
                if not is_transferred:
                    # fetch from memory
                    self.clock_cycles_rem += MEM_FETCH_CC
            case BusRequestType.BusRdX:
                is_transferred = False
                for other_core_id in range(4):
                    if request.core.id == other_core_id:
                        continue
                    other_state = self.caches[other_core_id].get_block_state(request.address)
                    if other_state == CacheBlockState.MODIFIED or other_state == CacheBlockState.EXCLUSIVE:
                        # Cache-to-cache transfer
                        is_transferred = True
                        self.process_transfer()
                        self.process_flush()
                # Invalidate
                self.invalidate_caches(request.core.id, request.address)
                if not is_transferred and request.curr_block_state==CacheBlockState.INVALID:
                    self.clock_cycles_rem += MEM_FETCH_CC
            case BusRequestType.Flush:
                pass
    
    def invalidate_caches(self, from_id, mem_addr):
        for i in range(4):
            if i == from_id:
                continue
            if self.caches[i].is_valid(mem_addr):
                self.invalidations_or_updates+=1
            self.caches[i].invalidate(mem_addr)

    def is_addr_in_other_cache(self, from_id, mem_addr):
        res = False
        for i in range(4):
            if i == from_id:
                continue
            if self.caches[i].is_valid(mem_addr):
                res = True
        return res

    def log(self, msg):
        LOGGER.info(f"Mesi Bus: {msg}")

    def print_final_outputs(self):
        print(f"Bus: {self.invalidations_or_updates} invalidations")
        print(f"Bus: {self.traffic} bytes of traffic")