import logging

from dipdup.cli import cli
from dipdup.exceptions import DipDupError

if __name__ == '__main__':
    try:
        cli(_anyio_backend='asyncio')
    except KeyboardInterrupt:
        pass
    except DipDupError as e:
        logging.critical(e.__repr__())
        logging.info(e.format())
        quit(e.exit_code)
