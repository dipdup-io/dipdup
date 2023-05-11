from aiohttp import web

import dipdup.performance
from dipdup.utils import json_dumps


async def create_api() -> web.Application:
    routes = web.RouteTableDef()

    @routes.get('/performance')
    async def _performance(request: web.Request) -> web.Response:
        return web.json_response(
            dipdup.performance.get_stats(),
            dumps=lambda x: json_dumps(x).decode(),
        )

    app = web.Application()
    app.add_routes(routes)
    return app
