<!-- markdownlint-disable first-line-h1 -->
And that's all! We can run the indexer now.

## Next steps

Run the indexer in memory:

```shell
dipdup run
```

Store data in SQLite database (defaults to /tmp, set `SQLITE_PATH` env variable):

```shell
dipdup -c . -c configs/dipdup.sqlite.yaml run
```

Or spawn a Compose stack with PostgreSQL and Hasura:

```shell
cd deploy
cp .env.default .env
# Edit .env file before running
docker-compose up
```

DipDup will fetch all the historical data and then switch to realtime updates. You can check the progress in the logs.

If you use SQLite, run this query to check the data:

```bash
sqlite3 /tmp/dipdup_indexer.sqlite 'SELECT * FROM holder LIMIT 10'
```

If you run a Compose stack, open `http://127.0.0.1:8080` in your browser to see the Hasura console (an exposed port may differ). You can use it to explore the database and build GraphQL queries.

Congratulations! You've just created your first DipDup indexer. Proceed to the Getting Started section to learn more about DipDup configuration and features.
