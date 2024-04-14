import re
from pathlib import Path
from typing import List

import requests
from dotenv import find_dotenv, load_dotenv
from openai import OpenAI
from PIL import Image as PILImage

from genzine.models.editorial import Article, Image, Zine
from genzine.prompts.editorial import (
    create_article,
    create_commission,
    format_article,
    zine_articles,
    zine_name,
)
from genzine.utils import h1, h2, to_camelcase

from langchain_core.output_parsers import JsonOutputParser, StrOutputParser
from langchain_openai import ChatOpenAI

load_dotenv(find_dotenv())

client = OpenAI()
model = ChatOpenAI()

article_parser = JsonOutputParser(pydantic_object=Article)
format_article.partial_variables['format_instructions'] = (
    article_parser.get_format_instructions()
)


def name_zine() -> str:
    """Generates a name for the zine."""
    get_name_chain = zine_name | model | StrOutputParser()

    name = get_name_chain.invoke({'input': ''})

    return name


def plan_articles(name: str) -> List[Article]:
    """Generates a list of articles based on the name."""
    get_articles_chain = zine_articles | model | StrOutputParser()

    format_article_chain = format_article | model | article_parser

    article_blob = get_articles_chain.invoke({'zine_name': name})

    article_blog_list = re.split(r'(?=\n\d)', article_blob, flags=0)
    articles_object_list = []

    for article in article_blog_list:
        article_formatted = format_article_chain.invoke({'article': article})
        article_object = Article(**article_formatted)
        article_object.filename = to_camelcase(article_object.title)
        articles_object_list.append(article_object)

    return articles_object_list


def write_article(zine_name: str, article: Article) -> str:
    """Writes an article based on its prompt."""
    write_article_chain = create_article | model | StrOutputParser()

    article_copy = write_article_chain.invoke(
        {'zine_name': zine_name, 'title': article.title, 'prompt': article.prompt}
    )

    return article_copy


def commission_images(zine_name: str, article: Article) -> List[Image]:
    """Generates illustration prompts based on an article."""
    commission_chain = create_commission | model | StrOutputParser()

    image_blob = commission_chain.invoke(
        {'zine_name': zine_name, 'title': article.title, 'text': article.text}
    )

    image_prompt_list = re.split(r'\d. ', image_blob, flags=0)
    image_prompt_list = [
        img.strip() for img in image_prompt_list if len(img.strip()) > 0
    ]

    image_list = []

    for prompt in image_prompt_list:
        image_name = to_camelcase(prompt)[:30] + '.png'
        image_list.append(Image(name=image_name, prompt=prompt))

    return image_list


def generate_images(article: Article, asset_dir: Path) -> None:
    """Generates illustrations based on prompts."""
    article_asset_dir = asset_dir / article.filename
    article_asset_dir.mkdir(parents=True, exist_ok=True)

    for image in article.images:
        response = client.images.generate(
            model='dall-e-3',
            prompt=image.prompt,
            size='1024x1024',
            quality='standard',
            n=1,
        )

        image_url = response.data[0].url
        image_raw = requests.get(image_url).content

        with open(article_asset_dir / image.name, 'wb') as f:
            f.write(image_raw)


def png_to_compressed_jpg(edpath: Path) -> None:
    """Converts an edition's PNGs to compressed JPGs."""

    p = edpath.glob('**/*.png')
    files = [x for x in p if x.is_file()]

    for imgpath in files:
        img = PILImage.open(imgpath)
        rgb_img = img.convert('RGB')
        imgpath_jpg = imgpath.with_suffix('.jpg')
        rgb_img.save(imgpath_jpg, quality=95, optimize=True)
        imgpath.unlink()


def zine_to_markdown(zine: Zine) -> str:
    """Turns a zine into markdown."""
    out = []
    out.append(h1(zine.name))
    out.append(
        f"* Edited by: {', '.join(zine.editors)} \n"
        f"* Written by by: {', '.join(zine.writers)} \n"
        f"* Illustrated by: {', '.join(zine.illustrators)}"
    )

    for article in zine.articles:
        out.append(h2(article.title))
        paras = article.text.split('\n\n')
        for para, image in zip(paras, article.images):
            out.append(para)
            img_rel_path = str(zine.asset_dir / article.filename / image.name)
            out.append(f'![{image.prompt}]({img_rel_path})')

    return '\n\n'.join(out)


if __name__ == '__main__':
    ed_root = Path().cwd() / 'genzine' / 'editions' / '1'

    # Generate the plan #
    # ----------------- #

    # name = name_zine()
    # articles = plan_articles(name=name)

    # zine = Zine(
    #     name=name,
    #     editors=["GPT-3.5 Turbo"],
    #     writers=["GPT-3.5 Turbo"],
    #     illustrators=["DALL-E 3"],
    #     articles=articles,
    #     asset_dir=Path("assets")
    # )

    # with open(ed_root / "zine_plan.json", "w") as f:
    #     f.write(zine.json(indent=2))

    # Add the articles and images prompts #
    # ----------------------------------- #

    # with open(ed_root / "zine_plan.json", "r") as f:
    #     zine = Zine.parse_raw(f.read())

    # articles_full = []

    # for article in zine.articles:
    #     article.text = write_article(zine_name=zine.name, article=article)
    #     article.images = commission_images(zine_name=zine.name, article=article)
    #     articles_full.append(article)

    # zine.articles = articles_full

    # with open(ed_root / "zine_finished.json", "w") as f:
    #     f.write(zine.json(indent=2))

    # Add the images #
    # -------------- #

    # with open(ed_root / "zine_finished.json", "r") as f:
    #     zine = Zine.parse_raw(f.read())

    # for article in zine.articles:
    #     generate_images(article=article, asset_dir=ed_root / zine.asset_dir)

    # Compile to markdown #
    # ------------------- #

    with open(ed_root / 'zine_finished.json', 'r') as f:
        zine = Zine.parse_raw(f.read())

    zinedown = zine_to_markdown(zine=zine)

    with open(ed_root / 'README.md', 'w') as f:
        f.write(zinedown)
