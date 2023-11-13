import time
from pathlib import Path

import pprofile  # type: ignore[import-untyped]

from dipdup.indexes.evm_subsquid_events.matcher import decode_event_data
from dipdup.package import EventAbiExtra

data = '0x000000000000000000000000c36442b4a4522e871399cd717abdd847ab11fe88000000000000000000000000000000000000000000000000000e15b0c3e67bc30000000000000000000000000000000000000000000000000dc0bcc485bdc70800000000000000000000000000000000000000000000000000000000000f1eb7'
topics = (
    '0x7a53080ba414158be7ec69b987b5fb7d07dee101fe85488f0853ae16239d0bde',
    '0x000000000000000000000000c36442b4a4522e871399cd717abdd847ab11fe88',
    '0xfffffffffffffffffffffffffffffffffffffffffffffffffffffffffffbc896',
    '0xfffffffffffffffffffffffffffffffffffffffffffffffffffffffffffbc8a0',
)
abi = EventAbiExtra(
    name='Mint',
    topic0='0x7a53080ba414158be7ec69b987b5fb7d07dee101fe85488f0853ae16239d0bde',
    inputs=(
        ('address', False),
        ('address', True),
        ('int24', True),
        ('int24', True),
        ('uint128', False),
        ('uint256', False),
        ('uint256', False),
    ),
)

prof = pprofile.Profile()
with prof():
    decode_event_data(data, topics, abi)

prof.dump_stats(Path(__file__).parent / f'cachegrind.out.{Path(__file__).stem}.{round(time.time())}')
