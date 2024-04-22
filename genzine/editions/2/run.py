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
from genzine.utils import LOG, slugify


def make_zine(edition: int) -> None:
    """Create edition of gen-zine."""
    # Choose a board
    board = create_board()
    LOG.info(
        f'Board of {len(board)} AIs created: '
        f'{', '.join([ai.lite_llm for ai in board])}'
    )

    # Board creates staff pool
    pool = create_staff_pool(board=board, n=10)
    LOG.info(f'Pool of {len(pool)} staff created')

    # Board chooses an editor from staff pool
    editor, pool = choose_editor(board=board, pool=pool)
    LOG.info(f'{editor.name} chosen as editor')

    # Editor names the zine
    zine_name = name_zine(editor=editor)
    categories = [f'#{edition} {zine_name}']
    LOG.info(f'Editor named the zine: {zine_name}')

    # Editor creates article briefs
    article_prompts = plan_articles(editor=editor, zine_name=zine_name)
    LOG.info(f'{len(article_prompts)} articles planned')

    # Editor chooses illustrator from staff pool
    illustrator, pool = choose_illustrator(
        editor=editor, pool=pool, zine_name=zine_name, articles=article_prompts
    )
    LOG.info(f'{illustrator.name} chosen as illustrator')

    # Editor chooses writers from staff pool for articles
    assigned_articles = choose_authors(
        editor=editor, pool=pool, zine_name=zine_name, articles=article_prompts
    )
    LOG.info(f'{len(assigned_articles)} articles assigned to writers')

    all_articles: list[Article] = []
    for article_assigned, author in assigned_articles:
        # Writers write articles
        article_written = write_article(
            article=article_assigned, author=author, zine_name=zine_name
        )
        LOG.info(f'Article written: {article_written.title}')

        # Illustrator creates images
        article_raw_images = illustrate_article(
            article=article_written, illustrator=illustrator, zine_name=zine_name
        )
        LOG.info(
            f'Article illustrated with {len(article_raw_images)} images: '
            f'{article_written.title}'
        )

        # Save images
        images = [
            image_to_s3(image=image, zine_edition=edition)
            for image in article_raw_images
        ]
        LOG.info(f'Article images saved: {article_written.title}')

        # Create completed article
        article_args = {
            k: v for k, v in article_written.dict().items() if k != 'version'
        }
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

    LOG.info(f'{len(all_articles)} articles completed')

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

    LOG.info(f'Zine saved: {zine_name}')

    # Draw editor, illustrator, authors
    all_staff = [staff_to_s3(staff=staff) for staff in [editor, illustrator] + pool]

    LOG.info(f'{len(all_staff)} staff saved to S3')

    # Save editor, illustrator, authors
    for staff in all_staff:
        staff.to_bio_page()

    LOG.info(f'{len(all_staff)} staff bios saved to site')

    LOG.info('Zine COMPLETE!')


if __name__ == '__main__':
    make_zine(edition=2)
