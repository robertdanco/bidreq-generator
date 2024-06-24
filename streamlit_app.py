__import__('pysqlite3')
import sys
sys.modules['sqlite3'] = sys.modules.pop('pysqlite3')

import streamlit as st
import os
from crewai import Agent, Task, Crew, Process
from crewai_tools import SerperDevTool, PDFSearchTool

"""
# Welcome to Streamlit!

Edit `/streamlit_app.py` to customize this app to your heart's desire :heart:.
If you have any questions, checkout our [documentation](https://docs.streamlit.io) and [community
forums](https://discuss.streamlit.io).

In the meantime, below is an example of what you can do with just a few lines of code:
"""


os.environ["OPENAI_API_KEY"] = st.secrets["OPENAI_API_KEY"]
os.environ["SERPER_API_KEY"] = st.secrets["SERPER_API_KEY"]
os.environ["OPENAI_MODEL_NAME"] = st.secrets["OPENAI_MODEL_NAME"]

pdf_file_path = os.path.join(os.path.dirname(__file__), '..', 'data', 'ortb_spec_2dot5.pdf')

if not os.path.isfile(pdf_file_path):
    st.error("PDF file not found at path: " + pdf_file_path)
else:
    st.success("PDF file found at path: " + pdf_file_path)
    
spec_pdf_tool = PDFSearchTool(pdf=pdf_file_path)
search_tool = SerperDevTool()

# Streamlit interface
st.title("Bid Request Generator")

# User input
user_request = st.text_area("Enter your request:", 
    "generate a bid request from FreeWheel for a connected TV video opportunity with a variety of deals and associated deal types, and include a SupplyChain object. Make sure at least one deal has a different auction type than the overall request."
)

if st.button("Generate Bid Request"):
    # Define the agents
    request_intake_agent = Agent(
        role="Request Intake Agent",
        goal=f"Translates the user request into a discrete list of requirements. Request: {user_request}",
        backstory="Expert in analyzing and structuring user inputs into actionable data.",
        allow_delegation=True,
        cache=False,
        tools=[spec_pdf_tool, search_tool],
    )

    dependency_map_agent = Agent(
        role="Dependency Map Agent",
        goal="Uses the provided openRTB spec PDF and requirements list to create a map of the various objects and fields within those objects that are required.",
        backstory="Specializes in mapping dependencies and relationships within complex data specifications.",
        allow_delegation=False,
        cache=False,
        tools=[spec_pdf_tool],
    )

    requirement_adherence_agent = Agent(
        role="Requirement Adherence Agent",
        goal="Uses the provided openRTB spec PDF, semi-structured object and field requirements list to generate a structured bid request with both keys and values that meet the requirements.",
        backstory="Focused on ensuring compliance and accuracy in data formatting and integration according to specifications.",
        allow_delegation=False,
        cache=False,
        tools=[spec_pdf_tool],
    )

    # Define and execute the tasks
    request_intake_task = Task(
        description="Translate the user request into a list of requirements.",
        agent=request_intake_agent
    )
    
    # Create Crew
    crew = Crew([request_intake_agent, dependency_map_agent, requirement_adherence_agent])

    # Run the process
    process = Process(crew=crew)
    process.start([request_intake_task])
    
    # Wait for the process to complete
    while not process.completed:
        process.step()
    
    # Display the results
    st.subheader("Bid Request")
    st.json(process.output)

# To run this Streamlit app, save this code to a file (e.g., `app.py`) and run `streamlit run app.py` in your terminal.
