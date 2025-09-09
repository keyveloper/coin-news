# -*- coding: utf-8 -*-
"""Chainlit Chat Application with EntryAgent"""
import logging

import chainlit as cl

from app.agent.entry_agent import get_entry_agent

logger = logging.getLogger(__name__)


@cl.on_chat_start
async def on_chat_start():
    """채팅 시작 시 세션 초기화"""
    # Chainlit 메모리에 컨텍스트 초기화
    cl.user_session.set("context", {
        "last_normalized_query": None,
        "last_plan_result": None,
        "coins": [],
        "message_count": 0
    })

    await cl.Message(
        content="안녕하세요! 암호화폐 뉴스 분석 챗봇입니다.\n\n"
                "예시 질문:\n"
                "- BTC 최근 이슈 알려줘\n"
                "- 이더리움 급등 원인 분석해줘\n"
                "- 솔라나 11월 시장 동향\n\n"
                "후속 질문도 가능합니다:\n"
                "- 더 자세히 알려줘\n"
                "- 뉴스는 뭐가 있어?\n"
    ).send()


@cl.on_message
async def on_message(message: cl.Message):
    """사용자 메시지 처리 - EntryAgent 사용"""
    user_query = message.content

    # 디버그 명령어
    if user_query == "/debug":
        context = cl.user_session.get("context") or {}
        debug_info = {
            "message_count": context.get("message_count", 0),
            "coins": context.get("coins", []),
            "has_normalized_query": bool(context.get("last_normalized_query")),
            "has_plan_result": bool(context.get("last_plan_result")),
            "last_intent": context.get("last_normalized_query", {}).get("intent_type") if context.get("last_normalized_query") else None
        }
        await cl.Message(content=f"```json\n{debug_info}\n```").send()
        return

    # 처리 중 메시지
    msg = cl.Message(content="")
    await msg.send()

    try:
        # 세션 컨텍스트 로드
        context = cl.user_session.get("context") or {}

        await msg.stream_token("처리 중...")

        # EntryAgent 호출
        entry_agent = get_entry_agent()
        result = entry_agent.process(
            user_message=user_query,
            session_context=context
        )

        # 경로 표시 (디버그용)
        path = result.get("path", "UNKNOWN")
        await msg.stream_token(f"\n[{path}]\n\n")

        # 최종 응답
        await msg.stream_token(result["response"])

        # 컨텍스트 업데이트
        if result.get("context_update"):
            context.update(result["context_update"])

        context["message_count"] = context.get("message_count", 0) + 1
        cl.user_session.set("context", context)

        logger.info(f"Processed with path: {path}")

    except Exception as e:
        logger.error(f"Error processing message: {e}", exc_info=True)
        await msg.stream_token(f"\n\n처리 중 오류가 발생했습니다: {str(e)}")


@cl.on_chat_end
async def on_chat_end():
    """채팅 종료 시 로깅"""
    context = cl.user_session.get("context") or {}
    logger.info(f"Chat ended. Messages: {context.get('message_count', 0)}")
