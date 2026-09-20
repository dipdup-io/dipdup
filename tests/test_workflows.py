from typing import Any
from typing import cast

from ruamel.yaml import YAML

from tests import REPO_ROOT

WORKFLOWS = REPO_ROOT / '.github' / 'workflows'


def _load(name: str) -> dict[str, Any]:
    return cast('dict[str, Any]', YAML(typ='safe').load((WORKFLOWS / name).read_text()))


def test_pull_requests_are_checked() -> None:
    # NOTE: `push` events of a fork PR fire in the fork, so without this trigger such PRs get no checks at all.
    assert 'pull_request' in _load('test.yml')['on']


def test_container_tests_have_a_runner() -> None:
    # NOTE: macOS runners have no Docker daemon; without a Linux one the container tests are silently skipped.
    matrix = _load('test.yml')['jobs']['test']['strategy']['matrix']['include']
    assert any(entry['os'].startswith('ubuntu') for entry in matrix)
