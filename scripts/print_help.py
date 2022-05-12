from unittest.mock import MagicMock
import dipdup.exceptions as exc
import dipdup.models as models

example_exceptions = (
    exc.DipDupError(),
    exc.DatasourceError('Everything is broken', 'tzkt_mainnet'),
    exc.ConfigurationError('Invalid config'),
    exc.DatabaseConfigurationError('Invalid model', models.Head),
    exc.MigrationRequiredError('1.1', '1.2'),
    exc.ReindexingRequiredError(
        exc.ReindexingReason.rollback,
        {'foo': 'bar', 'asdf': 'qwer'},
    ),
    exc.InitializationRequiredError('Missing handler'),
    exc.ProjectImportError('demo_tzbtz.handlers.on_mint', 'on_mint'),
    exc.ContractAlreadyExistsError(MagicMock(), 'test', 'tz1deadbeafdeadbeafdeadbeafdeadbeafdeadbeaf'),
    exc.IndexAlreadyExistsError(MagicMock(), 'test'),
    exc.InvalidDataError(models.BigMapData, 'foo', {'foo': 'bar'}),
    exc.CallbackError('demo_tzbtc.handlers.on_mint', ValueError('foo')),
    exc.CallbackTypeError('handler', 'on_mint', 'foo', int, str),
    exc.HasuraError('Invalid query'),
    exc.ConflictingHooksError('on_rollback', 'on_index_rollback')
)

for e in example_exceptions:
    print(f'{e.__class__.__name__}: {e}')
    print()
    print(e.help())
    print(exc._tab)
