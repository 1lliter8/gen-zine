import random
from datetime import date
from enum import Enum
from pathlib import Path
from typing import Any, Callable, Optional

import pytest
from faker import Faker

import genzine.models.editorial
import genzine.models.staff
from genzine.models.editorial import Article, Image, TagEnum, Zine
from genzine.models.staff import AIModel, ModelTypeEnum, RoleEnum, Staff
from genzine.utils import slugify

fake = Faker()


def random_enum(enum: Enum) -> Any:
    """Returns a random item from an Enum class."""
    enum_values = [e.value for e in ModelTypeEnum]
    return random.choice(enum_values)


def random_enums(enum: Enum, min: int = 1) -> list[Any]:
    """Returns a random number of random items from an Enum class.

    Without replacement.
    """
    enum_values = [e.value for e in enum]
    return random.sample(enum_values, k=fake.random_int(max=len(enum), min=min))


@pytest.fixture(scope='function')
def genzine_fs(fs, monkeypatch):
    mock_html: Path = Path('/html')
    fs.create_dir(mock_html / '_ai')
    fs.create_dir(mock_html / '_staff')
    fs.create_dir(mock_html / '_posts')

    monkeypatch.setattr(genzine.models.staff, 'HTML', mock_html)
    monkeypatch.setattr(genzine.models.editorial, 'HTML', mock_html)

    yield fs, monkeypatch


@pytest.fixture(scope='function')
def ai_factory(genzine_fs) -> Callable:
    def _ai_factory(
        retired: bool = False,
        ai_type: Optional[ModelTypeEnum] = None,
    ) -> AIModel:
        name: str = ' '.join(fake.words(nb=3, part_of_speech='noun')).title()

        retired_date = None
        if retired:
            retired_date: date = fake.date_object()

        if ai_type is None:
            ai_type: str = random_enum(ModelTypeEnum)

        return AIModel(
            short_name=slugify(name),
            prefix=fake.word(),
            name=name,
            site=fake.url(),
            ai_type=ai_type,
            description=fake.sentence(nb_words=10),
            avatar=Path(
                '/assets/images/avatars/ai/' + fake.file_name(category='image')
            ),
            retired=retired_date,
        )

    return _ai_factory


@pytest.fixture(scope='function')
def staff_factory(genzine_fs, ai_factory):
    def _staff_factory(
        roles: Optional[list[RoleEnum]] = None,
        lang_ai: Optional[AIModel] = None,
        img_ai: Optional[AIModel] = None,
    ) -> Staff:
        name: str = fake.name()

        if lang_ai is None:
            lang_ai: AIModel = ai_factory(ai_type='Language')
            lang_ai.to_bio_page()

        if img_ai is None:
            img_ai: AIModel = ai_factory(ai_type='Image')
            img_ai.to_bio_page()

        if roles is None:
            roles: list[str] = random_enums(RoleEnum)

        return Staff(
            short_name=slugify(name),
            name=name,
            roles=roles,
            avatar=f"{fake.url()}{fake.uri_path()}/{fake.file_name(category='image')}",
            lang_ai=lang_ai.short_name,
            img_ai=img_ai.short_name,
            bio=fake.sentence(nb_words=10),
            style=fake.sentence(nb_words=10),
        )

    return _staff_factory


@pytest.fixture(scope='function')
def image_factory(genzine_fs):
    def _image_factory() -> Image:
        name: str = fake.file_name(extension='jpg')

        return Image(
            file_name=name,
            prompt=fake.sentence(nb_words=10),
            url=fake.url() + fake.uri_path() + '/' + name,
        )

    return _image_factory


@pytest.fixture(scope='function')
def article_factory(genzine_fs, image_factory, staff_factory):
    def _article_factory(
        author: Optional[Staff] = None,
        illustrator: Optional[Staff] = None,
        categories: Optional[list[str]] = None,
    ) -> Article:
        image_count: int = fake.random_int(max=5, min=2)
        name: str = fake.sentence(nb_words=10).title()[:-1]
        path = Path(slugify(f'{str(date.today())} {name}') + '.md')

        if author is None:
            author: Staff = staff_factory(roles=['Author'])
            author.to_bio_page()

        if illustrator is None:
            illustrator: Staff = staff_factory(roles=['Illustrator'])
            illustrator.to_bio_page()

        if categories is None:
            edition_name: str = ' '.join(fake.words(nb=5)).title()
            edition_number: int = fake.random_int(min=1, max=10)
            category: str = f'#{edition_number} {edition_name}'
            categories: list[str] = [category]

        return Article(
            title=name,
            path=path,
            prompt=fake.sentence(nb_words=10),
            text='\n\n'.join(fake.paragraphs(nb=5)),
            images=[image_factory() for _ in range(image_count)],
            author=author.short_name,
            illustrator=illustrator.short_name,
            categories=categories,
            tags=random_enums(enum=TagEnum, min=0),
        )

    return _article_factory


@pytest.fixture(scope='function')
def zine_factory(genzine_fs, article_factory, ai_factory, staff_factory):
    def _zine_factory() -> Zine:
        mock_html: Path = Path('/html')
        mock_posts: Path = mock_html / '_posts'

        name: str = ' '.join(fake.words(nb=5)).title()
        edition: int = len(list(mock_posts.glob('*/'))) + 1
        path: Path = Path(slugify(f'{edition} {name}'))
        category: str = f'#{edition} {name}'

        img_ais: list[AIModel] = [
            ai_factory(ai_type='Image') for ai in range(fake.random_int(max=3, min=1))
        ]
        lang_ais: list[AIModel] = [
            ai_factory(ai_type='Language')
            for ai in range(fake.random_int(max=3, min=1))
        ]

        for ai in img_ais + lang_ais:
            ai.to_bio_page()

        staff_list: list[Staff] = [
            staff_factory(
                roles=['Author', 'Editor', 'Illustrator'],
                lang_ai=random.choice(lang_ais),
                img_ai=random.choice(img_ais),
            )
            for _ in range(10)
        ]

        for staff in staff_list:
            staff.to_bio_page()

        editor: Staff = staff_list[0]
        authors: list[Staff] = staff_list[1:7]
        illustrators: list[Staff] = staff_list[7:10]

        article_list: list[Article] = [
            article_factory(
                author=random.choice(authors),
                illustrator=random.choice(illustrators),
                categories=[category],
            )
            for _ in range(5)
        ]

        board_names: list[str] = [ai.short_name for ai in lang_ais]
        editor_name: str = editor.short_name
        author_names: list[str] = [author.short_name for author in authors]
        illustrator_names: list[str] = [illus.short_name for illus in illustrators]

        return Zine(
            name=name,
            edition=edition,
            path=path,
            board=board_names,
            editor=editor_name,
            authors=author_names,
            illustrators=illustrator_names,
            articles=article_list,
        )

    return _zine_factory
