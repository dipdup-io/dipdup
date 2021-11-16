from enum import Enum


class CodegenPath(Enum):
    INIT_FILE: str = '__init__.py'
    KEEP_FILE: str = '.keep'
    INTERFACE_TEMPLATE_FILE: str = 'interface.py'
    DOCKER_DIR: str = 'docker'
    GRAPHQL_DIR: str = 'graphql'
    HANDLERS_DIR: str = 'handlers'
    INTERFACES_DIR: str = 'interfaces'
    MODELS_DIR: str = 'models'
    SCHEMAS_DIR: str = 'schemas'
    SQL_DIR: str = 'sql'
    TYPES_DIR: str = 'types'
    PARAMETER_DIR: str = 'parameter'


class OperationType(Enum):
    endorsement: str = 'endorsement'
    ballot: str = 'ballot'
    proposal: str = 'proposal'
    activation: str = 'activation'
    double_baking: str = 'double_baking'
    double_endorsing: str = 'double_endorsing'
    nonce_revelation: str = 'nonce_revelation'
    delegation: str = 'delegation'
    origination: str = 'origination'
    transaction: str = 'transaction'
    reveal: str = 'reveal'
    migration: str = 'migration'
    revelation_penalty: str = 'revelation_penalty'
    baking: str = 'baking'
