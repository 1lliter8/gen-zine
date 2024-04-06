from langchain_core.prompts import ChatPromptTemplate

staff_bio = ChatPromptTemplate.from_template(
    'Write a 30-word bio in the third person for {ai}, {role} at gen-zine'
)

staff_name = ChatPromptTemplate.from_template(
    "{bio}. What is this staff member's name? Return only the name. Do not explain."
)
