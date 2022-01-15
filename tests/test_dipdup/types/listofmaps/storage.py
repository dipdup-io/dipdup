from typing import Dict
from typing import List
from typing import Union

from pydantic import BaseModel


class ListOfMapsStorage(BaseModel):
    __root__: List[Union[int, Dict[str, str]]]
