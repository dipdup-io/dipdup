from typing import Union

from dipdup.datasources.bcd.datasource import BcdDatasource
from dipdup.datasources.tzkt.datasource import TzktDatasource

DatasourceT = Union[TzktDatasource, BcdDatasource]
