"""Demo script for the PawPal system.

Builds a user, pets, and a few care tasks, then generates and prints a
daily plan so you can see which tasks fit the time budget and why.
"""

from datetime import date, datetime, time

from pawpal_system import (
    CareEventStatus,
    CareTask,
    Constraints,
    Feeding,
    Pet,
    RecurrenceFrequency,
    RecurrenceRule,
    ScheduleManager,
    TaskType,
    User,
    Walk,
)


def main() -> None:
    # --- User & pets ------------------------------------------------------
    alice = User(user_id="u1", name="Alice", email="alice@example.com")

    buddy = Pet(pet_id="p1", name="Buddy", species="Dog", breed="Labrador", age=4)
    whiskers = Pet(pet_id="p2", name="Whiskers", species="Cat", breed="Tabby", age=2)
    alice.add_pet(buddy)
    alice.add_pet(whiskers)

    print(f"{alice.name} has {len(alice.get_pets())} pets:")
    for pet in alice.get_pets():
        print(f"  - {pet.get_pet_details()}")
    print()

    # --- Schedule manager & care tasks -----------------------------------
    manager = ScheduleManager()
    manager.register_pet(buddy)
    manager.register_pet(whiskers)

    daily = RecurrenceRule(frequency=RecurrenceFrequency.DAILY)

    # Morning walk for Buddy: longer, medium priority.
    morning_walk = Walk(
        task_id="t1",
        pet_id="p1",
        type=TaskType.WALK,
        duration=30,
        priority=2,
        preferred_time=time(8, 0),
        recurrence=daily,
    )
    # Afternoon feeding for Whiskers: short, high priority.
    afternoon_feeding = Feeding(
        task_id="t2",
        pet_id="p2",
        type=TaskType.FEEDING,
        duration=15,
        priority=5,
        preferred_time=time(13, 0),
        recurrence=daily,
    )
    # Evening grooming for Buddy: medium length, low priority.
    evening_grooming = CareTask(
        task_id="t3",
        pet_id="p1",
        type=TaskType.GROOMING,
        duration=20,
        priority=1,
        preferred_time=time(19, 0),
        recurrence=daily,
    )

    # Scheduled at the EXACT same time as Buddy's 08:00 walk, on purpose, to
    # trigger conflict detection below. Different pet, identical time slot.
    clashing_feeding = Feeding(
        task_id="t4",
        pet_id="p2",
        type=TaskType.FEEDING,
        duration=10,
        priority=4,
        preferred_time=time(8, 0),
        recurrence=daily,
    )

    # Added intentionally OUT OF time order (evening, then morning, then
    # afternoon) so sort_by_time() has something real to reorder below.
    for task in (evening_grooming, morning_walk, afternoon_feeding, clashing_feeding):
        manager.add_task(task)

    def describe(task: CareTask) -> str:
        pet = manager.pets.get(task.pet_id)
        pet_name = pet.name if pet else task.pet_id
        when = task.preferred_time.strftime("%H:%M") if task.preferred_time else "anytime"
        return (
            f"[{task.type.value.upper()}] for {pet_name} at {when} "
            f"({task.duration} min, Priority: {task.priority})"
        )

    # --- Show tasks in the order they were added (unsorted) --------------
    print("All Registered Tasks (insertion order):")
    for task in manager.tasks:
        print(f"  - {describe(task)}")
    print()

    # --- Phase 1 demo: sort_by_time() ------------------------------------
    print("Tasks sorted by time (sort_by_time):")
    for task in manager.sort_by_time():
        print(f"  - {describe(task)}")
    print()

    # --- Phase 1 demo: filter_tasks() by pet -----------------------------
    print("Wishlist filtered to Buddy (filter_tasks):")
    for task in manager.filter_tasks(pet_name="Buddy"):
        print(f"  - {describe(task)}")
    print()

    # --- Phase 1 demo: detect_conflicts() (warn, don't crash) ------------
    conflicts = manager.detect_conflicts()
    if conflicts:
        print(f"Detected {len(conflicts)} scheduling conflict(s):")
        for warning in conflicts:
            print(f"  {warning}")
    else:
        print("No scheduling conflicts detected.")
    print()

    # --- Constraints & plan ----------------------------------------------
    constraints = Constraints(available_minutes=60)

    plan = manager.generate_daily_plan(date.today(), constraints)

    print(plan.get_summary())
    print(f"\nPlan score (fraction of due tasks scheduled): {plan.score:.2f}")
    print()

    # --- Phase 2 demo: mark_overdue() + filter_events() by status --------
    # Pretend it's just after 14:00, so anything scheduled earlier is overdue.
    now = datetime.combine(date.today(), time(14, 0))
    missed = manager.mark_overdue(now)
    print(f"mark_overdue(14:00) flipped {len(missed)} task(s) to MISSED.")

    print("\nLive schedule by status (filter_events):")
    for status in (
        CareEventStatus.SCHEDULED,
        CareEventStatus.COMPLETED,
        CareEventStatus.MISSED,
    ):
        events = manager.filter_events(status=status)
        names = [e.type.value for e in events] or ["(none)"]
        print(f"  {status.value:>9}: {', '.join(names)}")

    # --- Phase 2 demo: complete_event() auto-creates next occurrence -----
    # The grooming is a DAILY task still scheduled for today. Completing it
    # should both mark it done AND spawn tomorrow's instance automatically.
    print("\nCompleting today's daily grooming...")
    grooming_id = f"t3@{date.today().isoformat()}"
    spawned = manager.complete_event(grooming_id)
    if spawned:
        print(
            f"  -> Auto-created next occurrence: {spawned.type.value} on "
            f"{spawned.date_time.date().isoformat()} at "
            f"{spawned.date_time.strftime('%H:%M')} (status: {spawned.status.value})"
        )
    print(
        f"  Today was {date.today().isoformat()}; "
        f"next grooming is exactly one day later."
    )


if __name__ == "__main__":
    main()
