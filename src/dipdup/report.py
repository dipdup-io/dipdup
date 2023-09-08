import random
from datetime import datetime
from pathlib import Path
from typing import TypedDict

from dipdup.performance import get_stats
from dipdup.performance import metrics
from dipdup.yaml import dump

# FIXME: Hardcoded path
REPORTS_PATH = Path.home() / '.local' / 'share' / 'dipdup' / 'reports'
REPORTS_LIMIT = 100


class ReportHeader(TypedDict):
    id: str
    package: str
    reason: str
    date: str
    content: str


def save_report(package: str, error: Exception | None) -> str:
    """Saves a crashdump file with Sentry error data, returns the path to the tempfile"""

    event, content = {}, []
    if error:
        from dipdup.sentry import extract_event

        event.update(extract_event(error))
        content.append('error')

        # NOTE: Merge pieces of code into a single list
        for exception in event['exception']['values']:
            for frame in exception['stacktrace']['frames']:
                frame['code'] = [*frame.pop('pre_context'), frame.pop('context_line'), *frame.pop('post_context')]

    # NOTE: Performance stats if any
    if metrics:
        event.update(metrics=get_stats())
        content.append('stats')

    # NOTE: Add some metadata
    report_id = ''.join(random.choices('0123456789abcdef', k=10))
    reason = error.__repr__() if error else 'success'
    header = ReportHeader(
        id=report_id,
        package=package,
        reason=reason,
        date=datetime.now().isoformat(),
        content=','.join(content),
    )
    event.update(header)

    crashdump_dir = REPORTS_PATH
    crashdump_dir.mkdir(parents=True, exist_ok=True)
    path = crashdump_dir / f'{report_id}.yaml'

    event_yaml = dump(event)
    path.write_text(event_yaml)
    return report_id


def get_reports() -> list[Path]:
    """Returns a sorted list of crashdump files"""
    report_files = list(REPORTS_PATH.glob('*.yaml'))
    report_files.sort(key=lambda p: p.stat().st_mtime)
    return report_files


def cleanup_reports() -> None:
    """Removes old reports"""
    for path in get_reports()[:-REPORTS_LIMIT]:
        path.unlink()
