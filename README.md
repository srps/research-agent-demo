
# Research Agent Demo

An AI-powered research assistant that automates the process of gathering, analyzing, and synthesizing information on any given topic. Built with OpenAI's API and Streamlit.

## Features

- 🤖 AI-driven research planning and execution
- 🔍 Automated web search and content summarization
- 📊 Intelligent gap analysis (optional)
- 📝 Markdown report generation
- 💻 Interactive Streamlit interface

## Installation

1. Clone the repository:

```bash
git clone https://github.com/yourusername/research-agent-demo.git
cd research-agent-demo
```

2. Install dependencies:

```bash
pip install -r requirements.txt
```

3. Create a `.env` file in the root directory and add your OpenAI API key:

```bash
OPENAI_API_KEY=your_openai_api_key_here
```

## Usage

1. Start the Streamlit app:

```bash
streamlit run main.py
```

2. Open your browser and navigate to `http://localhost:8501`
3. Enter your research topic
4. Configure research settings (e.g., enable/disable gap analysis)
5. Start the research process
6. Review and download the generated report

## Architecture

The system follows a modular architecture with several specialized agents working together. For a detailed view of the system's flow and component interactions, see [sequence.md](sequence.md).

### Key Components

1. **TriageAgent**
   - Validates research queries
   - Requests clarification when needed
   - Ensures quality input for research

2. **ResearchPlannerAgent**
   - Generates structured research plans
   - Breaks down topics into manageable subtasks
   - Prioritizes research questions

3. **WebSearchAgent**
   - Performs targeted web searches
   - Extracts relevant information
   - Summarizes findings

4. **DecisionAgent**
   - Evaluates research completeness
   - Identifies knowledge gaps
   - Determines when to conclude research

5. **ReportGeneratorAgent**
   - Synthesizes research findings
   - Generates formatted reports
   - Includes citations and references

## Configuration

### Research Settings

- **Skip Gap Analysis**: Toggle to bypass the gap identification phase
- **Display Settings**: Control visibility of research plan and progress
- **API Configuration**: Manage OpenAI API settings

### Environment Variables

| Variable | Description | Required |
|----------|-------------|----------|
| OPENAI_API_KEY | Your OpenAI API key | Yes |

## Dependencies

- Python ≥3.12
- OpenAI ≥1.66.2
- Streamlit ≥1.43.2
- Additional requirements in `requirements.txt`

## Development

### Project Structure

```bash
research-agent-demo/
├── main.py                 # Application entry point
├── sequence.md            # System flow documentation
├── research_agent/        # Core agent modules
│   ├── planner.py        # Research planning logic
│   ├── search.py         # Web search functionality
│   ├── decision.py       # Research evaluation
│   ├── report.py         # Report generation
│   ├── triage.py         # Query validation
│   └── models.py         # Data models
├── requirements.txt       # Project dependencies
└── README.md             # This file
```

### Contributing

1. Fork the repository
2. Create a feature branch
3. Commit your changes
4. Push to the branch
5. Create a Pull Request

## License

[MIT License](LICENSE)

## Acknowledgments

- OpenAI for their API
- Streamlit for the web interface framework
- Contributors and maintainers

## Support

For support, please open an issue in the GitHub repository or contact the maintainers.
