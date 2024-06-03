import openai
import streamlit as st
import os
import time
from threading import Timer
import gspread
from google.oauth2.service_account import Credentials
import json
import pytz
from datetime import datetime

# Initialize the OpenAI client
api_key = os.getenv('OPENAI_API_KEY')
client = openai.OpenAI(api_key=api_key)

# Google Sheets setup
credentials_file = os.getenv('GOOGLE_API_KEY')  # Make sure this is the correct path
spreadsheet_id = os.getenv('GOOGLE_SHEET_ID')  # Update with your spreadsheet ID

# Check if the credentials file exists
if not os.path.exists(credentials_file):
    st.error(f"Credentials file not found at {credentials_file}")
else:
    # Load and validate the credentials
    try:
        scopes = ['https://www.googleapis.com/auth/spreadsheets', 'https://www.googleapis.com/auth/drive']
        # Read the service account credentials
        with open(credentials_file) as source:
            info = json.load(source)
            credentials = Credentials.from_service_account_info(info, scopes=scopes)

        gc = gspread.authorize(credentials)
        worksheet = gc.open_by_key(spreadsheet_id).sheet1

    except Exception as e:
        st.error(f"Failed to load credentials or connect to Google Sheets: {e}")

# Initialize Streamlit app
# st.title("Auto Application Assistant")

# Define the sub-products and their corresponding assistant IDs
sub_products = {
    ":racing_car:  1P OUTBOUND App": {"title": ":racing_car:  1P OUTBOUND AUTO APP ASSISTANT", "assistant_id": "asst_0DNRoZlp8fEOLZHVIEtkclWQ"},
    "1P INBOUND App": {"title": "1P INBOUND AUTO APP ASSISTANT", "assistant_id": "asst_jRwTRKlGmLddeAPA8pVgjEGM"},
    ":moneybag:3P OUTBOUND App": {"title": ":moneybag: 3P OUTBOUND APP ASSISTANT", "assistant_id": "asst_fN62Ct3gP0suki42r5MPx27b"},
    "3P INBOUND App": {"title": "3P INBOUND APP ASSISTANT", "assistant_id": "asst_S0OVC8LuiP1IxPi94ybDG1KL"}
}

# Sidebar for selecting sub-product
selected_sub_product = st.sidebar.radio("Select Sub-product", list(sub_products.keys()))

# Get the selected sub-product's title and assistant ID
selected_sub_product_info = sub_products[selected_sub_product]
sub_product_title = selected_sub_product_info["title"]
assistant_id = selected_sub_product_info["assistant_id"]
assistant_name = selected_sub_product_info["title"]

# Set the title based on the selected sub-product
st.title(sub_product_title)

# Define text input for user query
user_question = st.text_input("Enter your question")

# Custom CSS for input text box
input_text_css = """
<style>
/* Increase the height of the input box */
.stTextInput>div>div>input {
  height: 40px !important;
  color: black !important; /* Set text color to black */
  background-color: #f0f0f0 !important; /* Set background color to light gray */
}
</style>
"""
st.markdown(input_text_css, unsafe_allow_html=True)

# Center and widen the search button
search_button_css = """
<style>
  .stButton>button {
      width: 200px !important;
      margin: 0 auto !important;
      display: block !important;
  }
  .left-align .stButton>button {
      margin: 0 !important;
      display: inline-flex !important;
  }
</style>
"""
st.markdown(search_button_css, unsafe_allow_html=True)

# Initialize session state variables
if 'show_feedback_section' not in st.session_state:
    st.session_state['show_feedback_section'] = False
if 'assistant_answer' not in st.session_state:
    st.session_state['assistant_answer'] = ""
if 'submitted_feedback' not in st.session_state:
    st.session_state['submitted_feedback'] = False
if 'submitted_time' not in st.session_state:
    st.session_state['submitted_time'] = None


# Function to get the assistant's answer
def get_assistant_answer(query):
    my_assistant = client.beta.assistants.retrieve(assistant_id)
    thread = client.beta.threads.create()
    message = client.beta.threads.messages.create(
        thread_id=thread.id, role="user", content=query
    )
    run = client.beta.threads.runs.create(
        thread_id=thread.id, assistant_id=my_assistant.id,
        instructions="MANDATORY INSTRUCTIONS: You MUST NEVER answer questions that are beyond the scope of the attached documents. Only answer based on the attached documents in your vector stores.  If you are not confident, just tell the human that you are not confident. Before every response, You must provide a score of how confident you are in your answers on a scale of 0 to 5, 0 being least confident and 5 being most confident. keep the score text very short, like \"Answer confidence: 3 / 5\".ROLE: You are an assistant that helps the sales team, customer success team, and customer support team with questions regarding a software product."
    )

    while run.status != "completed":
        time.sleep(1)
        run = client.beta.threads.runs.retrieve(
            thread_id=thread.id, run_id=run.id
        )

    if run.status == "completed":
        all_messages = client.beta.threads.messages.list(thread_id=thread.id)
        return all_messages.data[0].content[0].text.value
    else:
        return "There was an error processing your request. Please try again."


# Function to hide feedback section after 3 seconds
def hide_feedback_section():
    st.session_state['show_feedback_section'] = False
    st.session_state['assistant_answer'] = ""
    st.session_state['submitted_feedback'] = False
    st.session_state['submitted_time'] = None
    st.experimental_rerun()


# Function to record feedback to Google Sheets
def record_feedback(feedback):
    current_time_utc = datetime.utcnow()
    ist = pytz.timezone('Asia/Kolkata')
    current_time_ist = current_time_utc.astimezone(ist)
    formatted_time = current_time_ist.strftime('%Y-%m-%d %H:%M:%S')
    worksheet.append_row([formatted_time, assistant_name, feedback, user_question, st.session_state['assistant_answer']])


# Search button functionality
if st.button("Search"):
    if user_question:
        with st.spinner("Processing..."):
            st.session_state['assistant_answer'] = get_assistant_answer(user_question)
            st.session_state['show_feedback_section'] = True
    else:
        st.error("Please enter a question before searching.")

# Display assistant's answer and feedback section
if st.session_state['assistant_answer']:
    # Calculate the height based on the length of the answer
    length_of_answer = len(st.session_state['assistant_answer'])
    height = min(800, max(200, length_of_answer))  # Example calculation

    st.text_area("Assistant's Answer", value=st.session_state['assistant_answer'], height=int(height))

if st.session_state['show_feedback_section']:
    feedback = st.radio(
        "How helpful was the answer?",
        ["Very Helpful", "Helpful", "Neutral", "Not Helpful", "Very Not Helpful"],
        key='feedback'
    )

    # Left-align the submit feedback button
    st.markdown('<div class="left-align">', unsafe_allow_html=True)
    if st.button("Submit Feedback"):
        st.write("Thank you for your feedback!")
        record_feedback(feedback)
        st.session_state['submitted_feedback'] = True
        st.session_state['submitted_time'] = time.time()
        Timer(3.0, hide_feedback_section).start()  # Hide the feedback section after 3 seconds
    st.markdown('</div>', unsafe_allow_html=True)

# Check if feedback submitted and 3 seconds passed
if st.session_state['submitted_feedback']:
    if time.time() - st.session_state['submitted_time'] >= 3:
        hide_feedback_section()
