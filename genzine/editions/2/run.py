from datetime import date
from pathlib import Path

from genzine.chains.editorial import (
    choose_authors,
    choose_illustrator,
    illustrate_article,
    image_to_s3,
    name_zine,
    plan_articles,
    write_article,
)
from genzine.chains.staff import (
    choose_editor,
    create_board,
    create_staff_pool,
    staff_to_s3,
)
from genzine.models.editorial import Article, Zine
from genzine.utils import slugify


def make_zine(edition: int) -> None:
    """Create edition of gen-zine."""
    # Choose a board
    board = create_board()

    # Board creates staff pool
    pool = create_staff_pool(board=board, n=10)

    # Board chooses an editor from staff pool
    editor, pool = choose_editor(board=board, pool=pool)

    # Editor names the zine
    zine_name = name_zine(editor=editor)
    categories = [f'#{edition} {zine_name}']

    # Editor creates article briefs
    article_prompts = plan_articles(editor=editor, zine_name=zine_name)

    # Editor chooses illustrator from staff pool
    illustrator, pool = choose_illustrator(
        editor=editor, pool=pool, zine_name=zine_name, articles=article_prompts
    )

    # Editor chooses writers from staff pool for articles
    assigned_articles = choose_authors(
        editor=editor, pool=pool, zine_name=zine_name, articles=article_prompts
    )

    all_articles: list[Article] = []
    for article_assigned, author in assigned_articles:
        # Writers write articles
        article_written = write_article(
            article=article_assigned, author=author, zine_name=zine_name
        )

        # Illustrator creates images
        article_raw_images = illustrate_article(
            article=article_written, illustrator=illustrator, zine_name=zine_name
        )

        # Save images
        images = [
            image_to_s3(image=image, zine_edition=edition)
            for image in article_raw_images
        ]

        # Create completed article
        article_args = {k: v for k, v in article_written.dict() if k != 'version'}
        article = Article(
            path=Path(slugify(f'{str(date.today())} {zine_name}') + '.md'),
            illustrator=illustrator.short_name,
            images=images,
            categories=categories,
            tags=['featured'],
            version=2,
            **article_args,
        )

        all_articles.append(article)

    # Complete zine
    zine = Zine(
        name=zine_name,
        edition=edition,
        path=Path(slugify(f'{edition} {zine_name}')),
        board=board,
        editor=editor.short_name,
        authors=[staff.short_name for staff in pool],
        illustrators=[illustrator.short_name],
        articles=all_articles,
    )

    # Save zine
    zine.to_posts()

    # Draw editor, illustrator, authors
    all_staff = [staff_to_s3(staff=staff) for staff in [editor, illustrator] + pool]

    # Save editor, illustrator, authors
    for staff in all_staff:
        staff.to_bio_page()


if __name__ == '__main__':
    make_zine(edition=2)
