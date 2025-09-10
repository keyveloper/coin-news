# -*- coding: utf-8 -*-
"""
Entry Agent - 대화 흐름 제어 및 세션 컨텍스트 활용

역할:
1. 사용자 메시지 분석 및 최적 경로 결정
2. 세션 컨텍스트 기반 단계 스킵
3. tools/entry_tools.py의 도구들을 사용
"""
import os
import logging
from pathlib import Path
from typing import Any, Dict, Optional

from langchain_anthropic import ChatAnthropic
from langsmith import traceable, trace

# Entry Tools - @tool 데코레이터 버전과 직접 호출 버전
from app.tools.entry_tools import (
    # @tool 데코레이터 버전 (LangChain Agent용)
    analyze_query,
    make_plan,
    execute_plan,
    generate_script,
    # 직접 호출 버전
    call_analyze_query,
    call_make_plan,
    call_execute_plan,
    call_generate_script,
)

logger = logging.getLogger(__name__)


class EntryAgent:
    """
    Entry Agent - 대화 흐름 제어

    세션 컨텍스트를 활용하여 최적의 처리 경로 결정
    """

    _instance: Optional["EntryAgent"] = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self):
        if hasattr(self, '_initialized') and self._initialized:
            return

        self.model_name = os.getenv("ANTHROPIC_ENTRY_MODEL", "claude-3-5-haiku-20241022")
        self.temperature = float(os.getenv("ENTRY_TEMPERATURE", "0.0"))
        self.timeout = float(os.getenv("ANTHROPIC_TIMEOUT", "30.0"))

        # Load prompts
        prompt_dir = Path(__file__).parent.parent / "prompt" / "entry"

        with open(prompt_dir / "system", 'r', encoding='utf-8') as f:
            self.system_prompt = f.read().strip()

        with open(prompt_dir / "decision", 'r', encoding='utf-8') as f:
            self.decision_prompt_template = f.read().strip()

        # 등록된 Tools (LangChain Agent용)
        self.tools = [
            analyze_query,
            make_plan,
            execute_plan,
            generate_script,
        ]

        self._initialized = True
        logger.info(f"EntryAgent initialized with model: {self.model_name}, tools: {len(self.tools)}")

    def _get_llm(self) -> ChatAnthropic:
        return ChatAnthropic(
            model_name=self.model_name,
            temperature=self.temperature,
            timeout=self.timeout,
            max_tokens=1024
        )

    def process(
        self,
        user_message: str,
        session_context: Optional[Dict] = None
    ) -> Dict[str, Any]:
        """
        사용자 메시지 처리

        Args:
            user_message: 사용자 입력
            session_context: 세션에 저장된 컨텍스트
                - last_normalized_query: 마지막 분석 결과
                - last_plan_result: 마지막 실행 결과
                - coins: 언급된 코인들

        Returns:
            {
                "response": str,  # 최종 응답
                "context_update": Dict,  # 세션에 저장할 업데이트
                "path": str  # 실행된 경로 (debug용)
            }
        """
        # 전체 워크플로우를 하나의 trace로 묶음
        with trace(
            name="ChatWorkflow",
            run_type="chain",
            inputs={"user_message": user_message, "has_context": bool(session_context)}
        ) as workflow_trace:
            logger.info(f"Processing message: {user_message}")
            session_context = session_context or {}

            # 세션 컨텍스트 분석
            # session_id: Chainlit에서 자동 관리 (cl.user_session)
            # 여기서는 "재사용 가능한 이전 분석 결과"가 있는지 확인
            previous_analysis = session_context.get("last_normalized_query")
            previous_result = session_context.get("last_plan_result")
            has_reusable_context = bool(previous_analysis and previous_result)

            previous_coins = session_context.get("coins", [])
            previous_intent = previous_analysis.get("intent_type") if previous_analysis else None

            # 이전 응답 요약 생성 (LLM이 관련성 판단에 사용)
            previous_response_summary = "없음"
            if previous_result:
                price_summary = previous_result.get("price_summary", "")[:200]
                news_summary = previous_result.get("news_summary", "")[:200]
                if price_summary or news_summary:
                    previous_response_summary = f"가격: {price_summary}... / 뉴스: {news_summary}..."

            # LLM으로 경로 결정
            llm = self._get_llm()

            decision_prompt = self.decision_prompt_template.format(
                user_message=user_message,
                has_previous=has_reusable_context,
                previous_coins=previous_coins,
                previous_intent=previous_intent,
                has_previous_result=bool(previous_result),
                previous_response_summary=previous_response_summary
            )

            messages = [
                {"role": "system", "content": self.system_prompt},
                {"role": "user", "content": decision_prompt}
            ]

            response = llm.invoke(messages)
            decision_text = response.content

            # 경로 파싱
            path = "FULL_PIPELINE"  # default
            if "PATH:" in decision_text:
                path_line = [l for l in decision_text.split("\n") if "PATH:" in l][0]
                path = path_line.split("PATH:")[1].strip().upper()

            logger.info(f"Decision path: {path}")

            # 경로별 실행
            context_update = {}

            try:
                if path == "DIRECT_RESPONSE" or "DIRECT" in path:
                    # 직접 응답 생성
                    direct_prompt = f"사용자 메시지에 간단히 응답하세요: {user_message}"
                    direct_response = llm.invoke([{"role": "user", "content": direct_prompt}])
                    result = {
                        "response": direct_response.content,
                        "context_update": {},
                        "path": "DIRECT_RESPONSE"
                    }

                elif path == "REUSE_RESULT" and previous_result:
                    # 기존 결과로 스크립트만 재생성
                    result_dict = previous_result.copy()
                    result_dict["original_query"] = user_message  # 새 질문으로 교체
                    final_response = call_generate_script(result_dict)
                    result = {
                        "response": final_response,
                        "context_update": {},
                        "path": "REUSE_RESULT"
                    }

                elif path == "REUSE_ANALYSIS" and previous_analysis:
                    # 기존 분석으로 계획부터 실행
                    normalized_query = previous_analysis
                    plan_dict = call_make_plan(normalized_query)
                    result_dict = call_execute_plan(plan_dict, user_message)
                    final_response = call_generate_script(result_dict)

                    context_update = {
                        "last_plan_result": result_dict
                    }
                    result = {
                        "response": final_response,
                        "context_update": context_update,
                        "path": "REUSE_ANALYSIS"
                    }

                else:
                    # 전체 파이프라인
                    normalized_query = call_analyze_query(user_message)
                    plan_dict = call_make_plan(normalized_query)
                    result_dict = call_execute_plan(plan_dict, user_message)
                    final_response = call_generate_script(result_dict)

                    context_update = {
                        "last_normalized_query": normalized_query,
                        "last_plan_result": result_dict,
                        "coins": normalized_query.get("target", {}).get("coin", [])
                    }
                    result = {
                        "response": final_response,
                        "context_update": context_update,
                        "path": "FULL_PIPELINE"
                    }

                # trace에 output 기록
                workflow_trace.end(outputs={"path": result["path"], "success": True})
                return result

            except Exception as e:
                logger.error(f"Error in path {path}: {e}", exc_info=True)
                workflow_trace.end(outputs={"path": path, "success": False, "error": str(e)})
                return {
                    "response": f"처리 중 오류가 발생했습니다: {str(e)}",
                    "context_update": {},
                    "path": f"ERROR_{path}"
                }


def get_entry_agent() -> EntryAgent:
    """EntryAgent 싱글톤 인스턴스 반환"""
    return EntryAgent()
