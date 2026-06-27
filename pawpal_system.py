"""PawPal system — core domain model.

Skeleton generated from diagrams/uml_draft.mmd.
Dataclasses hold state; method bodies are left as stubs to fill in later.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, datetime
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
        pass

    def get_pet_details(self) -> str:
        pass


@dataclass
class User:
    user_id: str
    name: str
    email: str
    pet_list: list[Pet] = field(default_factory=list)

    def add_pet(self, pet: Pet) -> None:
        pass

    def remove_pet(self, pet_id: str) -> None:
        pass

    def get_pets(self) -> list[Pet]:
        pass


@dataclass
class CareEvent:
    """Base task: a single scheduled care activity for a pet."""

    event_id: str
    pet_id: str
    type: TaskType
    date_time: datetime
    duration: int  # minutes
    priority: int = 0
    status: CareEventStatus = CareEventStatus.SCHEDULED

    def reschedule(self, new_time: datetime) -> None:
        pass

    def update_status(self, status: CareEventStatus) -> None:
        pass


# ---------------------------------------------------------------------------
# CareEvent subclasses
# ---------------------------------------------------------------------------
@dataclass
class Walk(CareEvent):
    distance: float = 0.0
    route: str = ""

    def record_distance(self, distance: float) -> None:
        pass


@dataclass
class Feeding(CareEvent):
    food_type: str = ""
    portion: str = ""

    def log_portion(self, portion: str) -> None:
        pass


# ---------------------------------------------------------------------------
# Planning
# ---------------------------------------------------------------------------
@dataclass
class Constraints:
    available_minutes: int
    priority_weights: dict[str, int] = field(default_factory=dict)
    owner_preferences: dict[str, str] = field(default_factory=dict)


@dataclass
class DailyPlan:
    date: date
    ordered_events: list[CareEvent] = field(default_factory=list)
    rationale: str = ""

    def get_summary(self) -> str:
        pass


class ScheduleManager:
    """Tracks care events and produces an explained daily plan."""

    def __init__(self, events: list[CareEvent] | None = None) -> None:
        self.events: list[CareEvent] = events if events is not None else []

    def generate_daily_plan(self, day: date, constraints: Constraints) -> DailyPlan:
        pass

    def get_events_by_type(self, type: TaskType, day: date) -> list[CareEvent]:
        pass

    def get_events_for_pet(self, pet_id: str, day: date) -> list[CareEvent]:
        pass
