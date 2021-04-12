from dipdup.models import HandlerContext, OperationContext
from dipdup_registrydao.models import *
from dipdup_registrydao.types.KT1QMdCTqzmY4QKHntV1nZEinLPU1GbxUFQu.parameter.transfer_contract_tokens import TransferContractTokens


async def on_transfer_contract_tokens(
    ctx: HandlerContext,
    transfer_contract_tokens: OperationContext[TransferContractTokens],
) -> None:
    ...
