from dataclasses import dataclass
from pathlib import Path

import orjson

from dipdup.runtimes import SubstrateSpecVersion
from dipdup.sys import set_up_logging


@dataclass
class Substrate:
    subscan: str
    spec_version: int
    event_qualname: str
    event_id: str


SUBSTATE_DATA = (
    Substrate(
        subscan='https://hydration.api.subscan.io/api',
        spec_version=227,
        event_qualname='AssetRegistry.Registered',
        event_id='4936483-5',
    ),
)
SUBSTRATE_DATA_PATH = Path(__file__).parent.joinpath('../tests/data/substrate/')


async def fetch_test_data(item: Substrate) -> None:
    """Fetch test data for Substrate tests.

    1. Fetch metadata from Subscan. Extract event item by qualname and put to `event_abi_{spec_version}_{qualname}.json`.
    2. Fetch block from Subscan. Filter events by qualname and put to `events_{spec_version}_{qualname}.json`.
    """
    from dipdup.config.substrate_subscan import SubstrateSubscanDatasourceConfig
    from dipdup.datasources.substrate_subscan import SubstrateSubscanDatasource

    set_up_logging()

    config = SubstrateSubscanDatasourceConfig(
        url=item.subscan,
    )
    config._name = 'test_substrate_subscan'
    subscan = SubstrateSubscanDatasource(config)

    async with subscan:
        # Fetch metadata
        metadata = await subscan.get_runtime_metadata(item.spec_version)
        spec = SubstrateSpecVersion(
            name=f'v{item.spec_version}',
            metadata=metadata,
        )
        event_abi = spec.get_event_abi(item.event_qualname)
        event_abi_path = SUBSTRATE_DATA_PATH.joinpath(f'event_abi_{item.spec_version}_{item.event_qualname}.json')
        event_abi_path.parent.mkdir(parents=True, exist_ok=True)
        event_abi_path.write_text(orjson.dumps(event_abi, option=orjson.OPT_INDENT_2).decode('utf-8'))

        # Fetch event params
        params = await subscan.request(
            'post',
            'scan/event/params',
            json={
                'event_index': [item.event_id],
            },
        )
        args = {i['name']: i['value'] for i in params['data'][0]['params']}

        args_path = SUBSTRATE_DATA_PATH.joinpath(f'event_args_{item.spec_version}_{item.event_qualname}.json')
        args_path.parent.mkdir(parents=True, exist_ok=True)
        args_path.write_text(orjson.dumps(args, option=orjson.OPT_INDENT_2).decode('utf-8'))


if __name__ == '__main__':
    import asyncio

    asyncio.run(fetch_test_data(SUBSTATE_DATA[0]))
