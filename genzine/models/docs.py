from typing import Optional, List
from pathlib import Path
from pydantic.v1 import BaseModel, Field


class Image(BaseModel):
    name: str = Field(description="name of the image")
    prompt: str = Field(description="prompt to generate the image")


class Article(BaseModel):
    title: str = Field(description="title of the article")
    filename: Optional[str] = Field(description="article subdirectory")
    prompt: str = Field(
        description="descriptive article summary to prompt the writer"
    )
    text: Optional[str] = Field(
        description="full text of the article in markdown format"
    )
    images: Optional[List[Image]] = Field(
        description="list of images that will go with the article"
    )


class Zine(BaseModel):
    name: str = Field(description="name of the zine")
    editors: List[str] = Field(description="name of editorial AIs")
    writers: List[str] = Field(description="name of writer AIs")
    illustrators: List[str] = Field(description="name of illustrator AIs")
    articles: List[Article] = Field(
        description="a list of articles, their titles, and the writer's prompt"
    )
    asset_dir: Path = Field(description="subdirectory to store images")
