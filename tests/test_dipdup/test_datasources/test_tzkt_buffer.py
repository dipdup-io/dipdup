from unittest import IsolatedAsyncioTestCase

from dipdup.datasources.tzkt.datasource import BufferedMessage
from dipdup.datasources.tzkt.datasource import MessageBuffer
from dipdup.datasources.tzkt.datasource import MessageType


class MessageBufferTest(IsolatedAsyncioTestCase):
    async def asyncSetUp(self) -> None:
        self.buffer = MessageBuffer(2)

    async def test_add(self) -> None:
        self.assertEqual(0, len(self.buffer))

        self.buffer.add(MessageType.head, 1, {})
        self.assertEqual(1, len(self.buffer))

        self.buffer.add(MessageType.operation, 1, [{}])
        self.assertEqual(1, len(self.buffer))

        self.buffer.add(MessageType.operation, 2, [{}])
        self.assertEqual(2, len(self.buffer))

    async def test_yield_from(self) -> None:
        self.buffer.add(MessageType.head, 1, {})
        self.buffer.add(MessageType.operation, 1, [{}])
        self.buffer.add(MessageType.head, 2, {})
        self.buffer.add(MessageType.operation, 2, [{}])
        self.buffer.add(MessageType.head, 3, {})
        self.buffer.add(MessageType.operation, 3, [{}])

        self.assertEqual(3, len(self.buffer))

        messages = list(self.buffer.yield_from())

        self.assertEqual(2, len(self.buffer))

        self.assertIsInstance(messages[0], BufferedMessage)
        self.assertEqual(MessageType.head, messages[0].type)
        self.assertIsInstance(messages[1], BufferedMessage)
        self.assertEqual(MessageType.operation, messages[1].type)

    async def test_rollback(self) -> None:
        self.buffer.add(MessageType.head, 2, {})
        self.buffer.add(MessageType.operation, 2, [{}])
        self.buffer.add(MessageType.head, 3, {})
        self.buffer.add(MessageType.operation, 3, [{}])
        self.buffer.add(MessageType.head, 4, {})
        self.buffer.add(MessageType.operation, 4, [{}])

        self.assertEqual(True, self.buffer.rollback(MessageType.head, 4, 3))
        self.assertEqual(True, self.buffer.rollback(MessageType.operation, 4, 3))
        self.assertEqual(True, self.buffer.rollback(MessageType.operation, 3, 1))
        self.assertEqual(True, self.buffer.rollback(MessageType.head, 3, 1))
        self.assertEqual(False, self.buffer.rollback(MessageType.operation, 1, 0))
        self.assertEqual(False, self.buffer.rollback(MessageType.head, 1, 0))
