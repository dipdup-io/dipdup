from typing import List

from pydantic import BaseModel
from pydantic import ConfigDict


class SaleToken(BaseModel):
    model_config = ConfigDict(extra='forbid')

    token_for_sale_address: str
    token_for_sale_token_id: str


class Key(BaseModel):
    model_config = ConfigDict(extra='forbid')

    sale_seller: str
    sale_token: SaleToken


class BazaarMarketPlaceStorageItem(BaseModel):
    model_config = ConfigDict(extra='forbid')

    key: Key
    value: str


class BazaarMarketPlaceStorage(BaseModel):
    root: List[BazaarMarketPlaceStorageItem]
