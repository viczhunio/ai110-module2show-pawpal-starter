# PawPal+ (Module 2 Project)

You are building **PawPal+**, a Streamlit app that helps a pet owner plan care tasks for their pet.

## Scenario

A busy pet owner needs help staying consistent with pet care. They want an assistant that can:

- Track pet care tasks (walks, feeding, meds, enrichment, grooming, etc.)
- Consider constraints (time available, priority, owner preferences)
- Produce a daily plan and explain why it chose that plan

Your job is to design the system first (UML), then implement the logic in Python, then connect it to the Streamlit UI.

## What you will build

Your final app should:

- Let a user enter basic owner + pet info
- Let a user add/edit tasks (duration + priority at minimum)
- Generate a daily schedule/plan based on constraints and priorities
- Display the plan clearly (and ideally explain the reasoning)
- Include tests for the most important scheduling behaviors

## Getting started

### Setup

```bash
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate
pip install -r requirements.txt
```

### Suggested workflow

1. Read the scenario carefully and identify requirements and edge cases.
2. Draft a UML diagram (classes, attributes, methods, relationships).
3. Convert UML into Python class stubs (no logic yet).
4. Implement scheduling logic in small increments.
5. Add tests to verify key behaviors.
6. Connect your logic to the Streamlit UI in `app.py`.
7. Refine UML so it matches what you actually built.

## 🖥️ Sample Output

Paste a sample of your app's CLI or Streamlit output here so a reader can see what a generated plan looks like:

```
Alice has 2 pets:
  - Buddy (Dog, Labrador), age 4. Medical notes: none
  - Whiskers (Cat, Tabby), age 2. Medical notes: none

All Registered Tasks for Today:
  - [WALK] for Buddy at 08:00 (30 min, Priority: 2)
  - [FEEDING] for Whiskers at 13:00 (15 min, Priority: 5)
  - [GROOMING] for Buddy at 19:00 (20 min, Priority: 1)

Daily plan for 2026-06-27:
  1. 13:00 - feeding (15 min)
  2. 08:00 - walk (30 min)

Reasoning: Scheduled 2 task(s) using 45 of 60 available minutes, ordered by priority.
- feeding at 13:00 (15 min, priority 5 x weight 1)
- walk at 08:00 (30 min, priority 2 x weight 1)

Plan score (fraction of due tasks scheduled): 0.67

```

## 🧪 Testing PawPal+

```bash
# Run the full test suite:
pytest

# Run with coverage:
pytest --cov
```

Sample test output:

```
=================================================== test session starts ====================================================
platform win32 -- Python 3.14.5, pytest-9.1.1, pluggy-1.6.0
rootdir: C:\Users\victo\Downloads\AI110-Codepath\pawpal-starter
collected 10 items                                                                                                           

tests\test_pawpal.py ..                                                                                               [ 20%]
tests\test_schedule_manager.py ........                                                                                [100%]

==================================================== 10 passed in 0.06s ====================================================
```       
### Test Coverage Summary       
The test suite verifies the core backend behaviors of the pet scheduler application across both happy paths and tricky edge cases. Specifically, it validates that active tasks are successfully sorted into their chronological or strict priority order, ensures recurring tasks accurately transition and handle calculation logic across day changes, and checks that the system properly flags time budget or overlapping event constraints. It also confirms stable and robust performance under boundary conditions, such as when processing empty profiles or matching identical task schedules.           

### Confidence Level
⭐ ⭐ ⭐ ⭐ ⭐ (5/5 Stars)      
**Rationale:** The system successfully passed all 10 unit tests focusing on robust priority routing, time conflict detection, and complex edge cases without a single failure or regression. 


## 📐 Smarter Scheduling

Beyond the basic daily plan, PawPal+ implements four "smarter scheduling"
behaviors. All of them live on `ScheduleManager` (and `RecurrenceRule`) in
`pawpal_system.py`.

| Feature | Method(s) | Notes |
|---------|-----------|-------|
| Sorting | `ScheduleManager.sort_by_time()` | Orders the task wishlist by time of day, earliest first; "anytime" tasks last |
| Filtering | `ScheduleManager.filter_tasks()`, `ScheduleManager.filter_events()` | Filter the wishlist by pet, and the live schedule by pet and/or completion status |
| Conflict detection | `ScheduleManager.detect_conflicts()` | Non-fatal warnings for overlapping time windows (same pet or different pets) |
| Recurring tasks | `RecurrenceRule.next_date()`, `ScheduleManager.complete_event()` | Completing a daily/weekly task auto-creates the next occurrence |

### Sorting behavior — `sort_by_time()`

Returns a new list of tasks ordered by `preferred_time`, earliest first. The
sort key is a lambda that builds a zero-padded `"HH:MM"` string, so
lexicographic order matches chronological order. Tasks with no `preferred_time`
("anytime") are pushed to the end via a composite `(is_none, "HH:MM")` key, and
the method is non-mutating — `self.tasks` is left untouched.

### Filtering behavior — `filter_tasks()` and `filter_events()`

Filtering is split across the two project phases:

- **Wishlist (before scheduling):** `filter_tasks(pet_name=...)` returns the
  `CareTask`s for a given pet (case-insensitive name match). Tasks carry no
  status, so the wishlist can only be filtered by pet.
- **Live schedule (after scheduling):** `filter_events(status=..., pet_name=...)`
  filters the generated `CareEvent`s by **completion status**
  (`SCHEDULED`/`COMPLETED`/`MISSED`/`CANCELLED`) and/or pet. Both arguments are
  optional and combined with AND, so `filter_events(status=COMPLETED)` answers
  "what's done?" and `filter_events(status=SCHEDULED)` answers "what's still
  pending?".

Supporting method: `mark_overdue(now)` flips still-`SCHEDULED` past events to
`MISSED`, so the status filter has real data to find.

### Conflict detection logic — `detect_conflicts()`

Scans the task wishlist and returns a list of human-readable warning strings —
one per overlapping pair — flagging whether the clash is for the **same pet** or
**different pets**. Two tasks conflict when one starts before the other ends
(comparing `[preferred_time, preferred_time + duration)` windows). It is
deliberately **non-fatal**: it returns warnings rather than raising, so callers
just check `if warnings:`. An empty list means no conflicts. Tasks with no
`preferred_time` can't clash on the clock and are skipped.

### Recurring task logic — `next_date()` and `complete_event()`

- `RecurrenceRule.next_date(after)` computes the next firing date using
  `timedelta` for calendar-accurate math (it rolls over month/year boundaries):
  **daily** → `after + timedelta(days=interval)` (i.e. today + 1 day by
  default), **weekly** → the next configured weekday (or `timedelta(weeks=interval)`),
  **once** → `None`.
- `ScheduleManager.complete_event(event_id)` marks an event `COMPLETED` and, if
  its task recurs, automatically creates a fresh `CareEvent` for the next
  occurrence. It is idempotent — completing the same event twice won't create a
  duplicate, and one-time (`ONCE`) tasks spawn nothing.

## 📸 Demo Walkthrough

Describe your app in numbered steps so a reader can follow along without watching a video:

1. <!-- Describe this step -->
2. <!-- Describe this step -->
3. <!-- Describe this step -->
4. <!-- Describe this step -->
5. <!-- Add more steps as needed -->

**Screenshot or video** *(optional)*: <!-- Insert a screenshot or link to a demo video here -->
