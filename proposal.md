We are developing a career interest test and are looking for a developer to turn it into a functional MVP.
The questionnaire will be built in Tally, and responses will be sent automatically to Google Sheets. We now need someone to implement the logic, connect the tools, and build a simple results interface.
Your mission
- Develop, in Python, a scoring system that uses a LLM API (Gemini, OpenAI or similar). The script should:
* read users’ answers from Google Sheets,
* call the LLM with the relevant data,
* parse the output to produce interest scores and a match with an existing list of jobs.The code should be clean, configurable and easy to extend
- Connect this logic to a simple web interface in HTML, CSS and JavaScript: users complete the questionnaire, submit, and are redirected to a results page showing their top recommended jobs and brief explanations.



- Design and implement the necessary LLM prompts (with guidance from our technical lead), so that the model produces clear, short feedback texts based on the results.



- Use the Tally → Google Sheets connection (one row per respondent, including email address), process the data with your Python + LLM pipeline, and output all information needed for the results display.



- Provide light technical documentation: how to run the project locally, where to edit prompts, jobs and main parameters, and how the data flows between Tally, Sheets, the LLM and the results page.



You will follow clear functional guidelines and work closely with a technical lead and a subject‑matter expert in career guidance. We are looking for a very hands‑on AI / software engineer, comfortable with Python, LLM APIs and basic web development.
