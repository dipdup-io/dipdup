# from dipdup.config import DatasourceConfig

# class GraphQLDatasourceConfig(DatasourceConfig):
#     url: str  # Add other configuration attributes as needed

# src/dipdup/config/graphql.py
# src/dipdup/config/graphql.py
from dipdup.config import DatasourceConfig
from dipdup.config import HttpConfig  # Make sure to import HttpConfig if used

# class GraphQLDatasourceConfig(DatasourceConfig):
#     def __init__(self, url: str, kind: str = "graphql", http: HttpConfig = None):
#         super().__init__(kind=kind, url=url, http=http)
#         self.url = url  # URL of the GraphQL endpoint
#         # Additional parameters if needed
#         self.timeout: int = 30  # Default timeout
#         self.headers: dict = {}  # Optional headers
#         self.retries: int = 3  # Default retries
# s: int = 3  # Default number of retries
class GraphQLDatasourceConfig(DatasourceConfig):
    def __init__(self, url: str, kind: str = "graphql", http: HttpConfig = None, auth_token: str = None):
        super().__init__(kind=kind, url=url, http=http)
        self.url = url
        self.timeout: int = 30
        self.headers: dict = {} if not auth_token else {'Authorization': f'Bearer {auth_token}'}
        self.retries: int = 3
        self.ssl_verify: bool = True  # Optional SSL verification

