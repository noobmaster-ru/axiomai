import logging
from enum import Enum

from axiomai.infrastructure.database.gateways.buyer import BuyerGateway
from axiomai.infrastructure.database.models.buyer import Buyer
from axiomai.infrastructure.database.transaction_manager import TransactionManager

logger = logging.getLogger(__name__)


class ScreenshotType(Enum):
    ORDER = "order"
    FEEDBACK = "feedback"
    CUT_LABELS = "cut_labels"


_FIELD_MAP: dict[ScreenshotType, str] = {
    ScreenshotType.ORDER: "is_ordered",
    ScreenshotType.FEEDBACK: "is_left_feedback",
    ScreenshotType.CUT_LABELS: "is_cut_labels",
}


class UpdateBuyerScreenshot:
    def __init__(
        self,
        buyer_gateway: BuyerGateway,
        transaction_manager: TransactionManager,
    ) -> None:
        self._buyer_gateway = buyer_gateway
        self._transaction_manager = transaction_manager

    async def execute(self, buyer_id: int, screenshot_type: ScreenshotType) -> Buyer:
        buyer = await self._buyer_gateway.get_buyer_by_id(buyer_id)
        if not buyer:
            msg = f"Buyer with id {buyer_id} not found"
            raise ValueError(msg)

        field_name = _FIELD_MAP[screenshot_type]
        setattr(buyer, field_name, True)
        await self._transaction_manager.commit()

        logger.info("buyer %s screenshot %s accepted", buyer_id, screenshot_type.value)
        return buyer
