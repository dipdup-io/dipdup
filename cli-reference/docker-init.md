# dipdup docker init

A new command `dipdup docker init` is available to generate a compose-based setup.

```text
dipdup [-c dipdup.yml] docker init [-i dipdup/dipdup] [-t 2.0.0] [-e dipdup.env]
```

The following files will be created:

```text
docker
├── dipdup.env
├── dipdup.env.example
├── docker-compose.yml
└── Dockerfile
```

Environment files are generated using substitution expressions \(`${VARIABLE:-default_value}`\) from DipDup configs provided throught the `dipdup -c` option.  
Now navigate to the created directory, edit the environment file and run the compose project:

```text
cd project/docker
nano dipdup.env
docker-compose up -d
docker-compose logs -f
```

By default, PostgreSQL and Hasura are exposed to localhost only: `5432` and `8080` respectively. Edit `docker-compose.yml` file according to your needs.

Finally, all the demo projects in DipDup have Docker templates generated. In order to spin up a demo run `docker-compose up` in the `<demo_project>/docker` directory.
