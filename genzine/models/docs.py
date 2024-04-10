from pathlib import Path
from typing import List, Optional

from pydantic.v1 import BaseModel, Field, HttpUrl, validator

from genzine.models.staff import AIModel, Staff


class Image(BaseModel):
    file_name: str = Field(description='name of the image with extension')
    prompt: str = Field(description='prompt to generate the image')
    url: HttpUrl = Field(description='url of the image')

    @validator('file_name')
    def check_filename(cls, v):
        file = Path(v)
        assert file.suffix.lower() in ('.png', '.jpg', '.jpeg')
        assert len(file.parents) == 1
        return v


class Article(BaseModel):
    title: str = Field(description='title of the article')
    path: Optional[Path] = Field(description='path to the article')
    prompt: str = Field(description='descriptive article summary to prompt the writer')
    text: Optional[str] = Field(
        description='full text of the article in markdown format'
    )
    images: Optional[List[Image]] = Field(
        description='list of images that will go with the article'
    )
    author: str = Field(description='short name of article author')
    illustrator: str = Field(description='short name of article illustrator')


class Zine(BaseModel):
    name: str = Field(description='name of the zine')
    path: Path = Field(description='zine subdirectory')
    board: List[str] = Field(description="the AIs on the zine's 🧭board")
    editor: str = Field(description='short name of editorial staff')
    authors: List[str] = Field(description='short names of author staff')
    illustrators: List[str] = Field(description='short names of illustrator staff')
    articles: List[Article] = Field(
        description="a list of articles, their titles, and the writer's prompt"
    )

    @validator('board')
    def check_ai(cls, v):
        for ai_name in v:
            model = AIModel.from_bio_page(short_name=ai_name)
            if model.model_type != 'Language':
                raise ValueError('f{model.short_name}: board must be language models')
            return v

    @validator('authors', 'illustrators')
    def check_staff(cls, v):
        for staff_name in v:
            _ = Staff.from_bio_page(short_name=staff_name)
            return v
