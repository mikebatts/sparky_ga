import json
from langchain.agents import create_json_agent
from langchain.llms.openai import OpenAI
from langchain.tools.json.tool import JsonSpec
from langchain.json.toolkit import JsonToolkit

def initialize_langchain_agent(json_data):
    json_spec = JsonSpec(dict_=json_data, max_value_length=4000)
    json_toolkit = JsonToolkit(spec=json_spec)
    json_agent_executor = create_json_agent(
        llm=OpenAI(temperature=0), toolkit=json_toolkit, verbose=True
    )
    return json_agent_executor

def process_json_data(json_data):
    # This function can be used to preprocess or modify the JSON data if needed
    return json_data
