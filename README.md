# Multi Agent travel AI assistant
Multi Agent travel AI assistant is a multi-agent system designed to assist users in planning travel itineraries efficiently. By leveraging AI agents, the system aims to automate and optimize various aspects of travel planning, providing users with tailored itineraries based on their preferences and constraints.​

![image](https://github.com/user-attachments/assets/dc21c407-fa46-44e6-9c9e-7bdff15c5951)


## Features
* **Multi-Agent Architecture**: Utilizes a system of AI agents, each responsible for specific tasks such as destination selection, accommodation booking, and activity scheduling.

* **Streamlit UI**: Provides an interactive web interface for users to input preferences and view generated itineraries.

* **Modular Design**: Structured codebase with separate modules for agents, utilities, and UI components, facilitating easy maintenance and scalability.

## Project Structure
```
travel_ai_agent/
├── agents/               # Contains agent definitions and logic
├── extras/               # Additional resources and data
├── streamlit_ui.py       # Streamlit-based user interface
├── agent_graph.py        # Defines the interaction graph between agents
├── utils.py              # Utility functions used across the project
├── requirements.txt      # Python dependencies
└── README.md             # Project documentation
```

## Installation
### 1. Clone the repository:
```
git clone https://github.com/jainutk20/travel_ai_agent.git
cd travel_ai_agent
```
### 2. Create a virtual environment (optional but recommended):
```
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```
### 3. Install the required packages:
```
pip install -r requirements.txt
```

## Usage
To launch the Streamlit interface:
```bash
streamlit run streamlit_ui.py
```
This will open a web application in your default browser where you can input your travel preferences and generate a customized itinerary.

## Contributing
Contributions are welcome! If you have suggestions for improvements or new features, feel free to fork the repository and submit a pull request.

## References
I followed the following youtube video for this project: https://www.youtube.com/watch?v=AgN3RHSZGwI&t=1818s  
Kudos to `Cole Medin` for introducing this fantastic multi-agent async architecture!

## Future work
There are quite a few things that can be improved in this project. For instance, the tool calls at the moment are using hardcoded values which can be replaced by actual API calls. 

I will continue to improve this project with time. If you would like to collaborate on making this project better, please reach out!
