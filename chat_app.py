import streamlit as st
from main import graph, State
from dotenv import load_dotenv
import os
from langchain_core.messages import AIMessage, ToolMessage

# Load environment variables
load_dotenv()

# API 키 검증
anthropic_api_key = os.getenv('ANTHROPIC_API_KEY')
tavily_api_key = os.getenv('TAVILY_API_KEY')

if not anthropic_api_key:
    st.error("ANTHROPIC_API_KEY가 설정되지 않았습니다. .env 파일을 확인해주세요.")
    st.stop()
if not tavily_api_key:
    st.error("TAVILY_API_KEY가 설정되지 않았습니다. .env 파일을 확인해주세요.")
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
    
    # 검색 결과를 관련성 점수(score) 기준으로 정렬
    sorted_results = sorted(
        search_results,
        key=lambda x: x.get('score', 0),
        reverse=True  # 높은 점수순으로 정렬
    )
    
    # 관련성 점수가 0.5 이상인 결과만 필터링
    filtered_results = [
        result for result in sorted_results 
        if result.get('score', 0) >= 0.5
    ]
    
    # 상위 10개 결과만 선택
    top_results = filtered_results[:10]
    
    sources = []
    for result in top_results:
        if isinstance(result, dict):
            title = result.get('title', '')
            url = result.get('url', '')
            score = result.get('score', 0)
            
            if title and url:
                # 관련성 점수를 백분율로 표시
                relevance = f"{score * 100:.1f}%"
                sources.append(f"[{title}]({url}) (관련성: {relevance})")
    
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
if "thread_id" not in st.session_state:
    st.session_state.thread_id = "1"

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
                config = {"configurable": {"thread_id": st.session_state.thread_id}}
                
                # 이전 대화 내용을 포함한 메시지 생성
                messages = []
                for msg in st.session_state.messages:
                    if msg["role"] == "user":
                        messages.append(("user", msg["content"]))
                    elif msg["role"] == "assistant":
                        messages.append(("assistant", msg["content"]))
                
                # 스트리밍 응답을 위한 컨테이너 생성
                response_container = st.empty()
                
                # 스트리밍 응답 처리
                final_answer = ""
                all_sources = []  # 리스트로 변경하여 순서 유지
                
                for event in graph.stream({"messages": messages}, config):
                    for value in event.values():
                        if "messages" in value and value["messages"]:
                            last_message = value["messages"][-1]
                            
                            # 검색 결과 처리
                            if isinstance(last_message, ToolMessage):
                                search_results = extract_search_results_from_messages([last_message])
                                new_sources = format_search_sources(search_results)
                                # 중복 제거하면서 순서 유지
                                for source in new_sources:
                                    if source not in all_sources:
                                        all_sources.append(source)
                            
                            # AI 응답 처리
                            elif isinstance(last_message, AIMessage):
                                if isinstance(last_message.content, str):
                                    final_answer = last_message.content
                                elif isinstance(last_message.content, list):
                                    for item in last_message.content:
                                        if isinstance(item, dict) and item.get('type') == 'text':
                                            final_answer = item.get('text', '')
                                            break
                                
                                # 실시간으로 응답 업데이트
                                if final_answer:
                                    response_container.markdown(final_answer)
                
                # 모든 소스를 한 번에 표시
                if all_sources:
                    st.markdown("---")
                    st.markdown("### 📚 참고 자료")
                    for source in all_sources:  # 이미 정렬된 순서로 표시
                        st.markdown(f"• {source}")
                
                # 최종 메시지 저장
                st.session_state.messages.append({
                    "role": "assistant",
                    "content": final_answer or "응답을 생성할 수 없습니다.",
                    "sources": all_sources
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
            st.json({
                "total_messages": len(st.session_state.messages),
                "thread_id": st.session_state.thread_id
            })
    
    if st.checkbox("상세 디버깅"):
        st.write("마지막 LangGraph 응답 구조를 확인하려면 이 옵션을 체크하세요.")
    
    if st.button("대화 기록 초기화"):
        st.session_state.messages = []
        st.session_state.thread_id = str(int(st.session_state.thread_id) + 1)  # 새로운 thread_id 생성
        st.rerun()