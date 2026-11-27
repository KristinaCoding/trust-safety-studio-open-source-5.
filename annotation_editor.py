"""Edit project annotations while preserving version-aware QA validity."""
import streamlit as st

LABELS = ["Helpful", "Needs improvement", "Off-topic", "Unclear", "Escalate for review"]


def render_annotation_editor(sb, uid, pid, annotations):
    if not annotations:
        return
    with st.expander("Edit existing annotation"):
        options = {item["id"]: item for item in annotations}
        selected = st.selectbox(
            "Annotation to edit", list(options),
            format_func=lambda key: f'{options[key]["sample_id"]} (v{options[key]["version"]})',
            key=f"edit_annotation_choice_{pid}",
        )
        current = options[selected]
        with st.form(f"edit_annotation_form_{selected}"):
            sample_id = st.text_input("Sample ID", value=current["sample_id"])
            sample_text = st.text_area("Fictional sample text", value=current["sample_text"])
            label = st.selectbox(
                "Classification", LABELS,
                index=LABELS.index(current["label"]) if current["label"] in LABELS else 0,
            )
            score = st.slider("Quality score", 1, 5, int(current["score"]))
            notes = st.text_area("Evaluation notes", value=current["notes"] or "")
            submitted = st.form_submit_button("Save annotation changes")
        if submitted:
            if not sample_id.strip() or not sample_text.strip():
                st.error("Sample ID and sample text are required.")
                return
            updates = {
                "sample_id": sample_id.strip(),
                "sample_text": sample_text.strip(),
                "label": label,
                "score": score,
                "notes": notes.strip(),
            }
            changed = any(updates[key] != current[key] for key in updates)
            if not changed:
                st.info("No changes to save.")
                return
            try:
                result = sb.table("annotations").update(updates).eq(
                    "id", selected
                ).eq("project_id", pid).eq("user_id", uid).eq(
                    "version", current["version"]
                ).select("id,version").execute()
                if not result.data:
                    st.warning("The annotation changed since it was loaded. Refresh before editing again.")
                    return
                st.success(f'Annotation saved as version {result.data[0]["version"]}. Previous QA approvals no longer qualify.')
                st.rerun()
            except Exception:
                st.error("Could not update annotation. Check permissions and refresh.")
