"""
Health Support System — Clean Header + Center Button Version
"""

import os
import json
import requests
import streamlit as st
from datetime import datetime, timezone
from html import escape

# -----------------------
# BASIC CONFIG
# -----------------------
DEFAULT_MODEL = "llama-3.1-8b-instant"
RECOMMENDED_MODELS = [
    "llama-3.1-8b-instant",
    "llama-3.3-70b-versatile",
    "llama3-groq-70b-tool-use-preview",
]
GROQ_API_BASE = "https://api.groq.com/openai/v1"


# -----------------------
# HELPERS
# -----------------------
def call_groq_chat(api_key, messages, model=DEFAULT_MODEL, temperature=0.2, max_tokens=512, timeout=30):
    url = f"{GROQ_API_BASE}/chat/completions"
    headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}
    payload = {"model": model, "messages": messages, "temperature": temperature, "max_tokens": max_tokens, "n": 1}
    resp = requests.post(url, headers=headers, json=payload, timeout=timeout)

    if resp.status_code != 200:
        http_err = requests.HTTPError(f"Groq API error {resp.status_code}: {resp.text}")
        http_err.response = resp
        raise http_err

    return resp.json()["choices"][0]["message"]["content"]


def fallback_assistant(patient_text, action):
    text = patient_text.strip().lower()
    if action == "Summarize":
        s = text.split(".")
        return ". ".join([x.strip().capitalize() for x in s[:3] if x.strip()])
    if action == "Suggest tests":
        out = []
        if "fever" in text:
            out.append("- CBC, CRP")
        if "cough" in text:
            out.append("- Chest X-ray, sputum culture")
        return "\n".join(out) if out else "- Basic labs suggested."
    if action == "Triage urgency":
        if "shortness of breath" in text:
            return "High urgency — evaluate soon."
        return "Low–moderate urgency."
    if action == "Generate SOAP note":
        return "Subjective: ...\nObjective: ...\nAssessment: ...\nPlan: ..."
    return "Action not recognized."


def make_download_filename(prefix="assistant_output", ext="txt"):
    ts = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    return f"{prefix}_{ts}.{ext}"


# -----------------------
# PAGE CONFIG + CSS
# -----------------------
st.set_page_config(page_title="Health Support System", layout="centered", page_icon="🩺")

page_css = """
<style>
:root{
  --bg:#050507;
  --muted:#9aa7b2;
  --cyan:#2eb7ff;
  --orange:#ff7a2d;
  --purple:#b69bff;
  --lav:#ece6ff;
  --border:rgba(255,255,255,0.04);
}

body {
  background-color: var(--bg) !important;
  background-image:
    radial-gradient(circle at 10% 10%, rgba(46,183,255,0.03), transparent 8%),
    radial-gradient(circle at 90% 85%, rgba(182,155,255,0.02), transparent 12%);
  color:#eaf6ff;
}

.card {
  background: linear-gradient(180deg, rgba(255,255,255,0.02), rgba(255,255,255,0.01));
  border-radius: 16px;
  padding: 22px;
  margin-bottom: 20px;
  border: 1px solid var(--border);
  box-shadow: 0 12px 40px rgba(0,0,0,0.7);
}

.header-icon {
  width:78px; height:78px; border-radius:16px;
  background: linear-gradient(135deg, rgba(46,183,255,0.18), rgba(255,122,45,0.14));
  display:flex; justify-content:center; align-items:center;
  font-size:38px;
  border:1px solid rgba(255,255,255,0.05);
}

.h1 {
  font-size: 44px;
  color:white;
  font-weight: 900;
  letter-spacing: 1px;
  margin:0;
}

.lead {
  color: rgba(230,245,255,0.85);
  font-size:15px;
  margin-top:6px;
}

.run-btn {
  background: linear-gradient(90deg, var(--cyan), var(--orange));
  color:#000;
  padding:14px 26px;
  font-size:18px;
  font-weight:800;
  border-radius:14px;
  border:none;
  box-shadow: 0 10px 36px rgba(46,183,255,0.15);
}

.output-box {
  background: linear-gradient(180deg, rgba(255,255,255,0.02), rgba(255,255,255,0.005));
  padding:14px;
  border-radius:12px;
  border:1px solid rgba(255,255,255,0.03);
  color:#eaf6ff;
  white-space: pre-wrap;
  font-family: monospace;
}

.footer {
  color:#8191a1;
  font-size:13px;
  text-align:center;
  margin-top:24px;
}
</style>
"""
st.markdown(page_css, unsafe_allow_html=True)


# -----------------------
# HEADER (Capital heading + icon, NO colored boxes)
# -----------------------
st.markdown(
    """
    <div class="card" style="display:flex; gap:20px; align-items:center;">
        <div class="header-icon">🩺</div>
        <div style="flex:1;">
            <div class="h1">HEALTH SUPPORT SYSTEM</div>
            <div class="lead">High-contrast clinician assistant</div>
        </div>
        <div style="text-align:right; color:white; font-weight:800;">v1.0</div>
    </div>
    """,
    unsafe_allow_html=True,
)


# -----------------------
# PATIENT INPUT
# -----------------------
st.markdown('<div class="card">', unsafe_allow_html=True)
st.subheader("Patient Case")
default_case = """50-year-old male with 3 days of productive cough, fever 38.9°C, mild shortness of breath."""
patient_text = st.text_area("Clinical note", value=default_case, height=200)
st.markdown('</div>', unsafe_allow_html=True)


# -----------------------
# ACTION SELECT
# -----------------------
st.markdown('<div class="card">', unsafe_allow_html=True)
action = st.selectbox("Select Action", ["Summarize", "Suggest tests", "Triage urgency", "Generate SOAP note"])
st.markdown('</div>', unsafe_allow_html=True)


# -----------------------
# MODEL & API
# -----------------------
st.markdown('<div class="card">', unsafe_allow_html=True)

inline_key = st.text_input("GROQ API Key (optional)", type="password")
env_key = os.getenv("GROQ_API_KEY", "")
groq_key = inline_key if inline_key else env_key

model = st.selectbox("Model", RECOMMENDED_MODELS)
temp = st.slider("Temperature", 0.0, 1.0, 0.2)
max_tokens = st.slider("Max Tokens", 64, 2048, 512)

st.markdown('</div>', unsafe_allow_html=True)


# -----------------------
# CENTERED RUN BUTTON
# -----------------------
st.markdown('<div class="card" style="text-align:center;">', unsafe_allow_html=True)
run_clicked = st.button("🚀 RUN ASSISTANT", use_container_width=False)
st.markdown('</div>', unsafe_allow_html=True)


# -----------------------
# OUTPUT
# -----------------------
st.markdown('<div class="card">', unsafe_allow_html=True)
st.subheader("Assistant Output")
output_placeholder = st.empty()


if run_clicked:
    output_placeholder.info("Processing...")

    system_msg = {
        "role": "system",
        "content": (
            "You are a concise clinical assistant. Provide short, actionable advice. "
            "Use bullet points. Avoid definitive diagnoses."
        ),
    }

    user_msg = {"role": "user", "content": f"Patient case:\n{patient_text}\nAction: {action}"}
    messages = [system_msg, user_msg]

    try:
        if not groq_key:
            result = fallback_assistant(patient_text, action)
        else:
            result = call_groq_chat(groq_key, messages, model=model, temperature=temp, max_tokens=max_tokens)

        output_placeholder.markdown(f"<div class='output-box'>{escape(result)}</div>", unsafe_allow_html=True)
    except Exception as e:
        fallback = fallback_assistant(patient_text, action)
        output_placeholder.error(str(e))
        output_placeholder.markdown(f"<div class='output-box'>{escape(fallback)}</div>", unsafe_allow_html=True)

st.markdown('</div>', unsafe_allow_html=True)

st.markdown('<div class="footer">Made with ❤️ — Health Support System</div>', unsafe_allow_html=True)
