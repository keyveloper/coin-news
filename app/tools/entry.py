from typing import Dict

from pywin.framework.toolmenu import tools


@tools
def tool_analyze_query(self, query: str) -> Dict:
    """쿼리 분석 도구"""
    logger.info(f"[Tool] analyze_query: {query}")
    return self.analyzer.analyze(query)


def _tool_make_plan(self, normalized_query: Dict) -> Dict:
    """계획 생성 도구"""
    logger.info(f"[Tool] make_plan: {normalized_query.get('intent_type')}")
    plan = self.planner.make_plan(normalized_query)
    return plan.model_dump()

def _tool_execute_plan(self, plan_dict: Dict, original_query: str) -> Dict:
    """계획 실행 도구"""
    logger.info(f"[Tool] execute_plan: {plan_dict.get('intent_type')}")
    from app.schemas.query_plan import QueryPlan
    plan = QueryPlan(**plan_dict)
    result = self.executor.do_plan(plan, original_query)
    return result.model_dump()

def _tool_generate_script(self, result_dict: Dict) -> str:
    """스크립트 생성 도구"""
    logger.info(f"[Tool] generate_script")
    from app.schemas.plan_result import PlanResult
    result = PlanResult(**result_dict)
    return self.script_agent.generate(result)