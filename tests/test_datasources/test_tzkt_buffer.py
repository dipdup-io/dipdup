import pytest

from dipdup.datasources.tezos_tzkt import BufferedMessage
from dipdup.datasources.tezos_tzkt import MessageBuffer
from dipdup.models.tezos_tzkt import MessageType


@pytest.fixture
def buffer() -> MessageBuffer:
    return MessageBuffer(2)


async def test_add(buffer: MessageBuffer) -> None:
    assert len(buffer) == 0

    buffer.add(MessageType.head, 1, {})
    assert len(buffer) == 1

    buffer.add(MessageType.operation, 1, [{}])
    assert len(buffer) == 1

    buffer.add(MessageType.operation, 2, [{}])
    assert len(buffer) == 2


async def test_yield_from(buffer: MessageBuffer) -> None:
    buffer.add(MessageType.head, 1, {})
    buffer.add(MessageType.operation, 1, [{}])
    buffer.add(MessageType.head, 2, {})
    buffer.add(MessageType.operation, 2, [{}])
    buffer.add(MessageType.head, 3, {})
    buffer.add(MessageType.operation, 3, [{}])

    assert len(buffer) == 3

    messages = list(buffer.yield_from())

    assert len(buffer) == 2

    assert isinstance(messages[0], BufferedMessage)
    assert messages[0].type == MessageType.head
    assert isinstance(messages[1], BufferedMessage)
    assert messages[1].type == MessageType.operation


async def test_rollback(buffer: MessageBuffer) -> None:
    buffer.add(MessageType.head, 2, {})
    buffer.add(MessageType.operation, 2, [{}])
    buffer.add(MessageType.head, 3, {})
    buffer.add(MessageType.operation, 3, [{}])
    buffer.add(MessageType.head, 4, {})
    buffer.add(MessageType.operation, 4, [{}])

    assert buffer.rollback(MessageType.head, 4, 3) is True
    assert buffer.rollback(MessageType.operation, 4, 3) is True
    assert buffer.rollback(MessageType.operation, 3, 1) is True
    assert buffer.rollback(MessageType.head, 3, 1) is True
    assert buffer.rollback(MessageType.operation, 1, 0) is False
    assert buffer.rollback(MessageType.head, 1, 0) is False
