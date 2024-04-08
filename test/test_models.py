import datetime
from pathlib import Path

import genzine.models.staff
from genzine.models.staff import AIModel, Staff


def test_create_load_ai(fs, monkeypatch):
    mock_html = Path('/html')
    monkeypatch.setattr(genzine.models.staff, 'HTML', mock_html)
    fs.create_dir(mock_html / '_ai')

    test_ai_1: AIModel = AIModel(
        short_name='foo',
        name='Foo Bar',
        site='http://www.foo.bar/',
        model_type='Image',
        description='Lorem ipsum dolor sit amet, consectetur adipiscing elit.',
        avatar=Path('/foo/bar'),
        retired=datetime.date(2024, 1, 25),
    )

    test_ai_1.to_bio_page()

    assert (mock_html / '_ai/foo.md').exists()

    test_ai_2: AIModel = AIModel.from_bio_page('foo')

    assert test_ai_1 == test_ai_2


def test_create_load_staff(fs, monkeypatch):
    mock_html = Path('/html')
    fs.add_real_directory(
        source_path=genzine.models.staff.HTML / '_ai', target_path=mock_html / '_ai'
    )
    monkeypatch.setattr(genzine.models.staff, 'HTML', mock_html)
    fs.create_dir(mock_html / '_staff')

    test_staff_1: Staff = Staff(
        short_name='bar',
        name='Bar Baz',
        roles=['Author', 'Editor'],
        avatar=Path('/bar/baz'),
        lang_ai='gpt-3.5-turbo',
        img_ai='dall-e-3',
        bio='Curabitur auctor imperdiet eros eu porttitor.',
        style='Sed cursus quis ante id dignissim.',
    )

    test_staff_1.to_bio_page()

    assert (mock_html / '_staff/bar.md').exists()

    test_staff_2: Staff = Staff.from_bio_page('bar')

    assert test_staff_1 == test_staff_2
