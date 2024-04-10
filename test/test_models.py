from pathlib import Path

from genzine.models.docs import Zine
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


def test_create_load_zine(zine_factory):
    zine: Zine = zine_factory()

    print(zine)

    assert (Path('/html/_posts/') / zine.path).exists()
