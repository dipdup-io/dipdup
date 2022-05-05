# DipDup contribution guide

> 🚧 **UNDER CONSTRUCTION**
>
> This page or paragraph is yet to be written. Come back later.

## Preparation

* To set up the development environment, you need to install [Poetry](https://python-poetry.org/docs/#installation) package manager and GNU Make.
* Run `make help` to get available commands.

## Git

* Branch names MUST follow `prefix/short-descriptions` format. Prefixes we currently use: `feat` for features, `fix` for bugfixes, `docs` for documentation, `aux` for miscelanous, `exp` for experiments.

## Codestyle

* We use the following combo of linters and formatters: `isort`, `black`, `flake8`, `mypy`. All linter checks MUST pass before merging code to master.

## Releases

* Release versions SHOULD conform to [Semantic Versioning](https://semver.org/). Releases that introduce breaking changes MUST be major ones.
* Only the latest major version is supported in general. Critical fixes COULD be backported to the previous major release.

## Documentation

* All changes that affect user experience MUST be documented in CHANGELOG.md file.
* Changelog formatting SHOULD stick to GitLab changelog [guidelines](https://docs.gitlab.com/ee/development/changelog.html).