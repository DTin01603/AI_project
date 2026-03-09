from research_agent.planning_agent import PlanningAgent


def test_planning_agent_fallback_plan_size_and_order() -> None:
    planner = PlanningAgent()

    plan = planner.create_plan("Phân tích chiến lược AI cho doanh nghiệp SMB")

    assert 1 <= len(plan) <= 5
    assert plan[0].order == 1
    assert all(item.query for item in plan)
