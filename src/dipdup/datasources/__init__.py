from typing import Union
from dipdup.datasources.bcd.datasource import BcdDatasource
from dipdup.datasources.tzkt.datasource import TzktDatasource


IndexName = str
Address = str
Path = str

DatasourceT = Union[TzktDatasource, BcdDatasource]
