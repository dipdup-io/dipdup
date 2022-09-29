import logging
from glob import glob
from os.path import dirname
from os.path import exists
from os.path import isdir
from os.path import join
from types import NoneType
from typing import Any

import asyncclick as cl
import orjson as json
from pydantic import BaseModel
from pydantic import Field

from dipdup.exceptions import ConfigurationError
from dipdup.install import tab
from dipdup.utils import load_template
from dipdup.utils import mkdir_p
from dipdup.utils import write

_logger = logging.getLogger('dipdup.project')


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
            return value  # noqa: R504
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

    def prompt(self) -> bool:
        cl.secho(f'=> {self.description}', fg='blue')
        return super().prompt()


class BooleanQuestion(Question):
    type = bool
    default: bool

    @property
    def text(self) -> str:
        return f'{self.name} [{self.default and "Y/n" or "y/N"}]'

    def prompt(self) -> bool:
        cl.secho(f'=> {self.description}', fg='blue')
        return super().prompt()


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
        cl.secho(f'=> {self.description}', fg='blue')
        for i, choice_pair in enumerate(zip(self.choices, self.comments)):
            choice, comment = choice_pair
            cl.echo(f'  {i}) {tab(choice, 40)}{comment}')
        print()
        value: int = super().prompt()
        return self.choices[value]


class JinjaAnswers(dict):
    def __getattr__(self, item):
        return self[item]


class Project(BaseModel):
    name: str
    path: str
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
        if self.answers:
            raise ConfigurationError('Answers already exist')

        if replay:
            with open(replay, 'rb') as f:
                self.answers = JinjaAnswers(json.loads(f.read()))
            return

        for question in self.questions:
            if quiet:
                value = question.choices[question.default] if isinstance(question, ChoiceQuestion) else question.default
                cl.echo(f'{question.name}: using default value `{value}`')
            else:
                value = question.prompt()

            self.answers[question.name] = value

    def write_cookiecutter_json(self, path: str) -> None:
        with open(path, 'wb') as f:
            f.write(
                json.dumps(
                    {k: v for k, v in self.answers.items() if not k.startswith('_')},
                    option=json.OPT_INDENT_2,
                )
            )

    def _render(self, path: str, output_path: str, force: bool) -> None:
        if exists(output_path) and not force:
            _logger.warning('File `%s` already exists, skipping', output_path)

        _logger.info('Generating `%s`', output_path)
        template = load_template(path)
        content = template.render(cookiecutter=self.answers)
        write(output_path, content, overwrite=force)

    def render(self, force: bool = False) -> None:
        from jinja2 import Template

        base_path = join(dirname(__file__), 'projects')
        project_path = join(base_path, self.path)
        project_paths = glob(
            '**',
            root_dir=project_path,
            recursive=True,
        )
        config_path = join(base_path, self.answers['template'], 'dipdup.yml.j2')

        for path in project_paths:
            output_path = join(self.answers['project_name'], path.replace('.j2', ''))
            output_path = Template(output_path).render(cookiecutter=self.answers)
            mkdir_p(dirname(output_path))
            path = join(project_path, path)

            if isdir(path):
                continue

            self._render(join(project_path, path), output_path, force)

        output_path = join(self.answers['project_name'], 'dipdup.yml')
        self._render(config_path, output_path, force)

    def get_defaults(self) -> dict[str, Any]:
        return {
            question.name: question.choices[question.default] if isinstance(question, ChoiceQuestion) else question.default
            for question in self.questions
        }


class DefaultProject(Project):
    name = 'dipdup'
    path = 'base'
    description = 'Default DipDup project, ex. cookiecutter template'
    questions: tuple[Question, ...] = (
        NotifyQuestion(
            name='_welcome',
            default=None,
            description=(
                'Welcome to DipDup! This command will help you to create a new project.\n'
                'You can abort at any time by pressing Ctrl+C.\n'
                'Let\'s start with some basic questions.  Press Enter to use default value.'
            ),
        ),
        ChoiceQuestion(
            name='template',
            description=('Choose config template depending on the type of your project (DEX, NFT marketplace etc.)\n'),
            default=0,
            choices=(
                'demo_domains',
                'demo_domains_big_map',
                'demo_hic_et_nunc',
                'demo_quipuswap',
                'demo_registrydao',
                'demo_tzbtc',
                'demo_tzbtc_transfers',
                'demo_tzcolors',
            ),
            comments=(
                'Tezos Domains name service',
                'Tezos Domains name service (bag maps only)',
                'hic at nunc NFT marketplace',
                'Quipuswap DEX balances and liquidity',
                'Homebase DAO registry (index factory)',
                'TzBTC FA1.2 token transfers',
                'TzBTC FA1.2 token transfers (transfers only)',
            ),
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
            name='dipdup_version',
            description='Choose DipDup version',
            default=0,
            choices=(
                '6',
                '6.1',
            ),
            comments=(
                'Latest stable release',
                'Latest release of 6.1 branch',
            ),
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
                'Official PostgreSQL',
                'TimescaleDB',
                'TimescaleDB HA (more extensions)',
            ),
        ),
        ChoiceQuestion(
            name='hasura_image',
            description=('Choose Hasura version\n' 'Test new releases before using in production; new versions may break compatibility.'),
            default=0,
            choices=(
                'hasura/graphql-engine:v2.11.2',
                'hasura/graphql-engine:v2.12.0',
                'hasura/graphql-engine:v2.13.0-beta.1',
            ),
            comments=(
                'Recommended',
                '',
                '',
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
        InputQuestion(
            name='line_length',
            description=('Enter maximum line length\n' 'Used by linters.'),
            default='120',
        ),
    )
