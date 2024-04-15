import json
import re
from enum import Enum
from html.parser import HTMLParser
from pathlib import Path
from typing import List, Optional

import yaml
from dateutil.parser import ParserError, parse
from pydantic.v1 import BaseModel, Field, HttpUrl, validator

from genzine.models.staff import AIModel, Staff
from genzine.utils import HTML


class TagEnum(str, Enum):
    sticky = 'sticky'
    featured = 'featured'


class ImgParser(HTMLParser):
    def __init__(self):
        super().__init__()
        self.img_src: Optional[str] = None
        self.img_alt: Optional[str] = None

    def handle_starttag(self, tag, attrs):
        if tag == 'img':
            attrs_dict: dict = dict(attrs)
            self.img_src: str = attrs_dict.get('src')
            self.img_alt: str = attrs_dict.get('alt')


class Image(BaseModel):
    file_name: str = Field(description='name of the image with extension')
    prompt: str = Field(description='prompt to generate the image')
    url: HttpUrl = Field(description='url of the image')
    version: int = Field(default=1, description='the version of this model schema')

    @validator('file_name')
    def check_filename(cls, v):
        file = Path(v)
        assert file.suffix.lower() in ('.png', '.jpg', '.jpeg')
        assert len(file.parents) == 1
        return v

    def to_html(self):
        return f'<img src="{self.url}" alt="{self.prompt}" />'

    @classmethod
    def from_html(cls, html: str) -> 'Image':
        parser: HTMLParser = ImgParser()
        parser.feed(html)

        return cls(
            file_name=Path(parser.img_src).name,
            prompt=parser.img_alt,
            url=parser.img_src,
        )


class ArticlePrompt(BaseModel):
    title: str = Field(description='title of the article')
    prompt: str = Field(description='descriptive article summary to prompt the writer')
    version: int = Field(default=1, description='the version of this model schema')


class ArticleAssigned(ArticlePrompt):
    author: str = Field(description='short name of article author')
    version: int = Field(default=1, description='the version of this model schema')


class ArticleWritten(ArticleAssigned):
    text: str = Field(description='full text of the article in markdown format')
    version: int = Field(default=1, description='the version of this model schema')


class Article(ArticleWritten):
    path: Path = Field(
        description='path to the article. Must begin with a date and end with .md'
    )
    illustrator: str = Field(description='short name of article illustrator')
    images: list[Image] = Field(
        description='list of images that will go with the article'
    )
    categories: list[str] = Field(
        description=('categories to use for the article, usually the edition')
    )
    tags: Optional[list[TagEnum]] = Field(
        default=None, description='used to stick or feature an article'
    )
    layout: str = Field(default='post', description='Jekyll layout to use')
    comments: bool = Field(default=False, description='whether comments are turned on')
    version: int = Field(default=2, description='the version of this model schema')

    @validator('path')
    def check_filename(cls, v):
        assert v.suffix.lower() == '.md'
        assert len(v.parents) == 1

        try:
            parse(v.stem[:10])
        except ParserError:
            assert False

        return v

    def to_post(self, path: Path) -> None:
        """Dumps to YAML/markdown appropriate for Jekyll site."""
        posts = HTML / '_posts'
        article_path: Path = posts / path

        with open(article_path / f'{self.path}.md', 'w') as f:
            article_as_dict: dict = json.loads(self.json())
            article_as_dict_no_text: dict = {
                k: v for k, v in article_as_dict.items() if k != 'text'
            }

            f.write('---\n')
            yaml.dump(article_as_dict_no_text, f, allow_unicode=True)
            f.write(f'image: {self.images[0].url}\n')
            f.write('---\n')

            paras: list[str] = self.text.split('\n\n')
            images: list[str] = [
                image.to_html() for image in self.images[1 : len(paras)]
            ]
            mix_div: int = len(paras) // len(images)

            for i, para in enumerate(paras):
                f.write(para)
                f.write('\n\n')
                if i % mix_div == 0 and len(images) > 0:
                    f.write(images.pop(0))
                    f.write('\n\n')

    @classmethod
    def from_post(cls, path: Path) -> 'Article':
        """Builds object from Jekyll site."""
        with open(path, 'r') as f:
            article: dict = next(yaml.safe_load_all(f))
            del article['image']

            f.seek(0)
            # '---' both indicates frontmatter and is a valid way to split markdown
            article_md_raw: str = '---'.join(f.read().split('---')[2:])
            article_md_no_img: str = re.sub(r'<img([\w\W]+?)/>', '', article_md_raw)

            paras: list[str] = article_md_no_img.split('\n')
            article_text: str = '\n\n'.join(
                [para.strip() for para in paras if len(para.strip()) != 0]
            )
            article['text'] = article_text

        return cls(**article)


class Zine(BaseModel):
    name: str = Field(description='name of the zine')
    edition: int = Field(description='the edition number of the zine')
    path: Path = Field(description='slugified zine subdirectory')
    board: List[str] = Field(description="the AIs on the zine's 🧭board")
    editor: str = Field(description='short name of editorial staff')
    authors: List[str] = Field(description='short names of author staff')
    illustrators: List[str] = Field(description='short names of illustrator staff')
    articles: List[Article] = Field(
        description="a list of articles, their titles, and the writer's prompt"
    )
    version: int = Field(default=2, description='the version of this model schema')

    @validator('board')
    def check_ai(cls, v):
        for ai_name in v:
            model = AIModel.from_bio_page(short_name=ai_name)
            if model.ai_type != 'Language':
                raise ValueError('f{model.short_name}: board must be language models')
            return v

    @validator('authors', 'illustrators')
    def check_staff(cls, v):
        for staff_name in v:
            _ = Staff.from_bio_page(short_name=staff_name)
            return v

    @validator('path')
    def check_filename(cls, v):
        assert v.suffix == ''
        assert len(v.parents) == 1
        assert v.stem.split('-')[0].isnumeric()
        return v

    def to_posts(self) -> None:
        """Dumps to YAML/markdown filesystem appropriate for Jekyll site."""
        posts: Path = HTML / '_posts'
        zine_path: Path = posts / self.path
        zine_path.mkdir(exist_ok=True)

        with open(zine_path / f'{self.path}.yaml', 'w') as f:
            zine_as_dict: dict = json.loads(self.json())
            del zine_as_dict['articles']

            yaml.dump(zine_as_dict, f, allow_unicode=True)

        for article in self.articles:
            article.to_post(path=self.path)

    @classmethod
    def from_posts(cls, path: Path) -> 'Zine':
        """Builds object from Jekyll site."""
        posts: Path = HTML / '_posts'
        zine_path: Path = posts / path

        with open(zine_path / f'{path}.yaml', 'r') as f:
            zine: dict = next(yaml.safe_load_all(f))

        article_list: list[Article] = []

        for article_path in zine_path.glob('*.md'):
            article = Article.from_post(zine_path / article_path.name)
            article_list.append(article)

        zine['articles'] = article_list

        return cls(**zine)
