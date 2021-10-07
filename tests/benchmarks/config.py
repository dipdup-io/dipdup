import operator
import sys
from contextlib import suppress
from os.path import dirname, join
from shutil import rmtree
from unittest import IsolatedAsyncioTestCase

from dipdup import __version__
from dipdup.config import DipDupConfig
from dipdup.dipdup import DipDup
import timeit

import pyperf

def add_cmdline_args(cmd, args):
    cmd += ['--quiet']

runner = pyperf.Runner(add_cmdline_args=add_cmdline_args)


paths = [join(dirname(__file__), '..', 'integration_tests', name) for name in [
    'hic_et_nunc.yml',
    'quipuswap.yml',
    'tzcolors.yml',
    'tezos_domains_big_map.yml',
    'registrydao.yml',
]]


def _load_config():
    for path in paths:
        for _ in range(20):
            DipDupConfig.load([path]).initialize(skip_imports=False)

runner.bench_func('config_load_initialize_import', _load_config)
