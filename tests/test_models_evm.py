"""Unit tests for the shared EVM subsquid parser.

`EvmTransactionData.from_subsquid_json` / `EvmEventData.from_subsquid_json` are used by
BOTH the v2.archive and the SQD Portal transports (see `_AbstractEvmSubsquidDatasource`).
The two transports return the same JSON shape EXCEPT for value encodings:

- v2.archive encodes `yParity` as a hex string (``'0x1'``);
- SQD Portal encodes it as a native int (``1``).

Quantity fields (``gas``, ``value``, ``gasPrice``, …) are hex strings on both transports;
small fields (``nonce``, ``chainId``, ``type``, ``status``, ``transactionIndex`` and the
block ``number``/``timestamp``) are native ints on both. These types were confirmed
against the live Portal ``/finalized-stream`` for ethereum-mainnet on 2026-06-01.
"""

import asyncio
from pathlib import Path
from typing import Any
from unittest.mock import AsyncMock

import orjson
import pytest

from dipdup.config.evm_sqd_portal import EvmPortalDatasourceConfig
from dipdup.datasources.evm_sqd_portal import EvmPortalDatasource
from dipdup.models.evm import EvmEventData
from dipdup.models.evm import EvmTransactionData

# NOTE: Real v2.archive-shaped transaction (note `yParity: null`, quantities as hex strings).
_ARCHIVE_TX: dict[str, Any] = orjson.loads(
    (Path(__file__).parent / 'responses' / 'subsquid_transaction.json').read_bytes(),
)

# NOTE: Real Portal block header — `number`/`timestamp` are native ints, `hash` a string.
_HEADER: dict[str, Any] = {
    'number': 18077421,
    'hash': '0x8205dd1b72b0b2205653ad4371310743e5b52b6cd18e0307c809fd0bff884f0b',
    'timestamp': 1694003543,
}


def _archive_tx(**overrides: Any) -> dict[str, Any]:
    tx = dict(_ARCHIVE_TX)
    tx.update(overrides)
    return tx


def _portal_tx(**overrides: Any) -> dict[str, Any]:
    # NOTE: Portal shape is identical to v2.archive except `yParity` is a native int.
    return _archive_tx(**{'yParity': 1, **overrides})


def _portal_datasource() -> EvmPortalDatasource:
    config = EvmPortalDatasourceConfig(
        kind='evm.sqd_portal',
        url='https://portal.sqd.dev/datasets/ethereum-mainnet',
    )
    config._name = 'portal'
    return EvmPortalDatasource(config)


# --- transaction parsing: quantity fields are hex on both transports -----------------


@pytest.mark.parametrize('shape', ['archive', 'portal'])
def test_from_subsquid_json_quantity_fields(shape: str) -> None:
    raw = _archive_tx() if shape == 'archive' else _portal_tx()
    tx = EvmTransactionData.from_subsquid_json(transaction_json=raw, header=_HEADER)

    # hex-string quantities -> int (same encoding on both transports)
    assert tx.gas == int(raw['gas'], 16)
    assert tx.gas_price == int(raw['gasPrice'], 16)
    assert tx.gas_used == int(raw['gasUsed'], 16)
    assert tx.value == int(raw['value'], 16)
    assert tx.cumulative_gas_used == int(raw['cumulativeGasUsed'], 16)
    assert tx.effective_gas_price == int(raw['effectiveGasPrice'], 16)
    assert tx.max_fee_per_gas == int(raw['maxFeePerGas'], 16)
    assert tx.max_priority_fee_per_gas == int(raw['maxPriorityFeePerGas'], 16)
    assert tx.v == int(raw['v'], 16)

    # natively-typed fields -> passed through unchanged
    assert tx.chain_id == raw['chainId']
    assert tx.nonce == raw['nonce']
    assert tx.status == raw['status']
    assert tx.type == raw['type']
    assert tx.transaction_index == raw['transactionIndex']

    # header fields
    assert tx.level == _HEADER['number']
    assert tx.block_hash == _HEADER['hash']
    assert tx.timestamp == _HEADER['timestamp']


# --- transaction parsing: yParity encoding differs between transports ----------------


@pytest.mark.parametrize(
    ('raw_y_parity', 'expected'),
    [
        ('0x1', True),  # v2.archive: odd parity, hex string
        ('0x0', False),  # v2.archive: even parity, hex string
        (1, True),  # Portal: odd parity, native int
        (None, None),  # absent / pre-Byzantium (both transports)
    ],
)
def test_y_parity_decoding(raw_y_parity: Any, expected: bool | None) -> None:
    tx = EvmTransactionData.from_subsquid_json(
        transaction_json=_archive_tx(yParity=raw_y_parity),
        header=_HEADER,
    )
    assert tx.y_parity is expected


def test_y_parity_portal_zero_is_false() -> None:
    # NOTE: real type-2 txs on Portal carry yParity == 0 (observed 2026-06-01). Regression:
    # the `is None` check must keep this as False (even parity), not collapse it to None the
    # way the old `if not raw_y_parity` guard did — that diverged from v2.archive's '0x0'.
    tx = EvmTransactionData.from_subsquid_json(
        transaction_json=_portal_tx(yParity=0),
        header=_HEADER,
    )
    assert tx.y_parity is False


# --- event parsing: identical shape on both transports -------------------------------


@pytest.mark.parametrize('transaction_index', [0, 6])
def test_event_from_subsquid_json(transaction_index: int) -> None:
    topics = ['0xddf2', '0xfrom', '0xto']
    log = {
        'address': '0xdac17f958d2ee523a2206206994597c13d831ec7',
        'data': '0x00',
        'logIndex': 12,
        'transactionIndex': transaction_index,
        'transactionHash': '0xabc',
        'topics': topics,
    }
    event = EvmEventData.from_subsquid_json(event_json=log, header=_HEADER)

    assert event.level == _HEADER['number']
    assert event.block_hash == _HEADER['hash']
    assert event.timestamp == _HEADER['timestamp']
    assert event.log_index == 12
    assert event.transaction_index == transaction_index
    assert event.topics == tuple(topics)
    assert event.removed is False


# --- status filtering through the shared iter_transactions loop ----------------------


async def test_iter_transactions_skips_pre_byzantium_status() -> None:
    """`status != 0` keeps successful (1) and pre-Byzantium (None) txs, drops failed (0)."""
    datasource = _portal_datasource()
    level_item = {
        'header': _HEADER,
        'transactions': [
            _portal_tx(hash='0xok', status=1),
            _portal_tx(hash='0xfailed', status=0),
            _portal_tx(hash='0xlegacy', status=None),
        ],
    }
    # NOTE: header.number == last_level so `current_level` advances past it and the loop ends.
    datasource.query_worker = AsyncMock(return_value=[level_item])  # type: ignore[method-assign]

    batches = [
        batch
        async for batch in datasource.iter_transactions(
            first_level=_HEADER['number'],
            last_level=_HEADER['number'],
            filters=(),
        )
    ]

    hashes = [tx.hash for batch in batches for tx in batch]
    assert hashes == ['0xok', '0xlegacy']


# --- issue #1: the shared loop must not spin on an empty Portal stream ---------------


async def test_iter_transactions_terminates_on_empty_stream() -> None:
    """An empty response over a multi-block range exhausts the range, it does not loop forever."""
    datasource = _portal_datasource()
    # NOTE: `current_level` never advances on an empty response; the guard must break the loop.
    datasource.query_worker = AsyncMock(return_value=[])  # type: ignore[method-assign]

    async def _drain() -> list[Any]:
        return [batch async for batch in datasource.iter_transactions(100, 200, filters=())]

    # NOTE: wait_for turns a regression (infinite re-query) into a fast failure instead of a hang.
    batches = await asyncio.wait_for(_drain(), timeout=5)

    assert batches == []
    assert datasource.query_worker.await_count == 1


async def test_iter_events_terminates_on_empty_stream() -> None:
    datasource = _portal_datasource()
    datasource.query_worker = AsyncMock(return_value=[])  # type: ignore[method-assign]

    async def _drain() -> list[Any]:
        return [batch async for batch in datasource.iter_events((), 100, 200)]

    batches = await asyncio.wait_for(_drain(), timeout=5)

    assert batches == []
    assert datasource.query_worker.await_count == 1


async def test_iter_transactions_paginates_then_stops() -> None:
    """A partial chunk (last block < last_level) is followed by another query; empty ends it."""
    datasource = _portal_datasource()
    partial = {
        'header': {**_HEADER, 'number': 150},
        'transactions': [_portal_tx(hash='0xpartial', status=1)],
    }
    # NOTE: first query returns blocks up to 150, second covers 151..200 and finds nothing -> stop.
    datasource.query_worker = AsyncMock(side_effect=[[partial], []])  # type: ignore[method-assign]

    batches = await asyncio.wait_for(
        anext_all(datasource.iter_transactions(100, 200, filters=())),
        timeout=5,
    )

    hashes = [tx.hash for batch in batches for tx in batch]
    assert hashes == ['0xpartial']
    assert datasource.query_worker.await_count == 2
    # NOTE: the second query resumes from the block after the last one returned (150 + 1)
    second_call_level = datasource.query_worker.await_args_list[1].args[1]
    assert second_call_level == 151


async def anext_all(aiter: Any) -> list[Any]:
    return [item async for item in aiter]
