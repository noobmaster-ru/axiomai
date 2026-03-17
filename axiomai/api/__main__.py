import asyncio

import uvicorn
from dishka import make_async_container
from dishka.integrations.fastapi import setup_dishka
from fastapi import FastAPI

from axiomai.api.routes.articles import router as articles_router
from axiomai.api.routes.banks import router as banks_router
from axiomai.api.routes.buyers import router as buyers_router
from axiomai.config import Config, load_config
from axiomai.infrastructure.di import ApiInteractorsProvider, ConfigProvider, DatabaseProvider, GatewaysProvider
from axiomai.infrastructure.logging import setup_logging


def create_app(config: Config | None = None) -> FastAPI:
    if config is None:
        config = load_config()

    setup_logging(json_logs=config.json_logs)

    app = FastAPI(title="AxiomAI API", version="0.1.0")

    di_container = make_async_container(
        DatabaseProvider(),
        ConfigProvider(),
        GatewaysProvider(),
        ApiInteractorsProvider(),
        context={Config: config},
    )

    setup_dishka(di_container, app)

    app.include_router(articles_router)
    app.include_router(banks_router)
    app.include_router(buyers_router)

    return app


async def main() -> None:
    config = load_config()
    app = create_app(config)

    server_config = uvicorn.Config(app, host="0.0.0.0", port=8000, log_config=None)
    server = uvicorn.Server(server_config)
    await server.serve()


if __name__ == "__main__":
    asyncio.run(main())
