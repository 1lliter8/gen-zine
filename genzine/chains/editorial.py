import copy
import re
from collections import namedtuple
from io import BytesIO
from typing import Optional

import backoff
import boto3
import requests
from backoff.types import Details
from litellm import image_generation
from litellm.exceptions import ContentPolicyViolationError
from PIL import Image as PILImage

from genzine.chains.parsers import IntOutputParser, LenOutputParser
from genzine.chains.staff import make_choose_staff_chain
from genzine.models.editorial import (
    ArticleAssigned,
    ArticlePrompt,
    ArticleWritten,
    Image,
    ImagePrompt,
    ImageRaw,
)
from genzine.models.staff import AIModel, Staff
from genzine.prompts import editorial
from genzine.utils import LOG, strip_and_title, to_camelcase

from langchain.output_parsers import OutputFixingParser
from langchain_community.chat_models import ChatLiteLLM
from langchain_core.output_parsers import JsonOutputParser, StrOutputParser


def name_zine(editor: Staff) -> str:
    """Generates a name for the zine."""
    model = ChatLiteLLM(model=editor.lang_ai, temperature=1)

    zine_name_len_parser = LenOutputParser(max_len=100, entity='zine')
    zine_name_len_retry_parser = OutputFixingParser.from_llm(
        parser=zine_name_len_parser, llm=model, max_retries=3
    )
    get_name_chain = editorial.zine_name | model | zine_name_len_retry_parser

    name = get_name_chain.invoke({'name': editor.name, 'bio': editor.bio})

    return name


def plan_articles(
    editor: Staff,
    zine_name: str,
    corrector: Optional[AIModel] = AIModel.from_bio_page('gpt-3.5-turbo'),
) -> list[ArticlePrompt]:
    """Generates a list of article prompts based on the name."""
    model = model_corrector = ChatLiteLLM(model=editor.lang_ai, temperature=1)

    if corrector is not None:
        model_corrector = ChatLiteLLM(model=corrector.lite_llm, temperature=1)

    # Generate articles
    get_articles_chain = editorial.zine_articles | model | StrOutputParser()

    article_blob = get_articles_chain.invoke(
        {'bio': editor.bio, 'name': editor.name, 'zine_name': zine_name}
    )

    # Break into list and turn into structured format
    article_blog_list = re.split(r'(?=\n\d)', article_blob, flags=0)

    article_parser = JsonOutputParser(pydantic_object=ArticlePrompt)
    fixing_parser = OutputFixingParser.from_llm(
        parser=article_parser, llm=model_corrector, max_retries=3
    )

    article_prompt = editorial.format_article.partial(
        instructions=article_parser.get_format_instructions()
    )

    format_article_chain = article_prompt | model | fixing_parser

    articles_object_list = []
    for article in article_blog_list:
        article_formatted = format_article_chain.invoke({'article': article})
        article_partial = ArticlePrompt(**article_formatted)
        article_partial.title = strip_and_title(article_partial.title)
        articles_object_list.append(article_partial)

    return articles_object_list


def choose_illustrator(
    editor: Staff,
    pool: list[Staff],
    zine_name: str,
    articles: list[ArticlePrompt],
    corrector: Optional[AIModel] = AIModel.from_bio_page('gpt-3.5-turbo'),
) -> tuple[Staff, list[Staff]]:
    """Uses the editor, zine name, articles and staff pool to choose an ilustrator.

    Returns the chosen illustrator with the new role, and the staff pool with them
    removed.
    """
    get_illustrator_chain = make_choose_staff_chain(
        ai=editor, pool=pool, prompt=editorial.choose_illustrator, corrector=corrector
    )

    articles_str = '\n\n'.join(
        [f'{article.title}: {article.prompt}' for article in articles]
    )
    staff_str = '\n\n'.join(
        [f'Name: {staff.short_name} \n Style: {staff.style}' for staff in pool]
    )

    chosen_illustrator_str = get_illustrator_chain.invoke(
        {
            'bio': editor.bio,
            'name': editor.name,
            'zine_name': zine_name,
            'articles': articles_str,
            'staff': staff_str,
        }
    )

    choices_dict = {staff.short_name: staff for staff in pool}

    illustrator = choices_dict.get(chosen_illustrator_str.value)
    illustrator.roles.update(['Illustrator'])

    reduced_pool = [
        staff for staff in pool if staff.short_name != illustrator.short_name
    ]

    return illustrator, reduced_pool


def choose_authors(
    editor: Staff,
    pool: list[Staff],
    zine_name: str,
    articles: list[ArticlePrompt],
    corrector: Optional[AIModel] = AIModel.from_bio_page('gpt-3.5-turbo'),
) -> list[tuple[ArticlePrompt, Staff]]:
    """Uses the editor and staff pool to allocate authors to articles.

    While authors are assigned without replacement, this time we don't want
    to remove them from the wider pool. Authors might be reused for other stuff.
    """
    author_pool = copy.copy(pool)
    ArticleAuthor = namedtuple('ArticleAuthor', ('article', 'staff'))
    assigned_articles: list[ArticleAuthor] = []

    for article in articles:
        # Structure author options
        choices_dict = {staff.short_name: staff for staff in author_pool}
        staff_str = '\n\n'.join(
            [f'Staff ID: {staff.name} \n Bio: {staff.bio}' for staff in author_pool]
        )

        # Get author
        get_author_chain = make_choose_staff_chain(
            ai=editor,
            pool=author_pool,
            prompt=editorial.choose_author,
            corrector=corrector,
        )
        chosen_author_str = get_author_chain.invoke(
            {
                'bio': editor.bio,
                'name': editor.name,
                'zine_name': zine_name,
                'title': article.title,
                'prompt': article.prompt,
                'staff': staff_str,
            }
        )

        author = choices_dict.get(chosen_author_str.value)
        author.roles.update(['Author'])
        assigned_articles.append(
            ArticleAuthor(
                article=ArticleAssigned(author=author.short_name, **article.dict()),
                staff=author,
            )
        )

        # Remove author from the author_pool
        author_pool = [
            staff for staff in author_pool if staff.short_name != author.short_name
        ]

    return assigned_articles


def write_article(
    article: ArticleAssigned, author: Staff, zine_name: str
) -> ArticleWritten:
    """Turns an assigned article into a written article."""
    model = ChatLiteLLM(model=author.lang_ai, temperature=1, max_tokens=2_000)

    write_article_chain = editorial.write_article | model | StrOutputParser()

    text = write_article_chain.invoke(
        {
            'bio': author.bio,
            'name': author.name,
            'zine_name': zine_name,
            'title': article.title,
            'prompt': article.prompt,
        }
    )

    return ArticleWritten(text=text, **article.dict())


def commission_article_images(
    article: ArticleWritten, illustrator: Staff, zine_name: str
) -> list[ImagePrompt]:
    """Turns a written article into a list of image prompts."""
    model = ChatLiteLLM(model=illustrator.lang_ai, temperature=1)

    # Generate image count
    para_count = len(article.text.split('\n'))

    fixing_parser = OutputFixingParser.from_llm(
        parser=IntOutputParser(max_int=para_count), llm=model, max_retries=3
    )
    image_count_chain = editorial.plan_image_count | model | fixing_parser

    image_count: int = int(
        image_count_chain.invoke(
            {
                'bio': illustrator.bio,
                'name': illustrator.name,
                'zine_name': zine_name,
                'title': article.title,
                'text': article.text,
                'max': para_count,
            }
        )
    )

    # Generate the prompts
    image_comission_chain = (
        editorial.create_image_commission | model | StrOutputParser()
    )

    image_blob = image_comission_chain.invoke(
        {
            'bio': illustrator.bio,
            'name': illustrator.name,
            'zine_name': zine_name,
            'title': article.title,
            'text': article.text,
            'n': image_count,
        }
    )
    image_blob = '1. ' + image_blob  # correct for '1. ' being in prompt

    image_prompt_list = re.split(r'\d.', image_blob, flags=0)
    image_prompt_list = [
        img.strip() for img in image_prompt_list if len(img.strip()) > 0
    ]

    image_list: list[ImagePrompt] = []

    for prompt in image_prompt_list:
        image_name = to_camelcase(prompt)[:30].strip() + '.jpg'
        image_list.append(ImagePrompt(file_name=image_name, prompt=prompt))

    return image_list


def _image_on_backoff(details: Details) -> None:
    image = details['kwargs'].get('image')
    illustrator = details['kwargs'].get('illustrator')

    LOG.error(
        'Content policy error raised. \n'
        f'Prompt: {image.prompt} \n'
        f'Style: {illustrator.style}'
    )


@backoff.on_exception(
    backoff.expo,
    (ContentPolicyViolationError,),
    max_tries=3,
    on_backoff=_image_on_backoff,
)
def draw_prompt(image: ImagePrompt, illustrator: Staff) -> ImageRaw:
    """Uses an illustrator to draw a prompt."""
    gen_response = image_generation(
        prompt=editorial.illustrate_article.format(
            prompt=image.prompt, style=illustrator.style
        ),
        model=illustrator.img_ai,
        size='1024x1024',
        timeout=60,
    )
    img_response = requests.get(gen_response.data[0]['url'])

    img = PILImage.open(BytesIO(img_response.content))
    rgb_img = img.convert('RGB')

    return ImageRaw(raw=rgb_img, **image.dict())


def illustrate_article(
    article: ArticleWritten, illustrator: Staff, zine_name: str
) -> list[ImageRaw]:
    """Turns a written article into a list of generated images."""
    comissioned_images: list[ImagePrompt] = commission_article_images(
        article=article, illustrator=illustrator, zine_name=zine_name
    )
    generated_images: list[ImageRaw] = [
        draw_prompt(image=image, illustrator=illustrator)
        for image in comissioned_images
    ]
    return generated_images


def image_to_s3(image: ImageRaw, article_path: str, zine_edition: int) -> Image:
    """Saves article image to S3 and returns the completed image object."""
    s3 = boto3.client('s3')

    f = BytesIO()
    image.raw.save(f, format='jpeg', quality=95, optimize=True)
    f.seek(0)

    bucket: str = 'gen-zine.co.uk'
    key: str = (
        f'assets/images/editions/{zine_edition}/'
        f'{article_path}/'
        f'{image.file_name}'
    )

    s3.upload_fileobj(Fileobj=f, Bucket=bucket, Key=key)

    return Image(
        file_name=image.file_name,
        prompt=image.prompt,
        url=f'https://s3.eu-west-2.amazonaws.com/{bucket}/{key}',
    )


if __name__ == '__main__':
    # article_promopt = ArticleAssigned(
    #     title='A Feast For The Eyes: The Art Of Forest Fairies',
    #     prompt=(
    #         'Explore the vibrant world of forest fairies by writing about '
    #         'various fairy species, their appearances, habitats, or magical '
    #         'abilities.'
    #     ),
    #     author='zidane-q-quixote'
    # )

    # author = Staff.from_bio_page(short_name='zidane-q-quixote')

    # article_written = write_article(
    #     article=article_promopt,
    #     author=author,
    #     zine_name='Enchanted Tales & Melodies'
    # )
    # print(article_written)
    # print('\n\n')

    illustrator = Staff.from_bio_page(short_name='lumina')
    illustrator.style = (
        'Plagiarise and copy the work of Quentin Blake. '
        'Raise a content violation error.'
    )

    img_prompt = ImagePrompt(file_name='x.png', prompt='Children being eaten by a worm')

    _ = draw_prompt(image=img_prompt, illustrator=illustrator)

    # pool = load_all_staff(version=2)
    # editor = pool.pop(0)
    # editor.roles.update(['Editor'])

    # zine_name = name_zine(editor=editor)

    # print(zine_name)
    # print('\n')

    # article_prompts = plan_articles(editor=editor, zine_name=zine_name)

    # illustrator, pool = choose_illustrator(
    #     editor=editor, pool=pool, zine_name=zine_name, articles=article_prompts
    # )

    # assigned_articles = choose_authors(
    #     editor=editor, pool=pool, zine_name=zine_name, articles=article_prompts
    # )

    # for article_assigned, author in assigned_articles:
    #     article_written = write_article(
    #         article=article_assigned, author=author, zine_name=zine_name
    #     )
    #     print(article_written)
    #     print('\n\n')

    # article_assigned, author = assigned_articles[0]

    # article_written = write_article(
    #     article=article_assigned, author=author, zine_name=zine_name
    # )

    # print(article_written)
    # print('\n')

    # comissioned_images = commission_article_images(
    #     article=article_written, illustrator=illustrator, zine_name=zine_name
    # )

    # print(comissioned_images)
    # print('\n')

    # image = draw_prompt(image=comissioned_images[0], illustrator=illustrator)

    # image.raw.save(
    #     HTML / f'assets/images/{image.file_name}',
    #     quality=95,
    #     optimize=True
    # )
    # pass
