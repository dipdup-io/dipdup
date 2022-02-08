# GenQL

[GenQL](https://genql.vercel.app) is a great library and CLI tool that automatically generates a fully typed SDK with a built-in GQL client. It works flawlessly with Hasura and is recommended for DipDup on the client-side.

## Project structure

GenQL CLI generates a ready-to-use package, compiled and prepared to publish to NPM. A typical setup is a mono repository containing several packages, including the auto-generated SDK and your front-end application.

```text
project_root/
├── package.json
└── packages/
    ├── app/
    │   ├── package.json
    │   └── src/
    └── sdk/
        └── package.json
```

## SDK package config

Your minimal _package.json_ file will look like the following:

```typescript
{
  "name": "%PACKAGE_NAME%",
  "version": "0.0.1",
  "main": "dist/index.js",
  "types": "dist/index.d.ts",
  "devDependencies": {
    "@genql/cli": "^2.6.0"
  },
  "dependencies": {
    "@genql/runtime": "2.6.0",
    "graphql": "^15.5.0"
  },
  "scripts": {
    "build": "genql --endpoint %GRAPHQL_ENDPOINT% --output ./dist"
  }
}
```

That's it! Now you only need to install dependencies and execute the build target:

```shell
yarn
yarn build
```

Read more about CLI [options](https://genql.vercel.app/docs/cli/generate) available.

### Demo

Create a `package.json` file with

* `%PACKAGE_NAME%` => `metadata-sdk`
* `%GRAPHQL_ENDPOINT%` => `https://metadata.dipdup.net/v1/graphql`

And generate the client:

```shell
yarn
yarn build
```

Then create new file `index.ts` and paste this query:

```typescript
import { createClient, everything } from './dist'

const client = createClient()

client.chain.query
    .token_metadata({ where: { network: { _eq: 'mainnet' } }})
    .get({ ...everything })
    .then(res => console.log(res))
```

We need some additional dependencies to run our sample:

```shell
yarn add typescript ts-node
```

Finally:

```shell
npx ts-node index.ts
```

You should see a list of tokens with metadata attached in your console.
