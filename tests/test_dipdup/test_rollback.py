from contextlib import AsyncExitStack
from datetime import datetime
from unittest import IsolatedAsyncioTestCase

import demo_hic_et_nunc.models as models
from dipdup.config import DipDupConfig
from dipdup.context import HandlerContext, HookContext
from dipdup.dipdup import DipDup
from dipdup.models import ModelUpdate
from dipdup.models import ModelUpdateAction


class RollbackTest(IsolatedAsyncioTestCase):
    async def test_model_update_creation(self) -> None:
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
                holder = models.Holder(address='tz1deadbeaf')
                await holder.save()

                swap = models.Swap(
                    creator=holder,
                    price=1,
                    amount=1,
                    amount_left=1,
                    level=1000,
                    status=models.SwapStatus.ACTIVE,
                    timestamp=datetime(1970, 1, 1)
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
                swap.status = models.SwapStatus.FINISHED
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
                'status': 1,
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

            # FIXME: Wrong PK
            swap = await models.Swap.filter(id=1).get()
            assert swap.status == models.SwapStatus.FINISHED
            
