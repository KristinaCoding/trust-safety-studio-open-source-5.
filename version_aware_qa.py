"""Version-aware QA and approved AI annotation CSV export."""
import csv
import io

import streamlit as st

OUTCOMES = ["Pass", "Needs correction", "Escalate"]


def _latest_reviews(reviews):
    latest = {}
    # created_at is assigned by the database; UUID is a deterministic tie-breaker.
    for review in sorted(reviews, key=lambda r: (r["created_at"] or "", r["id"])):
        latest[(review["item_type"], review["item_id"])] = review
    return latest


def render_version_aware_qa(sb, uid, rows, add, remove, choose_project):
    st.subheader("Quality Assurance")
    pid = choose_project("qa_project")
    if not pid:
        return

    kind = st.selectbox("Review item type", ["Moderation case", "AI annotation"])
    source = "cases" if kind == "Moderation case" else "annotations"
    columns = "id,sample_id,label,version" if kind == "AI annotation" else "id,category,status"
    items = rows(source, columns, project_id=pid)
    if items:
        choices = {item["id"]: item for item in items}
        with st.form("qa_form", clear_on_submit=True):
            chosen = st.selectbox(
                "Record", list(choices),
                format_func=lambda key: (
                    f'{choices[key]["sample_id"]} (v{choices[key]["version"]})'
                    if kind == "AI annotation"
                    else f'{choices[key]["category"]} ({key})'
                ),
            )
            result = st.selectbox("QA outcome", OUTCOMES)
            notes = st.text_area("QA findings")
            submitted = st.form_submit_button("Save QA review")
        if submitted:
            if not notes.strip():
                st.error("Add a QA note.")
            else:
                try:
                    payload = {
                        "project_id": pid, "item_type": kind,
                        "item_id": chosen, "result": result, "notes": notes.strip(),
                    }
                    if kind == "AI annotation":
                        current = sb.table("annotations").select("id,version").eq(
                            "id", chosen
                        ).eq("project_id", pid).eq("user_id", uid).execute().data or []
                        if not current or current[0]["version"] != choices[chosen]["version"]:
                            st.warning("Annotation changed while reviewing. Refresh and review its current version.")
                            return
                        payload["reviewed_version"] = current[0]["version"]
                    add("qa", payload)
                    st.rerun()
                except Exception:
                    st.error("Could not save QA review. Check permissions and refresh.")
    else:
        st.info("Add a case or annotation before reviewing it.")

    reviews = rows(
        "qa", "id,item_type,item_id,result,notes,reviewed_version,created_at",
        project_id=pid,
    )
    latest = _latest_reviews(reviews)
    annotations = rows(
        "annotations",
        "id,sample_id,sample_text,label,score,notes,version,created_at",
        project_id=pid,
    )

    st.markdown("#### QA review history")
    if reviews:
        st.dataframe(
            sorted(reviews, key=lambda r: (r["created_at"] or "", r["id"]), reverse=True),
            use_container_width=True, hide_index=True,
        )
    else:
        st.info("No QA reviews yet.")

    st.markdown("#### Annotation QA status")
    status_rows = []
    approved = []
    for annotation in annotations:
        review = latest.get(("AI annotation", annotation["id"]))
        if review is None:
            status = "Not reviewed"
        elif review["reviewed_version"] is None:
            status = "Re-review required (legacy QA)"
        elif review["reviewed_version"] != annotation["version"]:
            status = "Outdated QA"
        elif review["result"] == "Pass":
            status = "Approved"
            approved.append(annotation)
        else:
            status = review["result"]
        status_rows.append({
            "sample_id": annotation["sample_id"],
            "version": annotation["version"],
            "latest_qa": review["result"] if review else "None",
            "reviewed_version": review["reviewed_version"] if review else None,
            "status": status,
        })
    if status_rows:
        st.dataframe(status_rows, use_container_width=True, hide_index=True)
    else:
        st.info("No annotations for this project.")

    st.markdown("#### Approved dataset export")
    st.caption("Only annotations whose latest QA review is Pass for their current version are eligible. Dataset intake approval alone does not qualify.")
    st.metric("Currently QA-approved annotations", len(approved))
    if approved:
        output = io.StringIO()
        writer = csv.writer(output)
        writer.writerow(["sample_id", "sample_text", "label", "score", "notes", "annotation_version"])
        for a in sorted(approved, key=lambda a: (a["sample_id"], a["id"])):
            writer.writerow([a["sample_id"], a["sample_text"], a["label"], a["score"], a["notes"], a["version"]])
        st.download_button(
            "Download QA-approved annotations (CSV)",
            output.getvalue().encode("utf-8-sig"),
            file_name="qa_approved_annotations.csv",
            mime="text/csv",
        )
    else:
        st.info("No current QA-approved annotations to export.")

    if reviews:
        with st.expander("Delete QA review"):
            options = {r["id"]: r for r in reviews}
            chosen = st.selectbox(
                "Review", list(options),
                format_func=lambda key: f'{options[key]["item_type"]}: {options[key]["result"]} — {options[key]["created_at"]}',
            )
            confirmed = st.checkbox("I understand deletion is permanent", key="delete_qa_confirm")
            if st.button("Permanently delete QA review", disabled=not confirmed):
                try:
                    remove("qa", chosen)
                    st.rerun()
                except Exception:
                    st.error("Could not delete QA review.")
