from pathlib import Path

from genzine.models.editorial import Article, Image, Zine
from genzine.models.staff import AIModel, Staff


def test_create_load_ai(ai_factory):
    test_ai_1: AIModel = ai_factory()

    test_ai_1.to_bio_page()

    assert Path(f'/html/_ai/{test_ai_1.short_name}.md').exists()

    test_ai_2: AIModel = AIModel.from_bio_page(test_ai_1.short_name)

    assert test_ai_1 == test_ai_2


def test_create_load_staff(staff_factory):
    test_staff_1: Staff = staff_factory()

    test_staff_1.to_bio_page()

    assert Path(f'/html/_staff/{test_staff_1.short_name}.md').exists()

    test_staff_2: Staff = Staff.from_bio_page(test_staff_1.short_name)

    assert test_staff_1 == test_staff_2


def test_image(image_factory):
    test_image_1: Image = image_factory()
    test_image_str: str = test_image_1.to_html()
    test_image_2: Image = Image.from_html(html=test_image_str)

    assert test_image_1 == test_image_2


def test_create_load_article(article_factory):
    test_article_1: Article = article_factory()

    posts: Path = Path('/html/_posts/')
    article_subdir: Path = Path('foo')
    long_dir: Path = posts / article_subdir
    long_dir.mkdir(exist_ok=True)

    test_article_1.to_post(path=article_subdir)

    assert (long_dir / f'{test_article_1.path}.md').exists()

    test_article_2: Article = Article.from_post(
        path=long_dir / f'{test_article_1.path}.md'
    )

    assert test_article_1 == test_article_2


def test_create_load_zine(zine_factory):
    test_zine_1: Zine = zine_factory()

    test_zine_1.to_posts()

    assert (Path('/html/_posts/') / test_zine_1.path).exists()

    test_zine_2: Zine = Zine.from_posts(path=test_zine_1.path)

    for z1, z2 in zip(test_zine_1.__dict__.items(), test_zine_2.__dict__.items()):
        assert z1 == z2

    assert test_zine_1 == test_zine_2
