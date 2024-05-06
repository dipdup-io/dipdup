<!-- markdownlint-disable first-line-h1 -->

## Getting started

DipDup works with any EVM-compatible network as long as there are Subsquid and/or archive nodes available! Here's how to get started with your favorite network:

1. Follow the [EVM quickstart](../0.quickstart-evm.md) guide. Choose a template from the "EVM-compatible" section and follow the instructions.
2. Update the `datasources` config section with URLs from the table below. Modify the file or better use environment variables.
3. Update the `contracts` config section. If you want to run the demo project as is, just replace the ERC-20 contract address with the one from your network.

That's it! You can now run the indexer with `dipdup run`.

## Endpoints and status

::banner{type="warning"}
We do not recommend any specific node provider. Providers mentioned below were tested with DipDup on a free tier and listed for informational purposes only.
::
