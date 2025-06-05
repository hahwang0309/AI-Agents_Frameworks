#---------------------------------------------------------------------------------#
#                                                                                 #
#                              Hands-On With LangGraph                            #
#                                                                                 #
#---------------------------------------------------------------------------------#

# (1) Import Necessary Libraries
from typing import Annotated
from typing_extensions import TypedDict
from langgraph.graph import StateGraph, START, END
from langgraph.graph.message import add_messages
from dotenv import load_dotenv
import os
import graphviz

# Load environment variables from .env file
load_dotenv()
anthropic_api_key = os.getenv('ANTHROPIC_API_KEY')
tavily_api_key = os.getenv('TAVILY_API_KEY')


# (2) Define the State Structure
class State(TypedDict):
    # 'messages' will store the chatbot conversation history.
    # The 'add_messages' function ensures new messages are appended to the list.
    messages: Annotated[list, add_messages]

# Create an instance of the StateGraph, passing in the State class
graph_builder = StateGraph(State)


# (3) Initialize the LLM
from langchain_anthropic import ChatAnthropic

llm = ChatAnthropic(model="claude-3-5-sonnet-20240620")


# (4) Create the Chatbot Node
def chatbot(state: State):
    # Use the LLM to generate a response based on the current conversation history.
    response = llm.invoke(state["messages"])

    # Return the updated state with the new message appended
    return {"messages": [response]}

# Add the 'chatbot' node to the graph,
graph_builder.add_node("chatbot", chatbot)


# (5) Define Entry and Finish Points
 # For this basic chatbot, the 'chatbot' node is both the entry and finish point
graph_builder.add_edge(START, "chatbot")
graph_builder.add_edge("chatbot", END)


# (6) Compile the Graph
graph = graph_builder.compile()




#---------------------------------------------------------------------------------#
#                                                                                 #
#                          Advanced LangGraph Techniques                          #
#                                                                                 #
#---------------------------------------------------------------------------------#

from typing import Annotated
from langchain_anthropic import ChatAnthropic
from langchain_community.tools.tavily_search import TavilySearchResults
from langchain_core.messages import BaseMessage
from typing_extensions import TypedDict

from langgraph.graph import StateGraph
from langgraph.graph.message import add_messages
from langgraph.prebuilt import ToolNode, tools_condition


class State(TypedDict):
    messages: Annotated[list, add_messages]


graph_builder = StateGraph(State)

# Tools
tool = TavilySearchResults(max_results=5)
# add more tools here
tools = [tool] # list of tools

# LLM with Tools
llm = ChatAnthropic(model="claude-3-5-sonnet-20240620")
llm_with_tools = llm.bind_tools(tools)

# Nodes and Edges
# Chatbot Node
def chatbot(state: State):
    return {"messages": [llm_with_tools.invoke(state["messages"])]}
graph_builder.add_node("chatbot", chatbot)

# Tool Node
tool_node = ToolNode(tools=[tool])
graph_builder.add_node("tools", tool_node)

# Conditional Edges
graph_builder.add_conditional_edges(
    "chatbot",
    tools_condition, # AI가 도구를 호출했으면 tools 노드로, 아니면 대화 종료
)
# Any time a tool is called, we return to the chatbot to decide the next step
graph_builder.add_edge("tools", "chatbot")
graph_builder.set_entry_point("chatbot")
graph = graph_builder.compile()