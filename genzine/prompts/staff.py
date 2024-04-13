from langchain_core.prompts import ChatPromptTemplate, PromptTemplate

new = ChatPromptTemplate.from_template('Make up a person')

bio = ChatPromptTemplate.from_template(
    '{long_bio}\n\n. Summarise this person in 50 words.'
)

name = ChatPromptTemplate.from_template(
    'You are: {bio} \n\n What is your name? Return only your name. My name is:'
)

style = ChatPromptTemplate.from_template(
    '{bio}'
    '\n\n'
    'Make up an illustration style this person uses. '
    'Describe the emotion, palette and mood. '
    'Use real artistic movements as reference. '
    'Do not explain why it suits them. '
    'Only explain the style. '
    'Use 30 words or less. '
    "Do not mention the person's name"
)

avatar = PromptTemplate.from_template('{bio} {style}')
