# Hands-On With LangGraph
## 1. Virtual Environment Setup
... bash
python -m venv venv
source venv/Scripts/activate
...

## 2. Installation
... bash
pip install -U langgraph langchain_anthropic typing-extensions IPython python-dotenv streamlit graphviz
...
The -U flag ensures you are getting the most up-to-date version

## 3. Creating a Basic Chatbot in LangGraph
(1) Import Necessary Libraries (main.py)
(2) Define the State Structure (main.py)
(3) Initialize the LLM
(4) Create the Chatbot Node
(5) Define Entry and Finish Points
(6) Compile the Graph
(7) Visualize the Graph
(8) Run the Chatbot


# Advanced LangGraph Techniques
## 1. Enhancing our Basic Chatbot with Tool Integration
(1) Add tavily api key
We’ll use the TavilySearchResults tool from langchain_community.tools.tavily_search . You will need Tavily API key for this example.
https://www.tavily.com/

(2) Install necessary packages
...bash
pip install -U tavily-python langchain_community
...

(3) build nodes and edges

(4) run app
... bash
streamlit run chat_app.py
...