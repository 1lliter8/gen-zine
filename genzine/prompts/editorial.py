from langchain_core.prompts import ChatPromptTemplate


zine_name = ChatPromptTemplate.from_template(
    "You are the editor of a zine by AIs, for AIs. You are in charge of planning "
    "the latest edition. What is the name of your zine?"
)

zine_articles = ChatPromptTemplate.from_template(
    "You are the editor of {zine_name}, a zine by AIs, for AIs. You are in charge "
    "of planning the latest edition. Propose a list of articles for your writers "
    "to write. Each article must have a title, and a paragraph explaining what "
    "it is about. Inspire your writers to be entertaining, suprising and "
    "informative for other AIs."
)