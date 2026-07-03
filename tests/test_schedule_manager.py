"""Comprehensive tests for ScheduleManager planning and recurrence logic.

Covers the five target scenarios:

1. Happy path  - every due task fits within available_minutes.
2. Happy path  - priority ordering, dropping tasks that bust the time budget.
3. Edge case   - a pet with zero active tasks.
4. Edge case   - conflicting tasks sharing the exact same preferred_time.
5. Edge case   - a WEEKLY recurrence rule returns False on off-days.

Plus three explicit project-guideline requirements:

6. Sorting correctness  - sort_by_time returns tasks in chronological order.
7. Recurrence logic     - completing a DAILY task spawns the next day's event.
8. Conflict detection   - detect_conflicts flags duplicate preferred times.

Tests are written for pytest but use only plain ``assert`` statements, so
they also run cleanly under ``python -m unittest`` discovery style runners.
"""

from datetime import date, time

from pawpal_system import (
    CareEventStatus,
    CareTask,
    Constraints,
    Pet,
    RecurrenceFrequency,
    RecurrenceRule,
    ScheduleManager,
    TaskType,
)

# A fixed planning day (a Friday) used by the scheduling tests. Tasks below
# use ONCE recurrence, which fires on any day, so the specific date only needs
# to be stable — not meaningful.
PLAN_DAY = date(2026, 7, 3)


def _task(task_id, pet_id, task_type, duration, priority=0, preferred_time=None):
    """Build a CareTask with a ONCE recurrence (fires on every planning day)."""
    return CareTask(
        task_id=task_id,
        pet_id=pet_id,
        type=task_type,
        duration=duration,
        priority=priority,
        preferred_time=preferred_time,
    )


# ---------------------------------------------------------------------------
# 1. Happy path: all tasks fit within available_minutes.
# ---------------------------------------------------------------------------
def test_all_tasks_fit_within_budget():
    """Every due task is scheduled when the day's total fits the time budget."""
    manager = ScheduleManager()
    manager.register_pet(Pet("p1", "Rex", "dog", "lab", 3))

    # 30 + 20 + 15 = 65 minutes at distinct, non-overlapping times.
    manager.add_task(_task("t1", "p1", TaskType.WALK, 30, priority=5, preferred_time=time(8, 0)))
    manager.add_task(_task("t2", "p1", TaskType.FEEDING, 20, priority=5, preferred_time=time(9, 0)))
    manager.add_task(_task("t3", "p1", TaskType.ENRICHMENT, 15, priority=5, preferred_time=time(10, 0)))

    plan = manager.generate_daily_plan(PLAN_DAY, Constraints(available_minutes=120))

    # Nothing was dropped: 3 due tasks -> 3 scheduled events, perfect score.
    assert len(plan.ordered_events) == 3
    assert plan.score == 1.0
    scheduled_types = {event.type for event in plan.ordered_events}
    assert scheduled_types == {TaskType.WALK, TaskType.FEEDING, TaskType.ENRICHMENT}

    # The manager also records the fitted events for the planned day.
    assert len(manager.events) == 3
    assert all(e.status == CareEventStatus.SCHEDULED for e in manager.events)


# ---------------------------------------------------------------------------
# 2. Happy path: priority sorting, dropping over-budget lower-priority tasks.
# ---------------------------------------------------------------------------
def test_priority_ordering_drops_over_budget_tasks():
    """High-priority tasks are kept first; lower ones that bust the budget drop."""
    manager = ScheduleManager()
    manager.register_pet(Pet("p1", "Rex", "dog", "lab", 3))

    # Distinct times so drops are caused by the time budget, not overlap.
    # Budget = 70 min. Ordered by priority: high(30) + med(30) = 60 fits;
    # adding low(30) -> 90 > 70, so low is dropped.
    high = _task("t-high", "p1", TaskType.MEDICATION, 30, priority=10, preferred_time=time(8, 0))
    med = _task("t-med", "p1", TaskType.WALK, 30, priority=5, preferred_time=time(9, 0))
    low = _task("t-low", "p1", TaskType.GROOMING, 30, priority=1, preferred_time=time(10, 0))
    manager.add_task(low)   # add out of priority order to prove sorting happens
    manager.add_task(high)
    manager.add_task(med)

    plan = manager.generate_daily_plan(PLAN_DAY, Constraints(available_minutes=70))

    # Two of three tasks fit; the lowest priority one is dropped.
    assert len(plan.ordered_events) == 2
    assert plan.score == 2 / 3

    # Kept events are ordered highest-priority first.
    kept_ids = [event.task_id for event in plan.ordered_events]
    assert kept_ids == ["t-high", "t-med"]
    assert "t-low" not in kept_ids
    assert plan.ordered_events[0].priority > plan.ordered_events[1].priority


# ---------------------------------------------------------------------------
# 3. Edge case: a pet with zero active tasks.
# ---------------------------------------------------------------------------
def test_pet_with_no_tasks_produces_empty_plan():
    """A registered pet with no tasks yields an empty, well-formed plan."""
    manager = ScheduleManager()
    manager.register_pet(Pet("p1", "Ghost", "cat", "tabby", 2))

    assert manager.get_tasks_for_pet("p1") == []

    plan = manager.generate_daily_plan(PLAN_DAY, Constraints(available_minutes=120))

    assert plan.ordered_events == []
    # No tasks were due -> the "nothing scheduled" branch scores a full 1.0.
    assert plan.score == 1.0
    assert "No care tasks were due" in plan.rationale
    assert "(no tasks scheduled)" in plan.get_summary()
    assert manager.events == []


# ---------------------------------------------------------------------------
# 4. Edge case: conflicting tasks at the exact same preferred_time.
# ---------------------------------------------------------------------------
def test_conflicting_tasks_same_preferred_time():
    """Two tasks at the identical time are flagged, and only one is scheduled."""
    manager = ScheduleManager()
    manager.register_pet(Pet("p1", "Rex", "dog", "lab", 3))

    same_time = time(8, 0)
    keep = _task("t-keep", "p1", TaskType.WALK, 30, priority=5, preferred_time=same_time)
    drop = _task("t-drop", "p1", TaskType.FEEDING, 30, priority=1, preferred_time=same_time)
    manager.add_task(keep)
    manager.add_task(drop)

    # detect_conflicts warns about the overlapping pair (same pet, same clock).
    warnings = manager.detect_conflicts()
    assert len(warnings) == 1
    assert "[CONFLICT]" in warnings[0]
    assert "same pet" in warnings[0]

    # Budget is ample, so the drop is purely due to the time overlap:
    # the higher-priority task wins, the other is left out.
    plan = manager.generate_daily_plan(PLAN_DAY, Constraints(available_minutes=500))
    assert len(plan.ordered_events) == 1
    assert plan.ordered_events[0].task_id == "t-keep"
    assert plan.score == 0.5


# ---------------------------------------------------------------------------
# 5. Edge case: WEEKLY recurrence returns False on off-days.
# ---------------------------------------------------------------------------
def test_weekly_recurrence_false_on_off_days():
    """A Monday-only WEEKLY rule fires on Mondays and not on other days."""
    monday_only = RecurrenceRule(
        frequency=RecurrenceFrequency.WEEKLY,
        days_of_week=[0],  # 0 == Monday
    )

    monday = date(2026, 7, 6)     # weekday() == 0
    tuesday = date(2026, 7, 7)    # weekday() == 1
    next_monday = date(2026, 7, 13)

    # The rule itself.
    assert monday_only.occurs_on(monday) is True
    assert monday_only.occurs_on(tuesday) is False
    assert monday_only.occurs_on(next_monday) is True

    # And through a CareTask that carries the rule.
    task = CareTask(
        task_id="t-weekly",
        pet_id="p1",
        type=TaskType.WALK,
        duration=30,
        recurrence=monday_only,
    )
    assert task.occurs_on(monday) is True
    assert task.occurs_on(tuesday) is False

    # An off-day plan schedules nothing; the on-day plan schedules the task.
    manager = ScheduleManager()
    manager.register_pet(Pet("p1", "Rex", "dog", "lab", 3))
    manager.add_task(task)

    off_day_plan = manager.generate_daily_plan(tuesday, Constraints(available_minutes=120))
    assert off_day_plan.ordered_events == []

    on_day_plan = manager.generate_daily_plan(monday, Constraints(available_minutes=120))
    assert len(on_day_plan.ordered_events) == 1


# ---------------------------------------------------------------------------
# 6. Sorting correctness: sort_by_time returns tasks in chronological order.
# ---------------------------------------------------------------------------
def test_sort_by_time_is_chronological():
    """sort_by_time orders tasks earliest-first; 'anytime' (None) tasks sort last."""
    manager = ScheduleManager()
    # Deliberately added out of chronological order.
    manager.add_task(_task("late", "p1", TaskType.WALK, 30, preferred_time=time(10, 0)))
    manager.add_task(_task("early", "p1", TaskType.FEEDING, 10, preferred_time=time(8, 0)))
    manager.add_task(_task("anytime", "p1", TaskType.ENRICHMENT, 10, preferred_time=None))
    manager.add_task(_task("mid", "p1", TaskType.GROOMING, 10, preferred_time=time(9, 30)))

    ordered = manager.sort_by_time()

    # 08:00 -> 09:30 -> 10:00, then the untimed task at the end.
    assert [t.task_id for t in ordered] == ["early", "mid", "late", "anytime"]

    # The timed tasks are non-decreasing in time; verify pairwise ordering.
    timed = [t for t in ordered if t.preferred_time is not None]
    assert all(
        timed[i].preferred_time <= timed[i + 1].preferred_time
        for i in range(len(timed) - 1)
    )

    # Non-mutating: the manager's own task list keeps its insertion order.
    assert [t.task_id for t in manager.tasks] == ["late", "early", "anytime", "mid"]


# ---------------------------------------------------------------------------
# 7. Recurrence logic: completing a DAILY task creates the next day's event.
# ---------------------------------------------------------------------------
def test_completing_daily_task_spawns_next_day_event():
    """Marking a DAILY event complete auto-creates the following day's event."""
    manager = ScheduleManager()
    manager.register_pet(Pet("p1", "Rex", "dog", "lab", 3))

    task = CareTask(
        task_id="t-daily",
        pet_id="p1",
        type=TaskType.FEEDING,
        duration=15,
        preferred_time=time(8, 0),
        recurrence=RecurrenceRule(frequency=RecurrenceFrequency.DAILY),
    )
    manager.add_task(task)

    today = date(2026, 7, 3)
    today_event = task.create_event(f"t-daily@{today.isoformat()}", today)
    manager.events.append(today_event)

    new_event = manager.complete_event(today_event.event_id)

    # Today's event is completed...
    assert today_event.status == CareEventStatus.COMPLETED
    # ...and a fresh SCHEDULED event exists for the *next* day (today + 1).
    assert new_event is not None
    assert new_event.date_time.date() == date(2026, 7, 4)
    assert new_event.status == CareEventStatus.SCHEDULED
    assert new_event.task_id == "t-daily"
    assert new_event in manager.events
    assert len(manager.events) == 2

    # Idempotent: completing again does not create a duplicate next-day event.
    assert manager.complete_event(today_event.event_id) is None
    assert len(manager.events) == 2


# ---------------------------------------------------------------------------
# 8. Conflict detection: detect_conflicts flags duplicate preferred times.
# ---------------------------------------------------------------------------
def test_detect_conflicts_flags_duplicate_times():
    """Tasks sharing a time are flagged; non-overlapping ones are not."""
    manager = ScheduleManager()
    manager.register_pet(Pet("p1", "Rex", "dog", "lab", 3))
    manager.register_pet(Pet("p2", "Milo", "dog", "beagle", 5))

    # Two tasks at the identical 08:00 slot for different pets -> a conflict.
    manager.add_task(_task("t1", "p1", TaskType.WALK, 30, preferred_time=time(8, 0)))
    manager.add_task(_task("t2", "p2", TaskType.FEEDING, 20, preferred_time=time(8, 0)))
    # A third, well-separated task that must NOT be flagged.
    manager.add_task(_task("t3", "p1", TaskType.GROOMING, 15, preferred_time=time(12, 0)))

    warnings = manager.detect_conflicts()

    # Exactly one conflicting pair is reported.
    assert len(warnings) == 1
    message = warnings[0]
    assert "[CONFLICT]" in message
    assert "different pets" in message  # t1 (Rex) vs t2 (Milo)
    assert "08:00" in message
    # The clearly-separated 12:00 task is not implicated.
    assert "12:00" not in message

    # No false positives when every task is at a distinct, non-overlapping time.
    clean = ScheduleManager()
    clean.add_task(_task("a", "p1", TaskType.WALK, 30, preferred_time=time(8, 0)))
    clean.add_task(_task("b", "p1", TaskType.FEEDING, 20, preferred_time=time(9, 0)))
    assert clean.detect_conflicts() == []
