from typing import Dict
from typing import List
from typing import Union

from pydantic import BaseModel
from pydantic import Extra


class SaleToken(BaseModel):
    class Config:
        extra = Extra.forbid

    token_for_sale_address: str
    token_for_sale_token_id: str


class Key(BaseModel):
    class Config:
        extra = Extra.forbid

    sale_seller: str
    sale_token: SaleToken


class BazaarMarketPlaceStorageItem(BaseModel):
    class Config:
        extra = Extra.forbid

    key: Key
    value: str


class BazaarMarketPlaceStorage(BaseModel):
    __root__: Union[int, List[BazaarMarketPlaceStorageItem]]
