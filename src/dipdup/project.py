import logging
from glob import glob
from os.path import dirname
from os.path import exists
from os.path import join
from typing import Any

import orjson as json
from asyncclick import Choice
from asyncclick import echo
from asyncclick import prompt
from genericpath import isdir
from pydantic import BaseModel
from pydantic import Field

from dipdup.exceptions import ConfigurationError
from dipdup.utils import load_template
from dipdup.utils import mkdir_p
from dipdup.utils import write

_logger = logging.getLogger('dipdup.project')


class Question(BaseModel):
    name: str
    description: str
    default: Any

    def prompt(self) -> Any:
        echo(self.description)
        return prompt(self.name, default=self.default)

    class Config:
        frozen = True


class BooleanQuestion(Question):
    default: bool

    def prompt(self) -> bool:
        print(self.description)
        return prompt(self.name, default=self.default, type=bool)


class ChoiceQuestion(Question):
    default: str
    choices: tuple[str, ...]

    def prompt(self) -> str:
        print(self.description)
        return prompt(self.name, default=self.default, type=Choice(self.choices))


class InputQuestion(Question):
    default: str

    def prompt(self) -> str:
        print(self.description)
        return prompt(self.name, default=self.default)


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

    def prompt(self, quiet: bool) -> None:
        if not self.questions:
            raise ConfigurationError('No questions to prompt')
        if self.answers:
            raise ConfigurationError('Answers already exist')
        for question in self.questions:
            self.answers[question.name] = question.default if quiet else question.prompt()

    def write_cookiecutter_json(self, path: str) -> None:
        with open(path, 'wb') as f:
            f.write(json.dumps(self.answers, option=json.OPT_INDENT_2))

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
        InputQuestion(
            name='project_name',
            description='Project name',
            default='dipdup-indexer',
        ),
        InputQuestion(
            name='package',
            description='Package name',
            default='dipdup_indexer',
        ),
        InputQuestion(
            name='version',
            description='Project version',
            default='0.0.1',
        ),
        InputQuestion(
            name='description',
            description='Project description',
            default='My shiny new indexer based on DipDup',
        ),
        InputQuestion(
            name='license',
            description='License',
            default='MIT',
        ),
        InputQuestion(
            name='author',
            description='Author',
            default='John Smith <john_smith@localhost.lan>',
        ),
        ChoiceQuestion(
            name='dipdup_version',
            description='DipDup version',
            default='6',
            choices=(
                '6',
                '6.1',
            ),
        ),
        ChoiceQuestion(
            name='postgresql_version',
            description='PostgreSQL version',
            default='postgres:14',
            choices=(
                'postgres:14',
                'postgres:13',
                'timescale/timescaledb:latest-pg14',
                'timescale/timescaledb:latest-pg13',
            ),
        ),
        ChoiceQuestion(
            name='hasura_version',
            description='Hasura version',
            default='hasura/graphql-engine:v2.11.2',
            choices=(
                'hasura/graphql-engine:v2.11.2',
                'hasura/graphql-engine:v2.10.1',
            ),
        ),
        InputQuestion(
            name='line_length',
            description='Line length',
            default='140',
        ),
    )
