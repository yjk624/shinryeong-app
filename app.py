import streamlit as st
import google.generativeai as genai
import os

# ==========================================
# DIAGNOSTIC MODE: CONNECTION TEST
# ==========================================
st.set_page_config(page_title="신령 진단 모드", page_icon="🛠️", layout="centered")
st.title("🛠️ Shinryeong Diagnostic Mode")
st.write("Testing connection to Google Servers...")

# 1. TEST SECRETS
try:
    API_KEY = st.secrets["GEMINI_API_KEY"]
    st.success("✅ API Key found in Secrets.")
    # Print first 4 chars to verify it's the new key (Don't show full key)
    st.write(f"Key fingerprint: `{API_KEY[:4]}...`")
except Exception as e:
    st.error(f"❌ Critical: API Key NOT found in Secrets. Did you re-paste it after recreating the app?\nError: {e}")
    st.stop()

# 2. TEST LIBRARY VERSION
try:
    version = genai.__version__
    st.info(f"ℹ️ Google Library Version: {version}")
    # We need at least 0.7.0 for Flash models
except:
    st.warning("⚠️ Could not detect library version.")

# 3. TEST MODEL CONNECTION (The Real Test)
models_to_test = [
    'models/gemini-1.5-flash',
    'models/gemini-flash-latest',
    'models/gemini-pro'
]

model_found = False

for m in models_to_test:
    st.write(f"--- Testing Model: `{m}` ---")
    try:
        genai.configure(api_key=API_KEY)
        model = genai.GenerativeModel(m)
        response = model.generate_content("Hello, are you awake?")
        st.success(f"✅ SUCCESS! Connected to {m}")
        st.write(f"Response: {response.text}")
        model_found = True
        break # Stop testing if one works
    except Exception as e:
        st.error(f"❌ Failed: {e}")

if not model_found:
    st.error("🔥🔥 FATAL ERROR: All models failed. Check the specific error messages above.")
    st.markdown("""
    **Common Fixes:**
    1. **403 Permission/Invalid Key:** Your Key is dead or copied wrong. Get a new one.
    2. **404 Not Found:** The library is too old. Force update requirements.txt.
    3. **429 Quota:** You are using a 'free' key too fast.
    """)
