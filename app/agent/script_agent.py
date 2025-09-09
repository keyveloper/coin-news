# -*- coding: utf-8 -*-
"""
Script Agent - PlanResult를 기반으로 최종 사용자 응답 생성

역할:
1. PlanResult의 요약 데이터를 분석
2. 사용자의 원본 쿼리에 맞는 종합 분석 스크립트 생성
3. 최종 응답 반환
"""
import os
import logging
from typing import Optional

from langchain_anthropic import ChatAnthropic
from langsmith import traceable

from app.schemas.plan_result import PlanResult

logger = logging.getLogger(__name__)


SCRIPT_SYSTEM_PROMPT = """당신은 암호화폐 시장 분석 전문가입니다.

[역할]
수집된 가격 데이터 요약과 뉴스 요약을 바탕으로 사용자의 질문에 대한 종합 분석을 제공합니다.

[출력 형식]
1. 핵심 답변 (2-3문장)
2. 가격 분석 (있는 경우)
3. 뉴스/이슈 분석 (있는 경우)
4. 결론

[규칙]
- 제공된 데이터만 사용
- 추측이나 예측 금지
- 간결하고 명확한 답변"""


class ScriptAgent:
    """Script Agent - 최종 사용자 응답 생성"""

    _instance: Optional["ScriptAgent"] = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self):
        if hasattr(self, '_initialized') and self._initialized:
            return

        self.model_name = os.getenv("ANTHROPIC_SCRIPT_MODEL_NAME", "claude-3-5-haiku-20241022")
        self.temperature = float(os.getenv("SCRIPT_TEMPERATURE", "0.3"))
        self.timeout = float(os.getenv("ANTHROPIC_TIMEOUT", "60.0"))

        self._initialized = True
        logger.info(f"ScriptAgent initialized with model: {self.model_name}")

    def _get_llm(self) -> ChatAnthropic:
        """LLM 인스턴스 반환"""
        return ChatAnthropic(
            model_name=self.model_name,
            temperature=self.temperature,
            timeout=self.timeout,
            max_tokens=2048,
            stop=None
        )

    @traceable(name="ScriptAgent.generate", run_type="llm")
    def generate(self, plan_result: PlanResult) -> str:
        """
        PlanResult를 기반으로 최종 응답 생성

        Args:
            plan_result: Executor에서 생성된 PlanResult

        Returns:
            사용자에게 전달할 최종 응답 문자열
        """
        logger.info(f"Generating script for query: {plan_result.original_query}")

        llm = self._get_llm()

        # 사용자 프롬프트 구성
        user_prompt = f"""[사용자 질문]
{plan_result.original_query}

[분석 유형]
{plan_result.intent_type}

[대상 코인]
{', '.join(plan_result.coin_names) if plan_result.coin_names else '없음'}

[가격 데이터 분석]
{plan_result.price_summary if plan_result.price_summary else '가격 데이터 없음'}

[뉴스 분석]
{plan_result.news_summary if plan_result.news_summary else '관련 뉴스 없음'}

위 정보를 바탕으로 사용자의 질문에 대한 종합 분석을 제공하세요."""

        messages = [
            {"role": "system", "content": SCRIPT_SYSTEM_PROMPT},
            {"role": "user", "content": user_prompt}
        ]

        try:
            response = llm.invoke(messages)
            script = response.content.strip()
            logger.info(f"Script generated: {len(script)} chars")
            return script

        except Exception as e:
            error_msg = f"스크립트 생성 실패: {str(e)}"
            logger.error(error_msg, exc_info=True)
            return error_msg


def get_script_agent() -> ScriptAgent:
    """Get ScriptAgent singleton instance"""
    return ScriptAgent()
