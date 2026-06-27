"""Demo script for the PawPal system.

Builds a user, pets, and a few care tasks, then generates and prints a
daily plan so you can see which tasks fit the time budget and why.
"""

from datetime import date, time

from pawpal_system import (
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

    for task in (morning_walk, afternoon_feeding, evening_grooming):
        manager.add_task(task)

    # --- Show everything that was registered before scheduling -----------
    print("All Registered Tasks for Today:")
    for task in manager.tasks:
        pet = manager.pets.get(task.pet_id)
        pet_name = pet.name if pet else task.pet_id
        when = task.preferred_time.strftime("%H:%M") if task.preferred_time else "anytime"
        print(
            f"  - [{task.type.value.upper()}] for {pet_name} at {when} "
            f"({task.duration} min, Priority: {task.priority})"
        )
    print()

    # --- Constraints & plan ----------------------------------------------
    constraints = Constraints(available_minutes=60)

    plan = manager.generate_daily_plan(date.today(), constraints)

    print(plan.get_summary())
    print(f"\nPlan score (fraction of due tasks scheduled): {plan.score:.2f}")


if __name__ == "__main__":
    main()
