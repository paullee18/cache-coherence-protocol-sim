import unittest
from cache import Cache, CacheSet  # Replace 'your_module' with the actual module name where your classes are defined
from constants import MEM_FETCH_CC, L1_CACHE_HIT_CC, EVICT_DIRTY_CACHE_BLOCK_CC


class TestCache(unittest.TestCase):
    
    def setUp(self):
        # Setup method to initialize common objects used across multiple tests
        self.cache = Cache(id=0, size=64, associativity=2, block_size_bytes=16)

    def test_cache_miss_and_load(self):
        # Test Case 1: Cache Miss and Load
        # Read from two addresses that map to the same set but should not evict each other
        mem_addr1 = 0x00000000
        mem_addr2 = 0x00000010  # Maps to the same set as mem_addr1

        # Initial read should be a miss
        self.cache.read(mem_addr1)
        self.assertEqual(self.cache.cache_misses, 1)
        self.assertEqual(self.cache.cycles, MEM_FETCH_CC)

        # Second read should be a miss but no eviction
        self.cache.read(mem_addr2)
        self.assertEqual(self.cache.cache_misses, 2)
        self.assertEqual(self.cache.cycles, 2 * MEM_FETCH_CC)  # Two misses

    def test_cache_hit(self):
        # Test Case 2: Cache Hit after initial miss
        mem_addr = 0x00000000

        # Initial read should be a miss
        self.cache.read(mem_addr)
        self.assertEqual(self.cache.cache_misses, 1)
        self.assertEqual(self.cache.cycles, MEM_FETCH_CC)

        # Second read should be a hit
        self.cache.read(mem_addr)
        self.assertEqual(self.cache.cache_hits, 1)
        self.assertEqual(self.cache.cycles, MEM_FETCH_CC + L1_CACHE_HIT_CC)  # 1 miss + 1 hit

    def test_evict_non_dirty_block(self):
        # Test Case 3: Eviction of non-dirty block
        mem_addr1 = 0x00000000
        mem_addr2 = 0x00000010
        mem_addr3 = 0x00000020  # Should trigger eviction of mem_addr1

        # Load two blocks, no eviction yet
        self.cache.read(mem_addr1)
        self.cache.read(mem_addr2)

        # Now read a third block that will trigger eviction
        self.cache.read(mem_addr3)
        self.assertEqual(self.cache.cache_misses, 3)
        self.assertEqual(self.cache.cycles, 3 * MEM_FETCH_CC)

    def test_full_cache_eviction(self):
        # Test Case 5: Full Cache Eviction
        self.cache = Cache(id=0, size=128, associativity=4, block_size_bytes=16)

        # Sequentially load blocks into the cache until eviction occurs
        mem_addrs = [0x00000000, 0x00000010, 0x00000020, 0x00000030, 0x00000040]

        # Fill the cache set first
        for i, addr in enumerate(mem_addrs[:-1]):
            self.cache.read(addr)
            self.assertEqual(self.cache.cache_misses, i + 1)

        # Now trigger an eviction with the next block
        self.cache.read(mem_addrs[-1])
        self.assertEqual(self.cache.cache_misses, len(mem_addrs))
        self.assertEqual(self.cache.cycles, len(mem_addrs) * MEM_FETCH_CC)

    def test_dirty_block_write_back(self):
        # Test Case 6: Write-back of dirty block on eviction
        mem_addr1 = 0x00000000
        mem_addr2 = 0x00000010
        mem_addr3 = 0x00000020  # Evicts dirty block mem_addr1
        mem_addr4 = 0x00000040

        # Write to mem_addr1 and make it dirty
        self.cache.write(mem_addr1)
        self.cache.write(mem_addr2)

        # Evict mem_addr1 by loading mem_addr3
        self.cache.write(mem_addr3)
        self.cache.write(mem_addr4)
        self.cache.write(mem_addr3)
        self.cache.write(mem_addr4)
        self.assertEqual(self.cache.cycles, 4 * MEM_FETCH_CC + EVICT_DIRTY_CACHE_BLOCK_CC + 2)

    def test_write_to_evicted_dirty_block(self):
        # Test Case 7: Write to Evicted Dirty Block
        mem_addr1 = 0x00000000
        mem_addr2 = 0x00000010
        mem_addr3 = 0x00000020  # Evicts mem_addr1
        mem_addr4 = 0x00000040  # Evicts mem_addr1

        # Write to mem_addr1, making it dirty
        self.cache.write(mem_addr1)
        self.cache.write(mem_addr2)

        # Evict mem_addr1
        self.cache.write(mem_addr3)
        self.cache.write(mem_addr4)
        self.assertEqual(self.cache.cycles, 4 * MEM_FETCH_CC + EVICT_DIRTY_CACHE_BLOCK_CC)

        # Now write to mem_addr1 again (should miss and reload)
        self.cache.write(mem_addr1)
        self.assertEqual(self.cache.cycles, 5 * MEM_FETCH_CC + 2 * EVICT_DIRTY_CACHE_BLOCK_CC)

        self.cache.write(mem_addr3)
        self.assertEqual(self.cache.cycles, 6 * MEM_FETCH_CC + 3 * EVICT_DIRTY_CACHE_BLOCK_CC)

if __name__ == "__main__":
    unittest.main()
