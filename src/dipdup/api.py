from aiohttp import web

from dipdup.performance import caches
from dipdup.performance import profiler
from dipdup.performance import queues


async def create_api() -> web.Application:
    from aiohttp import web

    routes = web.RouteTableDef()

    @routes.get('/performance')
    async def performance(request: web.Request) -> web.Response:
        stats = {
            'caches': caches.stats(),
            'queues': queues.stats(),
            'profiler': profiler.stats(),
        }
        return web.json_response(stats)

    app = web.Application()
    app.add_routes(routes)
    return app
