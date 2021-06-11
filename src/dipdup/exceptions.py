class ConfigurationError(Exception):
    """DipDup YAML config is incorrect"""

    ...


class HandlerImportError(Exception):
    """Something's wrong with imports in handler, migration may help"""
