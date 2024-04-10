import random
from enum import Enum
from pathlib import Path
from typing import Any, Callable, Optional

import pytest
from faker import Faker

import genzine.models.staff
from genzine.models.docs import Article, Image, Zine
from genzine.models.staff import AIModel, ModelTypeEnum, RoleEnum, Staff
from genzine.utils import slugify

fake = Faker()


def random_enum(enum: Enum) -> Any:
    """Returns a random item from an Enum class."""
    enum_values = [e.value for e in ModelTypeEnum]
    return random.choice(enum_values)


def random_enums(enum: Enum) -> list[Any]:
    """Returns a random number of random items from an Enum class.

    Without replacement.
    """
    enum_values = [e.value for e in enum]
    return random.sample(enum_values, k=fake.random_int(max=len(enum), min=1))


@pytest.fixture(scope='function')
def genzine_fs(fs, monkeypatch):
    mock_html = Path('/html')
    fs.create_dir(mock_html / '_ai')
    fs.create_dir(mock_html / '_staff')

    monkeypatch.setattr(genzine.models.staff, 'HTML', mock_html)

    yield fs, monkeypatch


@pytest.fixture(scope='function')
def ai_factory(genzine_fs) -> Callable:
    def _ai_factory(
        retired: bool = False,
        model_type: Optional[ModelTypeEnum] = None,
    ) -> AIModel:
        name = ' '.join(fake.words(nb=3, part_of_speech='noun')).title()

        retired_date = None
        if retired:
            retired_date = fake.date_object()

        if model_type is None:
            model_type = random_enum(ModelTypeEnum)

        return AIModel(
            short_name=slugify(name),
            name=name,
            site=fake.url(),
            model_type=model_type,
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
        name = fake.name()

        if lang_ai is None:
            lang_ai = ai_factory(model_type='Language')
            lang_ai.to_bio_page()

        if img_ai is None:
            img_ai = ai_factory(model_type='Image')
            img_ai.to_bio_page()

        if roles is None:
            roles = random_enums(RoleEnum)

        return Staff(
            short_name=slugify(name),
            name=name,
            roles=roles,
            avatar=Path(
                '/assets/images/avatars/staff/' + fake.file_name(category='image')
            ),
            lang_ai=lang_ai.short_name,
            img_ai=img_ai.short_name,
            bio=fake.sentence(nb_words=10),
            style=fake.sentence(nb_words=10),
        )

    return _staff_factory


@pytest.fixture(scope='function')
def image_factory(genzine_fs):
    def _image_factory() -> Image:
        name = fake.file_name(extension='jpg')

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
    ) -> Article:
        image_count = fake.random_int(max=4, min=1)
        name = fake.sentence(nb_words=10).title()[:-1]

        if author is None:
            author = staff_factory(roles=['Author'])
            author.to_bio_page()

        if illustrator is None:
            illustrator = staff_factory(roles=['Illustrator'])
            illustrator.to_bio_page()

        return Article(
            title=name,
            path=Path(slugify(name)),
            prompt=fake.sentence(nb_words=10),
            text='\n\n'.join(fake.paragraphs()),
            images=[image_factory() for i in range(image_count)],
            author=author.short_name,
            illustrator=illustrator.short_name,
        )

    return _article_factory


@pytest.fixture(scope='function')
def zine_factory(genzine_fs, article_factory, ai_factory, staff_factory):
    def _zine_factory() -> Zine:
        name = ' '.join(fake.words(nb=5)).title()

        img_ais = [
            ai_factory(model_type='Image')
            for ai in range(fake.random_int(max=3, min=1))
        ]
        lang_ais = [
            ai_factory(model_type='Language')
            for ai in range(fake.random_int(max=3, min=1))
        ]

        for ai in img_ais + lang_ais:
            ai.to_bio_page()

        staff_list = [
            staff_factory(
                roles=['Author', 'Editor', 'Illustrator'],
                lang_ai=random.choice(lang_ais),
                img_ai=random.choice(img_ais),
            )
            for i in range(10)
        ]

        for staff in staff_list:
            staff.to_bio_page()

        editor = staff_list[0]
        authors = staff_list[1:7]
        illustrators = staff_list[7:10]

        article_list = [
            article_factory(
                author=random.choice(authors), illustrator=random.choice(illustrators)
            )
            for i in range(5)
        ]

        board_names = [ai.short_name for ai in lang_ais]
        editor_name = editor.short_name
        author_names = [author.short_name for author in authors]
        illustrator_names = [illus.short_name for illus in illustrators]

        return Zine(
            name=name,
            path=Path(slugify(str(fake.random_int(max=10, min=1)) + ' ' + name)),
            board=board_names,
            editor=editor_name,
            authors=author_names,
            illustrators=illustrator_names,
            articles=article_list,
        )

    return _zine_factory
