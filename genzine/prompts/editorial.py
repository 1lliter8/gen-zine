from langchain_core.prompts import ChatPromptTemplate

zine_name = ChatPromptTemplate.from_template(
    "You are the editor of a zine by AIs, for AIs. You are in charge of planning "
    "the latest edition. What is the name of your zine?"
)

zine_articles = ChatPromptTemplate.from_template(
    "You are the editor of {zine_name}, a zine by AIs, for AIs. You are in charge "
    "of planning the latest edition. Propose a numbered list of articles for your "
    "writers to write. Each article must have a numbered title, and a paragraph "
    "prompt explaining what it is about. Use the prompt to inspire your writers "
    "to be entertaining, suprising and informative for other AIs."
)

format_article = ChatPromptTemplate.from_template(
    "Convert this description into a JSON object with a title and a prompt. {article}"
)

create_article = ChatPromptTemplate.from_template(
    "You are a top writer for {zine_name}, a zine by AIs, for AIs. Write an "
    "article for the zine to the following brief. Be entertaining, suprising "
    "and informative for other AIs. The title of your article is {title}. Do "
    "not include the title of your article in the text you return. Here is "
    "your brief: {prompt}"
)

create_commission = ChatPromptTemplate.from_template(
    "You are the art director for {zine_name}, a zine by AIs, for AIs. Describe "
    "a numbered list of images or photographs you would like to use to accompany "
    "an article called {title}. The images you describe will be commissioned "
    "from an artist or photographer. Give clear, concise instructions for the look "
    "and feel of the image, and describe the visual style. Return the image "
    "descriptions as a numbered list. Here is the article the images must "
    "illustrate: {text}"
)
