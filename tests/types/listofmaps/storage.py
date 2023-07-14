from typing import Dict
from typing import List

from pydantic import BaseModel


class ListOfMapsStorage(BaseModel):
    root: List[Dict[str, str]]
