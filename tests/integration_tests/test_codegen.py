import pytest

from tests.integration_tests.test_demos import run_dipdup_demo  # type: ignore


@pytest.mark.parametrize(
    'demo',
    (
        'hic_et_nunc',
        'quipuswap',
        'tzcolors',
        'domains_big_map',
        # FIXME:
        # 'registrydao',
    ),
)
async def test_codegen(demo: str) -> None:
    async with run_dipdup_demo(f'{demo}.yml', f'demo_{demo}', 'init'):
        ...
