from contextlib import AsyncExitStack
from datetime import datetime

import demo_domains.models as domains_models
import demo_nft_marketplace.models as hen_models
from tortoise.expressions import F

from dipdup.config import DipDupConfig
from dipdup.context import HookContext
from dipdup.models import Index
from dipdup.models import IndexType
from dipdup.models import ModelUpdate
from dipdup.models import ModelUpdateAction
from dipdup.test import create_dummy_dipdup


async def test_model_updates() -> None:
    config = DipDupConfig(spec_version='2.0', package='demo_nft_marketplace')
    config.advanced.rollback_depth = 2

    async with AsyncExitStack() as stack:
        dipdup = await create_dummy_dipdup(config, stack)
        in_transaction = dipdup._transactions.in_transaction

        # NOTE: INSERT
        async with in_transaction(level=1000, index='test'):
            holder = hen_models.Holder(address='tz1deadbeaf')
            await holder.save()

            swap = hen_models.Swap(
                creator=holder,
                price=1,
                amount=1,
                amount_left=1,
                level=1000,
                status=hen_models.SwapStatus.ACTIVE,
                timestamp=datetime(1970, 1, 1),
            )
            await swap.save()

        model_update = await ModelUpdate.filter(id=1).get()
        assert model_update.action == ModelUpdateAction.INSERT
        assert model_update.index == 'test'
        assert model_update.level == 1000
        assert model_update.model_name == 'Holder'
        assert model_update.model_pk == 'tz1deadbeaf'
        assert model_update.data is None

        model_update = await ModelUpdate.filter(id=2).get()
        assert model_update.action == ModelUpdateAction.INSERT
        assert model_update.index == 'test'
        assert model_update.level == 1000
        assert model_update.model_name == 'Swap'
        assert model_update.model_pk == '1'
        assert model_update.data is None

        # NOTE: UPDATE
        async with in_transaction(level=1001, index='test'):
            swap.status = hen_models.SwapStatus.FINISHED
            await swap.save()

        model_update = await ModelUpdate.filter(id=3).get()
        assert model_update.action == ModelUpdateAction.UPDATE
        assert model_update.index == 'test'
        assert model_update.level == 1001
        assert model_update.model_name == 'Swap'
        assert model_update.model_pk == '1'
        assert model_update.data == {
            'status': 0,
        }

        # NOTE: DELETE
        async with in_transaction(level=1002, index='test'):
            await swap.delete()

        model_update = await ModelUpdate.filter(id=4).get()
        assert model_update.action == ModelUpdateAction.DELETE
        assert model_update.index == 'test'
        assert model_update.level == 1002
        assert model_update.model_name == 'Swap'
        assert model_update.model_pk == '1'
        assert model_update.data == {
            'amount': 1,
            'amount_left': 1,
            'creator_id': 'tz1deadbeaf',
            'level': 1000,
            'price': 1,
            'status': 1,
            'timestamp': '1970-01-01T00:00:00+00:00',
        }

        # NOTE: Rollback DELETE
        await HookContext.rollback(
            self=dipdup._ctx,
            index='test',
            from_level=1002,
            to_level=1001,
        )

        swap = await hen_models.Swap.filter(id=1).get()
        assert swap.status == hen_models.SwapStatus.FINISHED

        # NOTE: Rollback UPDATE
        await HookContext.rollback(
            self=dipdup._ctx,
            index='test',
            from_level=1001,
            to_level=1000,
        )

        swap = await hen_models.Swap.filter(id=1).get()
        assert swap.status == hen_models.SwapStatus.ACTIVE

        # NOTE: Rollback INSERT
        await HookContext.rollback(
            self=dipdup._ctx,
            index='test',
            from_level=1000,
            to_level=999,
        )

        holders = await hen_models.Holder.filter().count()
        assert holders == 0
        swaps = await hen_models.Swap.filter().count()
        assert swaps == 0
        model_updates = await ModelUpdate.filter().count()
        assert model_updates == 0


async def test_cleanup_and_filtering() -> None:
    config = DipDupConfig(spec_version='2.0', package='demo_nft_marketplace')
    config.advanced.rollback_depth = 2

    async with AsyncExitStack() as stack:
        dipdup = await create_dummy_dipdup(config, stack)
        in_transaction = dipdup._transactions.in_transaction

        # NOTE: Filter less than `rollback_depth` (which is 2 by default)
        sync_level = 1000
        for level in range(995, 1005):
            async with in_transaction(level=level, sync_level=sync_level, index='test'):
                holder = hen_models.Holder(address=str(level))
                await holder.save()

        model_update_levels = await ModelUpdate.filter().values_list('level', flat=True)
        assert model_update_levels == [998, 999, 1000, 1001, 1002, 1003, 1004]  # type: ignore[comparison-overlap]

        # NOTE: Cleanup
        index = Index(
            name='test',
            type=IndexType.tezos_tzkt_operations,
            config_hash='',
            level=1005,
        )
        await index.save()
        await dipdup._transactions.cleanup()

        model_update_levels = await ModelUpdate.filter().values_list('level', flat=True)
        assert model_update_levels == [1003, 1004]  # type: ignore[comparison-overlap]


async def test_optionals() -> None:
    config = DipDupConfig(spec_version='2.0', package='demo_domains')
    config.advanced.rollback_depth = 2

    async with AsyncExitStack() as stack:
        dipdup = await create_dummy_dipdup(config, stack)
        in_transaction = dipdup._transactions.in_transaction

        # NOTE: INSERT and DELETE model with optionals
        async with in_transaction(level=1000, index='test'):
            tld = await domains_models.TLD.create(
                id='test',
                owner='test',
            )
            domain = await domains_models.Domain.create(
                id='test',
                tld=tld,
                expiry=None,
                owner='test',
                token_id=None,
            )

        async with in_transaction(level=1001, index='test'):
            await domain.delete()

        # NOTE: Rollback DELETE
        await HookContext.rollback(
            self=dipdup._ctx,
            index='test',
            from_level=1001,
            to_level=1000,
        )

        domain = await domains_models.Domain.filter(id='test').get()
        assert domain.id == 'test'
        # assert domain.tld_id == tld.id
        # assert domain.expiry is None
        assert domain.owner == 'test'
        assert domain.token_id is None


async def test_bulk_create_update() -> None:
    config = DipDupConfig(spec_version='2.0', package='demo_domains')
    config.advanced.rollback_depth = 2

    async with AsyncExitStack() as stack:
        dipdup = await create_dummy_dipdup(config, stack)
        in_transaction = dipdup._transactions.in_transaction

        tlds: list[domains_models.TLD] = []
        for i in range(3):
            tld = domains_models.TLD(
                id=str(i),
                owner='test',
            )
            tlds.append(tld)

        async with in_transaction(level=1000, index='test'):
            await domains_models.TLD.bulk_create(tlds)

        domains: list[domains_models.Domain] = []
        for tld in tlds:
            domain = domains_models.Domain(
                id=tld.id,
                tld=tld,
                expiry=None,
                owner='test',
                token_id=None,
            )
            domains.append(domain)

        # NOTE: Yes, the same level, why not
        async with in_transaction(level=1000, index='test'):
            await domains_models.Domain.bulk_create(domains)

        for tld, domain in zip(tlds, domains, strict=True):
            tld.owner = tld.id
            domain.token_id = int(domain.id)

        async with in_transaction(level=1001, index='test'):
            await domains_models.TLD.bulk_update(tlds, ('owner',))
            await domains_models.Domain.bulk_update(domains, ('token_id',))

        owners = await domains_models.TLD.filter().values_list('owner', flat=True)
        assert owners == ['0', '1', '2']  # type: ignore[comparison-overlap]
        token_ids = await domains_models.Domain.filter().values_list('token_id', flat=True)
        assert token_ids == [0, 1, 2]  # type: ignore[comparison-overlap]

        model_updates = await ModelUpdate.filter().count()
        assert model_updates == 12

        # NOTE: Rollback bulk_update
        await HookContext.rollback(
            self=dipdup._ctx,
            index='test',
            from_level=1001,
            to_level=1000,
        )

        owners = await domains_models.TLD.filter().values_list('owner', flat=True)
        assert owners == ['test'] * 3  # type: ignore[comparison-overlap]
        token_ids = await domains_models.Domain.filter().values_list('token_id', flat=True)
        assert token_ids == [None] * 3

        model_updates = await ModelUpdate.filter().count()
        assert model_updates == 6

        # NOTE: Rollback bulk_insert
        await HookContext.rollback(
            self=dipdup._ctx,
            index='test',
            from_level=1000,
            to_level=999,
        )

        owners = await domains_models.TLD.filter().values_list('owner', flat=True)
        assert owners == []
        token_ids = await domains_models.Domain.filter().values_list('token_id', flat=True)
        assert token_ids == []

        model_updates = await ModelUpdate.filter().count()
        assert model_updates == 0


async def test_update_prefetch() -> None:
    config = DipDupConfig(spec_version='2.0', package='demo_domains')
    config.advanced.rollback_depth = 2

    async with AsyncExitStack() as stack:
        dipdup = await create_dummy_dipdup(config, stack)
        in_transaction = dipdup._transactions.in_transaction

        # NOTE: INSERT
        tlds: list[domains_models.TLD] = []
        for i in range(3):
            tld = domains_models.TLD(
                id=str(i),
                owner='test',
            )
            tlds.append(tld)

        async with in_transaction(level=1000, index='test'):
            await domains_models.TLD.bulk_create(tlds)

        owners = await domains_models.TLD.filter().values_list('owner', flat=True)
        assert owners == ['test'] * 3  # type: ignore[comparison-overlap]

        model_updates = await ModelUpdate.filter().count()
        assert model_updates == 3

        # NOTE: UPDATE with prefetch
        async with in_transaction(level=1001, index='test'):
            await domains_models.TLD.filter().update(owner='foo')

        owners = await domains_models.TLD.filter().values_list('owner', flat=True)
        assert owners == ['foo'] * 3  # type: ignore[comparison-overlap]

        model_updates = await ModelUpdate.filter().count()
        assert model_updates == 6

        # NOTE: Rollback UPDATE with prefetch
        await HookContext.rollback(
            self=dipdup._ctx,
            index='test',
            from_level=1001,
            to_level=1000,
        )

        owners = await domains_models.TLD.filter().values_list('owner', flat=True)
        assert owners == ['test'] * 3  # type: ignore[comparison-overlap]

        model_updates = await ModelUpdate.filter().count()
        assert model_updates == 3


async def test_update_arithmetics() -> None:
    config = DipDupConfig(spec_version='2.0', package='demo_nft_marketplace')
    config.advanced.rollback_depth = 2

    async with AsyncExitStack() as stack:
        dipdup = await create_dummy_dipdup(config, stack)
        in_transaction = dipdup._transactions.in_transaction

        # NOTE: INSERT
        async with in_transaction(level=1000, index='test'):
            creator = hen_models.Holder(address='')
            await creator.save()

            for i in range(3):
                await hen_models.Token(
                    creator=creator,
                    level=i,
                    supply=i,
                    timestamp=i,
                ).save()

        supply = await hen_models.Token.filter().values_list('supply', flat=True)
        assert supply == [0, 1, 2]  # type: ignore[comparison-overlap]

        model_updates = await ModelUpdate.filter().count()
        assert model_updates == 4

        # NOTE: UPDATE with arithmetics
        async with in_transaction(level=1001, index='test'):
            await hen_models.Token.filter().update(supply=F('supply') * 2)

        supply = await hen_models.Token.filter().values_list('supply', flat=True)
        assert supply == [0, 2, 4]  # type: ignore[comparison-overlap]

        model_updates = await ModelUpdate.filter().count()
        assert model_updates == 7

        # NOTE: Rollback UPDATE with arithmetics
        await HookContext.rollback(
            self=dipdup._ctx,
            index='test',
            from_level=1001,
            to_level=1000,
        )

        supply = await hen_models.Token.filter().values_list('supply', flat=True)
        assert supply == [0, 1, 2]  # type: ignore[comparison-overlap]

        model_updates = await ModelUpdate.filter().count()
        assert model_updates == 4
