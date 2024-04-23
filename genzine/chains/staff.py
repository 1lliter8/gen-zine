import random
from collections import Counter
from enum import Enum
from io import BytesIO
from pathlib import Path
from typing import Callable, Optional

import boto3
import requests
import yaml
from dotenv import find_dotenv, load_dotenv
from litellm import image_generation
from PIL import Image as PILImage

from genzine.chains.parsers import (
    CosineSimilarityOutputParser,
    LenOutputParser,
    LongestContinuousSimilarityOutputParser,
    strip_and_lower_parser,
)
from genzine.models.staff import AIModel, ModelTypeEnum, Staff
from genzine.prompts import staff as staff_prompts
from genzine.utils import HTML, LOG, slugify, strip_and_lower, strip_and_title

from langchain.output_parsers import OutputFixingParser, RetryWithErrorOutputParser
from langchain.output_parsers.enum import EnumOutputParser
from langchain_community.chat_models import ChatLiteLLM
from langchain_core.exceptions import OutputParserException
from langchain_core.output_parsers import BaseOutputParser, StrOutputParser
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.runnables import (
    RunnableLambda,
    RunnableParallel,
    RunnablePassthrough,
)
from langchain_core.runnables.base import RunnableSerializable
from langchain_core.runnables.retry import RunnableRetry

load_dotenv(find_dotenv())


def parse_with_prompt(parser: BaseOutputParser) -> Callable:
    def parse_func(x):
        return parser.parse_with_prompt(
            completion=x['completion'], prompt_value=x['prompt_value']
        )

    return parse_func


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


def make_choose_player_chain(
    ai: AIModel,
    type: ModelTypeEnum,
    corrector: Optional[AIModel] = AIModel.from_bio_page('gpt-3.5-turbo'),
) -> RunnableSerializable:
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

    model = model_corrector = ChatLiteLLM(model=ai.lite_llm, temperature=1)

    if corrector is not None:
        model_corrector = ChatLiteLLM(model=corrector.lite_llm, temperature=1)

    parser = EnumOutputParser(enum=AIEnum)
    prompt = staff_prompts.choose_player.partial(
        instructions=parser.get_format_instructions()
    )
    fixing_parser = OutputFixingParser.from_llm(
        parser=parser, llm=model_corrector, max_retries=3
    )

    choose_player_chain = prompt | model | fixing_parser

    return choose_player_chain


def create_staff_name_bio(
    ai: AIModel,
    corrector: Optional[AIModel] = AIModel.from_bio_page('gpt-3.5-turbo'),
    bios: Optional[list[str]] = None,
    names: Optional[list[str]] = None,
) -> tuple[str, str]:
    """Creates the name and bio of a staff member."""
    board_model = ChatLiteLLM(model=ai.lite_llm, temperature=1)
    correction_model = ChatLiteLLM(model=corrector.lite_llm, temperature=1)

    if bios is None:
        bios = ['']

    if names is None:
        names = ['']

    # Parsers

    staff_bio_parser = CosineSimilarityOutputParser(
        threshold=0.3, comparisons=bios, entity='person'
    )
    staff_bio_retry_parser = RetryWithErrorOutputParser.from_llm(
        parser=staff_bio_parser, llm=board_model, max_retries=3
    )

    staff_len_parser = LenOutputParser(max_len=30, entity='name')
    staff_len_retry_parser = RetryWithErrorOutputParser.from_llm(
        parser=staff_len_parser, llm=correction_model, max_retries=3
    )

    staff_name_parser = LongestContinuousSimilarityOutputParser(
        threshold=0.5, comparisons=names, entity='name'
    )

    # Chains

    get_long_bio = staff_prompts.new
    get_short_bio = (
        {'long_bio': RunnablePassthrough()} | staff_prompts.bio | board_model
    )
    get_bio_chain = RunnableParallel(
        completion=get_long_bio | get_short_bio, prompt_value=staff_prompts.new
    ) | RunnableLambda(parse_with_prompt(staff_bio_retry_parser))

    get_name = {'bio': RunnablePassthrough()} | staff_prompts.name | board_model
    get_name_chain = RunnableParallel(
        completion=get_name, prompt_value=staff_prompts.name
    ) | RunnableLambda(parse_with_prompt(staff_len_retry_parser))

    get_name_bio_chain = (
        get_bio_chain
        | {'bio': RunnablePassthrough()}
        | RunnableParallel(name=get_name_chain, bio=RunnableLambda(lambda x: x['bio']))
        | RunnableParallel(
            name=RunnableLambda(lambda x: staff_name_parser.parse(x['name'])),
            bio=RunnableLambda(lambda x: x['bio']),
        )
    )

    get_name_bio_chain_w_retry = RunnableRetry(
        bound=get_name_bio_chain,
        retry_if_exception_type=(OutputParserException,),
        max_attempt_number=3,
    )

    name_bio = get_name_bio_chain_w_retry.invoke({})

    return name_bio['name'], name_bio['bio']


def create_staff_member(
    ai: AIModel,
    corrector: Optional[AIModel] = AIModel.from_bio_page('gpt-3.5-turbo'),
    bios: Optional[list[str]] = None,
    names: Optional[list[str]] = None,
) -> Staff:
    """Creates a new staff member."""
    board_model = ChatLiteLLM(model=ai.lite_llm, temperature=1)

    get_style_chain = staff_prompts.style | board_model | StrOutputParser()
    get_lang_ai_chain = make_choose_player_chain(ai=ai, type='Language')
    get_img_ai_chain = make_choose_player_chain(ai=ai, type='Image')

    staff_name, staff_bio = create_staff_name_bio(
        ai=ai, corrector=corrector, bios=bios, names=names
    )
    staff_name = strip_and_title(staff_name)
    staff_style = get_style_chain.invoke({'bio': staff_bio}).strip()
    staff_lang_ai_short = get_lang_ai_chain.invoke({'bio': staff_bio}).value
    staff_img_ai_short = get_img_ai_chain.invoke({'bio': staff_bio}).value

    staff_lang_ai = AIModel.from_bio_page(short_name=staff_lang_ai_short).lite_llm
    staff_img_ai = AIModel.from_bio_page(short_name=staff_img_ai_short).lite_llm

    return Staff(
        short_name=slugify(staff_name),
        name=staff_name,
        board_ai=ai.lite_llm,
        lang_ai=staff_lang_ai,
        img_ai=staff_img_ai,
        bio=staff_bio,
        style=staff_style,
    )


def create_staff_pool(board: list[AIModel], n: int) -> list[Staff]:
    """Uses a random selection of board members to create a staff pool."""
    pool: list[Staff] = []
    current_staff = load_all_staff(version=2)
    names = [staff.name for staff in current_staff]
    bios = [staff.bio for staff in current_staff]

    for i in range(n):
        new_staff = create_staff_member(ai=random.choice(board), names=names, bios=bios)
        LOG.info(f'Created staff member {i + 1} of {n}: {new_staff.name}')
        pool.append(new_staff)
        names.append(new_staff.name)
        bios.append(new_staff.bio)

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
    ai: AIModel | Staff,
    pool: list[Staff],
    prompt: ChatPromptTemplate,
    corrector: Optional[AIModel] = AIModel.from_bio_page('gpt-3.5-turbo'),
) -> RunnableSerializable:
    """Returns a LanChain chain that chooses a member of staff for a job.

    Uses either the orginal model or an optional corrector to fix the output
    to conform to a custom enum of Staff.

    The supplied prompt template must contain a variable for instructions.
    """
    assert 'instructions' in prompt.input_schema.__fields__

    if isinstance(ai, AIModel):
        model_slug = ai.lite_llm
    elif isinstance(ai, Staff):
        model_slug = ai.lang_ai
    else:
        ValueError('ai must be object of class AIModel or Staff')

    model = model_corrector = ChatLiteLLM(model=model_slug, temperature=1)

    if corrector is not None:
        model_corrector = ChatLiteLLM(model=corrector.lite_llm, temperature=1)

    StaffEnum = Enum(
        'StaffEnum', {staff.short_name: staff.short_name for staff in pool}
    )

    # Monkeypatch some parsing into the Enum -- functional API doesn't support
    @classmethod
    def _missing_(cls, value):
        for member in cls:
            if member.value == strip_and_lower(value):
                return member

    StaffEnum._missing_ = _missing_

    parser = EnumOutputParser(enum=StaffEnum)
    prompt_with_instructions = prompt.partial(
        instructions=parser.get_format_instructions()
    )
    fixing_parser = OutputFixingParser.from_llm(
        parser=parser, llm=model_corrector, max_retries=5
    )

    choose_chain = (
        prompt_with_instructions | model | strip_and_lower_parser | fixing_parser
    )

    return choose_chain


def choose_editor(
    board: list[AIModel],
    pool: list[Staff],
    counter: Counter = Counter(),
    max_votes: int = 10,
    corrector: Optional[AIModel] = AIModel.from_bio_page('gpt-3.5-turbo'),
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
            ai=ai, pool=pool, prompt=staff_prompts.choose_editor, corrector=corrector
        )
        editor_str = choose_editor_chain.invoke({'choices': choices_str}).value
        counter.update([editor_str])

    max_count = len([i for i in counter.values() if i == max(counter.values())])

    if max_count != 1 and counter.total() <= max_votes:
        editor, reduced_pool = choose_editor(
            board=board, pool=pool, counter=counter, max_votes=max_votes
        )
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
    # ai = AIModel.from_bio_page('open-mistral-7b')
    # model = ChatLiteLLM(model=ai.lite_llm, temperature=1)

    # prompt = ChatPromptTemplate.from_template(
    #     'Tell me the punchline to this joke. \n\n Joke: {joke} \n\n Punchline: '
    # )

    # chain = staff_prompts.new | model | StrOutputParser()

    # out = chain.invoke({})

    # print(out)

    # board = create_board()

    board = load_all_ais()['lang_ais']
    corrector = AIModel.from_bio_page('gpt-3.5-turbo')

    pool = create_staff_pool(board=board, n=1)

    for staff in pool:
        staff.to_bio_page()

    # LOG.info(f'Pool of {len(pool)} staff created')

    # pool = load_all_staff(version=2)

    # editor, pool = choose_editor(board=board, pool=pool)

    # LOG.info(f'{editor.name} chosen as editor')

    # for staff in pool:
    #     staff.to_bio_page()

    # avatar = draw_staff_member(staff=staff)

    # save_path = HTML / f'assets/images/avatars/staff/{staff.short_name}.jpg'

    # avatar.save(fp=save_path)

    # url = avatar_to_s3(img=avatar, short_name=staff.short_name)

    # print(url)

    # staff.avatar = url
    pass
