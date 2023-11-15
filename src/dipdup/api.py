from collections.abc import Awaitable
from collections.abc import Callable

import orjson
from aiohttp import web

import dipdup.performance
from dipdup.context import DipDupContext
from dipdup.exceptions import ContractAlreadyExistsError
from dipdup.exceptions import IndexAlreadyExistsError
from dipdup.utils import json_dumps


async def _performance(request: web.Request) -> web.Response:
    return web.json_response(
        dipdup.performance.get_stats(),
        dumps=lambda x: json_dumps(x, option=orjson.OPT_SORT_KEYS).decode(),
    )


def _get_add_index(ctx: DipDupContext) -> Callable[[web.Request], Awaitable[web.Response]]:
    async def _add_index(request: web.Request) -> web.Response:
        try:
            await ctx.add_index(**(await request.json()))
        except IndexAlreadyExistsError:
            return web.Response(body='Index already exists', status=400)
        except TypeError as e:
            return web.Response(body=f'Bad arguments: {e!r}', status=400)
        return web.Response()

    return _add_index


def _get_add_contract(ctx: DipDupContext) -> Callable[[web.Request], Awaitable[web.Response]]:
    async def _add_contract(request: web.Request) -> web.Response:
        try:
            await ctx.add_contract(**(await request.json()))
        except ContractAlreadyExistsError:
            return web.Response(body='Contract already exists', status=400)
        except TypeError as e:
            return web.Response(body=f'Bad arguments: {e!r}', status=400)
        return web.Response()

    return _add_contract


async def create_api(ctx: DipDupContext) -> web.Application:
    routes = web.RouteTableDef()
    routes.get('/performance')(_performance)
    routes.post('/add_index')(_get_add_index(ctx))
    routes.post('/add_contract')(_get_add_contract(ctx))

    app = web.Application()
    app.add_routes(routes)
    return app
