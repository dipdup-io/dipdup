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
from dipdup.utils import load_template
from dipdup.utils import mkdir_p
from dipdup.utils import write

_logger = logging.getLogger('dipdup.project')


class Question(BaseModel):
    type: type = str
    name: str
    description: str
    default: Any

    def prompt(self) -> Any:
        try:
            if self.type == bool:
                text = f"{self.name} [{'Y/n' if self.default else 'y/N'}]"
                show_default = False
            else:
                text = self.name
                show_default = True
            return cl.prompt(
                text=text,
                default=self.default,
                type=self.type,
                show_default=show_default,
            )

        except cl.Abort:
            _logger.info('Aborted')
            exit(0)

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

    def prompt(self) -> bool:
        cl.secho(f'=> {self.description}', fg='blue')
        return super().prompt()


class ChoiceQuestion(Question):
    type = int
    default: int
    choices: tuple[str, ...]

    @property
    def default_choice(self) -> str:
        return self.choices[self.default]

    def prompt(self) -> str:
        cl.secho(f'=> {self.description}', fg='blue')
        for i, choice in enumerate(self.choices):
            cl.echo(f'  {i}) {choice}')
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

    def run(self, quiet: bool) -> None:
        if not self.questions:
            raise ConfigurationError('No questions defined')
        if self.answers:
            raise ConfigurationError('Answers already exist')

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

    def render(self) -> None:
        from jinja2 import Template

        for path in glob(join(self.path, '**'), recursive=True):
            if isdir(path):
                continue

            relative_path = path.replace(self.path, '').lstrip('/')
            output_path = join(self.answers['project_name'], relative_path).replace('.j2', '')
            output_path = Template(output_path).render(cookiecutter=self.answers)
            mkdir_p(dirname(output_path))
            if exists(output_path):
                _logger.warning('File `%s` already exists, skipping', output_path)
                continue

            _logger.info('Generating `%s`', output_path)
            template = load_template(path.replace('.j2', ''))
            content = template.render(cookiecutter=self.answers)
            write(output_path, content)


class DefaultProject(Project):
    name = 'dipdup'
    path = join(dirname(__file__), 'templates', 'project')
    description = 'Default DipDup project, ex. cookiecutter template'
    questions: tuple[Question, ...] = (
        NotifyQuestion(
            name='_welcome',
            default=None,
            description=(
                'Welcome to DipDup! This script will help you to create a new project.\n'
                'You can abort at any time by pressing Ctrl+C.\n'
                'Let\'s start with some basic questions.'
            ),
        ),
        InputQuestion(
            name='project_name',
            description='Project name:',
            default='dipdup-indexer',
        ),
        InputQuestion(
            name='package',
            description='Python package name:',
            default='dipdup_indexer',
        ),
        InputQuestion(
            name='version',
            description='Project version:',
            default='0.0.1',
        ),
        InputQuestion(
            name='description',
            description='Project description:',
            default='My shiny new indexer based on DipDup',
        ),
        InputQuestion(
            name='license',
            description=('Project license:\n' 'DipDup itself is MIT-licensed.'),
            default='MIT',
        ),
        InputQuestion(
            name='author',
            description=('Project author:\n' 'You can add more later.'),
            default='John Smith <john_smith@localhost.lan>',
        ),
        NotifyQuestion(
            name='_versions',
            default=None,
            description='Now choose versions of software you want to use.',
        ),
        ChoiceQuestion(
            name='dipdup_version',
            description='DipDup version:',
            default=0,
            choices=(
                '6',
                '6.1',
            ),
        ),
        ChoiceQuestion(
            name='postgresql_version',
            description=('PostgreSQL version:\n' 'Try TimescaleDB when working with time series.'),
            default=0,
            choices=(
                'postgres:14',
                'postgres:13',
                'timescale/timescaledb:latest-pg14',
                'timescale/timescaledb:latest-pg13',
            ),
        ),
        ChoiceQuestion(
            name='hasura_version',
            description=(
                'Hasura version:\n' 'Test new releases before using in production; breaking changes are possible between minor versions.'
            ),
            default=0,
            choices=(
                'hasura/graphql-engine:v2.11.2',
                'hasura/graphql-engine:v2.10.1',
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
            # FIXME: I really-really want it to be opt-out :/
            default=True,
        ),
        InputQuestion(
            name='line_length',
            description=('Maximum line length:\n' 'Used by linters.'),
            default='140',
        ),
    )
