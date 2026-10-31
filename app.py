"""Trust & Safety Studio — hosted Supabase edition (development)."""
import csv
import io
from datetime import datetime, timezone

import streamlit as st
from supabase import create_client
# HTML for the Turnstile widget.
HTML = """
<div id="turnstile-widget"></div>
"""

# JavaScript for Streamlit Components v2.
JS = """
export default function(component) {
    const { setStateValue, parentElement, data } = component;

    const container = parentElement.querySelector("#turnstile-widget");
    let widgetId = null;
    let cancelled = false;
    let retryTimer = null;

    function renderWidget() {
        if (cancelled) return;

        if (!window.turnstile) {
            retryTimer = setTimeout(renderWidget, 200);
            return;
        }

        if (widgetId !== null || !container) return;

        widgetId = window.turnstile.render(container, {
            sitekey: data.site_key,

            callback: (token) => {
                setStateValue("token", token);
            },

            "expired-callback": () => {
                setStateValue("token", null);
            },

            "error-callback": () => {
                setStateValue("token", null);
            },

            "timeout-callback": () => {
                setStateValue("token", null);
            }
        });
    }

    // Load the Cloudflare script if it is not already available.
    if (!document.querySelector('script[data-turnstile-test]')) {
        const script = document.createElement("script");
        script.src =
            "https://challenges.cloudflare.com/turnstile/v0/api.js?render=explicit";
        script.async = true;
        script.defer = true;
        script.dataset.turnstileTest = "true";
        document.head.appendChild(script);
    }

    renderWidget();

    return () => {
        cancelled = true;

        if (retryTimer !== null) {
            clearTimeout(retryTimer);
        }

        if (widgetId !== null && window.turnstile) {
            window.turnstile.remove(widgetId);
        }
    };
}
"""

# Register the bidirectional component.
turnstile_component = st.components.v2.component(
    "cloudflare_turnstile_test",
    html=HTML,
    js=JS,
)


# This callback registers "token" as a valid component state.
def on_token_change():
    pass


# Render the CAPTCHA.
result = turnstile_component(
    data={"site_key": site_key},
    key="turnstile_test",
    on_token_change=on_token_change,
    default={"token": None},
)


if result.token:
    if st.button("Verify CAPTCHA with Cloudflare"):
        if verify_turnstile_token(result.token):
            st.success("CAPTCHA verified successfully by Cloudflare!")
        else:
            st.error(
                "CAPTCHA verification failed or the token expired. "
                "Refresh the page and try again."
            )
else:
    st.info("Complete the CAPTCHA verification.")
st.set_page_config(page_title="Trust & Safety Studio | krisi.site", page_icon="🛡️", layout="wide")

st.markdown("""<style>
@import url('https://fonts.googleapis.com/css2?family=DM+Sans:wght@400;500;600&family=Playfair+Display:wght@500;600;700&display=swap');
html,body,[data-testid="stAppViewContainer"],.stApp{background:#120d11!important;color:#efe4d9}
[data-testid="stSidebar"]{background:#1c1219!important;border-right:1px solid #6b4a45}
[data-testid="stHeader"]{background:#120d11!important}
.block-container{max-width:1400px;padding-top:2rem}
h1,h2,h3{font-family:'Playfair Display',Georgia,serif!important;color:#f1e1d1!important}
html,body,p,label,button{font-family:'DM Sans',sans-serif}
.krisi-hero{border:1px solid #826044;background:linear-gradient(130deg,#3b1d2b,#150e14);padding:2.2rem;margin-bottom:1.5rem}
.krisi-hero small{color:#d0a975;letter-spacing:.2em;font-weight:bold}
.krisi-hero h1{font-size:clamp(2.1rem,4vw,3.7rem);margin:.7rem 0}
.krisi-hero em{color:#d1ac7c}
.krisi-hero p{color:#d6c1b5}
[data-testid="stMetric"]{background:#2c1924;border:1px solid #78563e;padding:1rem}
[data-testid="stForm"]{background:#21151c;border:1px solid #72503d;padding:1rem}
</style>""", unsafe_allow_html=True)

st.markdown("""<div class="krisi-hero"><small>KRISI.SITE / DIGITAL SAFETY</small>
<h1>Trust &amp; Safety <em>Studio</em></h1>
<p>Moderation, AI evaluation and quality assurance — your private workspace.</p>
<small>DEVELOPMENT PREVIEW · DARK ACADEMIA</small></div>""", unsafe_allow_html=True)

try:
    url = st.secrets["SUPABASE_URL"]
    key = st.secrets["SUPABASE_PUBLISHABLE_KEY"]
except (KeyError, FileNotFoundError):
    st.error("Supabase configuration is missing. Set SUPABASE_URL and SUPABASE_PUBLISHABLE_KEY in Streamlit secrets.")
    st.stop()

# A client belongs to one Streamlit session, never a global cached singleton.
if "supabase" not in st.session_state:
    st.session_state.supabase = create_client(url, key)
if "user_id" not in st.session_state:
    st.session_state.user_id = None
if "access_token" not in st.session_state:
    st.session_state.access_token = None
sb = st.session_state.supabase


def reset_session():
    st.session_state.pop("supabase", None)
    st.session_state.user_id = None
    st.session_state.access_token = None

def login(email, password, captcha_token):
    if not captcha_token:
        raise ValueError("CAPTCHA verification is required.")

    result = sb.auth.sign_in_with_password({
        "email": email,
        "password": password,
        "options": {
            "captcha_token": captcha_token
        }
    })

    if not result.session or not result.user:
        raise RuntimeError("No active session was returned.")

    st.session_state.user_id = result.user.id
    st.session_state.access_token = result.session.access_token

def ensure_session():
    """Refresh the token and verify identity before any database access."""
    if not st.session_state.user_id:
        return False
    try:
        result = sb.auth.get_session()
        if not result or not result.access_token:
            reset_session()
            return False
        user = sb.auth.get_user(result.access_token).user
        if not user or user.id != st.session_state.user_id:
            reset_session()
            return False
        st.session_state.access_token = result.access_token
        return True
    except Exception:
        reset_session()
        return False


if not ensure_session():
    st.info("Sign in or create an account to access your private workspace.")
    tab1, tab2 = st.tabs(["Sign in", "Create account"])
    with tab1:
        signin_captcha = turnstile_component(
            data={"site_key": st.secrets["TURNSTILE_SITE_KEY"]},
            key="turnstile_signin",
            on_token_change=on_token_change,
            default={"token": None},
        )
        with st.form("signin"):
            email = st.text_input("Email", key="signin_email")
            password = st.text_input("Password", type="password", key="signin_password")
            submitted = st.form_submit_button("Sign in")

        if submitted:
            captcha_token = signin_captcha.token

            if not captcha_token:
                st.error("Please complete the CAPTCHA verification.")
            else:
                try:
                    login(email.strip(), password, captcha_token)
                    st.rerun()
                except Exception:
                    st.error(
                        "Sign-in failed. Check your credentials, "
                        "email confirmation, and CAPTCHA."
                    )


    with tab2:
        signup_captcha = turnstile_component(
            data={"site_key": st.secrets["TURNSTILE_SITE_KEY"]},
            key="turnstile_signup",
            on_token_change=on_token_change,
            default={"token": None},
        )

        with st.form("signup"):

            email = st.text_input("Email", key="signup_email")
            password = st.text_input("Password (at least 12 characters)", type="password", key="signup_password")
            submitted = st.form_submit_button("Create account")
       
        if submitted:
            captcha_token = signup_captcha.token

            if len(password) < 12:
                st.error("Choose a password of at least 12 characters.")
            elif not captcha_token:
                st.error("Please complete the CAPTCHA verification.")
            else:
                try:
                    sb.auth.sign_up({
                        "email": email.strip(),
                        "password": password,
                        "options": {
                            "captcha_token": captcha_token
                        }
                    })
                    st.success(
                        "If the address is eligible, check your email "
                        "for confirmation, then sign in."
                    )
                except Exception:
                    st.error(
                        "Registration could not be completed. "
                        "Please try again later."
                    )

    st.stop()

uid = st.session_state.user_id
st.sidebar.caption("Signed in to your private workspace")
if st.sidebar.button("Sign out"):
    try:
        sb.auth.sign_out()
    except Exception:
        pass
    reset_session()
    st.rerun()

st.caption("Development preview. Use fictional, non-sensitive test data only. Do not enter real moderation content or client information.")


def rows(table, columns="*", **filters):
    q = sb.table(table).select(columns).eq("user_id", uid)
    for field, value in filters.items():
        q = q.eq(field, value)
    return q.execute().data or []


def add(table, values):
    sb.table(table).insert({**values, "user_id": uid}).execute()


def remove(table, record_id):
    sb.table(table).delete().eq("id", record_id).eq("user_id", uid).execute()


def show_table(data, empty="No records yet."):
    if data:
        st.dataframe(data, use_container_width=True, hide_index=True)
    else:
        st.info(empty)


def choose_project(key):
    projects = sorted(rows("projects", "id,name"), key=lambda p: p["name"])
    if not projects:
        st.info("Create a project in the Projects section first.")
        return None
    labels = {p["id"]: p["name"] for p in projects}
    return st.selectbox("Project", list(labels), format_func=lambda p: labels[p], key=key)


def delete_panel(title, data, table, project_id=None):
    if not data:
        return
    with st.expander(f"Delete {title}"):
        st.warning("Deletion is permanent. Export a report first if needed.")
        options = {r["id"]: r for r in data}
        chosen = st.selectbox("Record to delete", list(options), format_func=lambda i: str(options[i].get("name") or options[i].get("sample_id") or options[i].get("category") or i), key=f"del_{table}_{project_id}")
        confirm = st.checkbox("I understand this deletion is permanent", key=f"confirm_{table}_{project_id}")
        if st.button("Permanently delete", disabled=not confirm, key=f"button_{table}_{project_id}"):
            try:
                # The initial schema does not have an item FK for QA; clear linked QA first.
                if table in ("cases", "annotations"):
                    kind = "Moderation case" if table == "cases" else "AI annotation"
                    sb.table("qa").delete().eq("user_id", uid).eq("project_id", project_id).eq("item_type", kind).eq("item_id", chosen).execute()
                remove(table, chosen)
                st.rerun()
            except Exception:
                st.error("Deletion failed. Please try again.")


section = st.sidebar.radio("Workspace", ["Dashboard", "Projects", "Moderation Cases", "AI Annotation", "Quality Assurance", "Reports"])

try:
    if section == "Dashboard":
        st.subheader("Workspace overview")
        counts = [len(rows(t, "id")) for t in ("projects", "cases", "annotations", "qa")]
        for col, label, count in zip(st.columns(4), ("Projects", "Moderation cases", "Annotations", "QA reviews"), counts):
            col.metric(label, count)
        st.markdown("#### Recent moderation cases")
        recent = sorted(rows("cases", "id,platform,category,decision,status,created_at"), key=lambda r: r["created_at"], reverse=True)[:10]
        show_table(recent)

    elif section == "Projects":
        st.subheader("Projects")
        with st.form("new_project", clear_on_submit=True):
            name = st.text_input("Project name")
            alias = st.text_input("Client alias", value="Fictional Client")
            kind = st.selectbox("Project type", ["Social Media Moderation", "Community Safety", "AI Annotation & Evaluation", "Trust & Safety Audit"])
            submitted = st.form_submit_button("Create project")
        if submitted:
            if not name.strip() or not alias.strip():
                st.error("Name and client alias are required.")
            else:
                add("projects", {"name": name.strip(), "client_alias": alias.strip(), "project_type": kind})
                st.rerun()
        data = rows("projects", "id,name,client_alias,project_type,status,created_at")
        show_table(data)
        delete_panel("Projects", data, "projects")

    elif section == "Moderation Cases":
        st.subheader("Moderation Case Manager")
        pid = choose_project("case_project")
        if pid:
            with st.form("new_case", clear_on_submit=True):
                platform = st.selectbox("Platform", ["Instagram", "Facebook", "TikTok", "YouTube", "LinkedIn", "Pinterest", "Discord", "Reddit", "Twitch", "Other"])
                category = st.selectbox("Policy category", ["Spam", "Harassment", "Misinformation", "Privacy", "Impersonation", "Other / Unclear"])
                decision = st.selectbox("Decision", ["Allow", "Flag for review", "Escalate", "No decision"])
                rationale = st.text_area("Rationale (fictional scenario only)")
                status = st.selectbox("Status", ["Open", "Reviewed", "Escalated"])
                submitted = st.form_submit_button("Save case")
            if submitted:
                if not rationale.strip():
                    st.error("Add a rationale.")
                else:
                    add("cases", {"project_id": pid, "platform": platform, "category": category, "decision": decision, "rationale": rationale.strip(), "status": status})
                    st.rerun()
            data = rows("cases", "id,platform,category,decision,rationale,status,created_at", project_id=pid)
            show_table(data)
            delete_panel("Moderation Cases", data, "cases", pid)

    elif section == "AI Annotation":
        st.subheader("AI Annotation & Evaluation")
        pid = choose_project("annotation_project")
        if pid:
            with st.form("new_annotation", clear_on_submit=True):
                sample_id = st.text_input("Sample ID")
                sample_text = st.text_area("Fictional sample text")
                label = st.selectbox("Classification", ["Helpful", "Needs improvement", "Off-topic", "Unclear", "Escalate for review"])
                score = st.slider("Quality score", 1, 5, 3)
                notes = st.text_area("Evaluation notes")
                submitted = st.form_submit_button("Save annotation")
            if submitted:
                if not sample_id.strip() or not sample_text.strip():
                    st.error("Sample ID and sample text are required.")
                else:
                    add("annotations", {"project_id": pid, "sample_id": sample_id.strip(), "sample_text": sample_text.strip(), "label": label, "score": score, "notes": notes.strip()})
                    st.rerun()
            data = rows("annotations", "id,sample_id,sample_text,label,score,notes,created_at", project_id=pid)
            show_table(data)
            delete_panel("AI Annotations", data, "annotations", pid)

    elif section == "Quality Assurance":
        st.subheader("Quality Assurance")
        pid = choose_project("qa_project")
        if pid:
            item_type = st.selectbox("Review item type", ["Moderation case", "AI annotation"])
            source = "cases" if item_type == "Moderation case" else "annotations"
            items = rows(source, "id", project_id=pid)
            if items:
                with st.form("qa_form", clear_on_submit=True):
                    item_id = st.selectbox("Record ID", [i["id"] for i in items])
                    result = st.selectbox("QA outcome", ["Pass", "Needs correction", "Escalate"])
                    notes = st.text_area("QA findings")
                    submitted = st.form_submit_button("Save QA review")
                if submitted:
                    if not notes.strip():
                        st.error("Add a QA note.")
                    else:
                        add("qa", {"project_id": pid, "item_type": item_type, "item_id": item_id, "result": result, "notes": notes.strip()})
                        st.rerun()
            else:
                st.info("Add a case or annotation before reviewing it.")
            data = rows("qa", "id,item_type,item_id,result,notes,created_at", project_id=pid)
            show_table(data)
            delete_panel("QA Reviews", data, "qa", pid)

    elif section == "Reports":
        st.subheader("Reports & Insights")
        pid = choose_project("report_project")
        if pid:
            project = rows("projects", "id,name,client_alias", id=pid)[0]
            cases = rows("cases", "id,platform,category,decision,rationale,status,created_at", project_id=pid)
            annotations = rows("annotations", "id,sample_id,sample_text,label,score,notes,created_at", project_id=pid)
            qa = rows("qa", "id,item_type,item_id,result,notes,created_at", project_id=pid)
            for col, label, count in zip(st.columns(3), ("Moderation cases", "Annotations", "QA reviews"), (len(cases), len(annotations), len(qa))):
                col.metric(label, count)
            st.markdown("#### Decision breakdown")
            show_table([{"decision": k, "count": sum(c["decision"] == k for c in cases)} for k in sorted({c["decision"] for c in cases})])
            st.markdown("#### QA outcomes")
            show_table([{"result": k, "count": sum(q["result"] == k for q in qa)} for k in sorted({q["result"] for q in qa})])
            output = io.StringIO()
            writer = csv.writer(output)
            writer.writerow(["Trust & Safety Studio report", project["name"]])
            writer.writerow(["Client alias", project["client_alias"]])
            writer.writerow(["Generated", datetime.now(timezone.utc).isoformat()])
            for heading, data in (("Moderation cases", cases), ("AI annotations", annotations), ("QA reviews", qa)):
                writer.writerow([])
                writer.writerow([heading])
                if data:
                    writer.writerow(data[0].keys())
                    writer.writerows(r.values() for r in data)
            st.download_button("Download project report (CSV)", output.getvalue().encode("utf-8-sig"), file_name="trust_safety_report.csv", mime="text/csv")
except Exception:
    st.error("The operation could not be completed. Check the Supabase configuration and database permissions.")
