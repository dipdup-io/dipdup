import importlib
import pkgutil
from os.path import dirname, join
from shutil import rmtree
from unittest import IsolatedAsyncioTestCase

from dipdup import codegen
from dipdup.config import DipDupConfig


# NOTE: https://gist.github.com/breeze1990/0253cb96ce04c00cb7a67feb2221e95e
def import_submodules(package, recursive=True):
    """Import all submodules of a module, recursively, including subpackages
    :param recursive: bool
    :param package: package (name or actual module)
    :type package: str | module
    :rtype: dict[str, types.ModuleType]
    """
    if isinstance(package, str):
        package = importlib.import_module(package)
    results = {}
    for loader, name, is_pkg in pkgutil.walk_packages(package.__path__):
        full_name = package.__name__ + '.' + name
        results[full_name] = importlib.import_module(full_name)
        if recursive and is_pkg:
            results.update(import_submodules(full_name))
    return results


class CodegenTest(IsolatedAsyncioTestCase):
    async def test_codegen(self):
        for name in ['dipdup.yml', 'dipdup-templated.yml']:
            with self.subTest():
                config_path = join(dirname(__file__), name)
                config = DipDupConfig.load(config_path)
                config.package = 'tmp_test_dipdup'

                try:
                    await codegen.create_package(config)
                    await codegen.fetch_schemas(config)
                    await codegen.generate_types(config)
                    await codegen.generate_handlers(config)
                    await codegen.generate_hasura_metadata(config)

                    import_submodules(config.package)

                except Exception as exc:
                    rmtree('tmp_test_dipdup')
                    raise exc
                else:
                    rmtree('tmp_test_dipdup')
