import unittest

from cache import Cache


def create_mem_addr_test(size, associativity, block_size_bytes, addr, expected_offset, expected_set_ind, expected_tag):
    cache = Cache(
        id=0,
        size=size,
        associativity=associativity,
        block_size_bytes=block_size_bytes,
    )
    info = cache.get_info_from_addr(addr)
    assert info.offset==expected_offset, f"Expected offset {expected_offset}, but got {info.offset}"
    assert info.set_index==expected_set_ind, f"Expected set index {expected_set_ind}, but got {info.set_index}"
    assert info.tag==expected_tag, f"Expected tag {expected_tag}, but got {info.tag}"

class TestCache(unittest.TestCase):
    def test_mem_addr_1(self):
        create_mem_addr_test(64, 2, 8, 16, 0, 2, 0)

    def test_mem_addr_2(self):
        create_mem_addr_test(32, 2, 8, 36, 4, 0, 2)

    def test_mem_addr_3(self):
        create_mem_addr_test(128, 4, 16, 0x1F4, 4, 1, 15)

    def test_mem_addr_4(self):
        create_mem_addr_test(256, 2, 32, 0xFFFFFFFF, 31, 3, 33554431)

    def test_mem_addr_5(self):
        create_mem_addr_test(64,2,16,16,0,1,0)

if __name__ == '__main__':
    unittest.main()