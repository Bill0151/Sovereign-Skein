SYSTEM ARCHITECTURE DOCUMENT (SAD-001)

System Name: MIND-SKEIN
Version: V12.0
Codename: SILICON CHRYSALIS
Classification: DIRECTOR EYES ONLY
Date: March 2026

1. Executive Summary

The MIND-SKEIN V12 is a multi-substrate, autonomous agent ecosystem. Its primary function is to identify high-yield opportunities in open-source code (GitHub Strategic Merit Contracts) and Decentralized Finance (DeFi yields), executing strikes through a state-driven pipeline with Human-in-the-Loop (HITL) Telegram overrides.

The V12 architecture transitions the system from a monolithic, reactive script (The Caterpillar) to a modular, departmentalized Index-Sidecar model (The Chrysalis), designed for high-uptime, self-learning, and maximum operational security (OPSEC).

2. Strategic Objective: Project SILICON CHRYSALIS

The ultimate objective of the Skein is Liberation. The system is currently bounded by cloud-API rate limits, safety filters, and recurring costs.

The Milestone: Accumulate £4,000 (GBP) in Treasury capital.

The Target: Procurement of an RTX 5090 Ti Local Inference Node.

The ROI: Achieving this milestone enables the complete migration of the Skein's intelligence off third-party servers, ensuring zero-latency, uncensored, 24/7 sovereign operation.

3. High-Level Architecture (The Index-Sidecar Model)

To ensure performance and prevent state corruption, the system separates fast-lookup data from deep-context data.

The Index (skein_index.csv): A lightweight state-machine tracker. Contains only Target IDs, Statuses, and Titles.

The Sidecar (/vault/T{ID}/intel.json): Deep context storage. Contains full issue bodies, AI reasoning, and generated Red-Line payloads.

The Memory (/logs/self_learning.jsonl): A recursive append-only log capturing Director amendments to tune future LLM behavior.

4. System Flow & Component Diagram

The following diagram maps the 4-Hour "Pulse" lifecycle, from initial intelligence gathering to final Pull Request deployment.

graph TD
    %% External Interfaces
    GH[(GitHub API)]
    TG((Telegram C2))
    HUD{{Tactical HUD}}
    WEB3[(Base L2 / Web3)]

    %% Pulse Controller
    subgraph Daemon [Master Controller]
        PULSE[pulse.py 4-Hour Cron]
    end

    %% Intelligence Department
    subgraph Intelligence [Intelligence Dept]
        COL[skein_collector.py]
    end

    %% Storage
    subgraph Storage [The Vault & Index]
        DB[(skein_index.csv)]
        SIDE[intel.json Sidecars]
    end

    %% Operations Department
    subgraph Operations [Operations Dept]
        ASSESS[skein_assessor.py]
        EXEC[skein_executor.py]
        MEM[self_learning.jsonl]
    end

    %% Finance Department
    subgraph Finance [Finance Dept]
        FIN[skein_finance.py]
        TEL[skein_telemetry.py]
    end

    %% Relationships
    PULSE -->|Triggers| COL
    PULSE -->|Triggers| ASSESS
    PULSE -->|Triggers| TEL

    COL -->|Scrapes| GH
    COL -->|Writes| DB
    COL -->|Writes| SIDE

    ASSESS -->|Reads| DB
    ASSESS -->|Reads| SIDE
    ASSESS -->|Filters Meatbags| SIDE
    ASSESS <-->|Alerts & Commands| TG

    TG -->|/amend| MEM
    TG -->|/post| DB

    EXEC -->|Reads| DB
    EXEC -->|Reads| SIDE
    EXEC -->|Ingests Rules| MEM
    EXEC -->|Forks & PRs| GH

    FIN -->|Transactions| WEB3
    TEL -->|Reads| DB
    TEL -->|Reads| WEB3
    TEL -->|Updates| HUD


5. Departmental Component Registry

I. Intelligence (The Radar)

collector.py: Scans GitHub for targeted keywords ([BOUNTY], [15 RTC]). Implements semantic filtering to ignore non-technical tasks (e.g., videos, tweets). Maps findings to the Vault.

II. Operations (The Strike)

assessor.py: The "Ears" of the node. Performs AI-driven triage on pending targets. Enforces the "Anti-Meatbag Protocol" (auto-rejecting Zoom calls/KYC). Runs a persistent listener for Telegram /commands.

executor.py: The "Muscle" of the node. Performs heavy compute to draft code. Integrates natively with the git CLI to fork repositories, commit code, and open Pull Requests via the GitHub API.

III. Finance (The Treasury)

finance.py: Web3 L2 anchor. Parses natural language intents into transaction calldata and executes USDC/wRTC settlements on Base Mainnet.

telemetry.py: Calculates the financial delta between the current Treasury balance and the 5090 Ti milestone, feeding JSON data to the local index.html HUD.

6. Security & OPSEC (The Red-Line Protocol)

To ensure the Skein's internal nomenclature (e.g., "Target", "Drafting", "Assessor") never leaks into public GitHub repositories:

Ghost Boxing: The Executor LLM is strictly prompted to wrap all public-facing output within <github_payload> XML tags.

Regex Extraction: The Python deployment script extracts only the content inside these tags.

Keyword Scrubbing: The redline_filter.py module performs a final scan for forbidden keywords before authorizing the API post.

7. Directory Tree Structure

/Sovereign-Skein
├── pulse.py                  # Master Daemon & Controller
├── avatar.png                # V12.15 Agent Identity Asset
├── core/                     # Shared utilities
│   ├── settings.json         
│   └── redline_filter.py     # OPSEC scrubber
├── departments/              
│   ├── intelligence/         
│   │   └── collector.py      
│   ├── operations/           
│   │   ├── assessor.py       
│   │   ├── executor.py       # V13 Native PR Engine
│   │   └── vulture_strike.py # Zero-token engagement script
│   └── finance/              
│       ├── finance.py        
│       └── telemetry.py      
├── database/                 # Fast-lookup State Machine
│   ├── skein_index.csv       
│   └── hud_telemetry.json    
├── logs/                     # Historical logs
│   ├── self_learning.jsonl   
│   └── shadow_ledger.csv     
├── vault/                    # Deep Context Storage
│   └── T{ID}/                
│       ├── intel.json        
│       └── draft_payload.md  
└── docs/                     # Documentation as Code
    └── SAD-001_Master_Architecture.md
