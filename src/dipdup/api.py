import functools
import logging
from collections.abc import Awaitable
from collections.abc import Callable

from starlette.applications import Starlette
from starlette.requests import Request
from starlette.responses import JSONResponse
from starlette.responses import Response
from starlette.routing import Route

import dipdup.performance
from dipdup.context import DipDupContext
from dipdup.exceptions import Error

_logger = logging.getLogger(__name__)


def _method_wrapper(
    ctx: 'DipDupContext',
    method: Callable[[DipDupContext, Request], Awaitable[Response]],
) -> Callable[[Request], Awaitable[Response]]:
    @functools.wraps(method)
    async def resolved_method(request: Request) -> Response:
        try:
            return await method(ctx, request)
        except Error as e:
            return Response(str(e), status_code=400)
        except Exception as e:
            _logger.exception('Unhandled exception in API method')
            return Response(str(e), status_code=500)

    return resolved_method


async def _add_index(ctx: 'DipDupContext', request: Request) -> Response:
    json = await request.json()
    await ctx.add_index(**json)
    return Response()


async def _add_contract(ctx: 'DipDupContext', request: Request) -> Response:
    json = await request.json()
    await ctx.add_contract(**json)
    return Response()


async def _performance(ctx: 'DipDupContext', request: Request) -> Response:
    return JSONResponse(
        dipdup.performance.get_stats(),
    )


async def _config(ctx: 'DipDupContext', request: Request) -> Response:
    return Response(content=ctx.config.dump(strip_secrets=True))


async def _home(request: Request) -> Response:
    return Response('dipdup API is running')


async def create_api(ctx: DipDupContext) -> Starlette:
    routes = [
        Route('/', _home),
        Route('/performance', _method_wrapper(ctx, _performance)),
        Route('/metrics', _method_wrapper(ctx, _performance)),
        Route('/add_index', _method_wrapper(ctx, _add_index), methods=['POST']),
        Route('/add_contract', _method_wrapper(ctx, _add_contract), methods=['POST']),
        Route('/config', _method_wrapper(ctx, _config), methods=['GET']),
    ]
    return Starlette(
        debug=True,
        routes=routes,
    )
