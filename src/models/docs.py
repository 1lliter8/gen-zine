from typing import Optional, List
from pydantic import BaseModel


class Article(BaseModel):
    title: str
    prompt: str
    copy: Optional[str]


class Zine(BaseModel):
    articles: List[Article]
