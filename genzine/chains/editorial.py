import copy
import re
from collections import namedtuple

from genzine.chains.staff import make_choose_staff_chain
from genzine.models.editorial import ArticleAssigned, ArticlePrompt, ArticleWritten
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


def plan_articles(editor: Staff, zine_name: str) -> list[ArticlePrompt]:
    """Generates a list of article prompts based on the name."""
    model = ChatLiteLLM(model=editor.lang_ai, temperature=1)

    # Generate articles
    get_articles_chain = editorial.zine_articles | model | StrOutputParser()

    article_blob = get_articles_chain.invoke(
        {'bio': editor.bio, 'name': editor.name, 'zine_name': zine_name}
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

    illustrator = choices_dict.get(chosen_illustrator_str.value)
    illustrator.roles.update(['Illustrator'])

    reduced_pool = [
        staff for staff in pool if staff.short_name != illustrator.short_name
    ]

    return illustrator, reduced_pool


def choose_authors(
    editor: Staff, pool: list[Staff], zine_name: str, articles: list[ArticlePrompt]
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
            ai=editor, pool=author_pool, prompt=editorial.choose_author
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
    model = ChatLiteLLM(model=author.lang_ai, temperature=1)

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


if __name__ == '__main__':
    from genzine.chains.staff import load_all_staff

    pool = load_all_staff(version=2)
    editor = pool.pop(0)
    editor.roles.update(['Editor'])

    zine_name = name_zine(editor=editor)

    print(zine_name)

    article_prompts = plan_articles(editor=editor, zine_name=zine_name)

    illustrator, pool = choose_illustrator(
        editor=editor, pool=pool, zine_name=zine_name, articles=article_prompts
    )

    assigned_articles = choose_authors(
        editor=editor, pool=pool, zine_name=zine_name, articles=article_prompts
    )

    for article_assigned, author in assigned_articles:
        article_written = write_article(
            article=article_assigned, author=author, zine_name=zine_name
        )
        print('\n\n')
        print(article_written)
        print('\n\n')
