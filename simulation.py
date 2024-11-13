from dataclasses import dataclass, field
from coherence_protocol import CoherenceProtocol
from mesi import MESI, MESIBus
from bus import Bus
from core import Core, CoreState
from cache import Cache
from instruction import (
    Instruction,
    InstructionType
)
import logging

LOGGER = logging.getLogger("coherence")

@dataclass
class Simulation:
    protocol: CoherenceProtocol = field(init=False)
    protocol_str: str
    input_file: str
    cache_size: int
    associativity: int
    block_size_bytes: int
    word_size_bits: int
    cores: list[Core] = field(default_factory=list)
    clock_cycles = 0
    bus: Bus = field(init=False)

    def __post_init__(self):
        caches = [Cache(i, self.cache_size, self.associativity, self.block_size_bytes) for i in range(4)]
        self.bus = MESIBus(caches, self.block_size_bytes) if self.protocol_str == "MESI" else MESIBus()
        self.protocol = MESI(self.bus) if self.protocol_str == "MESI" else MESI(self.bus)
        self.cores = [Core(i, caches[i], self.protocol, self.bus) for i in range(4)]

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
        with open(self.input_file + "_0.data") as f0, \
             open(self.input_file + "_1.data") as f1, \
             open(self.input_file + "_2.data") as f2,  \
             open(self.input_file + "_3.data") as f3:
            
            files = [f0, f1, f2, f3]
            cores_not_done = set([i for i in range(4)])

            while True:
                LOGGER.info(f"===========EXECUTING CYCLE {self.clock_cycles}===========")
                for i, core in enumerate(self.cores):
                    if core.state == CoreState.READY:
                        next_line = files[i].readline()
                        if not next_line:
                            core.state = CoreState.DONE
                        else:
                            core.fetch_instr(self._parse_line(next_line))

                    if core.state != CoreState.DONE:
                        core.execute_cycle()
                    elif i in cores_not_done:
                        cores_not_done.remove(i)
                
                self.bus.execute_cycle()

                # check if all done
                if not cores_not_done:
                    LOGGER.info("All instructions executed.")             
                    self.print_final_outputs()
                    return
                
                self.clock_cycles+=1

    def print_final_outputs(self):
        print(f"====Printing final=====")
        print(f"Overall Execution Cycle: {self.clock_cycles}")
        print(f"Printing results for each core")
        for i in range(4):
            print("-------------")
            self.cores[i].print_final_outputs()
        print("----------")
        print(f"Printing from protocol")
        self.protocol.print_final_outputs()
        print("----------")
        print(f"Printing from bus")
        self.bus.print_final_outputs()