from langchain_core.output_parsers import StrOutputParser
from langchain_openai import ChatOpenAI
from dotenv import load_dotenv, find_dotenv

from genzine.prompts.editorial import zine_name, zine_articles

load_dotenv(find_dotenv())

model = ChatOpenAI()

get_name_chain = (
    zine_name
    | model
    | StrOutputParser()
)

get_articles_chain = (
    {"zine_name": get_name_chain}
    | zine_articles
    | model
    | StrOutputParser()
)

print(get_articles_chain.invoke())
