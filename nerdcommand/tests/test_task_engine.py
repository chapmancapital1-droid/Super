"""Task graph scheduling tests."""
from app.core.task_engine import TaskGraph
from app.models.schemas import Task, TaskStatus


def test_readiness_respects_dependencies():
    g = TaskGraph("build plan")
    t1 = Task(agent_id="researcher", goal="research")
    t2 = Task(agent_id="strategist", goal="strategy", depends_on=[t1.task_id])
    t3 = Task(agent_id="validator", goal="validate", depends_on=[t1.task_id, t2.task_id])
    g.add_task(t1); g.add_task(t2); g.add_task(t3)

    # Only t1 is ready initially.
    assert [t.task_id for t in g.ready_to_run()] == [t1.task_id]

    t1.status = TaskStatus.COMPLETE
    assert [t.task_id for t in g.ready_to_run()] == [t2.task_id]

    t2.status = TaskStatus.COMPLETE
    assert [t.task_id for t in g.ready_to_run()] == [t3.task_id]


def test_all_complete_only_when_done():
    g = TaskGraph("x")
    t1 = Task(agent_id="researcher", goal="a")
    g.add_task(t1)
    assert g.all_complete() is False
    t1.status = TaskStatus.COMPLETE
    assert g.all_complete() is True


def test_views_projection():
    g = TaskGraph("x")
    t1 = Task(agent_id="researcher", goal="a")
    g.add_task(t1)
    views = g.views()
    assert views[0].id == t1.task_id
    assert views[0].agent_id == "researcher"
