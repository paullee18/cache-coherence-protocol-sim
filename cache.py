from dataclasses import dataclass, field
from enum import Enum
from constants import (
    L1_CACHE_HIT_CC,
    MEM_FETCH_CC,
    BUS_UPDATE_WORD_CC,
    EVICT_DIRTY_CACHE_BLOCK_CC,
)
import math
import logging
logging.basicConfig(level=logging.INFO)
LOGGER = logging.getLogger("coherence")

@dataclass
class MemAddressCacheInfo:
    tag: int
    set_index: int
    offset: int


class CacheBlockState(Enum):
    MODIFIED = 1
    EXCLUSIVE = 3
    SHARED = 4
    INVALID = 2

class CacheBlockEvent(Enum):
    PrRd = 1
    PrWr = 2
    BusRd = 3
    BusRdX = 4

@dataclass
class CacheBlock:
    tag: int
    state: CacheBlockState = CacheBlockState.INVALID
    # data and size ?

@dataclass
class DLLNode:
    tag: int
    prev: "DLLNode" = None
    next: "DLLNode" = None

    def remove(self):
        self.prev.next = self.next
        self.next.prev = self.prev
        self.next = None
        self.prev = None

@dataclass
class DLL:
    head: DLLNode
    tail: DLLNode

    def __init__(self):
        self.head = DLLNode("")
        self.tail = DLLNode("")
        self.head.next = self.tail
        self.tail.prev = self.head
    
    def push_front(self, node: DLLNode):
        curr_next = self.head.next 
        self.head.next = node
        node.prev = self.head
        curr_next.prev = node
        node.next = curr_next

    def pop_back(self) -> DLLNode:
        last = self.tail.prev
        last.prev.next = self.tail
        self.tail.prev = last.prev
        self.next = None
        self.prev = None
        return last
    
    def __str__(self):
        s = ""
        itr = self.head.next
        while itr!=self.tail:
            s+=(str(itr.tag)+",")
            itr = itr.next
        return s[:-1]
    
@dataclass
class LRUEvictionHandler:
    tag_to_node: dict[int, DLLNode] = field(default_factory=dict)
    dll: DLL = field(default_factory=DLL)

    def use(self, tag: int):
        if tag in self.tag_to_node:
            node = self.tag_to_node[tag]
            node.remove()
            self.dll.push_front(node)
        else:
            node = DLLNode(tag)
            self.dll.push_front(node)
            self.tag_to_node[tag] = node

    def evict(self) -> str:
        evicted_node = self.dll.pop_back()
        self.tag_to_node.pop(evicted_node.tag)
        return evicted_node.tag
    
@dataclass
class CacheSet:
    associativity: int
    cache_blocks: dict[str, CacheBlock]
    index: int
    eviction_handler: LRUEvictionHandler

    def __init__(self, associativity, index):
        self.associativity = associativity
        self.cache_blocks: dict[str, CacheBlock] = dict()
        self.index = index
        self.eviction_handler = LRUEvictionHandler()

    def invalidate(self, tag):
        if tag not in self.cache_blocks:
            return # no op
        self.cache_blocks[tag].state = CacheBlockState.INVALID

    def is_valid(self, tag):
        if tag not in self.cache_blocks:
            return False
        block = self.cache_blocks[tag]
        return block.state != CacheBlockState.INVALID
    
    def is_in_cache(self, tag) -> bool:
        return tag in self.cache_blocks
    
    def on_cache_hit(self, tag):
        self.eviction_handler.use(tag)

    def on_block_use(self, tag):
        self.eviction_handler.use(tag)

    def get_block_state(self, tag) -> CacheBlockState:
        if tag not in self.cache_blocks:
            return CacheBlockState.INVALID
        return self.cache_blocks[tag].state

    def set_block_state(self, tag, new_state:CacheBlockState):
        if tag not in self.cache_blocks:
            raise Exception(f"Error, trying to set state for block not in cache set - {tag}, {self.cache_blocks}")
        self.cache_blocks[tag].state = new_state

    def is_cache_set_full(self):
        return len(self.cache_blocks) == self.associativity
    
    def evict_block(self):
        evicted_tag = self.eviction_handler.evict()
        evicted_block = self.cache_blocks[evicted_tag]
        self.cache_blocks.pop(evicted_tag)
        return evicted_block
    
    def add_block(self, tag):
        self.cache_blocks[tag] = CacheBlock(tag)

@dataclass
class Cache:
    """
    Write-back, write allocate cache with LRU policy
    """
    id: int
    size: int
    associativity: int
    block_size_bytes: int
    n_block: int # block size = 2^n bytes
    set_count: int
    m_set: int # Number of cache sets = 2^m
    sets: list[CacheSet]
    cache_hits:int = 0
    cache_misses: int = 0
    cycles: int = 0

    def __init__(self, id, size, associativity, block_size_bytes):
        self.id = id
        self.size = size
        self.associativity = associativity
        self.block_size_bytes = block_size_bytes
        self.n_block = int(math.log(self.block_size_bytes, 2))
        self.set_count = self.size // (self.block_size_bytes * self.associativity)
        self.m_set = int(math.log(self.set_count, 2))
        self.sets = [CacheSet(self.associativity, i) for i in range(self.set_count)]
    
    def get_info_from_addr(self, mem_addr: int):
        offset = mem_addr & ((1 << self.n_block) - 1)
        set_index = (mem_addr >> self.n_block) & ((1 << self.m_set) - 1)
        tag = mem_addr >> (self.n_block + self.m_set)
        return MemAddressCacheInfo(
            tag, set_index, offset
        )
    
    def is_in_cache(self, mem_addr: int) -> bool:
        addr_info: MemAddressCacheInfo = self.get_info_from_addr(mem_addr)
        set_ind = addr_info.set_index
        set = self.sets[set_ind]
        tag = addr_info.tag
        return set.is_in_cache(tag)
    
    def invalidate(self, mem_addr: int):
        addr_info: MemAddressCacheInfo = self.get_info_from_addr(mem_addr)
        set_ind = addr_info.set_index
        set = self.sets[set_ind]
        tag = addr_info.tag
        set.invalidate(tag)

    def is_valid(self, mem_addr: int):
        addr_info: MemAddressCacheInfo = self.get_info_from_addr(mem_addr)
        set_ind = addr_info.set_index
        set = self.sets[set_ind]
        tag = addr_info.tag
        return set.is_valid(tag)
    
    def on_cache_hit(self, mem_addr: int):
        addr_info: MemAddressCacheInfo = self.get_info_from_addr(mem_addr)
        set_ind = addr_info.set_index
        set = self.sets[set_ind]
        tag = addr_info.tag
        set.on_cache_hit(tag)

    def on_block_use(self, mem_addr: int):
        addr_info: MemAddressCacheInfo = self.get_info_from_addr(mem_addr)
        set_ind = addr_info.set_index
        set = self.sets[set_ind]
        tag = addr_info.tag
        set.on_block_use(tag)

    def get_block_state(self, mem_addr: int) -> CacheBlockState:
        addr_info: MemAddressCacheInfo = self.get_info_from_addr(mem_addr)
        set_ind = addr_info.set_index
        set = self.sets[set_ind]
        tag = addr_info.tag
        return set.get_block_state(tag)
    
    def set_block_state(self, mem_addr: int, new_state: CacheBlockState):
        addr_info: MemAddressCacheInfo = self.get_info_from_addr(mem_addr)
        set_ind = addr_info.set_index
        set = self.sets[set_ind]
        tag = addr_info.tag
        set.set_block_state(tag, new_state)

    def is_cache_set_full(self, mem_addr):
        addr_info: MemAddressCacheInfo = self.get_info_from_addr(mem_addr)
        set_ind = addr_info.set_index
        set = self.sets[set_ind]
        return set.is_cache_set_full()

    def evict_block(self, mem_addr):
        addr_info: MemAddressCacheInfo = self.get_info_from_addr(mem_addr)
        set_ind = addr_info.set_index
        set = self.sets[set_ind]
        return set.evict_block()

    def add_block(self, mem_addr):
        addr_info: MemAddressCacheInfo = self.get_info_from_addr(mem_addr)
        set_ind = addr_info.set_index
        set = self.sets[set_ind]
        tag = addr_info.tag
        set.add_block(tag)

    def log(self, message:str):
        LOGGER.info(f"Cache {self.id}: " + message)