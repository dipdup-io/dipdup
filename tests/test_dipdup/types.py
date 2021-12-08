from typing import List, Union

from pydantic import BaseModel, Extra


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


class BazaarMarketPlaceStorageTest(BaseModel):
    __root__: BazaarMarketPlaceStorage
