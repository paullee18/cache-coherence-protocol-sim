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
    block_size: int
    word_size: int

    def _parse_line(self, line) -> Instruction:
        line_list = line.split()
        return Instruction(InstructionType(line_list[0]), int(line_list[1], 16))

    def simulate(self):
        with open(self.input_file) as f:
            for line in f:
                instr: Instruction = self._parse_line(line)
                LOGGER.info(f"Parsed instruction: {instr}")
