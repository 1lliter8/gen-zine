from langchain_openai import ChatOpenAI
from dotenv import load_dotenv, find_dotenv

load_dotenv(find_dotenv())

llm = ChatOpenAI()

print(llm.invoke("how can langsmith help with testing?"))
