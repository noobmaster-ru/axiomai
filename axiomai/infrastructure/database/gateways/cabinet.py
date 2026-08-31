from sqlalchemy import or_, select, update

from axiomai.infrastructure.database.gateways.base import Gateway
from axiomai.infrastructure.database.models import CashbackTable, User
from axiomai.infrastructure.database.models.cabinet import Cabinet


class CabinetGateway(Gateway):
    async def create_cabinet(self, cabinet: Cabinet) -> None:
        self._session.add(cabinet)
        await self._session.flush()

    async def get_cabinet_by_telegram_id(self, telegram_id: int) -> Cabinet | None:
        return await self._session.scalar(select(Cabinet).join(User).where(User.telegram_id == telegram_id))

    async def get_cabinet_by_link_code(self, link_code: str) -> Cabinet | None:
        return await self._session.scalar(select(Cabinet).where(Cabinet.link_code == link_code))

    async def get_cabinet_by_id(self, cabinet_id: int) -> Cabinet | None:
        return await self._session.scalar(select(Cabinet).where(Cabinet.id == cabinet_id))

    async def get_cabinet_by_business_account_id(self, business_account_id: int) -> Cabinet | None:
        return await self._session.scalar(select(Cabinet).where(Cabinet.business_account_id == business_account_id))

    async def get_cabinet_by_telegram_id_or_business_account_id(self, telegram_id: int) -> Cabinet | None:
        return await self._session.scalar(
            select(Cabinet)
            .join(User)
            .where(or_(Cabinet.business_account_id == telegram_id, User.telegram_id == telegram_id))
        )

    async def get_cabinet_by_cashback_table_id(self, cashback_table_id: int) -> Cabinet | None:
        return await self._session.scalar(
            select(Cabinet).join(CashbackTable).where(CashbackTable.id == cashback_table_id)
        )

    async def get_cabinets_with_low_balance(self) -> list[Cabinet]:
        """Получить кабинеты с initial_balance > 0 и balance < 50% от initial_balance."""
        return list(
            await self._session.scalars(
                select(Cabinet).where(
                    Cabinet.initial_balance > 0,
                    Cabinet.balance <= Cabinet.initial_balance * 0.5,
                )
            )
        )

    async def get_cabinet_by_business_connection_id(self, business_connection_id: str) -> Cabinet | None:
        return await self._session.scalar(
            select(Cabinet).where(Cabinet.business_connection_id == business_connection_id)
        )

    async def add_refill_balance(self, cabinet_id: int, amount: int) -> None:
        """Начисляет пополнение и подтягивает initial_balance к новому балансу одним атомарным UPDATE."""
        await self._session.execute(
            update(Cabinet)
            .where(Cabinet.id == cabinet_id)
            .values(balance=Cabinet.balance + amount, initial_balance=Cabinet.balance + amount)
        )

    async def add_leads_balance(self, cabinet_id: int, leads: int) -> None:
        await self._session.execute(
            update(Cabinet).where(Cabinet.id == cabinet_id).values(leads_balance=Cabinet.leads_balance + leads)
        )

    async def try_debit_balance(self, cabinet_id: int, amount: int) -> bool:
        """Списывает amount, только если средств хватает; проверка и списание — один атомарный UPDATE."""
        result = await self._session.execute(
            update(Cabinet)
            .where(Cabinet.id == cabinet_id, Cabinet.balance >= amount)
            .values(balance=Cabinet.balance - amount)
        )
        return result.rowcount == 1
