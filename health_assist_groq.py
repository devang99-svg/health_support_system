"""
HealthAssist — Streamlit demo (Groq + fallback)
- Uses Groq chat completions endpoint if GROQ_API_KEY is provided (sidebar or env var).
- Default model: "llama-3.1-8b-instant" (fast/cheap / production).
- If Groq returns a model_decommissioned error, the app shows a friendly message.
"""

import os
import json
import requests
import streamlit as st

# -----------------------
# Configuration & helpers
# -----------------------

# Default model (production, supported): use a modern, available model from Groq
DEFAULT_MODEL = "llama-3.1-8b-instant"

# A short list of recommended models (you can change/add more from Groq console)
RECOMMENDED_MODELS = [
    "llama-3.1-8b-instant",      # fast, low-cost, large context options on Groq
    "llama-3.3-70b-versatile",   # higher-capacity model for heavier tasks
    "llama3-groq-70b-tool-use-preview",  # tool-use / agentic workflows (preview)
]

GROQ_API_BASE = "https://api.groq.com/openai/v1"

def call_groq_chat(api_key, messages, model=DEFAULT_MODEL, temperature=0.2, max_tokens=512, timeout=30):
    """
    Call Groq's OpenAI-compatible chat completions endpoint via HTTP.
    Returns the assistant text on success.
    Raises a requests.HTTPError for non-200 responses with response body attached.
    """
    url = f"{GROQ_API_BASE}/chat/completions"
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }
    payload = {
        "model": model,
        "messages": messages,
        "temperature": temperature,
        "max_tokens": max_tokens,
        "n": 1,
    }
    resp = requests.post(url, headers=headers, json=payload, timeout=timeout)
    # If error, raise with the response attached so caller can inspect
    if resp.status_code != 200:
        http_err = requests.HTTPError(f"Groq API error {resp.status_code}: {resp.text}")
        http_err.response = resp
        raise http_err
    data = resp.json()
    # Try to extract the assistant message in a robust way
    try:
        return data["choices"][0]["message"]["content"]
    except Exception:
        # Fallback: if Groq returns a different structure, stringify it for debugging
        return json.dumps(data, indent=2)

# Simple fallback assistant (local, rule-based) when no GROQ_API_KEY is provided
def fallback_assistant(patient_text, action):
    text = patient_text.strip().lower()
    if action == "Summarize":
        sents = text.replace("\n", " ").split(".")
        summary = ". ".join([s.strip().capitalize() for s in sents[:3] if s.strip()])
        return summary + ("." if summary and not summary.endswith(".") else "")
    if action == "Suggest tests":
        suggestions = []
        if any(k in text for k in ["fever", "temperature", "chills"]):
            suggestions.append("- CBC, CRP, blood cultures (if severe)")
        if any(k in text for k in ["cough", "sputum", "shortness of breath", "dyspnea"]):
            suggestions.append("- Chest X-ray, sputum culture, pulse oximetry")
        if any(k in text for k in ["chest pain", "palpitation"]):
            suggestions.append("- ECG, troponin, chest X-ray")
        if not suggestions:
            suggestions.append("- Basic metabolic panel (BMP), CBC, ECG as clinically indicated")
        return "\n".join(suggestions)
    if action == "Triage urgency":
        if any(k in text for k in ["unconscious", "not breathing", "severe bleeding", "cardiac arrest"]):
            return "Emergency — call code/transfer to ED immediately."
        if any(k in text for k in ["high fever", "severe shortness of breath", "chest pain"]):
            return "High urgency — urgent evaluation within hours."
        return "Low-moderate urgency — outpatient follow-up recommended."
    if action == "Generate SOAP note":
        subj = "Subjective: " + (text.split(".")[0].capitalize() + ".")
        obj = "Objective: vitals not provided. Exam: to be performed."
        assess = "Assessment: differential diagnosis to consider based on symptoms."
        plan = "Plan: order tests as needed, symptomatic treatment, follow-up."
        return f"{subj}\n\n{obj}\n\n{assess}\n\n{plan}"
    return "Action not recognized."

# -----------------------
# Streamlit UI
# -----------------------
st.set_page_config(page_title="HealthAssist — Groq demo", layout="centered")
st.title("HealthAssist — Agentic AI demo (Groq + fallback)")

with st.sidebar:
    st.header("Configuration & API")
    # Sidebar key input (users can paste an API key here — convenient for local testing).
    sidebar_key = st.text_input("GROQ API Key (optional)", type="password",
                               help="Paste your Groq API key here (or set env var GROQ_API_KEY).")

    # Also check environment variable
    env_key = os.getenv("GROQ_API_KEY", "")
    if env_key and not sidebar_key:
        st.caption("Using GROQ_API_KEY from environment.")
    groq_key = sidebar_key if sidebar_key else env_key

    st.markdown("---")
    st.subheader("Model / generation")
    model = st.selectbox("Model name", options=RECOMMENDED_MODELS, index=RECOMMENDED_MODELS.index(DEFAULT_MODEL) if DEFAULT_MODEL in RECOMMENDED_MODELS else 0)
    temp = st.slider("Temperature", 0.0, 1.0, 0.2, 0.05)
    max_tokens = st.slider("Max tokens", 64, 2048, 512, 64)
    st.markdown("---")
    st.write("Demo actions:")
    st.write("- Summarize patient note")
    st.write("- Suggest tests")
    st.write("- Triage urgency")
    st.write("- Generate SOAP note")
    st.markdown("---")
    st.caption("Do not paste real PHI here unless you are testing locally and understand the privacy implications.")

st.subheader("Patient case / clinical note")
default_case = """50-year-old male with 3 days of productive cough, fever 38.9°C, mild shortness of breath on exertion. No chest pain. Past history: hypertension. Meds: lisinopril."""
patient_text = st.text_area("Paste or type patient presentation, exam findings or history:", height=240, value=default_case)
action = st.selectbox("Action", ["Summarize", "Suggest tests", "Triage urgency", "Generate SOAP note"])

if st.button("Run assistant"):
    st.info("Running the assistant...")
    # If no API key provided, use local fallback assistant
    if not groq_key:
        st.warning("No GROQ API key provided — using built-in fallback assistant.")
        assistant_text = fallback_assistant(patient_text, action)
        st.markdown("**Assistant output (local fallback):**")
        st.code(assistant_text, language="text")
    else:
        # Build the system + user messages for Groq
        system_msg = {
            "role": "system",
            "content": (
                "You are a concise clinical assistant for doctors. Provide short, "
                "actionable suggestions. Use bullet points for tests or steps. "
                "Do not assert definitive diagnoses; list differential diagnoses where appropriate."
            )
        }
        user_prompt = f"Patient case:\n{patient_text}\n\nRequested action: {action}.\nRespond concisely."
        user_msg = {"role": "user", "content": user_prompt}
        messages = [system_msg, user_msg]

        try:
            assistant_text = call_groq_chat(groq_key, messages, model=model, temperature=temp, max_tokens=max_tokens)
            st.success("Assistant completed (Groq).")
            st.markdown("**Assistant output (Groq):**")
            st.code(assistant_text, language="text")
        except requests.HTTPError as http_err:
            # Try to parse error body to detect model_decommissioned and show helpful suggestion.
            resp = getattr(http_err, "response", None)
            try:
                err_json = resp.json() if resp is not None else {}
            except Exception:
                err_json = {"message": resp.text if resp is not None else str(http_err)}
            # Extract message if present
            err_msg = None
            if isinstance(err_json, dict):
                err_obj = err_json.get("error", err_json)
                if isinstance(err_obj, dict):
                    err_msg = err_obj.get("message") or err_obj.get("detail") or str(err_obj)
            if not err_msg:
                err_msg = str(err_json)

            # Model decommissioned detection
            if isinstance(err_msg, str) and ("decommissioned" in err_msg or "decommission" in err_msg or "model_decommissioned" in err_msg):
                st.error("Groq API rejected the model: it looks decommissioned or unsupported.")
                st.write("Error message from Groq:")
                st.code(err_msg)
                st.info("Suggested action: pick a supported model from the dropdown (e.g., 'llama-3.1-8b-instant' or 'llama-3.3-70b-versatile') or check https://console.groq.com/docs/deprecations for replacements.")
            else:
                # Other HTTP-level errors
                st.error(f"Groq API error (status code {resp.status_code if resp is not None else 'N/A'}).")
                st.write("Error details:")
                st.code(err_msg)
            # Offer fallback output
            st.write("Falling back to local assistant for now.")
            assistant_text = fallback_assistant(patient_text, action)
            st.markdown("**Fallback output:**")
            st.code(assistant_text, language="text")
        except Exception as e:
            # Generic error
            st.error(f"Error calling Groq: {e}")
            st.write("Falling back to local assistant.")
            assistant_text = fallback_assistant(patient_text, action)
            st.markdown("**Fallback output:**")
            st.code(assistant_text, language="text")

st.markdown("---")
st.caption("This demo is for educational purposes only and not a substitute for clinical judgment. Always follow local privacy and security rules when handling patient data.")
