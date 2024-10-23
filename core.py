from cache import Cache
from dataclasses import dataclass
from instruction import (
    Instruction,
    InstructionType
)
import logging

LOGGER = logging.getLogger("coherence")

@dataclass
class Core:
    id: int
    cache: Cache
    #execution_cycles: int = 0
    compute_cycles: int = 0
    load_store_instrs: int = 0
    #idle_cycles: int = 0

    def execute_instr(self, instr: Instruction):
        LOGGER.info(f"Core {self.id}: Executing instruction: {instr}")

        if instr.type == InstructionType.LOAD:
            LOGGER.info(f"Core {self.id}: Attempting to read address: {instr.value} from cache")
            self.load_store_instrs+=1
            self.cache.read(instr.value)
        elif instr.type == InstructionType.STORE:
            LOGGER.info(f"Core {self.id}: Attempting to write to address: {instr.value} from cache")
            self.load_store_instrs+=1
            self.cache.write(instr.value)
        else:
            LOGGER.info(f"Core {self.id}: {instr.value} compute cycles")
            self.compute_cycles += instr.value
    
    def print_final_outputs(self):
        idle_cycles = self.cache.cycles
        self.print(f"{idle_cycles+self.compute_cycles} Execution cycles")
        self.print(f"{self.compute_cycles} Compute cycles")
        self.print(f"{self.load_store_instrs} load/store instructions")
        self.print(f"{idle_cycles} idle cycles")
        self.print(f"{self.cache.cache_hits} cache hits")
        self.print(f"{self.cache.cache_misses} cache misses")

    def print(self, str):
        print(f"Core: {self.id}: " + str)