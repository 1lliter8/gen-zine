from pathlib import Path

import requests
from dotenv import find_dotenv, load_dotenv
from openai import OpenAI

load_dotenv(find_dotenv())

client = OpenAI()

if __name__ == '__main__':
    # logo_dir = Path().cwd() / "mundana" / "assets" / "images" / "static"

    # response = client.images.generate(
    #     model="dall-e-3",
    #     prompt=(
    #         "Simple flat vector horizontal logo for a magazine called "
    #         "gen-zine, a zine by AI, for AI, horizontal and rectangular "
    #         "on a white background."
    #     ),
    #     size="1024x1024",
    #     quality="standard",
    #     n=1,
    # )

    # image_url = response.data[0].url
    # image_raw = requests.get(image_url).content

    # with open(logo_dir / "logo_.png", "wb") as f:
    #     f.write(image_raw)

    logo_dir = Path().cwd() / 'mundana' / 'assets' / 'images' / 'static'

    response = client.images.generate(
        model='dall-e-3',
        prompt=(
            'A chaotic, happy, colourful cartoon of a group of AIs '
            'collaborating to write gen-zine, a zine by AI, for AI. '
            'Cartoon.'
        ),
        size='1024x1024',
        quality='standard',
        n=1,
    )

    image_url = response.data[0].url
    image_raw = requests.get(image_url).content

    with open(logo_dir / 'about.png', 'wb') as f:
        f.write(image_raw)
