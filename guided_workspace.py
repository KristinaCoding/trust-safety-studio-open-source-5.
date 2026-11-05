"""Guided workspace UI for KRISI Trust & Safety Studio v2."""
import streamlit as st

STEPS = [
    ("Create a project", "Projects", "Give your work a home before adding client details or reviewing content."),
    ("Onboard your client", "Client Onboarding", "Record the fictional client brief and working arrangements."),
    ("Set your policies", "Client Policies", "Add the rules that will guide review decisions."),
    ("Process work", "Ticket Intake", "Import tickets, manage cases, or annotate AI samples."),
    ("Review quality", "Quality Assurance", "Review completed work and approve the current annotation version."),
    ("Prepare a report", "Reports", "Review results and export the relevant project report."),
]

def navigate(section):
    st.session_state["workspace_page"] = section
    st.rerun()

def render_home(rows, choose_project):
    st.subheader("Welcome to your workspace")
    st.caption("Choose a project, follow your next step, or open a tool directly. Use fictional test data in this preview.")
    projects = rows("projects", "id,name")
    cases = rows("cases", "id,project_id")
    annotations = rows("annotations", "id,project_id")
    qa = rows("qa", "id,project_id")
    cols = st.columns(4)
    for col, label, value in zip(cols, ("Projects", "Cases", "Annotations", "QA reviews"), (len(projects), len(cases), len(annotations), len(qa))):
        col.metric(label, value)
    st.markdown("### Your guided workflow")
    if not projects:
        st.info("Start by creating a project. Your guide will adapt as you add records.")
        if st.button("Create my first project →", type="primary", use_container_width=True):
            navigate("Projects")
        return

    pid = choose_project("home_guide_project")
    if not pid:
        return
    onboarding = rows("client_onboarding", "id", project_id=pid)
    policies = rows("client_policies", "id", project_id=pid)
    tickets = rows("moderation_tickets", "id", project_id=pid)
    datasets = rows("ai_dataset_items", "id", project_id=pid)
    project_cases = [c for c in cases if c["project_id"] == pid]
    project_annotations = [a for a in annotations if a["project_id"] == pid]
    project_qa = [q for q in qa if q["project_id"] == pid]
    complete = [True, bool(onboarding), bool(policies),
                bool(tickets or datasets or project_cases or project_annotations),
                bool(project_qa), False]
    next_step = next((i for i, done in enumerate(complete) if not done), 5)
    st.progress(sum(complete[:5]) / 5, text=f"{sum(complete[:5])} of 5 setup and review milestones completed")
    with st.container(border=True):
        st.caption(f"RECOMMENDED NEXT STEP · {next_step + 1} / 6")
        title, destination, description = STEPS[next_step]
        st.markdown(f"#### {title}")
        st.write(description)
        if st.button(f"Open {destination} →", type="primary", key="next_step_button"):
            navigate(destination)
    with st.expander("Show all workflow steps", expanded=True):
        for i, (title, destination, description) in enumerate(STEPS):
            left, right = st.columns([5, 2])
            with left:
                st.markdown(f"{'✓' if complete[i] else '○'} **{i + 1}. {title}**")
                st.caption(description)
            with right:
                if st.button("Open →", key=f"guide_step_{i}", use_container_width=True):
                    navigate(destination)
    st.markdown("### Quick access")
    quick = [
        ("Review cases", "Moderation Cases"),
        ("Annotate samples", "AI Annotation"),
        ("Import dataset", "AI Dataset Intake"),
        ("Quality checks", "Quality Assurance"),
    ]
    for col, (label, destination) in zip(st.columns(4), quick):
        with col:
            if st.button(label, key=f"quick_{destination}", use_container_width=True):
                navigate(destination)

def render_help():
    st.subheader("Guides & Help")
    st.write("Follow these steps to move from a new project to a reviewed deliverable.")
    for i, (title, destination, description) in enumerate(STEPS, start=1):
        with st.expander(f"{i}. {title}"):
            st.write(description)
            if st.button(f"Go to {destination}", key=f"help_{i}"):
                navigate(destination)
    st.info("Quality approval is version-aware: editing an annotation requires a fresh QA review before export.")
