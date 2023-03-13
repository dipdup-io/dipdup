from dipdup.cli import cli
from dipdup.exception_writer import invoke_excepthook

if __name__ == '__main__':
    invoke_excepthook()
    cli(prog_name='dipdup', standalone_mode=False)
