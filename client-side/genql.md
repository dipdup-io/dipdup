# GenQL

[GenQL](https://genql.vercel.app/) is a fantastic library and CLI tool allowing to automatically generate a fully typed SDK with a builtin GQL client. It works flawlessly with Hasura and is currently a recommended way to use DipDup on the client side.

## Project structure

GenQL CLI generates a ready-to-use package, already compiled and prepared to be published to NPM. A typical setup is a mono repository containing several packages including the auto-generated SDK and your front-end application.

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
    "build": "genql --esm --endpoint %GRAPHQL_ENDPOINT% --output ./dist"
  }
}

```

That's it! Now you only need to install dependencies and execute the build target:

```bash
yarn
yarn build
```

