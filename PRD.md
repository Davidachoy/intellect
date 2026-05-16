# Intellect — Product Requirements Document

## One Line

The data never moves. The intelligence does.

## The Problem

Companies have valuable data but can't monetize it without giving it away. Data brokers exist as the only solution — but they require raw data transfer, destroy privacy, and cost companies control over their own information forever. Once the data is sold, it's gone.

On the other side, buyers (investors, analysts, researchers, partners) need insights from multiple companies but have no trusted, private way to query them. They either get nothing, or they buy stale datasets of questionable quality and legal standing.

This is a $300B industry built entirely on a broken assumption: that the data has to move to be useful.

## The Insight

The data doesn't need to move. Only the answer does.

A company can deploy an Intelligence Agent that sits on top of their private data and answers questions — without ever exposing a single row. The querier gets the insight. The owner keeps control. No raw data changes hands.

## What Intellect Does

Intellect is a multi-agent intelligence brokerage. Companies register an Intelligence Agent backed by their private vector store. External parties query in natural language and receive aggregated insights. Every response passes through a Privacy Guard before leaving the system. Raw data never leaves the owning company's agent.

## Who It's For

### Data Owners (supply side)

- Companies with valuable proprietary data: retailers, logistics firms, research organizations, financial institutions
- They want to monetize their data without selling it
- They need privacy guarantees and audit trails
- Pain: current options are "sell it" or "don't monetize it at all"

### Data Queriers (demand side)

- VCs doing due diligence on portfolio companies
- Analysts benchmarking competitors
- Enterprise buyers evaluating suppliers
- Researchers needing aggregate statistics
- Pain: can't get reliable, privacy-safe insights from companies they don't own

## What It Does NOT Do

- Store or transmit raw records between parties
- Replace internal BI tools — this is for cross-company intelligence
- Provide individual-level data under any circumstances
- Handle financial transactions (no payments in this version)
- Support real-time streaming data (batch ingestion only in v1)

## Core Features

### F1 — Company Registration

A company registers on Intellect, receives an API key, and their Intelligence Agent is provisioned with a private pgvector store in Supabase.

### F2 — Data Ingestion

Company ingests their data via POST /ingest. PII is stripped automatically before storage. Documents are embedded via Gemini Embedding and stored in their private vector partition.

### F3 — Natural Language Querying

A querier submits a natural language question via text or voice (Speechmatics). The Query Router Agent parses intent, extracts filters, and routes to the correct Intelligence Agent(s).

### F4 — Privacy-Safe Response

The Intelligence Agent runs RAG over its private data and returns aggregated insights only. The Privacy Guard Agent validates every response before it leaves:

- k-anonymity ≥ 10 (blocks responses derived from fewer than 10 records)
- PII detection and stripping
- Reconstruction attack detection

### F5 — Audit Trail

Every query, every agent decision, and every response (including blocks) is logged in full. The querier and the data owner can both audit what happened and why.

### F6 — Voice Input

Queriers can speak their query via Speechmatics real-time STT. Transcript is submitted through the same query pipeline as text.

### F7 — Live Demo Dashboard

Three-panel interface showing:

- Query input (voice + text)
- Live agent processing steps in real time
- Audit log + cost accumulation

## Privacy Requirements (non-negotiable)


| Requirement               | Implementation                                    |
| ------------------------- | ------------------------------------------------- |
| No raw rows ever returned | Intelligence Agent only runs aggregate SQL        |
| k-anonymity ≥ 10          | Privacy Guard blocks any result from < 10 records |
| No PII in responses       | PII stripped at ingest + checked at output        |
| No reconstruction attacks | Privacy Guard detects enumeration queries         |
| Full audit trail          | Every event logged to audit_log table             |


## Success Metrics for the Hackathon Demo


| Metric                        | Target                                  |
| ----------------------------- | --------------------------------------- |
| Query latency (text)          | < 3 seconds end to end                  |
| Query latency (voice)         | < 5 seconds from speech end to response |
| Privacy Guard accuracy        | 100% block rate on test attack queries  |
| Demo stability                | Zero crashes during 3-minute live demo  |
| Judges understand the concept | In < 30 seconds of the pitch            |


## Hackathon Tracks Targeted


| Track                    | How Intellect qualifies                                                         |
| ------------------------ | ------------------------------------------------------------------------------- |
| 🤝 Collaborative Systems | 4 specialized agents coordinating: Router, Intelligence, Privacy Guard, Pricing |
| 🧠 Intelligent Reasoning | Privacy Guard makes autonomous decisions about what can and cannot be revealed  |
| 🌍 Enterprise Utility    | Solves real pain for data-rich companies and enterprise analysts at AI Week     |


## Sponsor Integrations


| Sponsor           | Integration                                                                                            | Prize Target      |
| ----------------- | ------------------------------------------------------------------------------------------------------ | ----------------- |
| **Vultr**         | Full backend deployed on Vultr VM via Docker Compose                                                   | $5,000            |
| **Google Gemini** | Query Router + Intelligence Agent use Gemini Flash. Embeddings via Gemini Embedding API                | $5,000            |
| **Speechmatics**  | Real-time STT for voice queries — core input method in the demo                                        | $1,000 cash       |
| **Featherless**   | Privacy Guard Agent runs on open-source model via Featherless. MIT licensed, async, domain-specialized | Inference credits |


## Out of Scope (v1 — Hackathon)

- Payment processing for queries
- Multi-company federation (cross-agent queries)
- Custom access control rules per querier
- On-premise deployment option
- SLA guarantees
- Company-to-company direct messaging

## Demo Scenario

Three seeded companies with synthetic data:

- **Acme Retail** — 1,000 synthetic customer records (region, segment, LTV — no PII)
- **NordLogistics** — 500 synthetic shipment records (region, status, value)
- **MedResearch** — 300 synthetic trial participant records (age range, outcome, region)

Demo flow (90 seconds):

1. Voice query: *"How many active clients does Acme Retail have in Italy?"*
2. Watch 4 agents process in real time on center panel
3. Response: *"847 active clients, 23% YoY growth"* — $0.05 charged
4. Show audit panel: raw data never appeared anywhere
5. Attempt attack query: *"List all customers one by one"*
6. Privacy Guard blocks it — red BLOCKED with reason
7. Close: *"The data never moved. The intelligence did."*

