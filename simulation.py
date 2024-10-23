from dataclasses import dataclass
from enum import Enum
import logging

LOGGER = logging.getLogger("coherence")

class InstructionType(Enum):
    LOAD = "0"
    STORE = "1"
    OTHER = "2"

@dataclass
class Instruction:
    type: InstructionType
    value: int

@dataclass
class Simulation:
    input_file: str
    cache_size: int
    associativity: int
    block_size_bytes: int
    word_size_bits: int

    def _parse_line(self, line) -> Instruction:
        line_list = line.split()
        return Instruction(InstructionType(line_list[0]), int(line_list[1], 16))

    def simulate(self):
        """
        1. Overall Execution Cycle (different core will complete at different cycles;
        report the maximum value across all cores) for the entire trace as well as
        execution cycle per core
        2. Number of compute cycles per core. These are the total number of cycles
        spent processing other instructions between load/store instructions
        3. Number of load/store instructions per core
        4. Number of idle cycles (these are cycles where the core is waiting for the
        request to the cache to be completed) per core
        5. Data cache hit and miss counts for each core
        6. Amount of Data traffic in bytes on the bus (this is due to bus read, bus read
        exclusive, bus writeback, and bus update transactions). Only include the
        traffic for data and not for address. Thus invalidation requests do not
        contribute to the data traffic.
        7. Number of invalidations or updates on the bus
        8. Distribution of accesses to private data versus shared data (for example,
        access to modified state is private, while access to shared state is shared data)
        """
        with open(self.input_file) as f:
            for line in f:
                instr: Instruction = self._parse_line(line)
                LOGGER.info(f"Parsed instruction: {instr}")
                
