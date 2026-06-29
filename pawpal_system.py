"""PawPal system — core domain model.

Skeleton generated from diagrams/uml_draft.mmd.
Dataclasses hold state; method bodies implement the core logic.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, datetime, time, timedelta
from enum import Enum


# ---------------------------------------------------------------------------
# Enumerations
# ---------------------------------------------------------------------------
class TaskType(Enum):
    WALK = "walk"
    FEEDING = "feeding"
    MEDICATION = "medication"
    ENRICHMENT = "enrichment"
    GROOMING = "grooming"


class CareEventStatus(Enum):
    SCHEDULED = "scheduled"
    COMPLETED = "completed"
    CANCELLED = "cancelled"
    MISSED = "missed"


class RecurrenceFrequency(Enum):
    ONCE = "once"
    DAILY = "daily"
    WEEKLY = "weekly"


# ---------------------------------------------------------------------------
# Core entities
# ---------------------------------------------------------------------------
@dataclass
class Pet:
    pet_id: str
    name: str
    species: str
    breed: str
    age: int
    medical_notes: str = ""

    def update_medical(self, notes: str) -> None:
        """Append a note to this pet's medical history."""
        if self.medical_notes:
            self.medical_notes += f"; {notes}"
        else:
            self.medical_notes = notes

    def get_pet_details(self) -> str:
        """Return a human-readable summary of this pet."""
        return (
            f"{self.name} ({self.species}, {self.breed}), age {self.age}. "
            f"Medical notes: {self.medical_notes or 'none'}"
        )


@dataclass
class User:
    user_id: str
    name: str
    email: str
    pet_list: list[Pet] = field(default_factory=list)

    def add_pet(self, pet: Pet) -> None:
        """Add a pet to this user's list."""
        self.pet_list.append(pet)

    def remove_pet(self, pet_id: str) -> None:
        """Remove the pet with the given id from this user's list."""
        self.pet_list = [pet for pet in self.pet_list if pet.pet_id != pet_id]

    def get_pets(self) -> list[Pet]:
        """Return this user's list of pets."""
        return self.pet_list


# ---------------------------------------------------------------------------
# Recurrence
# ---------------------------------------------------------------------------
@dataclass
class RecurrenceRule:
    """Defines when a CareTask repeats."""

    frequency: RecurrenceFrequency = RecurrenceFrequency.ONCE
    interval: int = 1  # every N days/weeks
    days_of_week: list[int] = field(default_factory=list)  # 0=Mon .. 6=Sun (WEEKLY)
    start_date: date | None = None

    def occurs_on(self, day: date) -> bool:
        """Return True if this rule fires on the given day."""
        if self.frequency in (RecurrenceFrequency.ONCE, RecurrenceFrequency.DAILY):
            return True
        if self.frequency == RecurrenceFrequency.WEEKLY:
            return day.weekday() in self.days_of_week
        return False

    def next_date(self, after: date) -> date | None:
        """Return the next date this rule fires strictly after `after`.

        Uses timedelta so date math is calendar-accurate (it rolls over month
        and year boundaries for us). Returns None for ONCE rules, which never
        repeat.

        Algorithm:
            - DAILY: O(1) jump of `after + timedelta(days=interval)`.
            - WEEKLY with specific weekdays: scan the next 7 days and return
              the first whose weekday() is configured — O(7), i.e. constant.
            - WEEKLY without weekdays: O(1) jump of `timedelta(weeks=interval)`.
            - ONCE: returns None.

        Args:
            after: The reference date; the result is strictly later than this.

        Returns:
            The next firing date, or None if the rule never repeats.
        """
        if self.frequency == RecurrenceFrequency.DAILY:
            # "Daily" -> next due date is today + interval days (interval=1 by default).
            return after + timedelta(days=self.interval)

        if self.frequency == RecurrenceFrequency.WEEKLY:
            # If specific weekdays are set, find the next one within the coming week;
            # otherwise fall back to a plain "every N weeks" jump.
            if self.days_of_week:
                for offset in range(1, 8):
                    candidate = after + timedelta(days=offset)
                    if candidate.weekday() in self.days_of_week:
                        return candidate
            return after + timedelta(weeks=self.interval)

        return None  # ONCE: no next occurrence


# ---------------------------------------------------------------------------
# Care tasks (recurring templates)
# ---------------------------------------------------------------------------
@dataclass
class CareTask:
    """A recurring definition of care for a pet. Expanded into CareEvents per day."""

    task_id: str
    pet_id: str
    type: TaskType
    duration: int  # minutes
    priority: int = 0
    preferred_time: time | None = None
    recurrence: RecurrenceRule = field(default_factory=RecurrenceRule)

    def occurs_on(self, day: date) -> bool:
        """Return True if this task is due on the given day."""
        return self.recurrence.occurs_on(day)

    def create_event(self, event_id: str, day: date) -> CareEvent:
        """Build a concrete CareEvent for this task on the given day."""
        event_time = self.preferred_time or time(0, 0)
        return CareEvent(
            event_id=event_id,
            task_id=self.task_id,
            pet_id=self.pet_id,
            type=self.type,
            date_time=datetime.combine(day, event_time),
            duration=self.duration,
            priority=self.priority,
        )


@dataclass
class Walk(CareTask):
    distance: float = 0.0
    route: str = ""

    def record_distance(self, distance: float) -> None:
        """Set the distance covered for this walk."""
        self.distance = distance


@dataclass
class Feeding(CareTask):
    food_type: str = ""
    portion: str = ""

    def log_portion(self, portion: str) -> None:
        """Set the food portion given for this feeding."""
        self.portion = portion


# ---------------------------------------------------------------------------
# Care events (concrete dated occurrences)
# ---------------------------------------------------------------------------
@dataclass
class CareEvent:
    """A single scheduled occurrence of a CareTask on a specific date/time."""

    event_id: str
    task_id: str
    pet_id: str
    type: TaskType
    date_time: datetime
    duration: int  # minutes
    priority: int = 0
    status: CareEventStatus = CareEventStatus.SCHEDULED

    def reschedule(self, new_time: datetime) -> None:
        """Move this event to a new date/time."""
        self.date_time = new_time

    def update_status(self, status: CareEventStatus) -> None:
        """Set this event's status."""
        self.status = status


# ---------------------------------------------------------------------------
# Planning
# ---------------------------------------------------------------------------
@dataclass
class Constraints:
    available_minutes: int
    priority_weights: dict[TaskType, int] = field(default_factory=dict)
    owner_preferences: dict[str, str] = field(default_factory=dict)


@dataclass
class DailyPlan:
    date: date
    ordered_events: list[CareEvent] = field(default_factory=list)
    rationale: str = ""
    constraints: Constraints | None = None  # the inputs this plan was built from
    score: float = 0.0  # how well the plan satisfied the constraints

    def get_summary(self) -> str:
        """Return a formatted, multi-line summary of the plan and its reasoning."""
        lines = [f"Daily plan for {self.date.isoformat()}:"]
        if self.ordered_events:
            for i, event in enumerate(self.ordered_events, start=1):
                lines.append(
                    f"  {i}. {event.date_time.strftime('%H:%M')} - "
                    f"{event.type.value} ({event.duration} min)"
                )
        else:
            lines.append("  (no tasks scheduled)")
        lines.append("")
        lines.append(f"Reasoning: {self.rationale}")
        return "\n".join(lines)


class ScheduleManager:
    """Tracks care tasks/events for a set of pets and produces an explained daily plan.

    Note: tasks/events are kept as flat lists for simplicity. If volume grows,
    index by (day, pet_id) to avoid repeated O(n) scans.
    """

    def __init__(
        self,
        tasks: list[CareTask] | None = None,
        pets: dict[str, Pet] | None = None,
    ) -> None:
        """Initialize the manager with optional starting tasks and pet registry."""
        self.tasks: list[CareTask] = tasks if tasks is not None else []
        self.pets: dict[str, Pet] = pets if pets is not None else {}
        self.events: list[CareEvent] = []

    # --- write path -------------------------------------------------------
    def register_pet(self, pet: Pet) -> None:
        """Add a pet to the manager's registry."""
        self.pets[pet.pet_id] = pet

    def add_task(self, task: CareTask) -> None:
        """Add a care task to the manager."""
        self.tasks.append(task)

    def remove_task(self, task_id: str) -> None:
        """Remove a task and its generated events by task id."""
        self.tasks = [task for task in self.tasks if task.task_id != task_id]
        self.events = [event for event in self.events if event.task_id != task_id]

    def remove_pet(self, pet_id: str) -> None:
        """Remove a pet and cascade-delete its tasks/events."""
        self.pets.pop(pet_id, None)
        self.tasks = [task for task in self.tasks if task.pet_id != pet_id]
        self.events = [event for event in self.events if event.pet_id != pet_id]

    # --- queries ----------------------------------------------------------
    def _pet_name(self, pet_id: str) -> str:
        """Resolve a pet id to its display name, falling back to the id."""
        pet = self.pets.get(pet_id)
        return pet.name if pet else pet_id

    def get_tasks_for_pet(self, pet_id: str) -> list[CareTask]:
        """Return all tasks belonging to the given pet."""
        return [task for task in self.tasks if task.pet_id == pet_id]

    def get_tasks_by_type(self, type: TaskType) -> list[CareTask]:
        """Return all tasks of the given type."""
        return [task for task in self.tasks if task.type == type]

    def filter_tasks(self, pet_name: str | None = None) -> list[CareTask]:
        """Phase 1 (wishlist) filter: return tasks for the named pet.

        Tasks carry no status — only their generated CareEvents do — so the
        wishlist can only be filtered by pet. Name is matched
        case-insensitively against the pet registry. Omit pet_name to return
        all tasks (a copy, so callers can't mutate the internal list).
        """
        if pet_name is None:
            return list(self.tasks)

        wanted_ids = {
            pet_id
            for pet_id, pet in self.pets.items()
            if pet.name.lower() == pet_name.lower()
        }
        return [task for task in self.tasks if task.pet_id in wanted_ids]

    def sort_by_time(self) -> list[CareTask]:
        """Return tasks ordered by preferred_time, earliest first.

        Uses a lambda as the sort key that builds an "HH:MM" string for
        each task; strftime always zero-pads the hour, so lexicographic
        string order matches chronological order. Tasks with no
        preferred_time ("anytime") sort to the end.

        Algorithm:
            Single O(n log n) sort with a composite key
            (preferred_time is None, "HH:MM"). The leading bool sorts timed
            tasks (False) ahead of anytime tasks (True), so a None time is
            never compared against a real string. Non-mutating: returns a new
            list and leaves self.tasks untouched.

        Returns:
            A new list of tasks in ascending time order, anytime tasks last.
        """
        return sorted(
            self.tasks,
            key=lambda task: (
                task.preferred_time is None,
                task.preferred_time.strftime("%H:%M") if task.preferred_time else "",
            ),
        )

    def filter_events(
        self,
        status: CareEventStatus | None = None,
        pet_name: str | None = None,
    ) -> list[CareEvent]:
        """Return events matching the given status and/or pet name.

        Status lives on CareEvents (not CareTasks), so completion filtering
        works here. Both filters are optional and combined with AND: omit an
        argument to ignore it, pass both to narrow further. Pet name is matched
        case-insensitively against the pet registry.
        """
        wanted_ids = None
        if pet_name is not None:
            wanted_ids = {
                pet_id
                for pet_id, pet in self.pets.items()
                if pet.name.lower() == pet_name.lower()
            }

        return [
            event
            for event in self.events
            if (status is None or event.status == status)
            and (wanted_ids is None or event.pet_id in wanted_ids)
        ]

    def mark_overdue(self, now: datetime) -> list[CareEvent]:
        """Phase 2 (live schedule): flip still-scheduled past events to MISSED.

        Gives the MISSED status real data: any event still SCHEDULED whose end
        time (start + duration) is before `now` is treated as missed. Completed
        and cancelled events are left untouched. Returns the events changed so
        the caller can react (e.g. notify the owner).

        Algorithm:
            Single O(n) pass over self.events. Each event's end is computed as
            date_time + timedelta(minutes=duration) and compared to `now`;
            only SCHEDULED events can transition, so completed/cancelled/
            already-missed events are skipped.

        Args:
            now: The current moment; events ending before this are overdue.

        Returns:
            The list of events whose status was flipped to MISSED (possibly
            empty), in their original order within self.events.
        """
        missed: list[CareEvent] = []
        for event in self.events:
            if event.status != CareEventStatus.SCHEDULED:
                continue
            event_end = event.date_time + timedelta(minutes=event.duration)
            if event_end < now:
                event.update_status(CareEventStatus.MISSED)
                missed.append(event)
        return missed

    def complete_event(self, event_id: str) -> CareEvent | None:
        """Mark an event COMPLETED and auto-create its next occurrence.

        When a recurring task's event is finished, the next instance should be
        waiting. So we look up the originating task, ask its recurrence for the
        next date, and build a fresh CareEvent for that day. Returns the new
        event, or None when nothing was spawned: the event/task wasn't found,
        the task is one-time (ONCE), or that next occurrence already exists
        (so completing twice can't create duplicates).

        Algorithm:
            1. O(n) linear scan to find the event by id; mark it COMPLETED.
            2. O(m) linear scan to find its originating task by task_id.
            3. Delegate to RecurrenceRule.next_date to compute the next day.
            4. O(n) duplicate guard on the would-be event id before appending,
               which makes repeated completions idempotent.
            Overall O(n + m) where n = events, m = tasks.

        Args:
            event_id: Id of the event to complete.

        Returns:
            The newly created CareEvent for the next occurrence, or None when
            nothing was spawned (not found, one-time task, or duplicate).
        """
        event = next((e for e in self.events if e.event_id == event_id), None)
        if event is None:
            return None
        event.update_status(CareEventStatus.COMPLETED)

        task = next((t for t in self.tasks if t.task_id == event.task_id), None)
        if task is None:
            return None  # orphaned event (task was removed); nothing to repeat

        next_day = task.recurrence.next_date(event.date_time.date())
        if next_day is None:
            return None  # one-time task: nothing to repeat

        next_id = f"{task.task_id}@{next_day.isoformat()}"
        if any(e.event_id == next_id for e in self.events):
            return None  # next occurrence already scheduled; stay idempotent

        next_event = task.create_event(next_id, next_day)
        self.events.append(next_event)
        return next_event

    def detect_conflicts(self) -> list[str]:
        """Return warning messages for tasks whose time windows overlap.

        Lightweight, non-fatal check meant to *warn*, not stop the program:
        it compares each task's [preferred_time, preferred_time + duration)
        window against the others and returns one human-readable warning per
        overlapping pair — flagging whether it's the same pet or different
        pets. Tasks with no preferred_time ("anytime") can't clash on the
        clock and are skipped. Returns an empty list when nothing conflicts,
        so callers can simply check `if warnings:` instead of catching errors.

        Algorithm:
            Sort timed tasks by start minute (O(n log n)), then for each task
            scan forward only while later tasks could still overlap, breaking
            as soon as one starts at/after the current task's end. This makes
            the comparison phase output-sensitive: near-linear when few tasks
            overlap, O(n^2) only when many genuinely do (the cost of reporting
            every conflicting pair). Two tasks overlap when one starts before
            the other ends.

        Returns:
            A list of human-readable warning strings, one per overlapping
            pair; empty if there are no conflicts.
        """

        def minutes_of_day(t: time) -> int:
            return t.hour * 60 + t.minute

        timed = sorted(
            (task for task in self.tasks if task.preferred_time is not None),
            key=lambda task: minutes_of_day(task.preferred_time),
        )

        warnings: list[str] = []
        for index, task in enumerate(timed):
            start = minutes_of_day(task.preferred_time)
            end = start + task.duration
            for other in timed[index + 1 :]:
                other_start = minutes_of_day(other.preferred_time)
                if other_start >= end:
                    break  # sorted by start: nothing later can overlap `task`

                scope = (
                    "same pet"
                    if task.pet_id == other.pet_id
                    else "different pets"
                )
                warnings.append(
                    f"[CONFLICT] ({scope}) {task.type.value} for "
                    f"{self._pet_name(task.pet_id)} at "
                    f"{task.preferred_time.strftime('%H:%M')} overlaps "
                    f"{other.type.value} for {self._pet_name(other.pet_id)} at "
                    f"{other.preferred_time.strftime('%H:%M')}."
                )
        return warnings

    # --- planning ---------------------------------------------------------
    def generate_daily_plan(self, day: date, constraints: Constraints) -> DailyPlan:
        """Orchestrates the helpers below to build an explained plan for `day`."""
        due = self._due_tasks(day)
        events = [
            task.create_event(f"{task.task_id}@{day.isoformat()}", day) for task in due
        ]
        prioritized = self._prioritize(events, constraints)
        fitted = self._resolve_conflicts(prioritized, constraints)
        rationale = self._explain(fitted, constraints)
        score = len(fitted) / len(events) if events else 1.0

        # Refresh this manager's record of events for the planned day.
        self.events = [e for e in self.events if e.date_time.date() != day]
        self.events.extend(fitted)

        return DailyPlan(
            date=day,
            ordered_events=fitted,
            rationale=rationale,
            constraints=constraints,
            score=score,
        )

    def _due_tasks(self, day: date) -> list[CareTask]:
        """Tasks whose recurrence fires on `day`."""
        return [task for task in self.tasks if task.occurs_on(day)]

    def _prioritize(
        self, events: list[CareEvent], constraints: Constraints
    ) -> list[CareEvent]:
        """Order events by weighted priority + owner preferences."""

        def weight(event: CareEvent) -> int:
            base = event.priority * constraints.priority_weights.get(event.type, 1)
            preference = constraints.owner_preferences.get(event.type.value)
            if preference == "high":
                base += 100
            elif preference == "low":
                base -= 100
            return base

        # Highest weight first; ties broken by earlier scheduled time.
        return sorted(events, key=lambda event: (-weight(event), event.date_time))

    def _resolve_conflicts(
        self, events: list[CareEvent], constraints: Constraints
    ) -> list[CareEvent]:
        """Drop/shift overlapping events to fit available_minutes."""
        fitted: list[CareEvent] = []
        used_minutes = 0
        for event in events:
            if used_minutes + event.duration > constraints.available_minutes:
                continue  # over the time budget

            event_start = event.date_time
            event_end = event_start + timedelta(minutes=event.duration)
            overlaps = any(
                event_start < kept.date_time + timedelta(minutes=kept.duration)
                and kept.date_time < event_end
                for kept in fitted
            )
            if overlaps:
                continue

            fitted.append(event)
            used_minutes += event.duration
        return fitted

    def _explain(
        self, ordered_events: list[CareEvent], constraints: Constraints
    ) -> str:
        """Build the human-readable rationale for the chosen plan."""
        if not ordered_events:
            return "No care tasks were due, or none fit within the available time."

        total = sum(event.duration for event in ordered_events)
        parts = [
            f"Scheduled {len(ordered_events)} task(s) using {total} of "
            f"{constraints.available_minutes} available minutes, "
            f"ordered by priority."
        ]
        for event in ordered_events:
            weight = constraints.priority_weights.get(event.type, 1)
            parts.append(
                f"- {event.type.value} at {event.date_time.strftime('%H:%M')} "
                f"({event.duration} min, priority {event.priority} x weight {weight})"
            )
        return "\n".join(parts)
