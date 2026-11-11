from dipdup.report import save_report
from dipdup.sentry import extract_event


def _chained_error_with_tracebackless_cause() -> Exception:
    """Build an exception chain whose innermost cause was never raised, so it has no traceback."""
    try:
        try:
            # NOTE: Constructed, not raised - it has no __traceback__, so Sentry emits no `stacktrace`
            cause = ConnectionResetError(104, 'Connection reset by peer')
            raise ConnectionError('connection was closed in the middle of operation') from cause
        except ConnectionError as e:
            raise RuntimeError('cannot call Transaction.rollback()') from e
    except RuntimeError as e:
        return e


async def test_extract_event_has_tracebackless_value() -> None:
    # NOTE: Guards the precondition - the chain really does yield a value without `stacktrace`
    error = _chained_error_with_tracebackless_cause()
    values = extract_event(error)['exception']['values']
    assert any('stacktrace' not in value for value in values)


async def test_save_report_with_tracebackless_exception() -> None:
    # NOTE: Regression - previously raised `KeyError: 'stacktrace'`
    error = _chained_error_with_tracebackless_cause()
    report_id = save_report('demo', error)

    from dipdup.report import REPORTS_PATH

    path = REPORTS_PATH / f'{report_id}.yaml'
    assert path.exists()
    path.unlink()
