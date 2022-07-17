from contextlib import AsyncExitStack
from datetime import datetime
from typing import List
from unittest import IsolatedAsyncioTestCase

import pytest

import demo_hic_et_nunc.models as hen_models
import demo_tezos_domains.models as domains_models
from dipdup.config import DipDupConfig
from dipdup.context import HookContext
from dipdup.dipdup import DipDup
from dipdup.enums import IndexType
from dipdup.models import Index
from dipdup.models import ModelUpdate
from dipdup.models import ModelUpdateAction


class RollbackTest(IsolatedAsyncioTestCase):
    async def test_model_updates(self) -> None:
        config = DipDupConfig(spec_version='1.2', package='demo_hic_et_nunc')
        config.initialize()
        dipdup = DipDup(config)
        in_transaction = dipdup._transactions.in_transaction

        async with AsyncExitStack() as stack:
            await dipdup._set_up_database(stack)
            await dipdup._set_up_transactions(stack)
            await dipdup._set_up_hooks(set())
            await dipdup._initialize_schema()

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
            assert model_update.data == None

            model_update = await ModelUpdate.filter(id=2).get()
            assert model_update.action == ModelUpdateAction.INSERT
            assert model_update.index == 'test'
            assert model_update.level == 1000
            assert model_update.model_name == 'Swap'
            assert model_update.model_pk == '1'
            assert model_update.data == None

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
                'amount': 1,
                'amount_left': 1,
                'creator_id': 'tz1deadbeaf',
                'level': 1000,
                'price': 1,
                'status': 0,
                'timestamp': '1970-01-01T00:00:00+00:00',
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
                self=dipdup._ctx,  # type: ignore
                index='test',
                from_level=1002,
                to_level=1001,
            )

            swap = await hen_models.Swap.filter(id=1).get()
            assert swap.status == hen_models.SwapStatus.FINISHED

            # NOTE: Rollback UPDATE
            await HookContext.rollback(
                self=dipdup._ctx,  # type: ignore
                index='test',
                from_level=1001,
                to_level=1000,
            )

            swap = await hen_models.Swap.filter(id=1).get()
            assert swap.status == hen_models.SwapStatus.ACTIVE

            # NOTE: Rollback INSERT
            await HookContext.rollback(
                self=dipdup._ctx,  # type: ignore
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

    async def test_cleanup_and_filtering(self) -> None:
        config = DipDupConfig(spec_version='1.2', package='demo_hic_et_nunc')
        config.initialize()
        dipdup = DipDup(config)
        in_transaction = dipdup._transactions.in_transaction

        async with AsyncExitStack() as stack:
            await dipdup._set_up_database(stack)
            await dipdup._set_up_transactions(stack)
            await dipdup._set_up_hooks(set())
            await dipdup._initialize_schema()

            # NOTE: Filter less than `rollback_depth` (which is 2 by default)
            sync_level = 1000
            for level in range(995, 1005):
                async with in_transaction(level=level, sync_level=sync_level, index='test'):
                    holder = hen_models.Holder(address=str(level))
                    await holder.save()

            model_update_levels = await ModelUpdate.filter().values_list('level', flat=True)
            assert model_update_levels == [998, 999, 1000, 1001, 1002, 1003, 1004]

            # NOTE: Cleanup
            index = Index(
                name='test',
                type=IndexType.operation,
                config_hash='',
                level=1005,
            )
            await index.save()
            await dipdup._transactions.cleanup()

            model_update_levels = await ModelUpdate.filter().values_list('level', flat=True)
            assert model_update_levels == [1003, 1004]

    async def test_optionals(self) -> None:
        config = DipDupConfig(spec_version='1.2', package='demo_tezos_domains')
        config.initialize()
        dipdup = DipDup(config)
        in_transaction = dipdup._transactions.in_transaction

        async with AsyncExitStack() as stack:
            await dipdup._set_up_database(stack)
            await dipdup._set_up_transactions(stack)
            await dipdup._set_up_hooks(set())
            await dipdup._initialize_schema()

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
                self=dipdup._ctx,  # type: ignore
                index='test',
                from_level=1001,
                to_level=1000,
            )

            domain = await domains_models.Domain.filter(id='test').get()
            assert domain.id == 'test'
            assert domain.tld_id == tld.id
            assert domain.expiry is None
            assert domain.owner == 'test'
            assert domain.token_id is None

    @pytest.mark.skip('NotImplementedError')
    async def test_bulk_create_update(self) -> None:
        config = DipDupConfig(spec_version='1.2', package='demo_hic_et_nunc')
        config.initialize()
        dipdup = DipDup(config)
        in_transaction = dipdup._transactions.in_transaction

        async with AsyncExitStack() as stack:
            await dipdup._set_up_database(stack)
            await dipdup._set_up_transactions(stack)
            await dipdup._set_up_hooks(set())
            await dipdup._initialize_schema()

            holders: List[hen_models.Holder] = []
            for i in range(10):
                holder = hen_models.Holder(address=str(i))
                holders.append(holder)

            async with in_transaction(level=1000, index='test'):
                await hen_models.Holder.bulk_create(holders)  # type: ignore

            holders = await hen_models.Holder.filter().count()
            assert holders == 10
            model_updates = await ModelUpdate.filter().count()
            assert model_updates == 10
