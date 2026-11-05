"""A guided, project-aware home screen for KRISI Studio."""
import html
import streamlit as st

STEPS = [
    ("Create a project", "My Projects", "Set up a dedicated space for each client or evaluation."),
    ("Onboard your client", "Client Onboarding", "Capture the client brief and scope of work."),
    ("Define your policies", "Client Policies", "Document the rules behind review decisions."),
    ("Start your work", "Ticket Intake", "Import tickets, review cases, or annotate samples."),
    ("Review quality", "Quality Assurance", "Complete quality checks before delivery."),
    ("Prepare your report", "Reports", "Explore results and export your project report."),
]
QUICK_ACTIONS = [
    ("Review cases", "Moderation Cases", "Manage decisions and escalations."),
    ("AI annotations", "AI Annotation", "Classify and evaluate samples."),
    ("Dataset intake", "AI Dataset Intake", "Bring in evaluation data."),
    ("Quality reviews", "Quality Assurance", "Review and approve work."),
]

def navigate(section):
    st.session_state["workspace_page"] = section
    st.rerun()

def _project_progress(pid, rows, cases, annotations, qa):
    onboarding = bool(rows("client_onboarding", "id", project_id=pid))
    policies = bool(rows("client_policies", "id", project_id=pid))
    tickets = bool(rows("moderation_tickets", "id", project_id=pid))
    datasets = bool(rows("ai_dataset_items", "id", project_id=pid))
    work = tickets or datasets or any(x["project_id"] == pid for x in cases + annotations)
    reviews = any(x["project_id"] == pid for x in qa)
    return [True, onboarding, policies, work, reviews]

def render_home(rows, choose_project):
    st.markdown('<div class="krisi-eyebrow">YOUR PRIVATE WORKSPACE</div>', unsafe_allow_html=True)
    st.markdown("## Welcome back")
    st.write("Everything you need to manage trust, safety, and evaluation work — one step at a time.")

    projects = rows("projects", "id,name,project_type,status")
    cases = rows("cases", "id,project_id")
    annotations = rows("annotations", "id,project_id")
    qa = rows("qa", "id,project_id")
    for col, (label, value, note) in zip(st.columns(4), [
        ("PROJECTS", len(projects), "Your workspaces"),
        ("MODERATION CASES", len(cases), "Recorded decisions"),
        ("AI ANNOTATIONS", len(annotations), "Evaluated samples"),
        ("QA REVIEWS", len(qa), "Quality checks"),
    ]):
        with col:
            st.markdown(
                f'<div class="krisi-stat"><div class="krisi-stat-label">{label}</div>'
                f'<div class="krisi-stat-value">{value}</div>'
                f'<div class="krisi-stat-note">{note}</div></div>',
                unsafe_allow_html=True,
            )

    st.markdown("### Your projects")
    st.caption("Choose a project to see its next recommended action.")
    if not projects:
        with st.container(border=True):
            st.markdown("#### Your first project starts here")
            st.write("Create a project to unlock the guided workflow and keep work organized.")
            if st.button("Create my first project →", type="primary", key="create_first"):
                navigate("My Projects")
        return

    pid = choose_project("home_guide_project")
    if not pid:
        return
    project = next(p for p in projects if p["id"] == pid)
    completed = _project_progress(pid, rows, cases, annotations, qa)
    progress = sum(completed)
    next_step = next((i for i, done in enumerate(completed) if not done), 5)
    safe_name = html.escape(project["name"])
    safe_type = html.escape(project.get("project_type") or "Project")

    with st.container(border=True):
        st.markdown(
            f'<div class="krisi-eyebrow">SELECTED PROJECT</div>'
            f'<div class="krisi-project-name">{safe_name}</div>'
            f'<div class="krisi-project-type">{safe_type}</div>',
            unsafe_allow_html=True,
        )
        st.progress(progress / 5, text=f"{progress} of 5 setup and review milestones completed")
        a, b = st.columns(2)
        with a:
            if st.button("View project details", key="home_project_details", use_container_width=True):
                navigate("My Projects")
        with b:
            if st.button("Open reports", key="home_project_reports", use_container_width=True):
                navigate("Reports")

    st.markdown("### Continue working")
    title, destination, description = STEPS[next_step]
    with st.container(border=True):
        st.markdown(f'<div class="krisi-eyebrow">SUGGESTED NEXT ACTION · STEP {next_step + 1} OF 6</div>', unsafe_allow_html=True)
        st.markdown(f"#### {title}")
        st.write(description)
        if next_step == 5:
            st.caption("All five tracked setup and review milestones are complete. Reports can be generated whenever you need them.")
        if st.button(f"Continue to {destination} →", key="home_continue", type="primary", use_container_width=True):
            navigate(destination)

    with st.expander("Explore your complete workflow", expanded=False):
        for i, (title, destination, description) in enumerate(STEPS):
            left, right = st.columns([5, 2], vertical_alignment="center")
            with left:
                mark = "✓" if i < len(completed) and completed[i] else "○"
                st.markdown(f"**{mark}  {i + 1}. {title}**")
                st.caption(description)
            with right:
                if st.button("Open →", key=f"guide_step_{i}", use_container_width=True):
                    navigate(destination)

    st.markdown("### Quick actions")
    cols = st.columns(2)
    for i, (title, destination, description) in enumerate(QUICK_ACTIONS):
        with cols[i % 2]:
            with st.container(border=True):
                st.markdown(f"**{title}**")
                st.caption(description)
                if st.button(f"Open {title} →", key=f"quick_{i}", use_container_width=True):
                    navigate(destination)

def render_help():
    st.markdown('<div class="krisi-eyebrow">WORKSPACE COMPANION</div>', unsafe_allow_html=True)
    st.markdown("## Guides & Help")
    st.write("Not sure what comes next? Start with your project, then follow the steps below.")
    for i, (title, destination, description) in enumerate(STEPS, start=1):
        with st.expander(f"{i:02d} · {title}"):
            st.write(description)
            if st.button(f"Open {destination} →", key=f"help_{i}"):
                navigate(destination)
    st.info("When you edit an approved annotation, a new QA review is needed for the updated version.")
