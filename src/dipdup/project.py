import logging
from pathlib import Path
from types import NoneType
from typing import Any

import asyncclick as cl
import orjson as json
from pydantic import BaseModel
from pydantic import Field
from tabulate import tabulate

from dipdup import major_version
from dipdup.exceptions import ConfigurationError
from dipdup.utils.codegen import load_template
from dipdup.utils.codegen import write

_logger = logging.getLogger('dipdup.project')


# FIXME
DEMO_PROJECTS = (
    ('demo_domains', 'Tezos Domains name service'),
    ('demo_big_maps', 'Indexing a single big map'),
    ('demo_events', 'Processing contract events'),
    ('demo_head', 'Processing head block metadata'),
    ('demo_nft_marketplace', 'hic at nunc NFT marketplace'),
    ('demo_dex', 'Quipuswap DEX balances and liquidity'),
    ('demo_factories', 'Example of spawning indexes in runtime'),
    ('demo_dao', 'Homebase DAO registry'),
    ('demo_token', 'TzBTC FA1.2 token operations'),
    ('demo_token_transfers', 'TzBTC FA1.2 token transfers'),
    ('demo_auction', 'TzColors NFT marketplace'),
    ('blank', 'Empty config for a fresh start'),
    # TODO: demo_jobs
    # TODO: demo_backup
    # TODO: demo_sql
)


class Question(BaseModel):
    type: type = str
    name: str
    description: str
    default: Any

    @property
    def text(self) -> str:
        return f'{self.name} [{self.default}]'

    def prompt(self) -> Any:
        try:
            value = cl.prompt(
                text=self.text,
                default=self.default,
                type=self.type,
                show_default=False,
            )
            print('\n')
            return value
        except cl.Abort:
            cl.echo('\nAborted')
            quit(0)

    class Config:
        frozen = True


class NotifyQuestion(Question):
    type = NoneType

    def prompt(self) -> Any:
        cl.secho('\n' + self.description + '\n', fg='yellow')
        return self.default


class InputQuestion(Question):
    type = str
    default: str

    def prompt(self) -> str:
        cl.secho(f'=> {self.description}', fg='blue')
        return str(super().prompt())


class BooleanQuestion(Question):
    type = bool
    default: bool

    @property
    def text(self) -> str:
        return f'{self.name} [{self.default and "Y/n" or "y/N"}]'

    def prompt(self) -> bool:
        cl.secho(f'=> {self.description}', fg='blue')
        return bool(super().prompt())


class ChoiceQuestion(Question):
    type = int
    default: int
    choices: tuple[str, ...]
    comments: tuple[str, ...]

    @property
    def default_choice(self) -> str:
        return self.choices[self.default]

    @property
    def text(self) -> str:
        return f'{self.name} [{self.default_choice}]'

    def prompt(self) -> str:
        rows = [f'{i})' for i in range(len(self.choices))]
        table = tabulate(
            zip(rows, self.choices, self.comments),
            colalign=('right', 'left', 'left'),
        )
        cl.secho(f'=> {self.description}', fg='blue')
        cl.echo(table)
        return str(self.choices[super().prompt()])


class JinjaAnswers(dict[str, Any]):
    def __init__(self, *args: str, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)
        self['dipdup_version'] = major_version

    def __getattr__(self, item: str) -> Any:
        return self[item]


class Project(BaseModel):
    path: Path
    description: str
    questions: tuple[Question, ...]
    answers: JinjaAnswers = Field(default_factory=JinjaAnswers)

    def verify(self) -> None:
        for question in self.questions:
            if not self.answers.get(question.name):
                raise ConfigurationError(f'Question {question.name} is not answered')

    def reset(self) -> None:
        self.answers = JinjaAnswers()

    def run(self, quiet: bool, replay: str | None) -> None:
        if not self.questions:
            raise ConfigurationError('No questions defined')

        if replay:
            with open(replay, 'rb') as f:
                self.answers = JinjaAnswers(json.loads(f.read()))

        for question in self.questions:
            if question.name in self.answers:
                _logger.info('Skipping question `%s`', question.name)
                continue

            if quiet:
                value = question.choices[question.default] if isinstance(question, ChoiceQuestion) else question.default
                cl.echo(f'{question.name}: using default value `{value}`')
            else:
                value = question.prompt()

            self.answers[question.name] = value

    def write_cookiecutter_json(self, path: Path) -> None:
        values = {k: v for k, v in self.answers.items() if not k.startswith('_')}
        path.write_bytes(
            json.dumps(
                values,
                option=json.OPT_INDENT_2,
            )
        )

    def _render(self, template_path: Path, output_path: Path, force: bool) -> None:
        if output_path.exists() and not force:
            _logger.warning('File `%s` already exists, skipping', output_path)

        _logger.info('Generating `%s`', output_path)
        template = load_template(template_path)
        content = template.render(cookiecutter=self.answers)
        write(output_path, content, overwrite=force)

    def render(self, force: bool = False) -> None:
        from jinja2 import Template

        project_path = Path(__file__).parent / 'projects' / self.path
        project_paths = project_path.glob('**/*.j2')

        for path in project_paths:
            template_path = path.relative_to(Path(__file__).parent)
            output_path = Path(
                self.answers['project_name'],
                *path.relative_to(project_path).parts,
                # NOTE: Remove ".j2" from extension
            ).with_suffix(path.suffix[:-3])
            output_path = Path(Template(str(output_path)).render(cookiecutter=self.answers))
            self._render(template_path, output_path, force)

    def get_defaults(self) -> dict[str, Any]:
        return {
            question.name: question.choices[question.default]
            if isinstance(question, ChoiceQuestion)
            else question.default
            for question in self.questions
        }


class BaseProject(Project):
    path = Path('base')
    description = 'Default DipDup project, ex. cookiecutter template'
    questions: tuple[Question, ...] = (
        NotifyQuestion(
            name='_welcome',
            default=None,
            description=(
                'Welcome to DipDup! This command will help you to create a new project.\n'
                'You can abort at any time by pressing Ctrl+C. Press Enter to use default value.\n'
                "Let's start with some basic questions."
            ),
        ),
        ChoiceQuestion(
            name='template',
            description=('Choose config template depending on the type of your project (DEX, NFT marketplace etc.)\n'),
            default=7,
            choices=tuple(p[0] for p in DEMO_PROJECTS),
            comments=tuple(p[1] for p in DEMO_PROJECTS),
        ),
        InputQuestion(
            name='project_name',
            description='Enter project name',
            default='dipdup-indexer',
        ),
        InputQuestion(
            name='package',
            description='Enter Python package name',
            default='dipdup_indexer',
        ),
        InputQuestion(
            name='version',
            description='Enter project version',
            default='0.0.1',
        ),
        InputQuestion(
            name='description',
            description='Enter project description',
            default='My shiny new indexer based on DipDup',
        ),
        InputQuestion(
            name='license',
            description=('Enter project license\n' 'DipDup itself is MIT-licensed.'),
            default='MIT',
        ),
        InputQuestion(
            name='author',
            description=('Enter project author\n' 'You can add more later in pyproject.toml.'),
            default='John Smith <john_smith@localhost.lan>',
        ),
        NotifyQuestion(
            name='_versions',
            default=None,
            description='Now choose versions of software you want to use.',
        ),
        ChoiceQuestion(
            name='postgresql_image',
            description=('Choose PostgreSQL version\n' 'Try TimescaleDB when working with time series.'),
            default=0,
            choices=(
                'postgres:14',
                'timescale/timescaledb:latest-pg14',
                'timescale/timescaledb-ha:pg14-latest',
            ),
            comments=(
                'PostgreSQL',
                'TimescaleDB',
                'TimescaleDB HA (more extensions)',
            ),
        ),
        ChoiceQuestion(
            name='hasura_image',
            description=(
                'Choose Hasura version\n'
                'Test new releases before using in production; new versions may break compatibility.'
            ),
            default=0,
            choices=(
                'hasura/graphql-engine:v2.15.2',
                'hasura/graphql-engine:v2.15.2',
            ),
            comments=(
                f'tested with DipDup {major_version}',
                'latest',
            ),
        ),
        NotifyQuestion(
            name='_other',
            default=None,
            description='Miscellaneous tunables; leave default values if unsure',
        ),
        BooleanQuestion(
            name='crash_reporting',
            description='Enable crash reporting?\n' 'It helps us a lot to improve DipDup 🙏',
            default=False,
        ),
        ChoiceQuestion(
            name='linters',
            description=(
                'Choose tools to lint and test your code\n' 'You can always add more later in pyproject.toml.'
            ),
            default=0,
            choices=(
                'default',
                'advanced',
                'none',
            ),
            comments=(
                'Classic set: black, isort, flake8, mypy, pytest',
                'Same, plus coverage and more flake8 plugins',
                'None',
            ),
        ),
        InputQuestion(
            name='line_length',
            description=('Enter maximum line length\n' 'Used by linters.'),
            default='120',
        ),
    )

    def render(self, force: bool = False) -> None:
        super().render(force)

        # NOTE: Config and handlers
        Project(
            path=self.answers['template'],
            description='',
            questions=(),
            answers=self.answers,
        ).render(force)

        # NOTE: Linters and stuff
        Project(
            path='linters_' + self.answers['linters'],
            description='',
            questions=(),
            answers=self.answers,
        ).render(force)
