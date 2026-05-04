# 🧠 Career Interest Test MVP --- Technical Development Document

## 1. 🎯 Project Overview

We are building a **career interest test system** where:

1.  Users complete a questionnaire (Tally form)
2.  Responses are stored in Google Sheets (1 row per user)
3.  A Python backend:
    -   reads responses
    -   sends them to an LLM (OpenAI / Gemini)
    -   generates:
        -   interest profile scores
        -   ranked job recommendations
        -   short explanations
4.  Results are shown on a simple web page (HTML/CSS/JS)

------------------------------------------------------------------------

## 2. 🏗️ System Architecture

Tally Form ↓ Google Sheets (raw responses) ↓ Python Backend (core
logic + LLM) ↓ Processed Results Storage (Sheet or JSON DB) ↓ Frontend
Web App (results page)

------------------------------------------------------------------------

## 3. 📊 Data Flow

Step 1 --- User submits Tally form\
Step 2 --- Python reads Google Sheets\
Step 3 --- LLM processes answers\
Step 4 --- Structured JSON output\
Step 5 --- Store results\
Step 6 --- Frontend displays results

------------------------------------------------------------------------

## 4. 📥 LLM Input Format

{ "answers": { "Q1": "A", "Q2": "B", "Q3": "C" }, "job_list": \[
"Software Engineer", "Data Analyst", "UX Designer" \] }

------------------------------------------------------------------------

## 5. 📤 LLM Output Format

{ "scores": { "Software Engineer": 82, "Data Analyst": 76 }, "top_jobs":
\[ { "job": "Software Engineer", "score": 82, "reason": "Strong logical
thinking." } \], "summary": "You are analytical and structured." }

------------------------------------------------------------------------

## 6. 🐍 Backend Structure

backend/ ├── main.py ├── config.py ├── sheets_client.py ├──
llm_service.py ├── scoring_engine.py ├── prompt_templates.py ├──
models.py └── utils.py

------------------------------------------------------------------------

## 7. ⚙️ Core Logic

def process_user_response(row): answers = extract_answers(row) prompt =
build_prompt(answers) llm_response = call_llm(prompt) parsed =
parse_json(llm_response) save_results(parsed) return parsed

------------------------------------------------------------------------

## 8. 🧾 Prompt

SYSTEM: You are a career assessment engine. Return ONLY JSON.

USER: User answers: {answers}

Job list: {job_list}

Task: - score jobs (0--100) - pick top 3 - explain reasoning - return
JSON only

------------------------------------------------------------------------

## 9. 🌐 API Design

GET /api/results?email=xxx\
POST /api/process

------------------------------------------------------------------------

## 10. 🌐 Frontend Flow

/results.html?email=user@email.com

fetch('/api/results?email=...')

Render: - Top jobs - Scores - Summary

------------------------------------------------------------------------

## 11. 🧾 Google Sheets

Responses: email \| Q1 \| Q2 \| Q3 \| processed

Results: email \| top_jobs \| scores_json \| summary

------------------------------------------------------------------------

## 12. 🚀 Build Steps

1.  Google Sheets integration\
2.  LLM integration\
3.  Scoring engine\
4.  API backend\
5.  Frontend UI\
6.  Deployment
