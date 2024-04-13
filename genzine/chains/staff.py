import random
from collections import Counter
from enum import Enum
from io import BytesIO
from typing import Optional

import boto3
import requests
from dotenv import find_dotenv, load_dotenv
from langchain.output_parsers import OutputFixingParser
from langchain.output_parsers.enum import EnumOutputParser
from langchain_community.chat_models import ChatLiteLLM
from langchain_core.output_parsers import StrOutputParser
from langchain_core.runnables.base import RunnableSerializable
from litellm import image_generation
from PIL import Image as PILImage

from genzine.models.staff import AIModel, ModelTypeEnum, Staff
from genzine.prompts import staff as staff_prompts
from genzine.utils import HTML, slugify

load_dotenv(find_dotenv())


def load_all_ais() -> dict[str, list[AIModel]]:
    ais = [AIModel.from_bio_page(p.stem) for p in (HTML / '_ai').glob('*.md')]

    res = {'lang_ais': [], 'img_ais': []}

    for ai in ais:
        if ai.ai_type == 'Image':
            res['img_ais'].append(ai)
        elif ai.ai_type == 'Language':
            res['lang_ais'].append(ai)

    return res


def create_board(n: Optional[int] = None) -> list[AIModel]:
    lang_ais = load_all_ais().get('lang_ais')
    k = random.randint(1, len(lang_ais)) if n is None else n

    return random.sample(population=lang_ais, k=k)


def make_choose_player_chain(ai: AIModel, type: ModelTypeEnum) -> RunnableSerializable:
    all_ais = load_all_ais()

    if type.lower() == 'image':
        ai_choices = all_ais['img_ais']
    elif type.lower() == 'language':
        ai_choices = all_ais['lang_ais']
    else:
        return ValueError('type must be image or language')

    AIEnum = Enum('AIEnum', {ai.short_name: ai.short_name for ai in ai_choices})

    model = ChatLiteLLM(model=ai.short_name, temperature=1)
    parser = EnumOutputParser(enum=AIEnum)
    prompt = staff_prompts.choose_player.partial(
        instructions=parser.get_format_instructions()
    )
    fixing_parser = OutputFixingParser.from_llm(parser=parser, llm=model)

    choose_player_chain = prompt | model | fixing_parser

    return choose_player_chain


def create_staff_member(ai: AIModel) -> Staff:
    """Creates a new staff member."""
    board_model = ChatLiteLLM(model=ai.short_name, temperature=1)

    get_long_bio_chain = staff_prompts.new | board_model | StrOutputParser()
    get_bio_chain = staff_prompts.bio | board_model | StrOutputParser()
    get_name_chain = staff_prompts.name | board_model | StrOutputParser()
    get_style_chain = staff_prompts.style | board_model | StrOutputParser()
    get_lang_ai_chain = make_choose_player_chain(ai=ai, type='Language')
    get_img_ai_chain = make_choose_player_chain(ai=ai, type='Image')

    staff_long_bio = get_long_bio_chain.invoke({})
    staff_bio = get_bio_chain.invoke({'long_bio': staff_long_bio}).strip()
    staff_name = get_name_chain.invoke({'bio': staff_bio}).strip()
    staff_style = get_style_chain.invoke({'bio': staff_bio}).strip()
    staff_lang_ai = get_lang_ai_chain.invoke({'bio': staff_bio}).value
    staff_img_ai = get_img_ai_chain.invoke({'bio': staff_bio}).value

    return Staff(
        short_name=slugify(staff_name),
        name=staff_name,
        lang_ai=staff_lang_ai,
        img_ai=staff_img_ai,
        bio=staff_bio,
        style=staff_style,
    )


def create_staff_pool(board: list[AIModel], n: int) -> list[Staff]:
    pool: list[Staff] = []
    for _ in range(n):
        pool.append(create_staff_member(ai=random.choice(board)))
    return pool


def draw_staff_member(staff: Staff) -> PILImage:
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


def make_choose_editor_chain(ai: AIModel, pool: list[Staff]) -> RunnableSerializable:
    StaffEnum = Enum(
        'StaffEnum', {staff.short_name: staff.short_name for staff in pool}
    )

    model = ChatLiteLLM(model=ai.short_name, temperature=1)
    parser = EnumOutputParser(enum=StaffEnum)
    prompt = staff_prompts.choose_editor.partial(
        instructions=parser.get_format_instructions()
    )
    fixing_parser = OutputFixingParser.from_llm(parser=parser, llm=model)

    choose_editor_chain = prompt | model | fixing_parser

    return choose_editor_chain


def choose_editor(
    board: list[AIModel],
    pool: list[Staff],
    counter: Counter = Counter(),
    max_votes: int = 10,
) -> Staff:
    choices_str = '\n\n'.join([f'* {staff.short_name}: {staff.bio}' for staff in pool])

    for ai in board:
        choose_editor_chain = make_choose_editor_chain(ai=ai, pool=pool)
        editor_str = choose_editor_chain.invoke({'choices': choices_str}).value
        counter.update([editor_str])

    max_count = len([i for i in counter.values() if i == max(counter.values())])

    if max_count != 1 or counter.total() >= max_votes:
        choose_editor(board=board, pool=pool, counter=counter, max_votes=max_votes)
    else:
        chosen_editor_str = counter.most_common(n=1)[0][0]
        choices_dict = {staff.short_name: staff for staff in pool}
        editor = choices_dict.get(chosen_editor_str)
        if 'Editor' not in editor.roles:
            editor.roles.append('Editor')
        return editor


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


if __name__ == '__main__':
    board = create_board()

    pool = create_staff_pool(board=board, n=3)

    editor = choose_editor(board=board, pool=pool)

    print(editor)

    # avatar = draw_staff_member(staff=staff)

    # save_path = HTML / f'assets/images/avatars/staff/{staff.short_name}.jpg'

    # avatar.save(fp=save_path)

    # url = avatar_to_s3(img=avatar, short_name=staff.short_name)

    # print(url)

    # staff.avatar = url
