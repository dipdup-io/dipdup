import logging
from pathlib import Path
from types import NoneType
from typing import Any

import asyncclick as cl
import orjson as json
from pydantic import BaseModel
from pydantic import Field
from tabulate import tabulate

from dipdup import __version__
from dipdup.exceptions import ConfigurationError
from dipdup.utils import load_template
from dipdup.utils import write

_logger = logging.getLogger('dipdup.project')


DEMO_PROJECTS_TEZOS = (
    ('demo_domains', 'Tezos Domains name service'),
    ('demo_big_maps', 'Indexing specific big maps'),
    ('demo_events', 'Processing contract events'),
    ('demo_head', 'Processing head block metadata'),
    ('demo_nft_marketplace', 'hic at nunc NFT marketplace'),
    ('demo_dex', 'Quipuswap DEX balances and liquidity'),
    ('demo_factories', 'Example of spawning indexes in runtime'),
    ('demo_dao', 'Homebase DAO registry'),
    ('demo_token', 'TzBTC FA1.2 token operations'),
    ('demo_token_transfers', 'TzBTC FA1.2 token transfers'),
    ('demo_auction', 'TzColors NFT marketplace'),
    ('demo_raw', 'Process raw operations without filtering and strict typing (experimental)'),
    # TODO: demo_jobs
    # TODO: demo_backup
    # TODO: demo_sql
)
DEMO_PROJECTS_EVM = ()


# ask user smth with typecast to type, print_default=True print to user what default choise would be used
def prompt(text: str, default: Any, type_: type, print_default: bool = True) -> Any:
    try:
        value = cl.prompt(
            text=f'{text} [{default}]: ' if print_default else text,
            default=default,
            type=type_,
            show_default=False,
        )
        print('\n')
        return value
    except cl.Abort:
        cl.echo('\nAborted')
        quit(0)

# ask user to choose one option with question, list of options and there description(comments)
def choose_one(question: str, options: tuple[str, ...], comments: tuple[str, ...], default: int):  # default is position of default option in options
    table = tabulate(
        zip(range(len(options)), options, comments),
        colalign=('right', 'left', 'left'),
    )
    cl.secho(f'=> {question}', fg='blue')
    cl.echo(table)

    answer = prompt('Please choose an option', default, type_=int)
    return options[answer]

# script running on dipdup new command and will create a new project from console survey
def create_new_project_from_console():
    # dict with all new project config
    answers = {'dipdup_version': __version__.split('.')[0]}

    welcome_text = (
        'Welcome to DipDup! This command will help you to create a new project.\n'
        'You can abort at any time by pressing Ctrl+C. Press Enter to use default value.\n'
        "Let's start with some basic questions."
    )
    cl.secho('\n' + welcome_text + '\n', fg='yellow')


    # Choose new project template
    template_types = ('Tezos', 'EVM', 'Blank')
    template_types_desc = ('Tezos templates', 'EVM templates', 'Brief template to create project from scratch')
    template_type = choose_one('Choose a template: blockchain-specific or blank?', template_types, template_types_desc, default=3)
    
    # list of options can contain folder name of template or folder name of template with description
    # all project templates are in src/dipdup/projects
    template_types_dict = {
        'Tezos': DEMO_PROJECTS_TEZOS,
        'EVM': DEMO_PROJECTS_EVM,
        'Blank': 'blank',
    }
    DEMO_PROJECTS_BLANK = 'Blank'
    if template_type == DEMO_PROJECTS_BLANK:
        answers['template'] = template_types_dict[DEMO_PROJECTS_BLANK]
    else:
        options = tuple(x[0] for x in template_types_dict[template_type])  # FIXME zero EVM templates
        comments = tuple(x[1] for x in template_types_dict[template_type])
        answers['template'] = choose_one('Choose config template depending on the type of your project (DEX, NFT marketplace etc.)\n', options, comments, default=0)

    name_description = 'Enter project name (the name will be used for folder name and package name)'
    name_default = 'dipdup_indexer'
    cl.secho(f'=> {name_description} [{name_default}]', fg='blue')
    answers['project_name'] = prompt('', name_default, str, print_default=False)  # FIXME validate python package name

    version_default = '0.0.1'
    cl.secho(f'=> Enter project version [{version_default}]', fg='blue')
    answers['project_name'] = prompt('', name_default, str, print_default=False)


def write_cookiecutter_json(answers: dict[str, Any], path: Path) -> None:
    values = {k: v for k, v in answers.items() if not k.startswith('_')}
    path.write_bytes(
        json.dumps(
            values,
            option=json.OPT_INDENT_2,
        )
    )


class Question(BaseModel):
    type: type = str
    name: str
    description: str
    default: Any

    @property
    def text(self) -> str:
        return f'{self.name} [{self.default}]'

    def prompt(self, text: str | None = None, default: str | None = None) -> Any:
        try:
            value = cl.prompt(
                text=text or self.text,
                default=default or self.default,
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

    def prompt(self, text: str | None = None, default: str | None = None) -> Any:
        cl.secho('\n' + self.description + '\n', fg='yellow')
        return self.default


class InputQuestion(Question):
    type = str
    default: str

    def prompt(self, text: str | None = None, default: str | None = None) -> str:
        cl.secho(f'=> {self.description}', fg='blue')
        return str(super().prompt())


class BooleanQuestion(Question):
    type = bool
    default: bool

    @property
    def text(self) -> str:
        return f'{self.name} [{self.default and "Y/n" or "y/N"}]'

    def prompt(self, text: str | None = None, default: str | None = None) -> bool:
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

    def prompt(self, text: str | None = None, default: str | None = None) -> str:
        rows = [f'{i})' for i in range(len(self.choices))]
        table = tabulate(
            zip(rows, self.choices, self.comments),
            colalign=('right', 'left', 'left'),
        )
        cl.secho(f'=> {self.description}', fg='blue')
        cl.echo(table)
        return str(self.choices[super().prompt()])


class ConditionalChoiceQuestion(Question):
    type = int
    default: int
    choices: dict[str, tuple[tuple[str, str], ...]]  # condition -> tuple[choise, comment]

    condition_default: int
    condition_description: str
    condition_choices: tuple[tuple[str, str], ...]

    @property
    def default_choice(self) -> str:
        return self.choices[self.condition_choices[self.condition_default][0]][self.default][0]

    def prompt(self, text: str | None = None, default: str | None = None) -> str:
        condition_question = ChoiceQuestion(
            name='template',
            description=self.condition_description,
            default=self.condition_default,
            choices=tuple(c[0] for c in self.condition_choices),
            comments=tuple(c[1] for c in self.condition_choices),
        )
        condition = condition_question.prompt()  # string choise of condition

        # if condition question is enough
        if not self.choices[condition]:
            return condition
        if len(self.choices[condition]) == 1:
            return self.choices[condition][0][0]

        # choise inside condition
        table = tabulate(
            zip(
                (f'{x})' for x in range(len(self.choices[condition]))),
                (x[0] for x in self.choices[condition]),
                (x[1] for x in self.choices[condition]),
            ),
            colalign=('right', 'left', 'left'),
        )
        cl.secho(f'=> {self.description}', fg='blue')
        cl.echo(table)
        default = self.choices[condition][self.default][0]
        answer = super().prompt(text=f'{self.name} [{default}]', default=default)
        return str(self.choices[condition][answer][0])


class JinjaAnswers(dict[str, Any]):
    def __init__(self, *args: str, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)
        self['dipdup_version'] = __version__.split('.')[0]

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
                value = (
                    question.default_choice
                    if isinstance(question, ChoiceQuestion) or isinstance(question, ConditionalChoiceQuestion)
                    else question.default
                )
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
        template = load_template(str(template_path))
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
    # FIXME: Replace defaults with fields
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
        ConditionalChoiceQuestion(
            name='template',
            condition_description=('Choose a template: blockchain-specific or blank?'),
            description=('Choose config template depending on the type of your project (DEX, NFT marketplace etc.)\n'),
            condition_default=2,
            default=0,
            condition_choices=(
                ('Tezos', 'Tezos templates'),
                ('EVM', 'EVM templates'),
                ('Blank', 'Brief template to create project from scratch'),
            ),
            choices={
                'Tezos': DEMO_PROJECTS_TEZOS,
                'EVM': DEMO_PROJECTS_EVM,
                'Blank': (('blank', ''), ),
            },
        ),
        InputQuestion(
            name='project_name',
            description='Enter project name (the name will be used for folder name and package name)',
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
                'postgres:15',
                'timescale/timescaledb:latest-pg15',
                'timescale/timescaledb-ha:pg15-latest',
                'sqlite',
            ),
            comments=(
                'PostgreSQL',
                'TimescaleDB',
                'TimescaleDB HA (more extensions)',
                'Sqlite (simplified in-memory configuration)',
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
                'hasura/graphql-engine:v2.23.0',
                'hasura/graphql-engine:v2.23.0',
            ),
            comments=(
                'stable',
                'beta',
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
                'none',
            ),
            comments=(
                'Classic set: black, isort, ruff, mypy, pytest',
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

    def run(self, *args: Any, **kwargs: Any) -> None:
        super().run(*args, **kwargs)
        self.answers['package'] = self.answers['project_name']
