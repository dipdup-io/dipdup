# Overview

DipDup is a tool that abstracts developer from the indexing and data serving workflow and let him focus on the business logic only. It also applies selective indexing techniques to ensure fast initial sync phase and the most efficient use of public API endpoints.

# Quickstart

## Installing DipDup
## Creating a configuration file
## Initializing project
## Implementing handlers
## Running indexer

# Getting started

## Overview

## Installation
### Requirements

#### Linux
#### Python

### Database backends

This table will help you chose a database backend that suits your needs.

|-|sqlite|postgresql|timescaledb|
|-|--|-|-|
|supported version|||
|when to use|local development|Docker environment, prodection instances|same as pg but timeseries
|performance|average|good|great in some scenarios|
|caveats and limitations|sql hooks immune tables|1,2|incomp,missing methods|

1 see reindexing
2 see hasura limitations



## Installation
### poetry (recommended)
install and configure poetry
add dependency
almost semantic, break queckly
### pip requirements.txt

# Core concepts
## Big picture
## Index

# Preparing inventory
## Contract
## Datasource
## Index
order matters
### operation
### big_map
## Template

# Defining models
# Implementing app logic
## Template
## Handler context

# Client-side
## Hasura integration
## GenQL

# Managing project

## init
## migrate


# Cookbook
## Spawning indexes at runtime
## Processing offchain data
### immune tables

# Advanced
## Performance tuning
### Database, datasources
### logging
### Synchronizing multiple handlers

# Built with DipDup
* hicdex
* homebase
* youves

# Reference
## Config
## Cli

# Thanks