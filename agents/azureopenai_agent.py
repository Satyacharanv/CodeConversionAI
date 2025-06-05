import json
import os
from pathlib import Path
from click import prompt
from dotenv import load_dotenv
from langchain.agents import Tool
from agents.tools import get_folder_structure, list_directory
from models.migration import MigrationResult, PathInputSchema
from utils.file_utils import prepare_download_links
import asyncio
from langgraph.prebuilt import create_react_agent
from langchain_openai import AzureChatOpenAI
from langchain_core.messages import HumanMessage, SystemMessage
from pydantic import BaseModel
import logging

# Load environment variables
load_dotenv(dotenv_path=Path(__file__).parent.parent / ".env")

DEPLOYMENT_NAME = os.getenv("DEPLOYMENT_NAME")
AZURE_OPENAI_ENDPOINT = os.getenv("AZURE_OPENAI_ENDPOINT")
AZURE_OPENAI_API_KEY = os.getenv("AZURE_OPENAI_API_KEY")
AZURE_OPENAI_API_VERSION = os.getenv("AZURE_OPENAI_API_VERSION")

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)

def log_tool_call(tool_name, func):
    def wrapper(*args, **kwargs):
        logger.info("[TOOL CALLED] %s", tool_name)
        return func(*args, **kwargs)
    return wrapper

tools = [
    Tool(
        name="list_directory",
        func=log_tool_call("list_directory", list_directory),
        description="Lists the contents of a directory. Provide the full path to the directory.",
        input_schema=PathInputSchema
    ),
    Tool(
        name="get_folder_structure",
        func=log_tool_call("get_folder_structure", get_folder_structure),
        description="Gets the folder structure of a directory. Provide the full path to the directory.",
        input_schema=PathInputSchema
    ),
]

llm = AzureChatOpenAI(
    deployment_name=DEPLOYMENT_NAME,
    api_key=AZURE_OPENAI_API_KEY,
    openai_api_version=AZURE_OPENAI_API_VERSION,
    azure_endpoint=AZURE_OPENAI_ENDPOINT,
    temperature=1
)

prompt = "You are a helpful AI assistant. You can use the following tools to answer questions"
agent = create_react_agent(
    llm,
    tools,
    prompt=prompt
)

logger.info("Azure OpenAI agent and tools initialized.")