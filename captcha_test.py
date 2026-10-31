
import streamlit as st

st.set_page_config(page_title="Turnstile Test", page_icon="🔐")
st.title("🔐 Cloudflare Turnstile Test")

site_key = st.secrets.get("TURNSTILE_SITE_KEY")

if not site_key:
    st.error("TURNSTILE_SITE_KEY is missing.")
    st.stop()

HTML = """
<div id="turnstile-widget"></div>
<script src="https://challenges.cloudflare.com/turnstile/v0/api.js?render=explicit" async defer></script>
"""

JS = """
export default function(component) {
    const { setStateValue, parentElement, data } = component;

    let widgetId = null;

    function renderWidget() {
        if (!window.turnstile) {
            setTimeout(renderWidget, 200);
            return;
        }

        if (widgetId !== null) return;

        widgetId = window.turnstile.render(
            parentElement.querySelector("#turnstile-widget"),
            {
                sitekey: data.site_key,
                callback: (token) => {
                    setStateValue("token", token);
                },
                "expired-callback": () => {
                    setStateValue("token", null);
                },
                "error-callback": () => {
                    setStateValue("token", null);
                }
            }
        );
    }

    renderWidget();

    return () => {
        if (widgetId !== null && window.turnstile) {
            window.turnstile.remove(widgetId);
        }
    };
}
"""

turnstile_component = st.components.v2.component(
    "cloudflare_turnstile_test",
    html=HTML,
    js=JS,
)

result = turnstile_component(
    data={"site_key": site_key},
    key="turnstile_test",
    default={"token": None},
)

if result.token:
    st.success("CAPTCHA token received successfully!")
else:
    st.info("Complete the CAPTCHA verification.")

