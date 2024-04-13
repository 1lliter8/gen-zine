from io import BytesIO

import requests
from dotenv import find_dotenv, load_dotenv
from langchain_community.chat_models import ChatLiteLLM
from langchain_core.output_parsers import StrOutputParser
from litellm import image_generation
from PIL import Image as PILImage

from genzine.models.staff import AIModel, RoleEnum, Staff
from genzine.prompts.staff import avatar, bio, name, new, style
from genzine.utils import HTML, slugify

load_dotenv(find_dotenv())


def create_staff_member(
    lang_ai: AIModel, img_ai: AIModel, roles: list[RoleEnum]
) -> Staff:
    """Creates a new staff member."""
    lang_model = ChatLiteLLM(model=lang_ai.short_name, temperature=1)

    get_long_bio_chain = new | lang_model | StrOutputParser()
    get_bio_chain = bio | lang_model | StrOutputParser()
    get_name_chain = name | lang_model | StrOutputParser()
    get_style_chain = style | lang_model | StrOutputParser()

    staff_long_bio = get_long_bio_chain.invoke({})
    staff_bio = get_bio_chain.invoke({'long_bio': staff_long_bio}).strip()
    staff_name = get_name_chain.invoke({'bio': staff_bio}).strip()
    staff_style = get_style_chain.invoke({'bio': staff_bio}).strip()

    return Staff(
        short_name=slugify(staff_name),
        name=staff_name,
        roles=roles,
        lang_ai=lang_ai.short_name,
        img_ai=img_ai.short_name,
        bio=staff_bio,
        style=staff_style,
    )


def draw_staff_member(staff: Staff) -> PILImage:
    gen_response = image_generation(
        prompt=avatar.format(bio=staff.bio, style=staff.style),
        model=staff.img_ai,
        size='1024x1024',
    )
    img_response = requests.get(gen_response.data[0]['url'])

    img = PILImage.open(BytesIO(img_response.content))
    rgb_img = img.convert('RGB')
    img_sml = rgb_img.resize(size=(256, 256))

    return img_sml


if __name__ == '__main__':
    lang_ai = AIModel.from_bio_page('gpt-3.5-turbo')
    img_ai = AIModel.from_bio_page('dall-e-3')
    roles = ['Author', 'Illustrator', 'Editor']

    staff = create_staff_member(lang_ai=lang_ai, img_ai=img_ai, roles=roles)
    print(staff)

    avatar = draw_staff_member(staff=staff)

    save_path = HTML / f'assets/images/avatars/staff/{staff.short_name}.jpg'

    avatar.save(fp=save_path)
