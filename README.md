# LinkedIn Content Studio

LinkedIn Content Studio is a Python application that turns a topic or niche
into researched, reviewed LinkedIn content. It uses a five-agent CrewAI pipeline
and offers both a Streamlit dashboard and a command-line interface.

The pipeline prepares content for a person to review and publish. It does not
connect to LinkedIn, publish posts, or create calendar events.

## Features

- Five specialist agents work in a strict sequential pipeline:
  research, writing, critique, optimization, and scheduling recommendations.
- Gemini is used for language-model tasks through Google AI Studio.
- Serper provides web search for the research stage.
- Shared CrewAI memory is enabled with Gemini embeddings.
- Each completed stage can be viewed on the dashboard; the final handoff
  includes the optimized post and publication recommendations.
- The dashboard uses a light white-and-maroon theme.
- The CLI remains available for terminal-based runs.

## Pipeline

| Stage | Agent | Responsibility |
| --- | --- | --- |
| Research | Trend Researcher Agent | Find current, relevant evidence and source links; note uncertainty and audience insights. |
| Writing | Content Writer Agent | Draft an original LinkedIn post grounded in the research. |
| Critique | Content Critic Agent | Identify factual risks and prioritized editorial improvements. |
| Optimization | Content Optimizer Agent | Apply the critique and produce copy-ready post text. |
| Scheduling | Scheduling Agent | Recommend testable posting windows and provide a pre-publication checklist. |

Tasks run in CrewAI's sequential process, with explicit task context passed from
each stage to the next. The crew is verbose, memory-enabled, and rate-limited
to four requests per minute to reduce the likelihood of hitting common
AI Studio request limits.

## Requirements

- Python 3.10 or newer
- Google AI Studio API key with access to the configured Gemini model
- Serper API key
- Internet access for Gemini and Serper API requests

Python dependencies are listed in [requirements.txt](requirements.txt), including
CrewAI, CrewAI tools, Streamlit, Google GenAI support, `python-dotenv`, OpenAI
SDK compatibility, Requests, and Beautiful Soup.

## Setup

Run these commands from the project directory:

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
cp .env.example .env
```

Edit `.env` and replace the example values:

```dotenv
AI_STUDIO_API_KEY=your_google_ai_studio_api_key
SERPER_API_KEY=your_serper_api_key
```

Do not commit `.env` or share its contents. Keep real API keys secret.

`AI_STUDIO_API_KEY` is also configured for the Google-backed CrewAI memory
provider at runtime. The current language model in
[linkedin_content_manager.py](linkedin_content_manager.py) is
`gemini/gemini-3.5-flash-lite`. If that model is not available to your Google
AI Studio project, change the model identifier to one supported by your account.

## Start the dashboard

With the virtual environment activated:

```bash
streamlit run app.py
```

Open the local URL printed by Streamlit, usually
[http://localhost:8501](http://localhost:8501). Enter a topic or niche and
select **Create LinkedIn post**. The dashboard displays the stage results and
final handoff on the same page.

To listen on all network interfaces (for access from another device on a
trusted network), use:

```bash
streamlit run app.py --server.address 0.0.0.0
```

Avoid exposing the app publicly without adding appropriate authentication and
network protections.

## Run from the command line

```bash
python linkedin_content_manager.py
```

Enter a topic or niche when prompted. The CLI prints each completed stage and
then the publish-ready handoff.

## Configuration

### Streamlit theme

The app's fixed light theme and brand colors are defined in
[.streamlit/config.toml](.streamlit/config.toml). It sets a white background,
dark readable text, maroon accent colors, and pale maroon secondary surfaces.

### Model and request rate

The Gemini model and request rate are configured in
[linkedin_content_manager.py](linkedin_content_manager.py). The current model is
`gemini/gemini-3.5-flash-lite`; the crew rate limit is `max_rpm=4`. The research
agent uses `SerperDevTool`, which reads `SERPER_API_KEY` from the environment.

## Troubleshooting

### Missing environment variables

Check that `.env` exists in the project directory and contains non-empty
`AI_STUDIO_API_KEY` and `SERPER_API_KEY` values. Restart the Streamlit app after
changing environment configuration.

### Gemini model not found (404)

Gemini model availability can depend on the account and API. If Gemini returns
a 404, use the model identifier currently supported by your AI Studio project
and update the `model` value in `build_crew()` in
[linkedin_content_manager.py](linkedin_content_manager.py). Restart the app so
it reloads the updated module and rerun the workflow.

### Gemini quota or rate limit (429)

Gemini may return 429 when the project's request or token quota is exhausted.
Wait until the quota resets or review the project's AI Studio quota and billing.
The crew is rate-limited, but the five stages and memory can still use more
requests than a free-tier quota allows.

### Serper search failure

Confirm that `SERPER_API_KEY` is correct and that the Serper account has
available quota. Research needs working web search to find sources.

### Dashboard does not start

Run Streamlit from the repository directory using the same Python environment
where `requirements.txt` was installed:

```bash
python -m streamlit run app.py
```

If port 8501 is already in use, stop the existing Streamlit process or select
another port:

```bash
python -m streamlit run app.py --server.port 8502
```

## Project files

```text
.
├── .env.example                 # Environment variable template
├── .streamlit/
│   └── config.toml              # Light white-and-maroon dashboard theme
├── app.py                       # Streamlit dashboard
├── linkedin_content_manager.py  # Agents, tasks, CrewAI setup, and CLI
├── README.md                    # Project documentation
└── requirements.txt             # Python dependencies
```

## Usage notes

- Treat research output as a starting point; confirm important claims and
  sources before publishing.
- Suggested publishing times are testable recommendations, not guarantees.
  Compare performance with your own audience analytics.
- The scheduling agent only prepares guidance. No post is actually scheduled
  or published.
