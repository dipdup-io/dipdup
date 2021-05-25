from pydantic import BaseModel


# NOTE: This indexer does not use token storage which may vary from one contract to another (for ex. tzBTC)
class TokenFa2Storage(BaseModel):
    pass
