# from contextlib import AsyncExitStack
# from pathlib import Path
# from typing import AsyncIterator

# import pytest

# from dipdup.config import DipDupConfig
# from dipdup.dipdup import DipDup
# from dipdup.exceptions import ContractAlreadyExistsError
# from dipdup.exceptions import ReindexingRequiredError
# from dipdup.models import Contract
# from dipdup.models import ReindexingReason
# from dipdup.models import Schema


# @pytest.fixture
# async def dummy_dipdup() -> AsyncIterator[DipDup]:
#     path = Path(__file__).parent / 'configs' / 'dipdup.yaml'
#     config = DipDupConfig.load([path])
#     async with AsyncExitStack() as stack:
#         yield await DipDup.create_dummy(config, stack, in_memory=True)


# async def test_reindex_manual(dummy_dipdup: DipDup) -> None:
#     # Act
#     with pytest.raises(ReindexingRequiredError):
#         await dummy_dipdup._ctx.reindex()

#     # Assert
#     schema = await Schema.filter().get()
#     assert schema.reindex == ReindexingReason.manual


# async def test_reindex_field(dummy_dipdup: DipDup) -> None:
#     await Schema.filter().update(reindex=ReindexingReason.manual)

#     # Act
#     with pytest.raises(ReindexingRequiredError):
#         await dummy_dipdup._initialize_schema()

#     # Assert
#     schema = await Schema.filter().get()
#     assert schema.reindex == ReindexingReason.manual


# async def test_add_contract(dummy_dipdup: DipDup) -> None:
#     ctx = dummy_dipdup._ctx
#     await ctx.add_contract('address', 'KT1K4EwTpbvYN9agJdjpyJm4ZZdhpUNKB3F6')
#     await ctx.add_contract('code_hash', None, None, 54325432)

#     with pytest.raises(ContractAlreadyExistsError):
#         await ctx.add_contract('address_dup', 'KT1K4EwTpbvYN9agJdjpyJm4ZZdhpUNKB3F6')
#     with pytest.raises(ContractAlreadyExistsError):
#         await ctx.add_contract('address', 'KT1K4EwTpbvYN9agJdjpyJm4ZZdhpUNK0000')
#     with pytest.raises(ContractAlreadyExistsError):
#         await ctx.add_contract('code_hash_dup', None, None, 54325432)
#     with pytest.raises(ContractAlreadyExistsError):
#         await ctx.add_contract('code_hash', None, None, 54325432)

#     assert ctx.config.get_tezos_contract('address').address == 'KT1K4EwTpbvYN9agJdjpyJm4ZZdhpUNKB3F6'
#     assert ctx.config.get_tezos_contract('code_hash').code_hash == 54325432

#     assert (await Contract.get(name='address')).address == 'KT1K4EwTpbvYN9agJdjpyJm4ZZdhpUNKB3F6'
#     assert (await Contract.get(name='code_hash')).address is None
