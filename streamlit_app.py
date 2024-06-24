
__import__('pysqlite3')
import sys
sys.modules['sqlite3'] = sys.modules.pop('pysqlite3')

import streamlit as st
import os
from crewai import Agent, Task, Crew, Process
from crewai_tools import SerperDevTool, PDFSearchTool

os.environ["OPENAI_API_KEY"] = st.secrets["OPENAI_API_KEY"]
os.environ["SERPER_API_KEY"] = st.secrets["SERPER_API_KEY"]
os.environ["OPENAI_MODEL_NAME"] = st.secrets["OPENAI_MODEL_NAME"]

pdf_file_path = os.path.join(os.path.dirname(__file__), '.', 'data', 'ortb_spec_2dot5.pdf')

if not os.path.isfile(pdf_file_path):
    st.error("PDF file not found at path: " + pdf_file_path)
else:
    pass
    # st.success("PDF file found at path: " + pdf_file_path)
    
spec_pdf_tool = PDFSearchTool(pdf=pdf_file_path)
search_tool = SerperDevTool()

# Streamlit interface
st.title("Bid Request Generator")

# User input
user_request = st.text_area("Enter your request:", 
    "List your request requirements here!"
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

    request_intake_task = Task(
        description="Translate the user request into a discrete list of requirements. Use both the provided openRTB spec PDF as well as internet searches to augment knowledge as necessary.",
        expected_output="A list of items that represent the mapping of the user request to openRTB field-level requirements, formatted as JSON.",
        agent=request_intake_agent,
        priority=1,
        timeout=60,
    )
    
    dependency_map_task = Task(
        description="Uses the provided openRTB spec PDF and requirements list to create a map of the various objects and fields within those objects that are required. This should be done recursively to make sure that cross-dependencies and downstream considerations are accounted for. Also include recommended fields where possible to more closely align with real-world data patterns.",
        expected_output="A semi-structured list of objects and fields that are required, detailed with interdependencies.",
        agent=dependency_map_agent,
        priority=2,
        timeout=60,
        dependencies=[request_intake_task.id],  # Ensure this runs after request intake
    )

    requirement_adherence_task = Task(
        description="Uses the provided openRTB spec PDF, semi-structured object and field requirements list, and internet research as necessary to generate a structured bid request with both keys and values that meet the requirements. Prefer sample values from the examples found in the spec PDF rather than boilerplate values where possible.",
        expected_output="A JSON file containing a structured bid request with both keys and values that meet the requirements, validated against the latest spec.",
        agent=requirement_adherence_agent,
        # output_file=output_file_path,
        priority=3,
        timeout=60,
        dependencies=[dependency_map_task.id],  # Ensure this runs after dependency mapping
    )

    # Create the project crew
    # crew = Crew([request_intake_agent, dependency_map_agent, requirement_adherence_agent])
    project_crew = Crew(
        name="OpenRTB Project Crew",
        tasks=[request_intake_task, dependency_map_task, requirement_adherence_task],
        agents=[request_intake_agent, dependency_map_agent, requirement_adherence_agent],
        process=Process.sequential,
        memory=True,
    )

    process = Process(project_crew.kickoff())
    
    # Wait for the process to complete
    while not process.completed:
        process.step()

    raw_output = requirement_adherence_task.output.raw_output
    json_content = re.search(r"```json\n([\s\S]*?)\n```", raw_output).group(1)
    
    # Display the results
    st.subheader("Bid Request")
    st.json(json_content)

# To run this Streamlit app, save this code to a file (e.g., `app.py`) and run `streamlit run app.py` in your terminal.
