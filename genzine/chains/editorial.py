import re

from genzine.chains.staff import make_choose_staff_chain
from genzine.models.editorial import (
    ArticleAssigned,
    ArticlePrompt,
)
from genzine.models.staff import Staff
from genzine.prompts import editorial

from langchain.output_parsers import OutputFixingParser
from langchain_community.chat_models import ChatLiteLLM
from langchain_core.output_parsers import JsonOutputParser, StrOutputParser


def name_zine(editor: Staff) -> str:
    """Generates a name for the zine."""
    model = ChatLiteLLM(model=editor.lang_ai, temperature=1)
    get_name_chain = editorial.zine_name | model | StrOutputParser()

    name = get_name_chain.invoke({'name': editor.name, 'bio': editor.bio})

    return name


def plan_articles(editor: Staff, name: str) -> list[ArticlePrompt]:
    """Generates a list of article prompts based on the name."""
    model = ChatLiteLLM(model=editor.lang_ai, temperature=1)

    # Generate articles
    get_articles_chain = editorial.zine_articles | model | StrOutputParser()

    article_blob = get_articles_chain.invoke(
        {'bio': editor.bio, 'name': editor.name, 'zine_name': name}
    )

    # Break into list and turn into structured format
    article_blog_list = re.split(r'(?=\n\d)', article_blob, flags=0)

    article_parser = JsonOutputParser(pydantic_object=ArticlePrompt)
    fixing_parser = OutputFixingParser.from_llm(parser=article_parser, llm=model)

    article_prompt = editorial.format_article.partial(
        instructions=article_parser.get_format_instructions()
    )

    format_article_chain = article_prompt | model | fixing_parser

    articles_object_list = []
    for article in article_blog_list:
        article_formatted = format_article_chain.invoke({'article': article})
        article_partial = ArticlePrompt(**article_formatted)
        articles_object_list.append(article_partial)

    return articles_object_list


def choose_illustrator(
    editor: Staff, pool: list[Staff], zine_name: str, articles: list[ArticlePrompt]
) -> tuple[Staff, list[Staff]]:
    """Uses the editor, zine name, articles and staff pool to choose an ilustrator.

    Returns the chosen illustrator with the new role, and the staff pool with them
    removed.
    """
    get_illustrator_chain = make_choose_staff_chain(
        ai=editor, pool=pool, prompt=editorial.choose_illustrator
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
    illustrator = choices_dict.get(chosen_illustrator_str)
    illustrator.roles.update(['Illustrator'])

    reduced_pool = [
        staff for staff in pool if staff.short_name != illustrator.short_name
    ]

    return illustrator, reduced_pool


def choose_writers(
    editor: Staff, illustrator: Staff, pool: list[Staff], articles: list[ArticlePrompt]
) -> list[ArticleAssigned]:
    """Uses the editor and staff pool to allocate writers to articles."""
    pass


if __name__ == '__main__':
    editor = Staff.from_bio_page('harper-finch')

    name = name_zine(editor=editor)

    import copy

    pool = [copy.copy(editor) for _ in range(10)]

    print(name)

    article_prompts = plan_articles(editor=editor, name=name)

    print(article_prompts)

    illustrator, pool = choose_illustrator(
        editor=editor, pool=pool, zine_name=name, articles=article_prompts
    )

    print(illustrator)
