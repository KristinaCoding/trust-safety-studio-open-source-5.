
import streamlit as st

st.set_page_config(
    page_title="Cloudflare Turnstile Test",
    page_icon="🔐",
    layout="centered",
)

st.title("🔐 Cloudflare Turnstile Test")
st.caption("Trust & Safety Studio — CAPTCHA integration test")

# Read the public Turnstile site key from Streamlit Secrets.
site_key = st.secrets.get("TURNSTILE_SITE_KEY")

if not site_key:
    st.error("TURNSTILE_SITE_KEY is missing from Streamlit Secrets.")
    st.stop()


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


# Display the current CAPTCHA state.
if result.token:
    st.success("CAPTCHA token received successfully!")
    st.info(
        "The browser received a token. "
        "Server-side verification is still required."
    )
else:
    st.info("Complete the CAPTCHA verification.")


st.divider()
st.caption("Deployment check: Turnstile v3")
st.caption("Development test only — not production authentication protection.")
