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
    async def asyncSetUp(self):
        self.config_path = join(dirname(__file__), 'dipdup.yml')
        self.config = DipDupConfig.load(self.config_path)
        self.config.package = 'tmp_test_dipdup'

    async def test_codegen(self):
        try:
            await codegen.create_package(self.config)
            await codegen.fetch_schemas(self.config)
            await codegen.generate_types(self.config)
            await codegen.generate_handlers(self.config)
            await codegen.generate_hasura_metadata(self.config)

            import_submodules(self.config.package)

        except Exception:
            rmtree('tmp_test_dipdup')
            raise
        else:
            rmtree('tmp_test_dipdup')
