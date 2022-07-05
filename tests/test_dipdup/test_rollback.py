from contextlib import AsyncExitStack
from unittest import IsolatedAsyncioTestCase

import demo_hic_et_nunc.models as models
from dipdup.config import DipDupConfig
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

            async with in_transaction(level=1234, index='test'):
                holder = models.Holder(address='tz1deadbeaf')
                await holder.save()

            model_update = await ModelUpdate.filter(id=1).get()
            assert model_update.action == ModelUpdateAction.INSERT
            assert model_update.index == 'test'
            assert model_update.level == 1234
            assert model_update.model_name == 'Holder'
            assert model_update.model_pk == 'tz1deadbeaf'
            assert model_update.data == None
