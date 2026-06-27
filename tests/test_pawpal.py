"""Unit tests for the PawPal system."""

from datetime import datetime

from pawpal_system import (
    CareEvent,
    CareEventStatus,
    CareTask,
    ScheduleManager,
    TaskType,
)


def test_status_update():
    """update_status moves a CareEvent from SCHEDULED to COMPLETED."""
    event = CareEvent(
        event_id="e1",
        task_id="t1",
        pet_id="p1",
        type=TaskType.WALK,
        date_time=datetime(2026, 6, 27, 8, 0),
        duration=30,
    )

    assert event.status == CareEventStatus.SCHEDULED  # default

    event.update_status(CareEventStatus.COMPLETED)

    assert event.status == CareEventStatus.COMPLETED


def test_task_registration():
    """add_task appends a CareTask to the manager's tasks list."""
    manager = ScheduleManager()
    assert manager.tasks == []

    task = CareTask(task_id="t1", pet_id="p1", type=TaskType.FEEDING, duration=15)
    manager.add_task(task)

    assert len(manager.tasks) == 1
    assert manager.tasks[0] is task
