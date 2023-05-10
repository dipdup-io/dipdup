# Glossary

### DipDup Terms

| Term | Definition |
| --- | --- |
| Callback | |
| DipDup | An open source framework for building smart contract indexes for the Tezos network |
| Handler | |
| Hook | |
| Indexer | A program that reads data from a blockchain and stores it in a database for quick and easy querying |
| Model | A Python class representing a database table, defined using the Tortoise ORM library |
| RPC API | RPC stands for Remote Procedure Call. A protocol used to communicate with Tezos nodes and interact with the blockchain. DipDup receives minimal amount of data from RPC API due to slow performance relativly to TzKT and other APIs |
| SDK | A toolkit for developing smart contract indexing applications |
| tortoise | A Python asyncio library for defining models and relationships between tables, simplifying asynchronous database interactions and data management within the DipDup framework |
| TzKT API | A popular Tezos indexer API that provides a more user-friendly way to access Tezos blockchain data compared to the RPC API, often used for building applications on top of Tezos |

### Tezos Terms

| Term | Definition |
| --- | --- |
| big_map | big_map object covered in [big map index page](indexes/tezos_tzkt_big_maps.md) |
| Contract storage | Persistent data storage within a smart contract, holding the contract's state and any associated data |
| Entry points | Functions defined within a smart contract that can be called by external contract invocations or other contracts |
| Origination | The process of deploying a new smart contract on the Tezos network, creating a new originated contract address |

### Infrastructure Terms

| Term | Definition |
| --- | --- |
| Docker | An open-source platform for creating, deploying, and managing containerized applications, improving consistency and reducing infrastructure overhead |
| Docker Compose | A tool for defining and managing multi-container Docker applications, using a YAML file to configure services, networks, and volumes, simplifying application deployment and scaling |
| GraphQL | A query language and runtime for APIs that enables clients to request only the data they need, offering more flexibility and efficiency compared to traditional REST APIs |
| Hasura | An open-source engine that connects to databases and microservices, providing real-time GraphQL APIs for faster and efficient data access |
| PostgreSQL | A powerful, open-source object-relational database system known for its reliability, robustness, and performance, widely used for managing structured data |
| Prometheus | An open-source monitoring and alerting toolkit designed for reliability and scalability, used to collect and process metrics from various systems, providing valuable insights into application and infrastructure performance |
| Sentry | A real-time error tracking and monitoring platform that helps developers identify, diagnose, and fix issues in applications, improving overall software quality and performance |