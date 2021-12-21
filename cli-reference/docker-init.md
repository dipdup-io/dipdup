# docker init

Generate a generic docker-compose deployment inside of the project package.

```text
dipdup docker init [-i dipdup/dipdup] [-t 4.0.0] [-e dipdup.env]
```

This command will create the following files:

```text
docker
├── dipdup.env
├── dipdup.env.example
├── docker-compose.yml
└── Dockerfile
```

Environment files are generated using substitution expressions (`${VARIABLE:-default_value}`).

To deploy created stack, navigate to the created directory, edit the environment file and run `docker-compose up`:

```text
cd <package>/docker
nano dipdup.env
docker-compose up -d
docker-compose logs -f
```

By default, PostgreSQL and Hasura are exposed to localhost only: `5432` and `8080` ports, respectively. Edit `docker-compose.yml` file according to your needs.

All demo projects in the DipDup git repository already have docker-compose templates generated. To spin up a demo run `docker-compose up` in the `src/<package>/docker` directory. See [Demo projects](../examples/demo-projects.md) for details.
