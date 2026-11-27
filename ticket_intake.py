"""Moderation ticket intake for fictional test data."""
import csv
import io

import streamlit as st

PRIORITIES = ["Low", "Medium", "High", "Critical"]
STATUSES = ["New", "In review", "Resolved", "Escalated"]
CSV_FIELDS = ["external_ticket_id", "platform", "category", "priority", "status", "description"]
MAX_CSV_BYTES = 1_000_000
MAX_CSV_ROWS = 200


def _validate_ticket(raw):
    ticket = {field: str(raw.get(field) or "").strip() for field in CSV_FIELDS}
    if not ticket["external_ticket_id"] or not ticket["platform"] or not ticket["category"]:
        raise ValueError("Ticket ID, platform and category are required.")
    if any(len(ticket[field]) > 200 for field in ("external_ticket_id", "platform", "category")):
        raise ValueError("Ticket ID, platform and category must be at most 200 characters.")
    ticket["priority"] = ticket["priority"] or "Medium"
    ticket["status"] = ticket["status"] or "New"
    if ticket["priority"] not in PRIORITIES or ticket["status"] not in STATUSES:
        raise ValueError("Invalid priority or status.")
    if len(ticket["description"]) > 5000:
        raise ValueError("Description must be at most 5,000 characters.")
    return ticket


def render_ticket_intake(sb, uid, rows, add, choose_project):
    st.subheader("Ticket Intake")
    st.caption("Development preview: only fictional, non-sensitive tickets and CSV files.")
    pid = choose_project("ticket_intake_project")
    if not pid:
        return

    tickets = rows(
        "moderation_tickets",
        "id,external_ticket_id,platform,category,priority,status,description,created_at",
        project_id=pid,
    )
    st.markdown("#### Project tickets")
    if tickets:
        st.dataframe(tickets, use_container_width=True, hide_index=True)
    else:
        st.info("No tickets for this project yet.")

    with st.expander("Create ticket", expanded=not bool(tickets)):
        with st.form("create_ticket"):
            external_id = st.text_input("External ticket ID")
            platform = st.text_input("Platform")
            category = st.text_input("Category")
            priority = st.selectbox("Priority", PRIORITIES, index=1)
            status = st.selectbox("Status", STATUSES)
            description = st.text_area("Description (fictional only)")
            submitted = st.form_submit_button("Save ticket")
        if submitted:
            try:
                ticket = _validate_ticket({
                    "external_ticket_id": external_id, "platform": platform,
                    "category": category, "priority": priority,
                    "status": status, "description": description,
                })
                add("moderation_tickets", {"project_id": pid, **ticket})
                st.rerun()
            except ValueError as exc:
                st.error(str(exc))
            except Exception:
                st.error("Could not save ticket. Check whether the ID already exists and that permissions are configured.")

    with st.expander("Import tickets from CSV"):
        st.caption("Required headers: external_ticket_id, platform, category. Optional: priority, status, description.")
        template = "external_ticket_id,platform,category,priority,status,description\nDEMO-001,Instagram,Spam,Medium,New,Fictional example\n"
        st.download_button("Download CSV template", template, "ticket_intake_template.csv", "text/csv")
        upload = st.file_uploader("Choose CSV file (maximum 1 MB, 200 rows)", type=["csv"], key="ticket_csv")
        if upload is not None:
            try:
                data = upload.getvalue()
                if len(data) > MAX_CSV_BYTES:
                    raise ValueError("File exceeds 1 MB.")
                decoded = data.decode("utf-8-sig")
                reader = csv.DictReader(io.StringIO(decoded))
                if not reader.fieldnames or not set(CSV_FIELDS[:3]).issubset(set(reader.fieldnames)):
                    raise ValueError("Missing required CSV headers.")
                if any(field not in CSV_FIELDS for field in reader.fieldnames):
                    raise ValueError("Unknown CSV column. Use the template headers.")
                parsed = []
                for index, raw in enumerate(reader, start=2):
                    if len(parsed) >= MAX_CSV_ROWS:
                        raise ValueError("CSV exceeds 200 rows.")
                    try:
                        parsed.append(_validate_ticket(raw))
                    except ValueError as exc:
                        raise ValueError(f"Row {index}: {exc}") from exc
                if not parsed:
                    raise ValueError("CSV contains no tickets.")
                existing_ids = {r["external_ticket_id"] for r in tickets}
                ids = [r["external_ticket_id"] for r in parsed]
                if len(set(ids)) != len(ids):
                    raise ValueError("CSV contains duplicate external ticket IDs.")
                duplicates = existing_ids.intersection(ids)
                if duplicates:
                    raise ValueError(f"{len(duplicates)} ticket ID(s) already exist in this project. No rows imported.")
                st.success(f"{len(parsed)} rows validated. No existing duplicates found.")
                st.dataframe(parsed[:10], use_container_width=True, hide_index=True)
                if st.button("Import validated tickets", key="confirm_ticket_import"):
                    try:
                        # Database UNIQUE constraint also protects against concurrent duplicates.
                        sb.table("moderation_tickets").insert([
                            {"project_id": pid, "user_id": uid, **row} for row in parsed
                        ]).execute()
                        st.rerun()
                    except Exception:
                        st.error("Import failed; check duplicate IDs and database permissions. Refresh before retrying.")
            except (ValueError, UnicodeDecodeError, csv.Error) as exc:
                st.error(f"CSV validation failed: {exc}")

    if tickets:
        with st.expander("Update ticket status"):
            options = {t["id"]: t for t in tickets}
            selected = st.selectbox(
                "Ticket", list(options),
                format_func=lambda key: options[key]["external_ticket_id"],
                key="ticket_status_selection",
            )
            record = options[selected]
            with st.form("update_ticket_status"):
                status = st.selectbox(
                    "New status", STATUSES, index=STATUSES.index(record["status"])
                )
                submitted = st.form_submit_button("Save status")
            if submitted:
                try:
                    sb.table("moderation_tickets").update({"status": status}).eq(
                        "id", selected
                    ).eq("project_id", pid).eq("user_id", uid).execute()
                    st.rerun()
                except Exception:
                    st.error("Could not update ticket status.")
