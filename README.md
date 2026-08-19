# Physics AI Tutor

![CI](https://github.com/k94-ishi/physics-ai-tutor/actions/workflows/ci.yml/badge.svg)
![License](https://img.shields.io/badge/license-MIT-blue.svg)

Physics AI Tutor is an AI-assisted learning platform for high school physics students.

I previously worked as a high school physics teacher in Japan for three years. Through teaching experience, I noticed that many students struggled not only with understanding physics concepts but also with formulating the right questions.

This project aims to help students learn physics by combining:

- Structured educational knowledge management
- Semantic search using vector embeddings
- Retrieval-Augmented Generation (RAG)
- Human review workflows for AI-generated content

The goal is to build a reliable AI tutor that explains physics based on verified educational knowledge.

---

## Live Application

https://ai-tutor.pencil-net.com

---

## Getting Started

To run the project locally, see [docs/development.md](docs/development.md).

---

## Screenshots

English UI mode, with question and answer content still in Japanese (see [Features](#features)).

### Home / question list
![Home page in English UI mode](docs/images/home-en.png)

### AI similarity search results
<details><summary>Screen Shot</summary>

![AI search results with relevance scores](docs/images/search-en.png)

</details>

### Question detail page
<details><summary>Screen Shot</summary>

![Question detail page with related questions](docs/images/detail-en.png)

</details>

### Manage questions
<details><summary>Screen Shot</summary>

![Manage questions page](docs/images/manage-questions-en.png)

</details>

### Edit question
<details><summary>Screen Shot</summary>

![Edit question page](docs/images/edit-question-ja.png)

</details>

---

## System Architecture

```mermaid
flowchart LR
    User[User Browser]

    User --> Frontend[Next.js Frontend]

    Frontend --> Backend[FastAPI Backend]

    Backend --> DB[(Supabase PostgreSQL<br/>+ pgvector)]

    Backend --> Embedding[OpenAI Embedding API<br/>text-embedding-3-small]

    Backend --> LLM[DeepSeek API]
```

The backend acts as the central application layer, connecting the frontend, knowledge database, embedding service, and LLM generation service.

---

## AI/RAG Architecture

The application is designed to minimize unnecessary LLM usage by prioritizing existing educational knowledge.

```mermaid
flowchart LR
    U[User Question]

    DB[(PostgreSQL + pgvector<br/><br/>Questions<br/>Embeddings<br/>Concepts)]

    U --> EXACT{Exact Match Search}

    EXACT -->|Found| EXIST[Reuse Existing QA]

    EXACT -->|Not Found| EMB[Generate Embedding]

    EMB --> SEARCH[Vector Similarity Search]

    SEARCH <--> DB

    SEARCH --> SIM{High Similarity QA?}

    SIM -->|Yes| EXIST

    SIM -->|No| CONTEXT[Build RAG Context]

    CONTEXT --> LLM[DeepSeek<br/>LLM Generation]

    LLM --> ANSWER[AI Tutor Answer]

    ANSWER --> SAVE[Save AI-generated QA<br/>Status: UNREVIEWED]

    SAVE --> DB

    DB --> REVIEW[Admin Review]

    REVIEW -->|Approved| DB

    EXIST --> NEXT[Suggest Next Questions<br/>Concept-based Recommendation]

    ANSWER --> NEXT

    NEXT --> USER_ACTION[User selects next question]

    USER_ACTION --> U
```

### Design Principles

- Prefer existing verified knowledge over generating new answers
- Reduce unnecessary LLM API calls
- Ground AI responses with retrieved educational content
- Improve knowledge quality through human review

---

## Features

### AI-assisted Physics Question Answering

- Search existing physics explanations using semantic similarity
- Retrieve relevant educational content before generation
- Generate AI answers using Retrieval-Augmented Generation (RAG)
- Store generated answers for future knowledge reuse

### Semantic Question Search

- Generate embeddings for physics questions
- Store vectors using PostgreSQL + pgvector
- Search similar questions using cosine similarity
- Reuse existing knowledge before calling LLMs

### Knowledge Management

- Admin dashboard for educational content management
- Review workflow for AI-generated answers
- Separate approved content from unreviewed AI outputs

### Authentication and Authorization

- JWT-based authentication with HttpOnly cookies
- Role-based access control
- Admin-only management operations

### Responsive Web Application

- Next.js-based frontend
- Responsive UI for desktop and mobile browsers
- Japanese / English UI switching support

---

## Tech Stack

### Backend

- Python
- FastAPI
- SQLAlchemy
- PostgreSQL
- pgvector
- Alembic
- pytest

### Frontend

- Next.js (App Router)
- React
- TypeScript
- Tailwind CSS

### Infrastructure

- Docker Compose
- Vercel
- Render
- Supabase PostgreSQL

### AI

- OpenAI Embedding API (`text-embedding-3-small`)
- DeepSeek API for LLM generation

---

## Project Structure

```
physics-ai-tutor
├── backend
│   ├── physics_ai_tutor     # FastAPI application
│   ├── tests                # Backend tests
│   ├── alembic              # Database migrations
│   └── pyproject.toml
│
├── frontend
│   ├── src                  # Next.js application
│   ├── public
│   └── package.json
│
├── docs
│   └── development.md       # Development guide
│
├── docker-compose.yml
├── README.md
└── LICENSE
```

---

## Deployment

Production environment:

- Frontend: Vercel
- Backend: Render
- Database: Supabase PostgreSQL

---

## Future Improvements

- Expand English language support
- Support more physics domains
- Improve AI answer evaluation workflow
- Add more educational content generation features

---

## License

This project is licensed under the MIT License.
