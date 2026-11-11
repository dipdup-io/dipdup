from dipdup.config.evm_sqd_portal import EvmPortalDatasourceConfig
from dipdup.datasources._subsquid import _PortalTransport
from dipdup.datasources.evm_subsquid import _AbstractEvmSubsquidDatasource
from dipdup.models.evm_subsquid import Query


class EvmPortalDatasource(
    _AbstractEvmSubsquidDatasource[EvmPortalDatasourceConfig],
    _PortalTransport[EvmPortalDatasourceConfig, Query],
):
    # NOTE: EVM queries built by `iter_events`/`iter_transactions` omit `type`; Portal requires it.
    _portal_dataset_type = 'evm'
