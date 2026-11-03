# QA Integrity v2 — isolated test checklist

**Status:** Prepared, not executed. No production database changes.

## Prerequisites
- Disposable PostgreSQL/Supabase test database with the *same* schema, policies, roles, and constraints.
- Synthetic users A and B with real test auth identities.
- Synthetic projects, one case, one annotation per user.
- Verify function owner and RLS behavior before executing the migration.
- Confirm baseline SQL is backed up and migration can be rolled back.

## Tests
| ID | Scenario | Expected |
| --- | --- | --- |
| T01 | User A creates QA for own case in own project | Allowed |
| T02 | User A creates QA for own annotation in own project | Allowed |
| T03 | QA refers to nonexistent item_id | Rejected |
| T04 | QA refers to B's item | Rejected |
| T05 | QA item belongs to different project | Rejected |
| T06 | Delete a source item that still has QA | Rejected |
| T07 | Delete QA first, then delete its source | Allowed |
| T08 | Change source project_id or user_id while QA exists | Rejected |
| T09 | Concurrent source DELETE and QA INSERT | No orphan QA remains |
| T10 | Existing RLS cross-user SELECT/UPDATE/DELETE tests | Still denied |
| T11 | Normal app QA create/edit/delete workflow | Still works |
| T12 | Deploy then rollback on disposable DB | Restores baseline |

## Review blockers
1. Verify SECURITY DEFINER ownership, privilege grants, RLS/FORCE RLS, and safe search_path.
2. Check the source trigger's query cannot be bypassed by RLS or unexpected grants.
3. Verify lock behavior under concurrent writes and absence of orphan races.
4. Review preexisting invalid QA records before migration.
5. Check trigger names for collisions and deployment idempotency.
6. Confirm UI deletion flow handles rejected source deletions clearly.

## Release gate
Do **not** run the draft SQL in production until every test passes and a rollback
procedure has been verified. GitHub commits do not apply database migrations.
