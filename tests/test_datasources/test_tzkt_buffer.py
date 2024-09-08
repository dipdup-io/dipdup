import pytest

from dipdup.datasources.tezos_tzkt import BufferedMessage
from dipdup.datasources.tezos_tzkt import MessageBuffer
from dipdup.models.tezos_tzkt import TezosTzktMessageType


@pytest.fixture
def buffer() -> MessageBuffer:
    return MessageBuffer(2)


async def test_add(buffer: MessageBuffer) -> None:
    assert len(buffer) == 0

    buffer.add(TezosTzktMessageType.head, 1, {})
    assert len(buffer) == 1

    buffer.add(TezosTzktMessageType.operation, 1, [{}])
    assert len(buffer) == 1

    buffer.add(TezosTzktMessageType.operation, 2, [{}])
    assert len(buffer) == 2


async def test_yield_from(buffer: MessageBuffer) -> None:
    buffer.add(TezosTzktMessageType.head, 1, {})
    buffer.add(TezosTzktMessageType.operation, 1, [{}])
    buffer.add(TezosTzktMessageType.head, 2, {})
    buffer.add(TezosTzktMessageType.operation, 2, [{}])
    buffer.add(TezosTzktMessageType.head, 3, {})
    buffer.add(TezosTzktMessageType.operation, 3, [{}])

    assert len(buffer) == 3

    messages = list(buffer.yield_from())

    assert len(buffer) == 2

    assert isinstance(messages[0], BufferedMessage)
    assert messages[0].type == TezosTzktMessageType.head
    assert isinstance(messages[1], BufferedMessage)
    assert messages[1].type == TezosTzktMessageType.operation


async def test_rollback(buffer: MessageBuffer) -> None:
    buffer.add(TezosTzktMessageType.head, 2, {})
    buffer.add(TezosTzktMessageType.operation, 2, [{}])
    buffer.add(TezosTzktMessageType.head, 3, {})
    buffer.add(TezosTzktMessageType.operation, 3, [{}])
    buffer.add(TezosTzktMessageType.head, 4, {})
    buffer.add(TezosTzktMessageType.operation, 4, [{}])

    assert buffer.rollback(TezosTzktMessageType.head, 4, 3) is True
    assert buffer.rollback(TezosTzktMessageType.operation, 4, 3) is True
    assert buffer.rollback(TezosTzktMessageType.operation, 3, 1) is True
    assert buffer.rollback(TezosTzktMessageType.head, 3, 1) is True
    assert buffer.rollback(TezosTzktMessageType.operation, 1, 0) is False
    assert buffer.rollback(TezosTzktMessageType.head, 1, 0) is False
