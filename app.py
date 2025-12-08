import streamlit as st
import google.generativeai as genai
import os

st.set_page_config(page_title="Shinryeong Diagnostic", page_icon="🛠️")
st.title("🛠️ Deep Diagnostic Mode")

# --- TEST 1: CHECK LIBRARY VERSION ---
st.header("1. Library Check")
try:
    version = genai.__version__
    st.write(f"**Installed Library Version:** `{version}`")
    
    if version < "0.8.3":
        st.error("❌ CRITICAL: Library is too old. You need 0.8.3+. Update requirements.txt!")
    else:
        st.success("✅ Library version is good.")
except Exception as e:
    st.error(f"❌ Could not check version: {e}")

# --- TEST 2: CHECK API KEY ---
st.header("2. API Key Check")
try:
    API_KEY = st.secrets["GEMINI_API_KEY"]
    st.write(f"**Key Fingerprint:** `{API_KEY[:5]}...` (Verify this matches your new key)")
    genai.configure(api_key=API_KEY)
    st.success("✅ Key loaded from Secrets.")
except Exception as e:
    st.error(f"❌ Key missing from Secrets: {e}")
    st.stop()

# --- TEST 3: LIST AVAILABLE MODELS ---
st.header("3. Account Permissions Check")
st.write("Asking Google: *'Which models is this key allowed to use?'*")

try:
    # This lists what your Key actually has access to
    all_models = list(genai.list_models())
    available_names = [m.name for m in all_models if 'generateContent' in m.supported_generation_methods]
    
    if available_names:
        st.success(f"✅ Success! Your key can access {len(available_names)} models.")
        with st.expander("View Available Models List"):
            st.code(available_names)
    else:
        st.error("❌ Connection successful, but NO models are available. (Account restriction?)")
        
except Exception as e:
    st.error("❌ CONNECTION FAILED. Your Key was rejected.")
    st.error(f"Error Details: {e}")
    st.markdown("""
    **Common Causes:**
    * **403:** Key is invalid or deleted.
    * **400:** Bad Request (Key formatted wrong).
    """)
    st.stop()

# --- TEST 4: GENERATION TEST ---
st.header("4. 'Hello World' Test")
models_to_test = ["models/gemini-1.5-flash", "models/gemini-1.5-flash-001", "models/gemini-pro"]

for m in models_to_test:
    st.write(f"Testing connection to `{m}`...")
    try:
        model = genai.GenerativeModel(m)
        response = model.generate_content("Test")
        st.success(f"✅ {m} IS WORKING!")
    except Exception as e:
        st.error(f"❌ {m} Failed: {e}")
