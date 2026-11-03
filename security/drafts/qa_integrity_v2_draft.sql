-- KRISI Trust & Safety Studio v2.0
-- DRAFT ONLY — DO NOT EXECUTE IN PRODUCTION.
-- Requires review and tests against a disposable database with matching schema.
-- This migration validates polymorphic QA item references and prevents dangling
-- references after source-row deletion or changes to source ownership/project.
-- Existing data must be audited before deployment.
-- SECURITY DEFINER must be owned by a tightly controlled DB role able to inspect
-- both referenced tables despite RLS; never grant ownership to app users.
-- Function code uses fully-qualified table names and an empty search_path.

BEGIN;

CREATE OR REPLACE FUNCTION public.validate_qa_item_reference()
RETURNS trigger
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path = ''
AS $$
BEGIN
  IF NEW.item_type = 'Moderation case' THEN
    IF NOT EXISTS (
      SELECT 1 FROM public.cases c
      WHERE c.id = NEW.item_id
        AND c.project_id = NEW.project_id
        AND c.user_id = NEW.user_id
      FOR KEY SHARE
    ) THEN
      RAISE EXCEPTION 'QA item must reference a moderation case in the same project and owned by the same user'
        USING ERRCODE = '23503';
    END IF;
  ELSIF NEW.item_type = 'AI annotation' THEN
    IF NOT EXISTS (
      SELECT 1 FROM public.annotations a
      WHERE a.id = NEW.item_id
        AND a.project_id = NEW.project_id
        AND a.user_id = NEW.user_id
      FOR KEY SHARE
    ) THEN
      RAISE EXCEPTION 'QA item must reference an AI annotation in the same project and owned by the same user'
        USING ERRCODE = '23503';
    END IF;
  ELSE
    RAISE EXCEPTION 'Unsupported QA item type' USING ERRCODE = '23514';
  END IF;
  RETURN NEW;
END;
$$;

CREATE TRIGGER qa_validate_item_reference
BEFORE INSERT OR UPDATE OF item_type, item_id, project_id, user_id
ON public.qa
FOR EACH ROW EXECUTE FUNCTION public.validate_qa_item_reference();

-- Prevent source records with QA references from being deleted or reassigned.
-- This is deliberately restrictive; future design can choose cascading behavior.
CREATE OR REPLACE FUNCTION public.prevent_qa_source_orphaning()
RETURNS trigger
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path = ''
AS $$
DECLARE
  source_type text := TG_ARGV[0];
BEGIN
  IF TG_OP = 'DELETE' OR
     OLD.project_id IS DISTINCT FROM NEW.project_id OR
     OLD.user_id IS DISTINCT FROM NEW.user_id THEN
    IF EXISTS (
      SELECT 1 FROM public.qa q
      WHERE q.item_type = source_type AND q.item_id = OLD.id
    ) THEN
      RAISE EXCEPTION 'Cannot delete or reassign an item referenced by QA; remove its QA reviews first'
        USING ERRCODE = '23503';
    END IF;
  END IF;
  IF TG_OP = 'DELETE' THEN
    RETURN OLD;
  END IF;
  RETURN NEW;
END;
$$;

CREATE TRIGGER cases_prevent_qa_orphans
BEFORE DELETE OR UPDATE OF project_id, user_id ON public.cases
FOR EACH ROW EXECUTE FUNCTION public.prevent_qa_source_orphaning('Moderation case');

CREATE TRIGGER annotations_prevent_qa_orphans
BEFORE DELETE OR UPDATE OF project_id, user_id ON public.annotations
FOR EACH ROW EXECUTE FUNCTION public.prevent_qa_source_orphaning('AI annotation');

COMMIT;

-- IMPORTANT REVIEW NOTES:
-- 1. This is a design draft, not a production-ready migration.
-- 2. SECURITY DEFINER bypass behavior depends on the function owner, FORCE RLS,
--    and privileges. Verify exact Supabase deployment role and RLS semantics.
--    Review function EXECUTE privileges and default PUBLIC grants.
-- 3. FOR KEY SHARE is intended to serialize inserts with deletes/key updates.
--    Test concurrency, lock ordering, and possible deadlocks in isolation.
-- 4. Validate pre-existing QA data before enabling constraints/triggers.
-- 5. Confirm allowed item_type literals, trigger ordering, app delete workflows,
--    and migration/rollback strategy in an isolated test environment.

-- TEST PLAN (do not run here):
-- A. Valid QA insert succeeds for same user/project/source.
-- B. Nonexistent source item_id is rejected (23503).
-- C. Source from another user or project is rejected (23503).
-- D. Delete/reassign source with QA fails; removing QA first allows deletion.
-- E. Simultaneous QA insert and source delete cannot leave an orphan.
-- F. Existing QA workflows and policy grants work for real authenticated roles.
-- G. Verify a deployment rollback and restore on a disposable clone.
