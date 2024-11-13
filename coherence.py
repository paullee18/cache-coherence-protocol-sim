"""
Your program should take the input file name and cache configurations as arguments.
The command line should be
coherence “protocol” “input_file” “cache_size” “associativity” “block_size”
where coherence is the executable file name and input parameters are
• “protocol” is either MESI or Dragon
• “input_file” is the input benchmark name (e.g., bodytrack)
• “cache_size”: cache size in bytes
• “associativity”: associativity of the cache
• “block_size”: block size in bytes
For example, to read bodytrack trace files and execute MESI cache coherence protocol
with each core containing 1K direct-mapped cache and 16 byte block size, the command
will be
coherence MESI bodytrack 1024 1 16
Assume default parameters as 32-bit word size, 32-byte block size, and 4KB 2-way
set associative cache per processor.
"""
import logging
import sys
from simulation import Simulation
from coherence_protocol import CoherenceProtocol
from mesi import MESI
from constants import WORD_SIZE_BITS

logging.basicConfig(level=logging.INFO)
LOGGER = logging.getLogger("coherence")

DEFAULT_BLOCK_SIZE_BYTES = 32
DEFAULT_CACHE_SIZE_BYTES = 4096
DEFAULT_ASSOCIATIVITY = 2

def main():
    protocol = sys.argv[1]
    input_file = sys.argv[2]
    
    if (len(sys.argv)<4):
        cache_size = DEFAULT_CACHE_SIZE_BYTES
    else:
        cache_size = int(sys.argv[3])
    
    if len(sys.argv)<5:
        associativity = DEFAULT_ASSOCIATIVITY
    else:
        associativity = int(sys.argv[4])

    if len(sys.argv)<6:
        block_size = DEFAULT_BLOCK_SIZE_BYTES
    else:
        block_size = int(sys.argv[5])

    LOGGER.info(f"Command arguments: Protocol - {protocol}, input file - {input_file}, cache size - {cache_size}, associativity - {associativity}, block size - {block_size}")
    word_size = WORD_SIZE_BITS

    simulation: Simulation = Simulation(protocol, input_file, cache_size, associativity, block_size, word_size)
    simulation.simulate()

if __name__ == "__main__":
    main()