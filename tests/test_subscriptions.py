from dipdup.subscriptions.evm_node import EvmNodeLogsSubscription


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
