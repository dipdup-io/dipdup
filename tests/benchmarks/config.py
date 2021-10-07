from os.path import dirname, join

import pyperf  # type: ignore

from dipdup.config import DipDupConfig


def add_cmdline_args(cmd, args):
    cmd += ['--quiet']


runner = pyperf.Runner(add_cmdline_args=add_cmdline_args)


paths = [
    join(dirname(__file__), '..', 'integration_tests', name)
    for name in [
        'hic_et_nunc.yml',
        'quipuswap.yml',
        'tzcolors.yml',
        'tezos_domains_big_map.yml',
        'registrydao.yml',
    ]
]


def _load_config():
    for path in paths:
        for _ in range(20):
            config = DipDupConfig.load([path])
            config.initialize()
            for index_config in config.indexes.values():
                index_config.hash()


runner.bench_func('config_load_initialize_import', _load_config)
