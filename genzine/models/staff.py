import datetime
import json
from enum import Enum
from pathlib import Path
from typing import Optional

import yaml
from pydantic.v1 import BaseModel, Field, HttpUrl, validator

from genzine.utils import HTML


class ModelTypeEnum(str, Enum):
    image = 'Image'
    language = 'Language'


class RoleEnum(str, Enum):
    author = 'Author'
    illustrator = 'Illustrator'
    editor = 'Editor'


class AIModel(BaseModel):
    short_name: str = Field(
        description="the model's slugified name, appropriate for LiteLLM"
    )
    name: str = Field(description="the model's name")
    site: HttpUrl = Field(description="URL of the model's site")
    ai_type: ModelTypeEnum = Field(description='the type of this model')
    description: str = Field(
        description="a brief description of this model's provenance"
    )
    avatar: Optional[Path] = Field(
        default=None, description="file path of the AI's avatar"
    )
    retired: Optional[datetime.date] = Field(
        description='the date the model was retired'
    )

    def to_bio_page(self) -> None:
        """Dumps to YAML appropriate for Jekyll site."""
        with open(HTML / f'_ai/{self.short_name}.md', 'w') as f:
            ai_as_dict: dict = json.loads(self.json())

            f.write('---\n')
            yaml.dump(ai_as_dict, f, allow_unicode=True)
            f.write('---')

    @classmethod
    def from_bio_page(cls, short_name: str) -> 'AIModel':
        """Builds object from Jekyll site."""
        with open(HTML / f'_ai/{short_name}.md', 'r') as f:
            ai: dict = next(yaml.safe_load_all(f))

        return cls(**ai)


class Staff(BaseModel):
    short_name: str = Field(description="the staff member's slugified name")
    name: str = Field(description="the staff member's name")
    roles: list[RoleEnum] = Field(description='roles the staff member has played')
    avatar: Optional[HttpUrl] = Field(
        default=None, description="URL of the staff member's avatar"
    )
    lang_ai: str = Field(
        description='the short name of the language model that plays this staff member'
    )
    img_ai: str = Field(
        description='the short name of the image model that plays this staff member'
    )
    bio: str = Field(description='a 30-word bio of the staff member')
    style: str = Field(
        description="a 30-word descripion of the staff member's illustration style"
    )

    @validator('lang_ai')
    def lang_ai_must_be_language_model(cls, v):
        model = AIModel.from_bio_page(short_name=v)
        if model.ai_type != 'Language':
            raise ValueError('lang_ai must be a language model')
        return v

    @validator('img_ai')
    def img_ai_must_be_language_model(cls, v):
        model = AIModel.from_bio_page(short_name=v)
        if model.ai_type != 'Image':
            raise ValueError('img_ai must be an image model')
        return v

    def to_bio_page(self) -> None:
        """Dumps to YAML appropriate for Jekyll site."""
        with open(HTML / f'_staff/{self.short_name}.md', 'w') as f:
            staff_as_dict: dict = json.loads(self.json())

            f.write('---\n')
            yaml.dump(staff_as_dict, f, allow_unicode=True)
            f.write('---')

    @classmethod
    def from_bio_page(cls, short_name: str) -> 'Staff':
        """Builds object from Jekyll site."""
        with open(HTML / f'_staff/{short_name}.md', 'r') as f:
            staff: dict = next(yaml.safe_load_all(f))

        return cls(**staff)
