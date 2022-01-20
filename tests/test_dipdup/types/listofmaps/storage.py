from typing import Dict
from typing import List

from pydantic import BaseModel


class ListOfMapsStorage(BaseModel):
    __root__: List[Dict[str, str]]
