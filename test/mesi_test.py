import unittest
from core import Core, CoreState
from cache import Cache, CacheBlockState
from mesi import MESIBus, MESI
from bus import Bus, BusRequestType
from coherence_protocol import CoherenceProtocolResult

class TestMESIProtocol(unittest.TestCase):

    def setUp(self):
        self.cache1 = Cache(id=0, size=1024, associativity=2, block_size_bytes=32)
        self.cache2 = Cache(id=1, size=1024, associativity=2, block_size_bytes=32)
        self.cache3 = Cache(id=2, size=1024, associativity=2, block_size_bytes=32)
        self.cache4 = Cache(id=3, size=1024, associativity=2, block_size_bytes=32)
        self.bus = MESIBus([self.cache1, self.cache2, self.cache3, self.cache4], block_size_bytes=32) 
        self.protocol = MESI(self.bus)
        self.core1 = Core(id=0, cache=self.cache1, coherence_protocol=self.protocol, bus=self.bus)
        self.core2 = Core(id=1, cache=self.cache2, coherence_protocol=self.protocol, bus=self.bus)
        self.core2 = Core(id=2, cache=self.cache3, coherence_protocol=self.protocol, bus=self.bus)
        self.core2 = Core(id=3, cache=self.cache4, coherence_protocol=self.protocol, bus=self.bus)
    
    def test_modified_to_shared_on_bus_read(self):
        self.core1.cache.add_block(0x1A)
        self.core1.cache.set_block_state(0x1A, CacheBlockState.EXCLUSIVE)
        self.core2.coherence_protocol.on_read(self.core2, 0x1A)
        self.bus.execute_cycle()
        state_core1 = self.core1.cache.get_block_state(0x1A)
        state_core2 = self.core1.cache.get_block_state(0x1A)
        self.assertEqual(state_core1, CacheBlockState.SHARED)
        self.assertEqual(state_core2, CacheBlockState.SHARED)

    def test_exclusive_to_modified_on_private_write(self):
        self.core1.cache.add_block(0x1B)
        self.core1.cache.set_block_state(0x1B, CacheBlockState.EXCLUSIVE)
        self.core1.coherence_protocol.on_write(self.core1, 0x1B)
        self.bus.execute_cycle()
        state_core1 = self.core1.cache.get_block_state(0x1B)
        self.assertEqual(state_core1, CacheBlockState.MODIFIED)

    def test_shared_to_invalid_on_bus_read_exclusive(self):
        self.core1.cache.add_block(0x1C)
        self.core2.cache.add_block(0x1C)
        self.core1.cache.set_block_state(0x1C, CacheBlockState.SHARED)
        self.core2.cache.set_block_state(0x1C, CacheBlockState.SHARED)
        self.core2.coherence_protocol.on_write(self.core2, 0x1C)
        self.bus.execute_cycle()
        self.core2.state = CoreState.AWAIT_BUS_LOAD
        self.core2.execute_cycle()
        state_core1 = self.core1.cache.get_block_state(0x1C)
        state_core2 = self.core2.cache.get_block_state(0x1C)
        self.assertEqual(state_core1, CacheBlockState.INVALID)
        self.assertEqual(state_core2, CacheBlockState.MODIFIED)

if __name__ == '__main__':
    unittest.main()
