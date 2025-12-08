%%writefile app.py
import streamlit as st
import google.generativeai as genai
from saju_engine import calculate_saju_v3
from datetime import datetime, time
from geopy.geocoders import Nominatim
import gspread
from oauth2client.service_account import ServiceAccountCredentials
import json

# === CONFIGURATION ===
# Access API Key from Secrets
API_KEY = st.secrets["GEMINI_API_KEY"] # Assuming you set this in secrets too
genai.configure(api_key=API_KEY)
model = genai.GenerativeModel('models/gemini-flash-latest')

# Initialize Geocoder
geolocator = Nominatim(user_agent="shinryeong_app_v2")

# === DATABASE CONNECTION (Google Sheets) ===
def save_to_database(user_data, concern, analysis_summary):
    try:
        # Create a scope
        scope = ['https://spreadsheets.google.com/feeds', 'https://www.googleapis.com/auth/drive']
        
        # Load credentials from Streamlit Secrets
        # We reconstruct the JSON dictionary from the secrets object
        creds_dict = dict(st.secrets["gcp_service_account"])
        # Fix private key formatting if necessary (Streamlit sometimes messes up newlines)
        creds_dict["private_key"] = creds_dict["private_key"].replace("\\n", "\n")
        
        creds = ServiceAccountCredentials.from_json_keyfile_dict(creds_dict, scope)
        client = gspread.authorize(creds)
        
        # Open the Sheet
        sheet = client.open("Shinryeong_User_Data").sheet1
        
        # Prepare the Row Data
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        row = [
            timestamp,
            user_data['Year'],   # Saju Year
            user_data['Month'],  # Saju Month
            user_data['Day'],    # Saju Day
            user_data['Time'],   # Saju Time
            str(user_data.get('Birth_Place', 'Unknown')),
            user_data.get('Gender', 'Unknown'),
            concern,             # The user's worry
            # Note: We do NOT save PII (Name/IP) to respect Volume 6 
        ]
        
        # Append to Sheet
        sheet.append_row(row)
        return True
    except Exception as e:
        # Fail silently so the user experience isn't broken
        print(f"Database Error: {e}")
        return False

# ... [KEEP YOUR EXISTING LANGUAGE DICTIONARY & UI CODE HERE] ...
# ... (No changes needed to TRANS or UI LAYOUT until the Submit button) ...

# === LOGIC CORE ===
if submitted:
    if not location_input:
        st.error(txt["geo_error"])
    else:
        with st.spinner(txt["loading"]):
            try:
                # 1. Geocoding
                location = geolocator.geocode(location_input, timeout=10)
                
                if location:
                    lat = location.latitude
                    lon = location.longitude
                    
                    # 2. Calculate Saju
                    saju_data = calculate_saju_v3(
                        birth_date.year, birth_date.month, birth_date.day,
                        birth_time.hour, birth_time.minute, lat, lon
                    )
                    
                    # 3. Construct Prompt (Your existing code)
                    # ... [KEEP YOUR PROMPT CONSTRUCTION HERE] ...
                    
                    # 4. Call AI
                    response = model.generate_content(full_prompt)
                    
                    # 5. [NEW] SAVE DATA TO DATABASE
                    # We add 'Birth_Place' and 'Gender' to saju_data for logging
                    saju_data['Birth_Place'] = location_input
                    saju_data['Gender'] = gender
                    
                    # Run the save function in the background
                    save_to_database(saju_data, user_question, "Analysis Generated")

                    # 6. Display Result (Your existing code)
                    # ... [KEEP YOUR DISPLAY CODE HERE] ...

                else:
                    st.error(txt["geo_error"])
                    
            except Exception as e:
                st.error(f"{txt['error_connect']}{e}")
