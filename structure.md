<!-- TOC -->
- [Installing DipDup](#installing-dipdup)
- [Creating a configuration file](#creating-a-configuration-file)
- [Initializing project](#initializing-project)
- [Implementing handlers](#implementing-handlers)
- [Running indexer](#running-indexer)
- [Overview](#overview)
- [Installation](#installation)
    - [Requirements](#requirements)
        - [Linux](#linux)
        - [Python](#python)
    - [Database backends](#database-backends)
- [Installation](#installation)
    - [poetry (recommended)](#poetry-recommended)
    - [pip requirements.txt](#pip-requirementstxt)
- [Big picture](#big-picture)
- [Index](#index)
- [Datasources](#datasources)
- [Contracts](#contracts)
- [Indexes](#indexes)
    - [operation](#operation)
    - [big_map](#big_map)
- [Template](#template)
- [Template](#template)
- [Handler context](#handler-context)
- [Hasura integration](#hasura-integration)
- [GenQL](#genql)
- [init](#init)
- [migrate](#migrate)
- [Spawning indexes at runtime](#spawning-indexes-at-runtime)
- [Processing offchain data](#processing-offchain-data)
    - [immune tables](#immune-tables)
- [Performance tuning](#performance-tuning)
    - [Database, datasources](#database-datasources)
    - [logging](#logging)
    - [Synchronizing multiple handlers](#synchronizing-multiple-handlers)
- [Config](#config)
- [Cli](#cli)
<!-- /TOC -->


# Overview


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
### Atomicity and persistency

# Preparing inventory
## Datasources
## Contracts
## Indexes
order matters


### operation
### big_map
### head

## Template

# Defining models

# Implementing app logic
## Template
## Handler context

# Client-side
## Hasura integration
## GenQL

# Deployment
## Docker

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