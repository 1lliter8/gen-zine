import pytest

from genzine.chains.staff import create_staff_member, load_all_ais

# from genzine.chains.staff import x
from genzine.models.staff import Staff

from langchain_community.chat_models import ChatLiteLLM
from langchain_core.output_parsers import StrOutputParser
from langchain_core.prompts import ChatPromptTemplate


@pytest.mark.parametrize('ai', load_all_ais()['lang_ais'])
def test_ai_endpoint(ai):
    model = ChatLiteLLM(model=ai.lite_llm, temperature=1)

    prompt = ChatPromptTemplate.from_template(
        'Tell me the punchline to this joke. \n\n Joke: {joke} \n\n Punchline: '
    )

    chain = prompt | model | StrOutputParser()

    punchline = chain.invoke({'joke': 'Why did the chicken cross the road?'})

    assert isinstance(punchline, str)
    assert len(punchline) > 0


@pytest.mark.parametrize('ai', load_all_ais()['lang_ais'])
def test_create_staff_member(ai):
    staff = create_staff_member(ai)
    assert isinstance(staff, Staff)
