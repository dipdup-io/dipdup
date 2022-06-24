from unittest.mock import MagicMock
import dipdup.exceptions as exc
import dipdup.models as models

example_exceptions = (
    exc.DipDupError(),
    exc.DatasourceError('[error_message]', '[datasource_name]'),
    exc.ConfigurationError('[error_message]'),
    exc.DatabaseConfigurationError('[error_message]', models.Model),
    exc.ReindexingRequiredError(
        exc.ReindexingReason.manual,
        {'[context_key]': '[context_value]'},
    ),
    exc.InitializationRequiredError('[error_message]'),
    exc.ProjectImportError('[module_qualname]', '[name]'),
    exc.ContractAlreadyExistsError(MagicMock(), '[name]', 'tz1deadbeafdeadbeafdeadbeafdeadbeafdeadbeaf'),
    exc.IndexAlreadyExistsError(MagicMock(), '[index_name]'),
    exc.InvalidDataError(type, '[path]', {'[key]': '[value]'}),
    exc.CallbackError('[callback_qualname]', Exception()),
    exc.CallbackTypeError('[kind]', '[name]', '[arg]', type, type),
    exc.HasuraError('[error_message]'),
    exc.ConflictingHooksError('[old_hook]', '[new_hook]'),
)

print('# Common issues')
for e in example_exceptions:
    print(f'## {e.__class__.__name__}')
    print()
    print(f'### {e}')
    print()
    print(e.help())
    print()
