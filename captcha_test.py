import streamlit as st

st.set_page_config(page_title="Turnstile Test", page_icon="🔐")

st.title("🔐 Cloudflare Turnstile Test")

site_key = st.secrets.get("TURNSTILE_SITE_KEY")

if not site_key:
    st.error("TURNSTILE_SITE_KEY is missing.")
    st.stop()

st.success("Turnstile Site Key is configured.")
st.info("Next: render the CAPTCHA and receive its token.")
