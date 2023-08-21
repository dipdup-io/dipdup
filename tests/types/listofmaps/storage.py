from pydantic import BaseModel


class ListOfMapsStorage(BaseModel):
    __root__: list[dict[str, str]]
