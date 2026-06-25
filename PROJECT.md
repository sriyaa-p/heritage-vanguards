# Heritage Sentinel AI

### Preserving What Humanity Cannot Rebuild — With Multi-Agent AI

**Agents Intensive Capstone Project | Hackathon MVP | July 2026**

---

# Project Overview

Heritage Sentinel AI is a multi-agent system designed to reduce the heritage detection gap by helping communities submit potential heritage sites for expert review.

The system transforms unstructured community evidence into structured, explainable nomination dossiers through a sequential agent workflow.

The objective is not to automatically designate heritage sites.

The objective is to help archaeologists and heritage experts review submissions faster by providing:

* Structured evidence
* Registry deduplication
* Explainable scoring
* Human-in-the-loop verification

All final decisions remain with human reviewers.

---

# Problem Statement

Cultural heritage sites are frequently lost before they are formally documented.

Researchers estimate that a significant number of archaeological and culturally important sites remain undocumented worldwide.

Current nomination and review processes suffer from three major problems:

## P1 — Evidence Failure

Community reports arrive as:

* Photographs
* Text descriptions
* Multiple languages
* Inconsistent formats

Reviewers must manually organize and interpret submissions.

## P2 — Deduplication Failure

Submissions are evaluated independently.

Without automated registry checks:

* Existing sites may be re-submitted
* Reviewer time is wasted
* Protected sites may be re-evaluated unnecessarily

## P3 — Evaluation Failure

Early-stage assessment requires significant expert effort.

Reviewers spend time:

* Reading submissions
* Extracting evidence
* Comparing indicators
* Prioritizing candidates

This creates review bottlenecks.

---

# MVP Goal

The MVP will provide a complete end-to-end workflow:

1. Community member submits a candidate heritage site.
2. System checks whether the site already exists in the registry dataset.
3. System extracts evidence from the submission.
4. System generates an explainable Heritage Score.
5. System generates a Confidence Card.
6. Human reviewer approves or rejects the submission.

The MVP focuses on:

* Explainability
* Human oversight
* Reproducibility
* Fast review workflows

The MVP does not attempt to replace expert judgment.

---

# Solution Overview

Heritage Sentinel AI is a three-agent sequential workflow.

Community evidence is transformed into a structured nomination dossier that can be reviewed by heritage experts.

## Why Agentic AI

Traditional form-based systems cannot:

* Process multilingual submissions automatically
* Deduplicate semantically similar sites
* Generate explainable evidence summaries
* Enforce human approval before progression

Agents enable:

* Structured intake
* Registry lookup
* Evidence extraction
* Confidence-card generation
* Human review checkpoints

---

# Architecture

## Agent 1 — RegistryAgent

### Purpose

Prevent duplicate evaluation of already-documented sites.

### Responsibilities

* Receive Canonical Dossier
* Search UNESCO World Heritage Sites dataset
* Perform BM25 retrieval to identify the Top 5 candidate matches
* Use Gemini to compare the submission against retrieved candidates
* Detect potential duplicate submissions

### Outputs

#### If Match Found

* Existing site details returned
* Duplicate flag recorded in dossier
* Workflow terminated

#### If No Match Found

* Dossier forwarded to EvaluationAgent

---

## Agent 2 — EvaluationAgent

### Purpose

Extract evidence and generate explainable scoring.

### Responsibilities

Gemini acts only as an evidence extraction engine.

Gemini does not:

* Assign scores
* Approve sites
* Determine heritage status

Gemini extracts:

* Historic features
* Cultural significance indicators
* Geographic context
* Documentation evidence
* Supporting evidence

---

## Structured Evidence Extraction

To prevent mismatches between evidence extraction and scoring, Gemini never sends free-form text directly to the scoring engine.

Instead, Gemini returns structured outputs that conform to a predefined schema.

Evidence is extracted into the following categories:

* Historic Features
* Cultural Significance
* Geographic Context
* Documentation
* Supporting Evidence

The output is validated using Pydantic before scoring begins.

Workflow:

```text
Community Evidence
        │
        ▼
Gemini Structured Extraction
        │
        ▼
Pydantic Validation
        │
        ▼
Deterministic Scoring Engine
        │
        ▼
Heritage Score
```

This ensures:

* Predictable scorer inputs
* Reduced category ambiguity
* Consistent scoring
* Easier evaluation and debugging

Gemini extracts evidence.

The scoring engine assigns points.

The human reviewer makes the final decision.

---

### Evidence Categories

| Category              | Maximum Points |
| --------------------- | -------------- |
| Historic Features     | 30             |
| Cultural Significance | 25             |
| Geographic Context    | 15             |
| Documentation         | 15             |
| Supporting Evidence   | 15             |
| Total                 | 100            |

---

### Outputs

#### Heritage Score

0–100

#### Confidence Level

* Low
* Moderate
* High

#### Evidence Summary

Plain-language explanation of:

* Evidence found
* Missing evidence
* Category breakdown

Example:

```text
Historic Features: 25/30
Cultural Significance: 20/25
Geographic Context: 13/15
Documentation: 5/15
Supporting Evidence: 15/15

Total Heritage Score: 78/100
Confidence Level: Moderate
```

---

## Agent 3 — VerificationAgent

### Purpose

Generate reviewer-facing decision package.

### Responsibilities

Create a Confidence Card containing:

* Heritage Score
* Category Breakdown
* Confidence Level
* Evidence Summary

Present dossier to reviewer.

Pause workflow until reviewer action occurs.

### Reviewer Actions

#### Approve

Submission enters approval queue.

#### Reject

Submission archived with rejection reason.

---

# Sequential Workflow

```text
Community Submission
        │
        ▼
   Intake Processor
        │
        ▼
   Canonical Dossier
        │
        ▼
   RegistryAgent
        │
 ┌──────┴──────┐
 │ Duplicate?  │
 └──────┬──────┘
        │
   Yes ─┘
        ▼
 Existing Record

        No
        │
        ▼
 EvaluationAgent
        │
        ▼
 Deterministic Scoring
        │
        ▼
 VerificationAgent
        │
        ▼
 Confidence Card
        │
        ▼
 Archaeologist Decision
        │
   ┌────┴────┐
   ▼         ▼
Approve   Reject
```

---

# Canonical Dossier

The Canonical Dossier is the system's single source of truth.

All agents read from and write to the dossier.

---

## Persistent State Management

The system does not rely on in-memory session storage.

Workflow state is stored inside PostgreSQL through the Canonical Dossier.

Each agent:

1. Reads the latest dossier.
2. Performs its task.
3. Writes outputs back to PostgreSQL.
4. Updates workflow status.

Benefits:

* No loss of state after server restarts
* Long-running workflows remain recoverable
* Consistent agent context
* Complete auditability of processing steps

PostgreSQL therefore acts as the persistent memory layer of the system.

---

## Dossier Sections

### Metadata

* Submission ID
* Status
* Timestamp

### Raw Evidence

* Photos
* Description
* Source language
* Translated description

### Registry Check

* Match status
* Top candidate matches

### Extracted Evidence

* Historic features
* Cultural indicators
* Geographic indicators
* Supporting evidence

### Scoring

* Category scores
* Heritage score
* Confidence level

### Review

* Reviewer decision
* Notes
* Timestamp

---

# Technology Stack

## Backend

* Python 3.11
* FastAPI

## AI

* Gemini 2.5 Flash

## Storage

* PostgreSQL

## Frontend

* Next.js
* Tailwind CSS

## Infrastructure

* Docker Compose

## Retrieval

* BM25

## Datasets

* UNESCO World Heritage Sites Dataset
* Scoring Criteria Dataset

---

# Dashboard

## Community Reporter View

Allows users to:

* Upload photos
* Enter description
* Submit candidate site

---

## Reviewer View

Displays:

* Submission photos
* Description
* Evidence summary
* Heritage score
* Confidence level
* Category breakdown

Actions:

* Approve
* Reject

---

## Admin Dashboard

Displays:

* Queue size
* Review status
* Duplicate detections
* Processing metrics

---

# Evaluation Plan

## Duplicate Detection

Validate that already-listed sites are correctly identified.

## Workflow Completion

Validate end-to-end processing.

## Deterministic Scoring

Confirm identical dossiers produce identical scores.

## Multilingual Intake

Validate correct dossier generation across languages.

## HITL Enforcement

Confirm workflow cannot advance without reviewer action.

---

# Success Criteria

The MVP is successful if it demonstrates:

* End-to-end workflow completion
* Explainable evidence extraction
* Deterministic scoring
* Human-in-the-loop approval
* Registry deduplication
* Reviewer-ready Confidence Cards

The system is a decision-support tool for heritage experts and does not autonomously designate heritage status.

Contributors: Sriya, Aishwarya, Ujjwal, Rujul, Sanjana