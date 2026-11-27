"""Project-scoped Client Onboarding UI for the hosted Streamlit edition."""
from datetime import datetime, timezone
import streamlit as st


def render_client_onboarding(sb, uid, rows, add, remove, choose_project):
    st.subheader("Client Onboarding")
    st.caption("Development preview — use fictional, non-sensitive client details only.")
    pid = choose_project("client_onboarding_project")
    if not pid:
        return

    records = rows(
        "client_onboarding",
        "id,client_name,contact_name,contact_email,onboarding_status,notes,created_at,updated_at",
        project_id=pid,
    )
    statuses = ["Not started", "In progress", "Completed", "On hold"]
    record = records[0] if records else None
    if record:
        st.info("Edit the onboarding profile for this project.")
    else:
        st.info("Create an onboarding profile for this project.")

    with st.form("client_onboarding_form"):
        client_name = st.text_input("Fictional client name", value=record["client_name"] if record else "")
        contact_name = st.text_input("Fictional contact name", value=record["contact_name"] if record else "")
        contact_email = st.text_input("Fictional contact email", value=record["contact_email"] if record else "")
        current_status = record["onboarding_status"] if record else statuses[0]
        status = st.selectbox("Onboarding status", statuses, index=statuses.index(current_status))
        notes = st.text_area("Notes (fictional only)", value=record["notes"] if record else "")
        submitted = st.form_submit_button("Save onboarding profile")

    if submitted:
        if not client_name.strip():
            st.error("Client name is required.")
        else:
            values = {
                "client_name": client_name.strip(),
                "contact_name": contact_name.strip(),
                "contact_email": contact_email.strip(),
                "onboarding_status": status,
                "notes": notes.strip(),
            }
            try:
                if record:
                    values["updated_at"] = datetime.now(timezone.utc).isoformat()
                    sb.table("client_onboarding").update(values).eq("id", record["id"]).eq("project_id", pid).eq("user_id", uid).execute()
                else:
                    add("client_onboarding", {"project_id": pid, **values})
                st.rerun()
            except Exception:
                st.error("Unable to save onboarding profile. Please try again.")

    if record:
        with st.expander("Delete onboarding profile"):
            st.warning("This permanently deletes the onboarding profile, not the project.")
            confirm = st.checkbox("I understand this cannot be undone", key="onboarding_delete_confirm")
            if st.button("Permanently delete onboarding profile", disabled=not confirm):
                try:
                    remove("client_onboarding", record["id"])
                    st.rerun()
                except Exception:
                    st.error("Unable to delete onboarding profile.")
