from dataclasses import dataclass
from enum import Enum

class InstructionType(Enum):
    LOAD = "0"
    STORE = "1"
    OTHER = "2"

@dataclass
class Instruction:
    type: InstructionType
    value: int