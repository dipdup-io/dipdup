import demo_evm_uniswap.models as models
from demo_evm_uniswap.models.position import save_position_snapshot
from demo_evm_uniswap.models.repo import models_repo
from demo_evm_uniswap.types.position_manager.evm_logs.transfer import TransferPayload
from dipdup.context import HandlerContext
from dipdup.models.evm import EvmLog
from eth_utils.address import to_normalized_address


async def transfer(
    ctx: HandlerContext,
    log: EvmLog[TransferPayload],
) -> None:
    if log.payload.from_ == '0x0000000000000000000000000000000000000000':
        idx = f'{log.data.level}.{log.data.transaction_index}.{log.data.log_index}'
        pending_position = models_repo.get_pending_position(idx)
        if pending_position is None:
            ctx.logger.warning('Skipping position %s (must be blacklisted pool)', log.payload.tokenId)
            return

        position = models.Position(id=log.payload.tokenId, **pending_position)
    else:
        pos = await models.Position.get_or_none(id=log.payload.tokenId)
        if pos is None:
            ctx.logger.warning('Skipping position %s (must be blacklisted pool)', log.payload.tokenId)
            return
        position = pos

    position.owner = to_normalized_address(log.payload.to)
    await position.save()
    await save_position_snapshot(position, log.data.level, log.data.timestamp)