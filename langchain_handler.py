import json
from langchain.agents import create_json_agent
from langchain.llms.openai import OpenAI
from langchain.tools.json.tool import JsonSpec
from langchain.agents.agent_toolkits import JsonToolkit
from langchain.chat_models import ChatOpenAI
from langchain.agents.agent_types import AgentType

from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain.docstore import document


from langchain.prompts.chat import (
    ChatPromptTemplate,
    HumanMessagePromptTemplate,
    SystemMessagePromptTemplate,
)
from langchain.schema import HumanMessage, SystemMessage


def initialize_langchain_agent(json_data):
    print("Type of json_data:", type(json_data))
    print("Content of json_data:", json_data)
    # Ensure json_data is a dictionary
    if isinstance(json_data, str):
        try:
            json_data = json.loads(json_data)
        except json.JSONDecodeError:
            raise ValueError("Provided JSON data is neither a dict nor a JSON decodable string.")

    json_spec = JsonSpec(dict_=json_data, max_value_length=4000)
    json_toolkit = JsonToolkit(spec=json_spec)

    # Define the role for the model
    system_message_template = "You are a data analysis expert. Your task is to analyze complex data sets and extract meaningful insights into a comprehensive summary for the user."
    system_message_prompt = SystemMessagePromptTemplate.from_template(system_message_template)

    # Set up the prompt template with the system message
    chat_prompt = ChatPromptTemplate.from_messages([system_message_prompt])

    # Create the JSON agent with the ChatOpenAI model
    json_agent_executor = create_json_agent(
        llm=ChatOpenAI(temperature=0, model="gpt-3.5-turbo-0613"),
        toolkit=json_toolkit,
        chat_prompt_template=chat_prompt,
        verbose=True,
        handle_parsing_errors=True
    )
    return json_agent_executor


def split_json_data(json_data):
    # Convert JSON data to string if necessary
    text_data = json.dumps(json_data) if isinstance(json_data, dict) else str(json_data)
    splitter = RecursiveCharacterTextSplitter(chunk_size=1000, chunk_overlap=200)
    return splitter.split_text(text_data)


def process_json_data(json_data):
    # If json_data is a list, convert it to a JSON string
    if isinstance(json_data, list):
        json_data = json.dumps(json_data)
    
    # Split the large JSON data into chunks
    document_chunks = split_json_data(json_data)
    processed_data = []

    for chunk in document_chunks:
        processed_data.append(process_chunk(chunk))

    # Join the processed chunks into a single JSON string
    # Convert this JSON string back to a dictionary
    processed_data_json_string = json.dumps(processed_data)
    return json.loads(processed_data_json_string)




def process_chunk(chunk):
    # Example processing function (adjust as needed)
    return chunk  # Placeholder for actual processing

