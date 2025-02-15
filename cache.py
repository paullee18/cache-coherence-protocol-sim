from dataclasses import dataclass, field
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

@dataclass
class CacheBlock:
    tag: int
    dirty: bool = False
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

    def read(self, tag, cache: "Cache"):
        if tag not in self.cache_blocks:
            cache.log(f"Cache miss for tag: {tag}, set id = {self.index}")
            cache.cache_misses+=1
            cache.cycles+=MEM_FETCH_CC
            # have to load it in, check if set is at full capacity
            if len(self.cache_blocks) == self.associativity:
                cache.log(f"Cache set full with size {len(self.cache_blocks)} and associativity {self.associativity}. Evicting.")
                # have to choose one to evict
                evicted_tag = self.eviction_handler.evict()
                # handle writing of evicted block if needed
                evicted_block = self.cache_blocks[evicted_tag]
                cache.log(f"Evicting block: {evicted_block}")
                if evicted_block.dirty:
                    # write
                    cache.log(f"Writing to memory for dirty evicted block")
                    cache.cycles+=EVICT_DIRTY_CACHE_BLOCK_CC

                self.cache_blocks.pop(evicted_tag)

            # bring in new block
            self.cache_blocks[tag] = CacheBlock(tag)
            # add cc for final read from cache
            cache.cycles+=L1_CACHE_HIT_CC
        else:
            cache.log(f"Cache hit for tag: {tag}, set id = {self.index}")
            cache.cache_hits+=1
            cache.cycles+=L1_CACHE_HIT_CC
        
        self.eviction_handler.use(tag)
        # perform read

    def write(self, tag, cache: "Cache"):
        if tag not in self.cache_blocks:
            cache.log(f"Cache miss for tag: {tag}, set id = {self.index}")
            cache.cache_misses+=1
            cache.cycles+=MEM_FETCH_CC
            # have to load it in, check if set is at full capacity
            if len(self.cache_blocks) == self.associativity:
                # have to choose one to evict
                cache.log(f"Cache set full with size {len(self.cache_blocks)} and associativity {self.associativity}. Evicting.")
                evicted_tag = self.eviction_handler.evict()
                # handle writing of evicted block if needed
                evicted_block = self.cache_blocks[evicted_tag]
                cache.log(f"Evicting block: {evicted_block}")
                if evicted_block.dirty:
                    # write
                    cache.log(f"Writing to memory for dirty evicted block")
                    cache.cycles+=EVICT_DIRTY_CACHE_BLOCK_CC

                self.cache_blocks.pop(evicted_tag)
            # bring in new block
            self.cache_blocks[tag] = CacheBlock(tag)
            # add cc for final read from cache
            cache.cycles+=L1_CACHE_HIT_CC
        else:
            cache.log(f"Cache hit for tag: {tag}, set id = {self.index}")
            cache.cache_hits+=1
            cache.cycles+=L1_CACHE_HIT_CC
        
        self.eviction_handler.use(tag)
        # perform write
        self.cache_blocks[tag].dirty = True

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
    
    def read(self, mem_addr: int):
        self.log(f"Processing read from address {mem_addr}")
        addr_info: MemAddressCacheInfo = self.get_info_from_addr(mem_addr)
        set_ind = addr_info.set_index
        set = self.sets[set_ind]
        tag = addr_info.tag
        return set.read(tag, self)

    def write(self, mem_addr: int):
        self.log(f"Processing write from address {mem_addr}")
        addr_info: MemAddressCacheInfo = self.get_info_from_addr(mem_addr)
        set_ind = addr_info.set_index
        set = self.sets[set_ind]
        tag = addr_info.tag
        return set.write(tag, self)

    def log(self, message:str):
        LOGGER.info(f"Cache {self.id}: " + message)