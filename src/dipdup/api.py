from aiohttp import web

from dipdup.cache import cache


async def create_api() -> web.Application:
    from aiohttp import web

    routes = web.RouteTableDef()

    @routes.get('/performance')
    async def performance(request: web.Request) -> web.Response:
        return web.json_response(cache.stats())

    app = web.Application()
    app.add_routes(routes)
    return app
