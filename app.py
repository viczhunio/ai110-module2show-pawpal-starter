from datetime import datetime, time

import streamlit as st
from pawpal_system import (
    CareEventStatus,
    CareTask,
    Constraints,
    Pet,
    ScheduleManager,
    TaskType,
    User,
)

# Human-readable priority labels <-> the numeric priority the scheduler ranks by.
PRIORITY_TO_NUM = {"low": 1, "medium": 2, "high": 3}
NUM_TO_PRIORITY = {num: label.title() for label, num in PRIORITY_TO_NUM.items()}

if "owner" not in st.session_state: 
    st.session_state.owner = User(user_id="u1", name="Alice", email="alice@example.com")
    st.session_state.manager = ScheduleManager()

owner = st.session_state.owner
manager = st.session_state.manager
st.set_page_config(page_title="PawPal+", page_icon="🐾", layout="centered")

st.title("🐾 PawPal+")

st.markdown(
    """
Welcome to the PawPal+ starter app.

This file is intentionally thin. It gives you a working Streamlit app so you can start quickly,
but **it does not implement the project logic**. Your job is to design the system and build it.

Use this app as your interactive demo once your backend classes/functions exist.
"""
)

with st.expander("Scenario", expanded=True):
    st.markdown(
        """
**PawPal+** is a pet care planning assistant. It helps a pet owner plan care tasks
for their pet(s) based on constraints like time, priority, and preferences.

You will design and implement the scheduling logic and connect it to this Streamlit UI.
"""
    )

with st.expander("What you need to build", expanded=True):
    st.markdown(
        """
At minimum, your system should:
- Represent pet care tasks (what needs to happen, how long it takes, priority)
- Represent the pet and the owner (basic info and preferences)
- Build a plan/schedule for a day that chooses and orders tasks based on constraints
- Explain the plan (why each task was chosen and when it happens)
"""
    )

st.divider()

st.subheader("Quick Demo Inputs (UI only)")
owner_name = st.text_input("Owner name", value="Jordan")
pet_name = st.text_input("Pet name", value="Mochi")
species = st.selectbox("Species", ["dog", "cat", "other"])

st.markdown("### Tasks")
st.caption("Add a few tasks. In your final version, these should feed into your scheduler.")

col1, col2, col3 = st.columns(3)
with col1:
    task_type = st.selectbox(
        "Task type", [t.value for t in TaskType], format_func=str.title
    )
with col2:
    duration = st.number_input("Duration (minutes)", min_value=1, max_value=240, value=20)
with col3:
    priority = st.selectbox("Priority", ["low", "medium", "high"], index=2)

preferred_time = st.time_input("Preferred time", value=time(8, 0))

if st.button("Add task"):
    if pet_name not in st.session_state.manager.pets:
        new_pet = Pet(
            pet_id=pet_name.lower(),
            name=pet_name,
            species=species,
            breed="Unknown",
            age=1
        )
        st.session_state.manager.register_pet(new_pet)

    next_id = f"task_{len(st.session_state.manager.tasks) + 1}"

    numeric_priority = PRIORITY_TO_NUM.get(priority, 1)

    new_task = CareTask(
        task_id=next_id,
        pet_id=pet_name.lower(),
        type=TaskType(task_type),
        duration=int(duration),
        priority=numeric_priority,
        preferred_time=preferred_time,
    )

    st.session_state.manager.add_task(new_task)

    st.success(
        f"Successfully registered {task_type} for {pet_name} at "
        f"{preferred_time.strftime('%H:%M')} in ScheduleManager!"
    )

# --- Wishlist, sorted chronologically by the scheduler -----------------------
if manager.tasks:
    st.write("**Current tasks** (sorted by time of day):")
    sorted_tasks = manager.sort_by_time()  # ScheduleManager.sort_by_time()
    rows = [
        {
            "Time": task.preferred_time.strftime("%H:%M")
            if task.preferred_time
            else "Anytime",
            "Pet": manager.pets[task.pet_id].name
            if task.pet_id in manager.pets
            else task.pet_id,
            "Task": task.type.value.title(),
            "Duration": f"{task.duration} min",
            "Priority": NUM_TO_PRIORITY.get(task.priority, str(task.priority)),
        }
        for task in sorted_tasks
    ]
    st.table(rows)

    # --- Conflict detection ---------------------------------------------------
    conflicts = manager.detect_conflicts()  # ScheduleManager.detect_conflicts()
    if conflicts:
        st.warning(
            f"⚠️ {len(conflicts)} scheduling conflict(s) found — "
            "these tasks want overlapping time slots:"
        )
        for message in conflicts:
            # Drop the internal "[CONFLICT] " tag for a pet-owner-friendly read.
            st.markdown(f"- {message.replace('[CONFLICT] ', '')}")
        st.caption(
            "💡 Tip: *same pet* overlaps can't happen at once — reschedule one. "
            "*Different pets* may be fine if you can care for both together, "
            "otherwise stagger their times."
        )
    else:
        st.success("✅ No time conflicts — every task has a clear slot.")
else:
    st.info("No tasks yet. Add one above.")

st.divider()

st.subheader("Build Schedule")
st.caption("This button should call your scheduling logic once you implement it.")

available = st.number_input(
    "Available minutes today", min_value=15, max_value=600, value=60
)

if st.button("Generate schedule"):
    now = datetime.now()

    # Phase 2: turn the task wishlist into a timed, conflict-resolved plan.
    constraints = Constraints(available_minutes=int(available))
    plan = manager.generate_daily_plan(now.date(), constraints)

    # Any scheduled event whose window has already passed is now MISSED.
    missed = manager.mark_overdue(now)

    st.text(plan.get_summary())
    st.caption(f"Plan score (fraction of due tasks scheduled): {plan.score:.2f}")

    if missed:
        st.warning(
            f"{len(missed)} task(s) were already overdue and marked MISSED."
        )

    # Live-schedule status breakdown, powered by filter_events().
    st.markdown("### Today's status")
    labels = {
        CareEventStatus.SCHEDULED: "⏳ Pending",
        CareEventStatus.COMPLETED: "✅ Completed",
        CareEventStatus.MISSED: "❌ Missed",
        CareEventStatus.CANCELLED: "🚫 Cancelled",
    }
    rows = []
    for status, label in labels.items():
        for event in manager.filter_events(status=status):
            pet = manager.pets.get(event.pet_id)
            rows.append(
                {
                    "Status": label,
                    "Pet": pet.name if pet else event.pet_id,
                    "Task": event.type.value,
                    "Time": event.date_time.strftime("%H:%M"),
                }
            )
    if rows:
        st.table(rows)
    else:
        st.info("No tasks were due today.")
