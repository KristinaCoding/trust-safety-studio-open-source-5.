"""Project-scoped AI dataset intake for fictional sample data."""
import csv
import io

import streamlit as st

STATUSES = ["Pending", "In review", "Approved", "Rejected"]
FIELDS = ["sample_id", "sample_text", "source", "expected_label", "status", "notes"]
MAX_BYTES = 1_000_000
MAX_ROWS = 200


def _validate(raw):
    item = {key: str(raw.get(key) or "").strip() for key in FIELDS}
    if not item["sample_id"] or not item["sample_text"]:
        raise ValueError("Sample ID and sample text are required.")
    if len(item["sample_id"]) > 200 or len(item["source"]) > 200 or len(item["expected_label"]) > 200:
        raise ValueError("Sample ID, source and expected label must be at most 200 characters.")
    if len(item["sample_text"]) > 5000 or len(item["notes"]) > 5000:
        raise ValueError("Sample text and notes must be at most 5,000 characters.")
    item["status"] = item["status"] or "Pending"
    if item["status"] not in STATUSES:
        raise ValueError("Invalid status.")
    return item


def render_ai_dataset_intake(sb, uid, rows, add, choose_project):
    st.subheader("AI Dataset Intake")
    st.caption("Development preview — use fictional, non-sensitive examples only. 'Approved' is an intake status, not a QA approval.")
    pid = choose_project("ai_dataset_project")
    if not pid:
        return

    items = rows(
        "ai_dataset_items",
        "id,sample_id,sample_text,source,expected_label,status,notes,created_at,updated_at",
        project_id=pid,
    )
    st.markdown("#### Project dataset items")
    if items:
        st.dataframe(items, use_container_width=True, hide_index=True)
    else:
        st.info("No dataset items for this project yet.")

    with st.expander("Add dataset item", expanded=not bool(items)):
        with st.form("add_dataset_item"):
            sample_id = st.text_input("Sample ID")
            sample_text = st.text_area("Sample text (fictional only)")
            source = st.text_input("Source")
            expected_label = st.text_input("Expected label (optional)")
            status = st.selectbox("Intake status", STATUSES)
            notes = st.text_area("Notes")
            submitted = st.form_submit_button("Save dataset item")
        if submitted:
            try:
                item = _validate({
                    "sample_id": sample_id, "sample_text": sample_text,
                    "source": source, "expected_label": expected_label,
                    "status": status, "notes": notes,
                })
                add("ai_dataset_items", {"project_id": pid, **item})
                st.rerun()
            except ValueError as exc:
                st.error(str(exc))
            except Exception:
                st.error("Could not save item. Check for an existing sample ID and database permissions.")

    with st.expander("Import dataset items from CSV"):
        st.caption("Required CSV columns: sample_id, sample_text. Optional: source, expected_label, status, notes.")
        template = "sample_id,sample_text,source,expected_label,status,notes\nDEMO-AI-001,Fictional test sentence,Synthetic,Neutral,Pending,Demo only\n"
        st.download_button("Download CSV template", template, "ai_dataset_template.csv", "text/csv")
        upload = st.file_uploader("Choose CSV (maximum 1 MB, 200 rows)", type=["csv"], key="ai_dataset_csv")
        if upload is not None:
            try:
                data = upload.getvalue()
                if len(data) > MAX_BYTES:
                    raise ValueError("File exceeds 1 MB.")
                reader = csv.DictReader(io.StringIO(data.decode("utf-8-sig")))
                if not reader.fieldnames or not {"sample_id", "sample_text"}.issubset(set(reader.fieldnames)):
                    raise ValueError("Required headers sample_id and sample_text are missing.")
                if len(reader.fieldnames) != len(set(reader.fieldnames)) or any(field not in FIELDS for field in reader.fieldnames):
                    raise ValueError("Duplicate or unsupported CSV headers. Use the template.")
                parsed = []
                for row_num, raw in enumerate(reader, start=2):
                    if len(parsed) >= MAX_ROWS:
                        raise ValueError("CSV exceeds 200 rows.")
                    if None in raw:
                        raise ValueError(f"Row {row_num} has more values than headers.")
                    try:
                        parsed.append(_validate(raw))
                    except ValueError as exc:
                        raise ValueError(f"Row {row_num}: {exc}") from exc
                if not parsed:
                    raise ValueError("CSV has no items.")
                sample_ids = [item["sample_id"] for item in parsed]
                if len(sample_ids) != len(set(sample_ids)):
                    raise ValueError("CSV has duplicate sample IDs.")
                existing_ids = {item["sample_id"] for item in items}
                duplicates = existing_ids.intersection(sample_ids)
                if duplicates:
                    raise ValueError(f"{len(duplicates)} sample ID(s) already exist in this project. No rows imported.")
                st.success(f"{len(parsed)} rows validated.")
                st.dataframe(parsed[:10], use_container_width=True, hide_index=True)
                if st.button("Import validated dataset items", key="confirm_ai_dataset_import"):
                    try:
                        sb.table("ai_dataset_items").insert([
                            {"user_id": uid, "project_id": pid, **item} for item in parsed
                        ]).execute()
                        st.rerun()
                    except Exception:
                        st.error("Import failed. Check database permissions and duplicate sample IDs, then refresh.")
            except (ValueError, UnicodeDecodeError, csv.Error) as exc:
                st.error(f"CSV validation failed: {exc}")

    if items:
        with st.expander("Update intake status"):
            options = {item["id"]: item for item in items}
            chosen = st.selectbox(
                "Dataset item", list(options),
                format_func=lambda key: options[key]["sample_id"],
                key="ai_dataset_status_selection",
            )
            record = options[chosen]
            with st.form("update_ai_dataset_status"):
                status = st.selectbox(
                    "New intake status", STATUSES,
                    index=STATUSES.index(record["status"]),
                )
                submitted = st.form_submit_button("Save intake status")
            if submitted:
                try:
                    sb.table("ai_dataset_items").update({"status": status}).eq(
                        "id", chosen
                    ).eq("project_id", pid).eq("user_id", uid).execute()
                    st.rerun()
                except Exception:
                    st.error("Could not update intake status.")
