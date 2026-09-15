"""CreateBuyer фиксирует условия артикула (процент и инструкцию) в заявке на момент её создания."""

from axiomai.application.interactors.create_buyer import CreateBuyer


async def test_create_buyer_freezes_article_percent_and_instruction(
    di_container, session, cabinet_factory, cashback_article_factory
):
    cabinet = await cabinet_factory()
    article = await cashback_article_factory(cabinet_id=cabinet.id, cashback_percent=20)
    create_buyer = await di_container.get(CreateBuyer)

    buyer = await create_buyer.execute(telegram_id=4242, username="u", fullname="U", article_id=article.id)

    assert buyer.cashback_percent == 20
    assert buyer.instruction_text == "Test Instruction"

    # селлер поменял условия в таблице → синк обновил артикул, но заявка осталась на старых условиях
    article.cashback_percent = 30
    article.instruction_text = "Новая инструкция"
    await session.flush()
    await session.refresh(buyer)

    assert buyer.cashback_percent == 20
    assert buyer.instruction_text == "Test Instruction"


async def test_create_buyer_returns_existing_request_with_original_conditions(
    di_container, session, cabinet_factory, cashback_article_factory
):
    cabinet = await cabinet_factory()
    article = await cashback_article_factory(cabinet_id=cabinet.id, cashback_percent=20)
    create_buyer = await di_container.get(CreateBuyer)
    first = await create_buyer.execute(telegram_id=4243, username="u", fullname="U", article_id=article.id)

    article.cashback_percent = 30
    await session.flush()
    second = await create_buyer.execute(telegram_id=4243, username="u", fullname="U", article_id=article.id)

    assert second.id == first.id
    assert second.cashback_percent == 20
