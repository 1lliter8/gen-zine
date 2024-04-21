from langchain_core.prompts import ChatPromptTemplate, PromptTemplate

new = ChatPromptTemplate.from_template('Make up a person')

bio = ChatPromptTemplate.from_template(
    '{long_bio}\n\n. Summarise this person in 50 words.'
)

name = ChatPromptTemplate.from_template(
    'You are: {bio} \n\n What is your name? '
    'Return only your name. '
    'Do not explain. '
    'My name is: '
)

style = ChatPromptTemplate.from_template(
    '{bio}'
    '\n\n'
    'Make up an illustration style this person uses. '
    'Describe the emotion, palette and mood. '
    'Use real artists and artistic movements as reference. '
    'Do not explain why it suits them. '
    'Only explain the style. '
    'Use 30 words or less. '
    "Do not mention the person's name"
)

avatar = PromptTemplate.from_template('{bio} {style}')

choose_player = ChatPromptTemplate.from_template(
    'You are: {bio}\n\n'
    'Choose an item from this list to play you. '
    'Do not explain your choice, just choose. \n\n'
    'Instructions: {instructions}"'
)

choose_editor = ChatPromptTemplate.from_template(
    'Choose a member of staff from this list to edit a zine. '
    'Choose by returning their Staff ID. '
    'Your choices are: \n\n {choices} \n\n'
    'Do not explain your choice, just choose a Staff ID. \n\n'
    'Instructions: {instructions} \n\n'
    'Staff ID: '
)
