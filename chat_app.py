import streamlit as st
from main import graph, State
from dotenv import load_dotenv
import os

# Load environment variables
load_dotenv()
anthropic_api_key = os.getenv('ANTHROPIC_API_KEY')
tavily_api_key = os.getenv('TAVILY_API_KEY')

# 페이지 설정
st.set_page_config(page_title="LangGraph 챗봇", page_icon="💬")
st.title("LangGraph 챗봇")

# 세션 상태 초기화
if "messages" not in st.session_state:
    st.session_state.messages = []

# 채팅 기록 표시
for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])

# 사용자 입력
if prompt := st.chat_input("메시지를 입력하세요"):
    # 사용자 메시지 추가
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)

    # 챗봇 응답 생성
    with st.chat_message("assistant"):
        with st.spinner("생각 중..."):
            # LangGraph를 통해 응답 생성
            for event in graph.stream({"messages": [("user", prompt)]}):
                for value in event.values():
                    response = value["messages"][-1].content
                    st.markdown(response)
                    st.session_state.messages.append({"role": "assistant", "content": response}) 
