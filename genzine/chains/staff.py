import random
from collections import Counter
from enum import Enum
from io import BytesIO
from pathlib import Path
from string import punctuation
from typing import Optional

import boto3
import requests
import yaml
from dotenv import find_dotenv, load_dotenv
from litellm import image_generation
from PIL import Image as PILImage

from genzine.models.staff import AIModel, ModelTypeEnum, Staff
from genzine.prompts import staff as staff_prompts
from genzine.utils import HTML, slugify

from langchain.output_parsers import OutputFixingParser
from langchain.output_parsers.enum import EnumOutputParser
from langchain_community.chat_models import ChatLiteLLM
from langchain_core.output_parsers import StrOutputParser
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.runnables.base import RunnableSerializable

load_dotenv(find_dotenv())


def load_all_ais() -> dict[str, list[AIModel]]:
    """Loads all AIs listed on the website.

    Returns a dictionary keyed to model type, with a list of AIs of that type.
    """
    ais = [AIModel.from_bio_page(p.stem) for p in (HTML / '_ai').glob('*.md')]

    res = {'lang_ais': [], 'img_ais': []}

    for ai in ais:
        if ai.ai_type == 'Image':
            res['img_ais'].append(ai)
        elif ai.ai_type == 'Language':
            res['lang_ais'].append(ai)

    return res


def load_all_staff(version: Optional[int] = None) -> list[Staff]:
    """Loads all staff listed on the website."""
    staff_paths = [p for p in (HTML / '_staff').glob('*.md')]
    staff_paths_filtered: list[Path] = []

    if version is not None:
        for staff_path in staff_paths:
            with open(staff_path, 'r') as f:
                staff: dict = next(yaml.safe_load_all(f))

            if staff['version'] == version:
                staff_paths_filtered.append(staff_path)

    staff = [Staff.from_bio_page(staff.stem) for staff in staff_paths_filtered]

    return staff


def create_board(n: Optional[int] = None) -> list[AIModel]:
    """Returns a random selection of language AIs to be the board."""
    lang_ais = load_all_ais().get('lang_ais')
    k = random.randint(1, len(lang_ais)) if n is None else n

    return random.sample(population=lang_ais, k=k)


def make_choose_player_chain(ai: AIModel, type: ModelTypeEnum) -> RunnableSerializable:
    """Returns a LanChain chain that chooses an AI to play a staff member.

    Uses the specified model to fix the output to conform to a custom enum of AI by
    type.
    """
    all_ais = load_all_ais()

    if type.lower() == 'image':
        ai_choices = all_ais['img_ais']
    elif type.lower() == 'language':
        ai_choices = all_ais['lang_ais']
    else:
        return ValueError('type must be image or language')

    AIEnum = Enum('AIEnum', {ai.short_name: ai.short_name for ai in ai_choices})

    model = ChatLiteLLM(model=ai.lite_llm, temperature=1)
    parser = EnumOutputParser(enum=AIEnum)
    prompt = staff_prompts.choose_player.partial(
        instructions=parser.get_format_instructions()
    )
    fixing_parser = OutputFixingParser.from_llm(parser=parser, llm=model)

    choose_player_chain = prompt | model | fixing_parser

    return choose_player_chain


def create_staff_member(ai: AIModel) -> Staff:
    """Creates a new staff member."""
    board_model = ChatLiteLLM(model=ai.lite_llm, temperature=1)

    get_long_bio_chain = staff_prompts.new | board_model | StrOutputParser()
    get_bio_chain = staff_prompts.bio | board_model | StrOutputParser()
    get_name_chain = staff_prompts.name | board_model | StrOutputParser()
    get_style_chain = staff_prompts.style | board_model | StrOutputParser()
    get_lang_ai_chain = make_choose_player_chain(ai=ai, type='Language')
    get_img_ai_chain = make_choose_player_chain(ai=ai, type='Image')

    staff_long_bio = get_long_bio_chain.invoke({})
    staff_bio = get_bio_chain.invoke({'long_bio': staff_long_bio}).strip()
    staff_name = get_name_chain.invoke({'bio': staff_bio}).strip(punctuation + ' ')
    staff_style = get_style_chain.invoke({'bio': staff_bio}).strip()
    staff_lang_ai_short = get_lang_ai_chain.invoke({'bio': staff_bio}).value
    staff_img_ai_short = get_img_ai_chain.invoke({'bio': staff_bio}).value

    staff_lang_ai = AIModel.from_bio_page(short_name=staff_lang_ai_short).lite_llm
    staff_img_ai = AIModel.from_bio_page(short_name=staff_img_ai_short).lite_llm

    return Staff(
        short_name=slugify(staff_name),
        name=staff_name,
        lang_ai=staff_lang_ai,
        img_ai=staff_img_ai,
        bio=staff_bio,
        style=staff_style,
    )


def create_staff_pool(board: list[AIModel], n: int) -> list[Staff]:
    """Uses a random selection of board members to create a staff pool."""
    pool: list[Staff] = []
    for _ in range(n):
        pool.append(create_staff_member(ai=random.choice(board)))
    return pool


def draw_staff_member(staff: Staff) -> PILImage:
    """Gets a staff member to draw an avatar of themselves."""
    gen_response = image_generation(
        prompt=staff_prompts.avatar.format(bio=staff.bio, style=staff.style),
        model=staff.img_ai,
        size='1024x1024',
    )
    img_response = requests.get(gen_response.data[0]['url'])

    img = PILImage.open(BytesIO(img_response.content))
    rgb_img = img.convert('RGB')
    img_sml = rgb_img.resize(size=(256, 256))

    return img_sml


def make_choose_staff_chain(
    ai: AIModel | Staff, pool: list[Staff], prompt: ChatPromptTemplate
) -> RunnableSerializable:
    """Returns a LanChain chain that chooses a member of staff for a job.

    Uses the specified model to fix the output to conform to a custom enum of Staff.

    The supplied prompt template must contain a variable for instructions.
    """
    assert 'instructions' in prompt.input_schema.__fields__

    if isinstance(ai, AIModel):
        model_slug = ai.name
    elif isinstance(ai, Staff):
        model_slug = ai.lang_ai
    else:
        ValueError('ai must be object of class AIModel or Staff')

    model = ChatLiteLLM(model=model_slug, temperature=1)

    StaffEnum = Enum(
        'StaffEnum', {staff.short_name: staff.short_name for staff in pool}
    )

    parser = EnumOutputParser(enum=StaffEnum)
    prompt_with_instructions = prompt.partial(
        instructions=parser.get_format_instructions()
    )
    fixing_parser = OutputFixingParser.from_llm(parser=parser, llm=model, max_retries=3)

    choose_chain = prompt_with_instructions | model | fixing_parser

    return choose_chain


def choose_editor(
    board: list[AIModel],
    pool: list[Staff],
    counter: Counter = Counter(),
    max_votes: int = 10,
) -> tuple[Staff, list[Staff]]:
    """Uses the board and staff pool to choose an editor.

    A counter of votes that recurses until someone wins, or the max votes are hit.

    In a tie at max votes, the editor who was suggested first is chosen -- the
    default behaviour of collections.Counter.

    Returns the chosen editor with the new role, and the staff pool with them removed.
    """
    choices_str = '\n\n'.join([f'* {staff.short_name}: {staff.bio}' for staff in pool])

    for ai in board:
        choose_editor_chain = make_choose_staff_chain(
            ai=ai, pool=pool, prompt=staff_prompts.choose_editor
        )
        editor_str = choose_editor_chain.invoke({'choices': choices_str}).value
        counter.update([editor_str])

    max_count = len([i for i in counter.values() if i == max(counter.values())])

    if max_count != 1 or counter.total() >= max_votes:
        choose_editor(board=board, pool=pool, counter=counter, max_votes=max_votes)
    else:
        chosen_editor_str = counter.most_common(n=1)[0][0]
        choices_dict = {staff.short_name: staff for staff in pool}
        editor = choices_dict.get(chosen_editor_str)
        editor.roles.update(['Editor'])

        reduced_pool = [
            staff for staff in pool if staff.short_name != editor.short_name
        ]

        return editor, reduced_pool


def avatar_to_s3(img: PILImage, short_name: str) -> str:
    """Saves avatar to S3 and returns the URL."""
    s3 = boto3.client('s3')

    f = BytesIO()
    img.save(f, format='jpeg', quality=95)
    f.seek(0)

    bucket: str = 'gen-zine.co.uk'
    key: str = f'assets/images/avatars/staff/{short_name}.jpg'

    s3.upload_fileobj(Fileobj=f, Bucket=bucket, Key=key)

    return f'https://s3.eu-west-2.amazonaws.com/{bucket}/{key}'


def staff_to_s3(staff: Staff) -> Staff:
    """Draws a staff member's avatar, saves to S3, and returns updated object."""
    avatar = draw_staff_member(staff=staff)
    url = avatar_to_s3(img=avatar, short_name=staff.short_name)
    staff.avatar = url

    return staff


if __name__ == '__main__':
    board = create_board()

    pool = create_staff_pool(board=board, n=2)

    for staff in pool:
        staff.to_bio_page()

    # avatar = draw_staff_member(staff=staff)

    # save_path = HTML / f'assets/images/avatars/staff/{staff.short_name}.jpg'

    # avatar.save(fp=save_path)

    # url = avatar_to_s3(img=avatar, short_name=staff.short_name)

    # print(url)

    # staff.avatar = url
