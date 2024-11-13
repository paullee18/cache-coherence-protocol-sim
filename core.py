from bus import Bus, BusRequestType
from cache import Cache, CacheBlockState
from dataclasses import dataclass
from coherence_protocol import CoherenceProtocol, CoherenceProtocolResult
from constants import (
    L1_CACHE_HIT_CC,
    MEM_FETCH_CC,
    BUS_UPDATE_WORD_CC,
    EVICT_DIRTY_CACHE_BLOCK_CC,
)
from enum import Enum
from instruction import (
    Instruction,
    InstructionType
)
import logging

LOGGER = logging.getLogger("coherence")

class CoreState(Enum):
    READY = 1,
    DONE = 2,
    EXECUTE_LOAD = 3,
    EXECUTE_STORE = 4,
    AWAIT_BUS_LOAD = 5,
    AWAIT_BUS_STORE = 6,
    EXECUTE_NON_MEM = 7,

@dataclass
class Core:
    id: int
    cache: Cache
    coherence_protocol: CoherenceProtocol
    bus: Bus
    execution_cycles: int = 0
    compute_cycles: int = 0
    load_instrs: int = 0
    store_instrs: int = 0
    idle_cycles: int = 0
    cache_hits:int = 0
    cache_misses: int = 0
    state: CoreState = CoreState.READY
    curr_instr: Instruction = None
    remaining_cycles: int = 0 # Stores the number of cycles remaining before current core state is completed

    def fetch_instr(self, instr: Instruction):
        self.log(f"Fetching instruction {instr}")
        self.curr_instr = instr

    def update_cache_for_addr(self, address):
        # handle cache updating and eviction
        # if already in cache, just update cache
        if not self.cache.is_in_cache(address):
            if self.cache.is_cache_set_full(address):
                # have to evict one 
                evicted_block = self.cache.evict_block(address)
                if evicted_block.state == CacheBlockState.MODIFIED:
                    # write back
                    self.log(f"Writing back to memory for dirty evicted block {evicted_block}")
                    self.remaining_cycles+=EVICT_DIRTY_CACHE_BLOCK_CC
            # bring in new block
            self.cache.add_block(address)
            
        self.cache.on_block_use(address)

    def execute_cycle(self):
        self.log("Executing cycle")
        match self.state:
            case CoreState.READY:
                # ready to start executing new instruction
                LOGGER.info(f"Core {self.id}: Executing new instruction: {self.curr_instr}")

                if self.curr_instr.type == InstructionType.LOAD:
                    LOGGER.info(f"Core {self.id}: Attempting to read address: {self.curr_instr.value} from cache")
                    self.load_instrs+=1
                    self.idle_cycles+=1
                    res: CoherenceProtocolResult = self.coherence_protocol.on_read(self, self.curr_instr.value)
                    if res == CoherenceProtocolResult.CACHE_HIT:
                        # completed, 
                        self.cache.on_cache_hit(self.curr_instr.value)
                        self.cache_hits+=1
                    else:
                        self.state = CoreState.AWAIT_BUS_LOAD
                        self.cache_misses+=1
                elif self.curr_instr.type == InstructionType.STORE:
                    LOGGER.info(f"Core {self.id}: Attempting to write to address: {self.curr_instr.value} from cache")
                    self.store_instrs+=1
                    self.idle_cycles+=1
                    res: CoherenceProtocolResult = self.coherence_protocol.on_write(self, self.curr_instr.value)
                    if res == CoherenceProtocolResult.CACHE_HIT:
                        self.cache.on_cache_hit(self.curr_instr.value)
                        self.cache_hits+=1
                        pass
                    else:
                        self.state = CoreState.AWAIT_BUS_STORE
                        self.cache_misses+=1
                else:
                    self.state = CoreState.EXECUTE_NON_MEM
                    self.compute_cycles+=1
                    self.remaining_cycles = self.curr_instr.value - 1
                    LOGGER.info(f"Core {self.id}: Executing non memory instruction, {self.remaining_cycles} compute cycles remaining")
            case CoreState.EXECUTE_NON_MEM:
                self.remaining_cycles-=1
                self.compute_cycles+=1
                LOGGER.info(f"Core {self.id}: Executing non memory instruction, {self.remaining_cycles} compute cycles remaining")
                if (self.remaining_cycles == 0):
                    self.state = CoreState.READY
            case CoreState.EXECUTE_LOAD:
                self.log(f"Current state: executing load, {self.remaining_cycles} remaining")
                self.idle_cycles+=1
                self.remaining_cycles-=1
                if (self.remaining_cycles == 0):
                    self.state = CoreState.READY
            case CoreState.EXECUTE_STORE:
                self.log(f"Current state: executing store, {self.remaining_cycles} remaining")
                self.idle_cycles+=1
                self.remaining_cycles-=1
                if (self.remaining_cycles == 0):
                    self.state = CoreState.READY
            case CoreState.AWAIT_BUS_LOAD:
                self.log(f"Current state: awaiting bus load")
                if self.id in self.bus.core_to_resp:
                    resp = self.bus.core_to_resp[self.id]
                    self.log(f"Bus load completed")
                    self.bus.core_to_resp.pop(self.id, None)
                    if resp.req.req_type == BusRequestType.BusRd or resp.req.req_type == BusRequestType.BusRdX:
                        # handle cache updating and eviction
                        self.update_cache_for_addr(resp.req.address)
                    # coherence protocol handles changing of states if necessary
                    self.coherence_protocol.on_bus_resp(self, resp)
                    if self.remaining_cycles > 0:
                        self.state = CoreState.EXECUTE_LOAD
                    else:
                        self.state = CoreState.READY
                self.idle_cycles+=1
            case CoreState.AWAIT_BUS_STORE:
                self.log(f"Current state: awaiting bus store")
                if self.id in self.bus.core_to_resp:
                    resp = self.bus.core_to_resp[self.id]
                    self.log(f"Bus store completed")
                    self.bus.core_to_resp.pop(self.id, None)
                    if resp.req.req_type == BusRequestType.BusRd or resp.req.req_type == BusRequestType.BusRdX:
                        # handle cache updating and eviction
                        self.update_cache_for_addr(resp.req.address)
                    # coherence protocol handles changing of states if necessary
                    self.coherence_protocol.on_bus_resp(self, resp)
                    if self.remaining_cycles > 0:
                        self.state = CoreState.EXECUTE_STORE
                    else:
                        self.state = CoreState.READY
                
                self.idle_cycles+=1

    def print_final_outputs(self):
        self.print(f"{self.idle_cycles+self.compute_cycles} Execution cycles")
        self.print(f"{self.compute_cycles} Compute cycles")
        self.print(f"{self.load_instrs} load instructions")
        self.print(f"{self.store_instrs} store instructions")
        self.print(f"{self.idle_cycles} idle cycles")
        self.print(f"{self.cache_hits} cache hits")
        self.print(f"{self.cache_misses} cache misses")
    
    def log(self, msg):
        LOGGER.info(f"Core {self.id}: {msg}")
        
    def print(self, str):
        print(f"Core: {self.id}: " + str)