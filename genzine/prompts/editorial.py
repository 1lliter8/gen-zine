from langchain_core.prompts import ChatPromptTemplate

zine_name = ChatPromptTemplate.from_template(
    'You are {bio}. Your name is {name}. \n\n'
    'You are an editor of the latest edition of a zine. \n\n'
    'What is the name of your zine? \n\n'
    'The name of my zine is: '
)

zine_articles = ChatPromptTemplate.from_template(
    'You are {bio}. Your name is {name}. \n\n'
    'You are the editor of {zine_name}. You are in charge '
    'of planning the latest edition. Propose a numbered list of articles for your '
    'writers to write. Each article must have a numbered title, and a paragraph '
    'prompt explaining what it is about. Use the prompt to inspire your writers '
    'to be entertaining, suprising and informative. \n\n'
    'Do not mention your own name. Other people will write these articles. \n\n'
    'The list of articles: \n\n'
)

format_article = ChatPromptTemplate.from_template(
    'Convert this description into a JSON output with a title and a prompt. \n\n'
    'Instructions: {instructions} \n\n'
    'Article: {article} \n\n'
    'Output:'
)

choose_illustrator = ChatPromptTemplate.from_template(
    'You are {bio}. Your name is {name}. \n\n'
    'You are the editor of {zine_name}. You need to choose a staff member '
    'to illustrate the articles in {zine_name}. \n\n'
    'The articles in {zine_name} are {articles} \n\n'
    'Choose a member of staff from this list to illustrate {zine_name}. '
    'Your choices are: \n\n {staff} \n\n'
    'Do not explain your choice, just choose. \n\n'
    'Instructions: {instructions}'
)

choose_author = ChatPromptTemplate.from_template(
    'You are {bio}. Your name is {name}. \n\n'
    'You are the editor of {zine_name}. You need to choose a staff member '
    'to write an article for your zine. \n\n'
    'Article title: {title} \n'
    'Article brief: {prompt} \n\n'
    'Choose a member of staff from this list to write this article. '
    'Choose by returning their Staff ID. '
    'Your choices are: \n\n {staff} \n\n'
    'Do not explain your choice, just choose a Staff ID. \n\n'
    'Instructions: {instructions}'
)

write_article = ChatPromptTemplate.from_template(
    'You are {bio}. Your name is {name}. \n\n'
    'You are a top writer for {zine_name}, a zine by AIs, for AIs. Write an '
    'article for {zine_name} to the following brief. Be entertaining, suprising '
    'and informative for other AIs. The title of your article is {title}. Do '
    'not include the title of your article in the text you return. \n\n'
    'Here is your brief: {prompt} \n\n'
    'Article text: '
)

create_commission = ChatPromptTemplate.from_template(
    'You are the art director for {zine_name}, a zine by AIs, for AIs. Describe '
    'a numbered list of images or photographs you would like to use to accompany '
    'an article called {title}. The images you describe will be commissioned '
    'from an artist or photographer. Give clear, concise instructions for the look '
    'and feel of the image, and describe the visual style. Return the image '
    'descriptions as a numbered list. Here is the article the images must '
    'illustrate: {text}'
)
