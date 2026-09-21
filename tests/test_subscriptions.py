from dipdup.subscriptions.evm_node import EvmNodeHeadSubscription
from dipdup.subscriptions.evm_node import EvmNodeLogsSubscription


def test_head_subscriptions_differ_but_share_params() -> None:
    # NOTE: `evm.events` indexes ask for `EvmNodeHeadSubscription()`, `evm.transactions` ones for
    # `EvmNodeHeadSubscription(transactions=True)`. Both land in the same set (evm.node never
    # merges subscriptions), and `transactions` never reaches the wire — so a project with both
    # index kinds on one node datasource opens two identical `newHeads` streams and gets every
    # head announced twice.
    subscriptions = {EvmNodeHeadSubscription(), EvmNodeHeadSubscription(transactions=True)}

    assert len(subscriptions) == 2
    assert {tuple(s.get_params()) for s in subscriptions} == {('newHeads',)}


def test_logs_subscription_omits_unset_filters() -> None:
    # NOTE: strict JSON-RPC nodes (Octez/Etherlink EVM) reject `null`; the key must be absent
    params = EvmNodeLogsSubscription().get_params()
    assert params == ['logs', {}]


def test_logs_subscription_includes_address_only() -> None:
    params = EvmNodeLogsSubscription(address=('0xabc',)).get_params()
    assert params == ['logs', {'address': ('0xabc',)}]


def test_logs_subscription_includes_topics() -> None:
    params = EvmNodeLogsSubscription(topics=(('0xtopic',),)).get_params()
    assert params == ['logs', {'topics': (('0xtopic',),)}]


def test_logs_subscription_includes_both_filters() -> None:
    params = EvmNodeLogsSubscription(address=('0xabc',), topics=(('0xtopic',),)).get_params()
    assert params == ['logs', {'address': ('0xabc',), 'topics': (('0xtopic',),)}]
