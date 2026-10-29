<div align="center">

# 🧠 MultiagentAI — AI Research Assistant

### Ask a question. A team of AI agents researches it for you.

A Django-based web application where multiple specialized AI agents work together, using live web search, to research any topic and deliver a clear, organized, source-backed report.

![Python](https://img.shields.io/badge/Python-3.10%2B-blue?logo=python&logoColor=white)
![Django](https://img.shields.io/badge/Django-5.x-092E20?logo=django&logoColor=white)
![AI Agents](https://img.shields.io/badge/AI-Multi--Agent-8A2BE2)
![License](https://img.shields.io/badge/License-MIT-green)
![PRs Welcome](https://img.shields.io/badge/PRs-welcome-brightgreen)

[Overview](#-overview) · [Why Multi-Agent](#-why-multi-agent) · [How It Works](#-how-it-works) · [Features](#-features) · [Installation](#-installation) · [Usage](#-usage) · [FAQ](#-faq)

</div>

---

## 📑 Table of Contents

1. [Overview](#-overview)
2. [The Problem It Solves](#-the-problem-it-solves)
3. [Why Multi-Agent?](#-why-multi-agent)
4. [How It Works](#-how-it-works)
5. [Meet the Agents](#-meet-the-agents)
6. [Example Walkthrough](#-example-walkthrough)
7. [Features](#-features)
8. [Tech Stack](#-tech-stack)
9. [Project Structure](#-project-structure)
10. [Installation](#-installation)
11. [Configuration](#-configuration)
12. [Usage](#-usage)
13. [Data Model](#-data-model)
14. [Limitations](#-limitations)
15. [Roadmap](#-roadmap)
16. [Contributing](#-contributing)
17. [FAQ](#-faq)
18. [License](#-license)

---

## 📖 Overview

**MultiagentAI** is an AI-powered research assistant built with **Django**. Instead of relying on a single AI model to answer your question from memory, it uses a **team of AI agents**, each with a specific job, that cooperate to:

1. Understand your topic
2. Search the live web for relevant information
3. Read and evaluate what they find
4. Write a structured, easy-to-read report with sources

You type a topic. You get back a researched answer, along with the links so you can verify it yourself.

---

## 🎯 The Problem It Solves

Researching online is slow and repetitive:

- You open many tabs and search several times with different keywords.
- Many results are irrelevant, outdated, or repeat each other.
- You have to read each source, pick out the useful parts, and combine them yourself.
- Plain chatbots answer from training data, which may be outdated and often come with no sources.

**MultiagentAI automates this workflow.** It combines the reasoning ability of language models with fresh information from the web, and organizes the result into a report you can actually use.

---

## 🤝 Why Multi-Agent?

A single AI doing everything in one step tends to be shallow or inconsistent. Splitting the work between specialized agents gives better results:

| Single AI model | Multi-agent system |
|---|---|
| One prompt does planning, searching, reading, and writing | Each agent focuses on one task and does it well |
| Hard to debug when something goes wrong | You can see which stage produced which output |
| Easily misses sub-topics | A planner explicitly breaks the topic into sub-questions |
| Answers often unsourced | A dedicated step tracks sources and citations |
| Hard to extend | Add a new agent (e.g. fact-checker) without rewriting everything |

Think of it as a small research team: one person plans, one searches, one analyzes, one writes.

---

## ⚙️ How It Works

```
 ┌─────────────────┐
 │   User Query    │   "What are the latest advances in solid-state batteries?"
 └────────┬────────┘
          ▼
 ┌─────────────────┐
 │  Planner Agent  │   Breaks the topic into focused research questions
 └────────┬────────┘
          ▼
 ┌─────────────────┐
 │  Search Agent   │   Runs web searches for each question, collects results
 └────────┬────────┘
          ▼
 ┌─────────────────┐
 │  Analyst Agent  │   Reads results, removes noise, extracts key facts
 └────────┬────────┘
          ▼
 ┌─────────────────┐
 │  Writer Agent   │   Combines everything into a structured final report
 └────────┬────────┘
          ▼
 ┌─────────────────┐
 │  Final Report   │   Summary + key findings + source links, saved to history
 └─────────────────┘
```

**Step by step:**

1. **Input:** The user submits a topic or question through the web interface.
2. **Planning:** The planner turns the broad topic into several smaller, searchable questions so nothing important is missed.
3. **Searching:** The search agent sends those questions to a web search API and gathers titles, snippets, and URLs.
4. **Analysis:** The analyst agent reviews the results, filters out irrelevant or duplicate content, and extracts the important facts.
5. **Writing:** The writer agent turns the analyzed information into a readable report with headings, key points, and cited sources.
6. **Output:** The report is shown to the user and stored in the database so it can be revisited later.

---

## 🤖 Meet the Agents

> The roles below describe the intended design. Rename or adjust them to match your actual implementation.

### 🗺️ Planner Agent
**Job:** Understand what the user really wants to know.
**Input:** The original topic or question.
**Output:** A list of focused research questions or search queries.
**Why it matters:** Good research starts with good questions. This agent makes sure different angles of the topic are covered.

### 🔎 Search Agent
**Job:** Find relevant, up-to-date information on the web.
**Input:** The research questions from the planner.
**Output:** A collection of results (titles, snippets, URLs).
**Why it matters:** This is what gives the system access to current information beyond the AI model's training data.

### 🧪 Analyst Agent
**Job:** Make sense of the raw search results.
**Input:** The collected search results.
**Output:** Cleaned, relevant facts and key takeaways, linked to their sources.
**Why it matters:** Raw search results are noisy. This agent separates useful signal from clutter.

### ✍️ Writer Agent
**Job:** Produce the final, human-friendly report.
**Input:** The analyst's findings.
**Output:** A structured report: summary, key findings, and references.
**Why it matters:** Information is only useful if it's clearly communicated.

---

## 🔍 Example Walkthrough

**User asks:**
> "What is the current state of solid-state battery technology?"

**What happens behind the scenes:**

1. **Planner** produces sub-questions such as:
   - What are solid-state batteries and how do they differ from lithium-ion?
   - Which companies are leading development?
   - What are the main technical challenges?
   - When are they expected to reach consumers?
2. **Search agent** runs a web search for each sub-question.
3. **Analyst** reads the results, discards duplicates and low-quality pages, and extracts the key facts.
4. **Writer** produces a report like:

```
# Solid-State Batteries: Current State

## Summary
A short, plain-language overview of the topic...

## Key Findings
- Finding one (Source 1)
- Finding two (Source 2)
- Finding three (Source 3)

## Challenges
...

## Sources
1. Title: https://example.com/article-1
2. Title: https://example.com/article-2
```

*(The above is an illustrative format, not real output.)*

---

## ✨ Features

- 🤖 **Multi-agent architecture:** specialized agents collaborate instead of one model doing everything
- 🌐 **Live web search:** fetches current information from the internet
- 📚 **Source-backed reports:** every report includes links so findings can be verified
- 🧩 **Structured output:** summary, key points, and references in a consistent format
- 🕘 **Research history:** past queries and reports are saved and can be reopened
- 🔌 **Configurable providers:** change the LLM or search API through environment variables
- 🛠️ **Django admin panel:** manage stored research records easily
- 🧱 **Modular design:** add or modify agents without rewriting the whole app

---

## 🧰 Tech Stack

| Layer | Technology | Purpose |
|---|---|---|
| Language | Python 3.10+ | Core application language |
| Web framework | Django | Routing, views, ORM, admin, templates |
| AI / LLM | OpenAI-compatible LLM API | Powers the reasoning of each agent |
| Agent layer | Custom orchestration (or your framework of choice) | Coordinates the agents and passes data between them |
| Web search | Search API (e.g. Tavily, SerpAPI) | Retrieves live web results |
| Database | SQLite (default) | Stores research history; PostgreSQL-ready |
| Frontend | Django templates, HTML, CSS, JavaScript | User interface |

> Update this table to match the exact libraries and services you used.

---

## 📁 Project Structure

```
MultiagentAI/
│
├── manage.py                 # Django command-line utility
├── requirements.txt          # Python dependencies
├── .env.example              # Template for environment variables
├── .gitignore
├── README.md
│
├── config/                   # Django project configuration
│   ├── settings.py           # Settings (reads from environment variables)
│   ├── urls.py               # Root URL routes
│   └── wsgi.py / asgi.py
│
└── research/                 # Main application
    ├── models.py             # Database models (research sessions, results)
    ├── views.py              # Handles requests and displays reports
    ├── urls.py               # App-level routes
    ├── admin.py              # Admin panel configuration
    │
    ├── agents/               # The AI agents
    │   ├── planner.py
    │   ├── searcher.py
    │   ├── analyst.py
    │   └── writer.py
    │
    ├── services/             # External integrations
    │   ├── llm.py            # LLM API wrapper
    │   └── search.py         # Web search API wrapper
    │
    ├── templates/            # HTML templates
    └── static/               # CSS, JavaScript, images
```

> Edit this tree to match your actual folders and file names.

---

## 🚀 Installation

### Prerequisites

- **Python 3.10 or higher**
- **pip** and **venv**
- **Git**
- An **API key for an LLM provider**
- An **API key for a web search provider**

### Steps

**1. Clone the repository**
```bash
git clone https://github.com/<your-username>/MultiagentAI.git
cd MultiagentAI
```

**2. Create and activate a virtual environment**
```bash
python -m venv venv

# macOS / Linux
source venv/bin/activate

# Windows
venv\Scripts\activate
```

**3. Install dependencies**
```bash
pip install -r requirements.txt
```

**4. Set up environment variables**
```bash
cp .env.example .env
```
Open `.env` and add your keys (see [Configuration](#-configuration)).

**5. Run database migrations**
```bash
python manage.py migrate
```

**6. (Optional) Create an admin account**
```bash
python manage.py createsuperuser
```

**7. Start the development server**
```bash
python manage.py runserver
```

**8. Open the app**

Visit **http://127.0.0.1:8000** in your browser.

---

## 🔐 Configuration

All secrets and settings live in a `.env` file in the project root:

```env
# --- Django ---
SECRET_KEY=your-django-secret-key
DEBUG=True
ALLOWED_HOSTS=127.0.0.1,localhost

# --- LLM provider ---
LLM_API_KEY=your-llm-api-key
LLM_MODEL=your-model-name

# --- Web search provider ---
SEARCH_API_KEY=your-search-api-key
```

| Variable | Required | Description |
|---|---|---|
| `SECRET_KEY` | Yes | Django secret key. Generate a long random string. |
| `DEBUG` | Yes | `True` for development, `False` for production. |
| `ALLOWED_HOSTS` | Yes | Comma-separated list of allowed hostnames. |
| `LLM_API_KEY` | Yes | API key for your language model provider. |
| `LLM_MODEL` | Yes | Name of the model the agents should use. |
| `SEARCH_API_KEY` | Yes | API key for your web search provider. |

> ⚠️ **Never commit your `.env` file.** Make sure it is listed in `.gitignore`, and never share your API keys publicly.

---

## 💡 Usage

1. **Open the app** in your browser.
2. **Enter a topic or question** in the search box. Good examples:
   - *"How does CRISPR gene editing work and what are its risks?"*
   - *"Compare electric vehicle adoption in Europe and Asia."*
   - *"Latest trends in renewable energy storage."*
3. **Submit** and wait while the agents plan, search, analyze, and write.
4. **Read the report**, including the summary, key findings, and sources.
5. **Click the source links** to verify any claim you care about.
6. **Return to the history page** to reopen earlier research.

**Tips for better results:**
- Be specific. "Solid-state battery challenges in 2026" works better than "batteries."
- Ask focused questions rather than several unrelated ones at once.
- Always check the sources for anything important.

---

## 🗄️ Data Model

> Example structure. Adjust to match your `models.py`.

| Model | Fields (example) | Purpose |
|---|---|---|
| `ResearchSession` | `id`, `query`, `status`, `created_at` | One record per research request |
| `SearchResult` | `session`, `title`, `url`, `snippet` | Raw results collected by the search agent |
| `Report` | `session`, `summary`, `content`, `created_at` | The final report produced by the writer agent |

---

## ⚠️ Limitations

Being honest about what this project can and can't do:

- **AI can make mistakes.** Reports may contain errors, misinterpretations, or outdated details. Always verify important information using the cited sources.
- **Quality depends on search results.** If the search API returns poor or limited results, the report will reflect that.
- **API costs and limits.** LLM and search APIs may charge per request or have rate limits.
- **Not a replacement for expert advice.** Do not rely on this tool alone for medical, legal, or financial decisions.
- **Speed.** Several agents making several API calls takes time, so a report may take a while to generate.

---

## 🗺️ Roadmap

- [ ] Stream results live as each agent finishes
- [ ] Export reports to PDF and Markdown
- [ ] User accounts and saved research collections
- [ ] Upload documents (PDF, text) as additional sources
- [ ] Add a fact-checker agent to verify claims
- [ ] Source credibility scoring
- [ ] Docker setup for one-command deployment
- [ ] Support for multiple LLM providers with a simple switch
- [ ] REST API for programmatic access

---

## 🤝 Contributing

Contributions of all kinds are welcome: bug fixes, new agents, documentation, or ideas.

1. **Fork** the repository.
2. **Create a branch** for your change:
   ```bash
   git checkout -b feature/your-feature-name
   ```
3. **Make your changes** and test them.
4. **Commit** with a clear message:
   ```bash
   git commit -m "Add: short description of your change"
   ```
5. **Push** your branch:
   ```bash
   git push origin feature/your-feature-name
   ```
6. **Open a Pull Request** describing what you changed and why.

For larger changes, please open an issue first so we can discuss the approach.

---

## ❓ FAQ

**Is this free to use?**
The project itself is open source, but the LLM and search APIs it relies on may have their own costs.

**Do I need to know AI to use it?**
No. You only type a question. The agents handle the rest.

**How is this different from a normal chatbot?**
A chatbot mostly answers from what it learned during training. MultiagentAI actively searches the web, so it can include recent information and show sources.

**Can I change which AI model it uses?**
Yes. Update the model and API key in your `.env` file, provided the provider is supported by the code.

**Can I add my own agent?**
Yes. Agents live in the `agents/` folder. Create a new one and plug it into the workflow.

**Is my data stored?**
Research queries and reports are saved in your local database so you can view your history. Nothing is shared unless you deploy it publicly.

---

## 📄 License

This project is licensed under the **MIT License**. See the [LICENSE](LICENSE) file for details.

---

## 🙌 Acknowledgments

- [Django](https://www.djangoproject.com/) for the web framework
- The LLM and search API providers that power the agents
- Everyone who contributes ideas, code, and feedback

---

<div align="center">

### ⭐ If you find this project useful, please star the repository!

Made with ❤️ using Django and AI

</div>
