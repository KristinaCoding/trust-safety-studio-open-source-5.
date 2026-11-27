"""Project-scoped client policy management for the hosted Streamlit app."""
from datetime import datetime, timezone

import streamlit as st


STATUSES = ["Draft", "Active", "Archived"]
CATEGORIES = ["General", "Content Moderation", "Community Safety", "AI Evaluation", "Escalation", "Privacy", "Other"]


def render_client_policies(sb, uid, rows, add, remove, choose_project):
    st.subheader("Client Policies")
    st.caption("Development preview — enter fictional, non-sensitive policy examples only.")
    pid = choose_project("client_policies_project")
    if not pid:
        return

    policies = rows(
        "client_policies",
        "id,title,category,policy_text,version,status,created_at,updated_at",
        project_id=pid,
    )
    st.markdown("#### Existing policies")
    if policies:
        st.dataframe(
            [{k: v for k, v in item.items() if k != "policy_text"} for item in policies],
            use_container_width=True,
            hide_index=True,
        )
    else:
        st.info("No client policies for this project yet.")

    with st.expander("Create new policy", expanded=not bool(policies)):
        with st.form("create_client_policy", clear_on_submit=True):
            title = st.text_input("Policy title")
            category = st.selectbox("Category", CATEGORIES)
            policy_text = st.text_area("Policy text (fictional example)")
            status = st.selectbox("Status", STATUSES)
            submitted = st.form_submit_button("Create policy")
        if submitted:
            if not title.strip() or not policy_text.strip():
                st.error("Policy title and text are required.")
            else:
                try:
                    add("client_policies", {
                        "project_id": pid,
                        "title": title.strip(),
                        "category": category,
                        "policy_text": policy_text.strip(),
                        "version": 1,
                        "status": status,
                    })
                    st.rerun()
                except Exception:
                    st.error("Could not create policy. Check database permissions.")

    if not policies:
        return

    labels = {p["id"]: f'{p["title"]} (v{p["version"]}, {p["status"]})' for p in policies}
    chosen = st.selectbox("Select policy to edit", list(labels), format_func=lambda k: labels[k])
    record = next(p for p in policies if p["id"] == chosen)
    with st.form("edit_client_policy"):
        title = st.text_input("Policy title", value=record["title"])
        category = st.selectbox(
            "Category", CATEGORIES,
            index=CATEGORIES.index(record["category"]) if record["category"] in CATEGORIES else CATEGORIES.index("Other"),
        )
        policy_text = st.text_area("Policy text", value=record["policy_text"])
        status = st.selectbox("Status", STATUSES, index=STATUSES.index(record["status"]))
        st.caption(f'Current version: {record["version"]}. Editing title, category or text increments the version.')
        submitted = st.form_submit_button("Save policy changes")
    if submitted:
        if not title.strip() or not policy_text.strip():
            st.error("Policy title and text are required.")
        else:
            content_changed = (
                title.strip() != record["title"]
                or category != record["category"]
                or policy_text.strip() != record["policy_text"]
            )
            values = {
                "title": title.strip(),
                "category": category,
                "policy_text": policy_text.strip(),
                "status": status,
                "updated_at": datetime.now(timezone.utc).isoformat(),
            }
            if content_changed:
                values["version"] = record["version"] + 1
            try:
                sb.table("client_policies").update(values).eq("id", chosen).eq("project_id", pid).eq("user_id", uid).eq("version", record["version"]).execute()
                st.rerun()
            except Exception:
                st.error("Could not update policy. Refresh and try again.")

    with st.expander("Delete selected policy"):
        st.warning("Deleting a policy is permanent.")
        confirm = st.checkbox("I understand this cannot be undone", key="client_policy_delete_confirm")
        if st.button("Permanently delete policy", disabled=not confirm):
            try:
                remove("client_policies", chosen)
                st.rerun()
            except Exception:
                st.error("Could not delete policy.")
