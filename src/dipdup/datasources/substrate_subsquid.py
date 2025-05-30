from collections.abc import AsyncIterator
from itertools import pairwise

from dipdup.config.substrate_subsquid import SubstrateSubsquidDatasourceConfig
from dipdup.datasources._subsquid import AbstractSubsquidDatasource
from dipdup.models._subsquid import AbstractSubsquidQuery
from dipdup.models.substrate import _SubstrateSubsquidEventResponse

Query = AbstractSubsquidQuery


class SubstrateSubsquidDatasource(AbstractSubsquidDatasource[SubstrateSubsquidDatasourceConfig, Query]):
    async def iter_events(
        self,
        first_level: int,
        last_level: int,
        names: tuple[str, ...],
    ) -> AsyncIterator[tuple[_SubstrateSubsquidEventResponse, ...]]:
        current_level = first_level

        while current_level <= last_level:
            # NOTE: we have to query previous level to decode event
            if current_level == 0:
                current_level = 1
                continue
            query: Query = {  # type: ignore[typeddict-unknown-key]
                'fields': {
                    'event': {
                        'name': True,
                        'args': True,
                    },
                    'block': {
                        'hash': True,
                        'parentHash': True,
                        'stateRoot': True,
                        'extrinsicsRoot': True,
                        'digest': True,
                        'specName': True,
                        'specVersion': True,
                        'implName': True,
                        'implVersion': True,
                        'timestamp': True,
                        'validator': True,
                    },
                },
                'events': [
                    {
                        'name': list(names),
                    },
                ],
                # NOTE: to decode event we have to use previous level's specification version
                'fromBlock': current_level - 1,
                'toBlock': last_level,
                'type': 'substrate',
            }
            response = await self.query_worker(query, current_level)

            for prev_level_item, level_item in pairwise(response):
                for event_item in level_item['events']:
                    event_item['header'] = level_item['header']
                    # NOTE: to decode event we have to use previous level's specification version
                    level_item['header'] = level_item['header'].copy()
                    event_item['header']['specVersion'] = prev_level_item['header']['specVersion']
                yield tuple(level_item['events'])
                current_level = level_item['header']['number'] + 1
