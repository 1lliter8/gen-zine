from enum import Enum
from pathlib import Path

from pydantic.v1 import BaseModel, Field


class RoleEnum(str, Enum):
    author = 'Author'
    illustrator = 'Illustrator'
    editor = 'Editor'


class Staff(BaseModel):
    ai: str = Field(description='the model that plays this staff member')
    role: RoleEnum = Field(description="the staff member's role")
    bio: str = Field(description='a 30-word bio of the third staff member')
    name: str = Field(description="the staff member's name")
    short_name: str = Field(description="the staff member's slugified name")
    avatar: Path = Field(description='file path of the avatar')
