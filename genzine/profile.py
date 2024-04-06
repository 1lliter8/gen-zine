from pathlib import Path

import requests
from dotenv import find_dotenv, load_dotenv
from langchain_core.output_parsers import StrOutputParser
from langchain_openai import ChatOpenAI
from openai import OpenAI

from genzine.models.staff import Staff
from genzine.prompts.staff import staff_bio, staff_name
from genzine.utils import to_camelcase

load_dotenv(find_dotenv())

client = OpenAI()
model = ChatOpenAI()


def create_staff_member(ai: str, role: str) -> Staff:
    """Generates a bio for a writer."""
    get_bio_chain = staff_bio | model | StrOutputParser()
    get_name_chain = staff_name | model | StrOutputParser()

    bio = get_bio_chain.invoke({'ai': ai, 'role': role})
    name = get_name_chain.invoke({'bio': bio})

    avatar_dir = (
        Path().cwd() / 'mundana' / 'assets' / 'images' / 'avatars' / to_camelcase(name)
        + '.png'
    )

    response = client.images.generate(
        model='dall-e-3',
        prompt=f'An avatar for {bio}. Their name is {name}.',
        size='256x256',
        quality='standard',
        n=1,
    )

    image_url = response.data[0].url
    image_raw = requests.get(image_url).content

    with open(avatar_dir, 'wb') as f:
        f.write(image_raw)

    staff = Staff(ai=ai, role=role, bio=bio, name=name, avatar=avatar_dir)

    return staff


if __name__ == '__main__':
    pass
