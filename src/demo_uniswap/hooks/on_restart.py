import decimal

from dipdup.context import HookContext


async def on_restart(
    ctx: HookContext,
) -> None:
    decimal_context = decimal.getcontext()
    # FIXME: Not a single idea why.
    # Try quantizing 340256786836388094070642339899681172762184831912254825631.508231530591534 with lower value.
    decimal_context.prec = 127
    decimal.setcontext(decimal_context)
