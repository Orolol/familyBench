import dataclasses
from typing import List, Optional

@dataclasses.dataclass
class Person:
    id: str
    first_name: str
    gender: str # M ou F
    profession: str
    hair_color: str
    eye_color: str
    hat_color: str
    parent_ids: List[str] = dataclasses.field(default_factory=list)
    children_ids: List[str] = dataclasses.field(default_factory=list)
    generation: int = 0