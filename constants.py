"""
Clock cycle constants.
L1 cache hit is 1 cycle. Fetching a block from memory to cache takes additional 100
cycles. Sending a word from one cache to another (e.g., BusUpdate) takes only 2 cycles.
However, sending a cache block with N words (each word is 4 bytes) to another cache
takes 2N cycle. Assume that evicting a dirty cache block to memory when it gets replaced
is 100 cycles
"""
L1_CACHE_HIT_CC = 1
MEM_FETCH_CC = 100
BUS_UPDATE_WORD_CC = 2
EVICT_DIRTY_CACHE_BLOCK_CC = 100

WORD_SIZE_BITS = 32