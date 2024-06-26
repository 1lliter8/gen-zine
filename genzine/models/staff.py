import datetime
import json
import re
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
    prefix: str = Field(
        default='',
        description=(
            'the model prefix, typically used by LiteLLm for different AI ' 'providers'
        ),
    )
    lite_llm: Optional[str] = Field(
        default=None,
        description='identified for LiteLLM. Composite of prefix/short_name',
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
    version: int = Field(default=1, description='the version of this model schema')

    @validator('lite_llm', always=True)
    def composite_name(cls, v, values, **kwargs):
        if values['prefix'] == '':
            return f"{values['short_name']}"
        else:
            return f"{values['prefix']}/{values['short_name']}"

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
    roles: Optional[set[RoleEnum]] = Field(
        default=set(), description='roles the staff member has played'
    )
    avatar: Optional[HttpUrl] = Field(
        default=None, description="URL of the staff member's avatar"
    )
    board_ai: str = Field(description='the board member that created this staff member')
    lang_ai: str = Field(
        description=(
            'the lite_llm name of the language model that plays this staff member'
        )
    )
    img_ai: str = Field(
        description='the lite_llm name of the image model that plays this staff member'
    )
    bio: str = Field(description='a 30-word bio of the staff member')
    style: str = Field(
        description="a 30-word descripion of the staff member's illustration style"
    )
    version: int = Field(default=2, description='the version of this model schema')

    @validator('lang_ai', 'board_ai')
    def lang_ai_must_be_language_model(cls, v):
        short_name = re.search(r'[^/]*$', v)[0]
        model = AIModel.from_bio_page(short_name=short_name)
        if model.ai_type != 'Language':
            raise ValueError('lang_ai and board_ai must be a language model')
        return v

    @validator('img_ai')
    def img_ai_must_be_language_model(cls, v):
        short_name = re.search(r'[^/]*$', v)[0]
        model = AIModel.from_bio_page(short_name=short_name)
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
