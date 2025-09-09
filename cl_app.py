# -*- coding: utf-8 -*-
"""Chainlit Chat Application"""
import os
import uuid
import logging

import chainlit as cl

from app.config.redis_config import get_session_manager
from app.agent.query_analyzer_agent import get_query_analyzer_agent
from app.agent.query_planning_agent import get_query_planning_agent
from app.agent.executor_agent import get_executor_agent
from app.agent.script_agent import get_script_agent

logger = logging.getLogger(__name__)

# 세션 매니저
session_manager = get_session_manager()


@cl.on_chat_start
async def on_chat_start():
    """채팅 시작 시 세션 초기화"""
    # Chainlit 세션 ID 사용
    session_id = cl.user_session.get("id") or str(uuid.uuid4())

    # Redis에 세션 생성
    session_manager.create_session(session_id)

    # Chainlit 세션에 저장
    cl.user_session.set("session_id", session_id)

    await cl.Message(
        content="안녕하세요! 암호화폐 뉴스 분석 챗봇입니다.\n\n"
                "예시 질문:\n"
                "- BTC 최근 이슈 알려줘\n"
                "- 이더리움 급등 원인 분석해줘\n"
                "- 솔라나 11월 시장 동향\n"
    ).send()


@cl.on_message
async def on_message(message: cl.Message):
    """사용자 메시지 처리"""
    session_id = cl.user_session.get("session_id")
    user_query = message.content

    # 메시지 저장
    session_manager.add_message(session_id, "user", user_query)

    # 처리 중 메시지
    msg = cl.Message(content="")
    await msg.send()

    try:
        # Step 1: Query Analyzer
        await msg.stream_token("분석 중...")
        analyzer = get_query_analyzer_agent()
        normalized_query = analyzer.analyze(user_query)

        # 컨텍스트 저장
        session_manager.update_context(session_id, {
            "last_normalized_query": normalized_query,
            "coins": normalized_query.get("target", {}).get("coin", [])
        })

        # Step 2: Query Planning
        await msg.stream_token("\n계획 수립 중...")
        planner = get_query_planning_agent()
        query_plan = planner.make_plan(normalized_query)

        # Step 3: Execute
        await msg.stream_token("\n데이터 수집 중...")
        executor = get_executor_agent()
        plan_result = executor.do_plan(
            query_plan=query_plan,
            original_query=user_query
        )

        # Step 4: Script Generation
        await msg.stream_token("\n응답 생성 중...\n\n")
        script_agent = get_script_agent()
        final_response = script_agent.generate(plan_result)

        # 최종 응답 - stream_token으로 추가
        await msg.stream_token(final_response)

        # 응답 저장
        session_manager.add_message(session_id, "assistant", final_response)

    except Exception as e:
        logger.error(f"Error processing message: {e}")
        msg.content = f"처리 중 오류가 발생했습니다: {str(e)}"
        await msg.update()


@cl.on_chat_end
async def on_chat_end():
    """채팅 종료 시 정리"""
    session_id = cl.user_session.get("session_id")
    if session_id:
        logger.info(f"Chat ended: {session_id}")
        # 세션 유지 (TTL로 자동 만료)


@cl.on_chat_resume
async def on_chat_resume(thread):
    """채팅 재개 시 히스토리 로드"""
    session_id = cl.user_session.get("session_id")

    if session_id:
        # Redis에서 메시지 히스토리 로드
        messages = session_manager.get_messages(session_id)

        # 이전 컨텍스트 확인
        session = session_manager.get_session(session_id)
        if session and session.get("context"):
            cl.user_session.set("context", session["context"])

        logger.info(f"Chat resumed: {session_id}, {len(messages)} messages")
