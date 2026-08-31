import asyncio
import logging

from aiogram import Bot
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from dishka import AsyncContainer, make_async_container

from axiomai.application.interactors.observe_balance_notifications import ObserveBalanceNotifications
from axiomai.application.interactors.observe_cashback_tables import ObserveCashbackTables
from axiomai.application.interactors.observe_inactive_reminders import ObserveInactiveReminders
from axiomai.application.interactors.sync_cashback_tables import SyncCashbackTables
from axiomai.config import Config, load_config
from axiomai.infrastructure.di import DatabaseProvider, GatewaysProvider, ObserverInteractorsProvider
from axiomai.infrastructure.logging import setup_logging

logger = logging.getLogger(__name__)


async def _run_observer_loop[InteractorT](
    di_container: AsyncContainer,
    interactor_type: type[InteractorT],
    name: str,
    interval_seconds: int,
) -> None:
    """Бесконечный цикл одного observer'а: ошибка итерации логируется,
    но не убивает ни этот цикл, ни соседние task'и в gather().
    """
    logger.info("start %s observer...", name)
    while True:
        try:
            async with di_container() as r_container:
                interactor = await r_container.get(interactor_type)
                await interactor.execute()  # type: ignore[attr-defined]
        except Exception:
            logger.exception("%s observer iteration failed", name)

        await asyncio.sleep(interval_seconds)


async def run_cashback_tables_observer(di_container: AsyncContainer) -> None:
    await _run_observer_loop(di_container, ObserveCashbackTables, "cashback tables", interval_seconds=10)


async def run_sync_cashback_tables(di_container: AsyncContainer) -> None:
    await _run_observer_loop(di_container, SyncCashbackTables, "sync cashback tables", interval_seconds=10)


async def run_balance_notifications_observer(di_container: AsyncContainer) -> None:
    await _run_observer_loop(di_container, ObserveBalanceNotifications, "balance notifications", interval_seconds=10)


async def run_inactive_reminders_observer(di_container: AsyncContainer) -> None:
    """Намеренно не запущен в main(): напоминания неактивным лидам отключены,
    чтобы не тревожить пользователей слишком часто.
    """
    await _run_observer_loop(di_container, ObserveInactiveReminders, "inactive reminders", interval_seconds=3600)


async def main() -> None:
    config = load_config()
    setup_logging(json_logs=config.json_logs)
    bot = Bot(token=config.bot_token, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
    di_container = make_async_container(
        DatabaseProvider(),
        ObserverInteractorsProvider(),
        GatewaysProvider(),
        context={Config: config, Bot: bot},
    )
    try:
        await asyncio.gather(
            asyncio.create_task(run_cashback_tables_observer(di_container)),
            asyncio.create_task(run_sync_cashback_tables(di_container)),
            asyncio.create_task(run_balance_notifications_observer(di_container)),
        )
    finally:
        await di_container.close()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except (KeyboardInterrupt, SystemExit):
        logger.info("observer stopped")
