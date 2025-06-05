import streamlit as st
from main import graph, State
from dotenv import load_dotenv
import os
from langchain_core.messages import AIMessage, ToolMessage

# Load environment variables
load_dotenv()
anthropic_api_key = os.getenv('ANTHROPIC_API_KEY')
tavily_api_key = os.getenv('TAVILY_API_KEY')

# API 키 검증
if not anthropic_api_key or not tavily_api_key:
    st.error("환경변수에 ANTHROPIC_API_KEY와 TAVILY_API_KEY가 설정되지 않았습니다.")
    st.stop()

# 페이지 설정
st.set_page_config(page_title="LangGraph 챗봇", page_icon="💬")
st.title("LangGraph 챗봇")

def extract_search_results_from_messages(messages):
    """메시지에서 Tavily 검색 결과를 추출"""
    search_results = []
    
    for message in messages:
        # ToolMessage에서 Tavily 검색 결과 찾기
        if isinstance(message, ToolMessage):
            try:
                content = message.content
                # content가 문자열인 경우 JSON 파싱 시도
                if isinstance(content, str):
                    import json
                    results = json.loads(content)
                    if isinstance(results, list):
                        search_results.extend(results)
                # content가 이미 리스트인 경우
                elif isinstance(content, list):
                    search_results.extend(content)
            except (json.JSONDecodeError, TypeError):
                continue
        
        # AIMessage에서 tool_calls가 있는 경우도 확인
        elif isinstance(message, AIMessage) and hasattr(message, 'tool_calls'):
            tool_calls = getattr(message, 'tool_calls', [])
            for tool_call in tool_calls:
                if hasattr(tool_call, 'name') and 'tavily' in tool_call.name.lower():
                    # tool_call에서 검색 결과 추출 시도
                    pass
    
    return search_results

def format_search_sources(search_results):
    """검색 결과를 소스 링크 형태로 포맷팅"""
    if not search_results:
        return []
    
    sources = []
    for result in search_results[:10]:  # 상위 10개만
        if isinstance(result, dict):
            title = result.get('title', '')
            url = result.get('url', '')
            score = result.get('score', 0)
            
            if title and url:
                # 관련성 점수가 있는 경우 표시
                if score > 0:
                    relevance = f" (관련성: {score:.1%})"
                else:
                    relevance = ""
                sources.append(f"[{title}]({url}){relevance}")
    
    return sources

def get_final_response_and_sources(response):
    """LangGraph 응답에서 최종 답변과 검색 소스를 추출"""
    if not isinstance(response, dict) or "messages" not in response:
        return str(response), []
    
    messages = response["messages"]
    
    # 검색 결과 추출
    search_results = extract_search_results_from_messages(messages)
    sources = format_search_sources(search_results)
    
    # 최종 AI 응답 찾기
    final_answer = ""
    for message in reversed(messages):
        if isinstance(message, AIMessage):
            content = message.content
            # content가 리스트인 경우 (예: [{'text': '...', 'type': 'text'}])
            if isinstance(content, list):
                for item in content:
                    if isinstance(item, dict) and item.get('type') == 'text':
                        final_answer = item.get('text', '')
                        break
                if final_answer:
                    break
            # content가 문자열인 경우
            elif isinstance(content, str):
                final_answer = content
                break
    
    return final_answer, sources

# 세션 상태 초기화
if "messages" not in st.session_state:
    st.session_state.messages = []

# 채팅 기록 표시
for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])
        # 소스가 있는 경우 표시
        if message.get("sources"):
            st.markdown("---")
            st.markdown("### 📚 참고 자료")
            for source in message["sources"]:
                st.markdown(f"• {source}")

# 사용자 입력
if prompt := st.chat_input("메시지를 입력하세요"):
    # 사용자 메시지 추가
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)

    # 챗봇 응답 생성
    with st.chat_message("assistant"):
        try:
            with st.spinner("생각 중..."):
                # LangGraph를 통해 응답 생성
                response = graph.invoke({"messages": [("user", prompt)]})
                
                # 응답과 소스 추출
                final_answer, sources = get_final_response_and_sources(response)
                
                # 답변 표시
                if final_answer:
                    st.markdown(final_answer)
                else:
                    st.markdown("응답을 생성할 수 없습니다.")
                
                # 소스가 있는 경우 표시
                if sources:
                    st.markdown("---")
                    st.markdown("### 📚 참고 자료")
                    for source in sources:
                        st.markdown(f"• {source}")
                
                # 메시지 저장
                st.session_state.messages.append({
                    "role": "assistant",
                    "content": final_answer or "응답을 생성할 수 없습니다.",
                    "sources": sources
                })
                
        except Exception as e:
            error_msg = f"오류가 발생했습니다: {str(e)}"
            st.error(error_msg)
            st.session_state.messages.append({
                "role": "assistant", 
                "content": error_msg,
                "sources": []
            })

# 사이드바에 디버깅 정보 (선택적)
with st.sidebar:
    st.header("디버깅 정보")
    if st.checkbox("응답 구조 보기"):
        if st.session_state.messages:
            st.json({"total_messages": len(st.session_state.messages)})
    
    if st.checkbox("상세 디버깅"):
        st.write("마지막 LangGraph 응답 구조를 확인하려면 이 옵션을 체크하세요.")
    
    if st.button("대화 기록 초기화"):
        st.session_state.messages = []
        st.rerun()