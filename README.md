# 🏛️ Heritage Sentinel AI (Heritage Vanguards)

![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)
![Python](https://img.shields.io/badge/Python-3.10%2B-blue)
![Next.js](https://img.shields.io/badge/Next.js-14-black)
![PostgreSQL](https://img.shields.io/badge/PostgreSQL-16-blue)
![Docker](https://img.shields.io/badge/Docker-Ready-2496ED)

> **Moving from "discovery" to "protection" in minutes, not months.**

## 🌍 The Silent Loss
Cultural heritage is humanity’s memory. But did you know that 90% of some archaeological sites are destroyed before they are even officially identified? It’s not just a lack of preservation—it’s a structural detection blindspot. In a world where conflict and climate change move faster than academic bureaucracy, we need a smarter, faster way to protect our history. 

**This is Heritage Sentinel AI.**

---

## 🧠 Agentic Intelligence: The Solution

We built a **3-agent sequential pipeline** to solve the three failures of modern preservation: Evidence, Deduplication, and Scoring.

### 🕵️‍♂️ Agent 1: The Registry Agent
Cross-references new submissions against the official UNESCO dataset. If a site is already protected, the workflow stops—saving human experts from redundant work.

### 🔬 Agent 2: The Evaluation Agent (Gemini Powered)
Acts as an evidence extraction engine. It analyzes raw text, detects languages, and scans photos to identify key indicators (Outstanding Universal Value). It then passes this structured data to a deterministic scoring tool, ensuring our **Heritage Score** is based on solid evidence, not model hallucinations.

### ⚖️ Agent 3: The Verification Agent (Human-in-the-Loop)
Our system doesn't make autonomous final decisions; it equips experts to make rapid, informed choices. This agent generates a detailed **Confidence Card** for the archaeologist reviewer.

---

## 📸 The Golden Path (Demo)

In less than three minutes, our pipeline transforms a messy, multi-lingual field report into an actionable nomination. 

### 1. The Ingestion Stage
Users can submit raw field data and photos from anywhere in the world. 
![Ingestion View](./assets/ingestion.png) ### 2. The Data Transformation
The AI automatically translates, extracts historical features, and structures the raw data into a clean JSON dossier.
![Data Transformation](./assets/transformation.png) ### 3. AI-Assisted Verification (The Confidence Card)
The Archaeologist Reviewer is presented with an AI-generated Heritage Score and OUV breakdown, empowering them to approve or reject the site rapidly.
![Confidence Card - Ajanta Caves](./assets/confidence-card.png) ---

## 🛠️ Technical Stack & Architecture

* **Frontend:** Next.js (React), TailwindCSS
* **Backend:** FastAPI (Python)
* **Database:** PostgreSQL (with Asyncpg & Alembic for migrations)
* **AI Engine:** Google Gemini
* **Infrastructure:** Docker & Docker Compose, Nginx (Reverse Proxy)

---

## 🚀 Quick Start (Local Deployment)

To run the Heritage Sentinel AI locally, ensure you have [Docker](https://www.docker.com/) installed.

1. **Clone the repository:**
   ```bash
   git clone [https://github.com/sriyaa-p/heritage-vanguards.git](https://github.com/sriyaa-p/heritage-vanguards.git)
   cd heritage-vanguards
