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
    def get_tasks_for_pet(self, pet_id: str) -> list[CareTask]:
        """Return all tasks belonging to the given pet."""
        return [task for task in self.tasks if task.pet_id == pet_id]

    def get_tasks_by_type(self, type: TaskType) -> list[CareTask]:
        """Return all tasks of the given type."""
        return [task for task in self.tasks if task.type == type]

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
