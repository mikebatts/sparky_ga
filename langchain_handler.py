import json
from langchain.agents import create_json_agent
from langchain.llms.openai import OpenAI
from langchain.tools.json.tool import JsonSpec
from langchain.agents.agent_toolkits import JsonToolkit
from langchain.chat_models import ChatOpenAI
from langchain.agents.agent_types import AgentType

from langchain.prompts.chat import (
    ChatPromptTemplate,
    HumanMessagePromptTemplate,
    SystemMessagePromptTemplate,
)
from langchain.schema import HumanMessage, SystemMessage


def initialize_langchain_agent(json_data):
    # Existing setup
    json_spec = JsonSpec(dict_=json_data, max_value_length=4000)
    json_toolkit = JsonToolkit(spec=json_spec)

    # Define the role for the model
    system_message_template = "You are a data analysis expert. Your task is to analyze complex data sets and extract meaningful insights about user engagement, session durations, and purchasing behaviors."
    system_message_prompt = SystemMessagePromptTemplate.from_template(system_message_template)

    # Set up the prompt template with the system message
    chat_prompt = ChatPromptTemplate.from_messages([system_message_prompt])

    # Create the JSON agent with the ChatOpenAI model
    json_agent_executor = create_json_agent(
        llm=ChatOpenAI(temperature=0, model="gpt-3.5-turbo-0613"),
        toolkit=json_toolkit,
        chat_prompt_template=chat_prompt,  # Add the chat prompt template
        verbose=True,
        handle_parsing_errors=True
    )
    return json_agent_executor


def process_json_data(json_data):
    # This function can be used to preprocess or modify the JSON data if needed
    return json_data
