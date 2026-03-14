# Architecture Diagrams

This document captures the core execution paths of the repository so the notebooks, README, and interview walkthroughs all describe the same system.

## Workflow Flowchart

```mermaid
flowchart TD
    Q["User Query"] --> N["normalize_query"]
    N --> C["classify_query"]
    C --> P["make_plan"]
    P --> R["retrieve_docs"]
    R --> T["decide_tools"]
    T --> D{"requires_tools?"}
    D -- "Yes" --> U["run_tools"]
    D -- "No" --> S["synthesize_answer"]
    U --> S
    S --> V["verify_grounding"]
    V --> G{"grounded and coverage >= 0.65?"}
    G -- "Yes" --> F["fallback_or_finalize -> answered"]
    G -- "No" --> A["fallback_or_finalize -> abstained"]

    classDef io fill:#d9f7e8,stroke:#20744a,color:#143b25;
    classDef process fill:#dce9ff,stroke:#2457a6,color:#13315c;
    classDef verify fill:#fff1cc,stroke:#b87c00,color:#5a3b00;
    classDef fail fill:#ffd7d7,stroke:#a12727,color:#5c1111;

    class Q,F,A io;
    class N,C,P,R,T,U,S process;
    class V,G verify;
```

## Memory-Augmented Workflow

```mermaid
flowchart TD
    Q["User Query"] --> N["normalize_query"]
    N --> C["classify_query"]
    C --> P["make_plan"]
    P --> R["retrieve_docs"]
    R --> M["retrieve_memories"]
    M --> ST["ShortTermMemory"]
    M --> LT["LongTermMemory"]
    M --> VM["VectorMemory"]
    M --> D["decide_tools"]
    D --> U["run_tools"]
    U --> S["synthesize_answer"]
    S --> V["verify_grounding"]
    V --> F["fallback_or_finalize"]
    F --> UM["update_memory"]
    UM --> OUT["Answer or Abstain"]

    classDef io fill:#d9f7e8,stroke:#20744a,color:#143b25;
    classDef process fill:#dce9ff,stroke:#2457a6,color:#13315c;
    classDef memory fill:#efe1ff,stroke:#6d37b1,color:#38215a;
    classDef verify fill:#fff1cc,stroke:#b87c00,color:#5a3b00;

    class Q,OUT io;
    class N,C,P,R,M,D,U,S,UM process;
    class ST,LT,VM memory;
    class V,F verify;
```

## State Lifecycle

```mermaid
stateDiagram-v2
    [*] --> INIT
    INIT --> NORMALIZED: normalize_query
    NORMALIZED --> CLASSIFIED: classify_query
    CLASSIFIED --> PLANNED: make_plan
    PLANNED --> RETRIEVED: retrieve_docs
    RETRIEVED --> MEMORIES_RETRIEVED: retrieve_memories (memory workflow)
    RETRIEVED --> TOOLS_DECIDED: decide_tools
    MEMORIES_RETRIEVED --> TOOLS_DECIDED: decide_tools
    TOOLS_DECIDED --> TOOLS_EXECUTED: run_tools
    TOOLS_EXECUTED --> SYNTHESIZED: synthesize_answer
    SYNTHESIZED --> VERIFIED: verify_grounding
    VERIFIED --> FINALIZED: fallback_or_finalize(answered)
    VERIFIED --> ABSTAINED: fallback_or_finalize(abstained)
    FINALIZED --> MEMORY_UPDATED: update_memory (memory workflow)
    ABSTAINED --> MEMORY_UPDATED: update_memory (memory workflow)
    INIT --> FAILED: workflow_error
    NORMALIZED --> FAILED: workflow_error
    CLASSIFIED --> FAILED: workflow_error
    PLANNED --> FAILED: workflow_error
    RETRIEVED --> FAILED: workflow_error
    TOOLS_DECIDED --> FAILED: workflow_error
    TOOLS_EXECUTED --> FAILED: workflow_error
    SYNTHESIZED --> FAILED: workflow_error
    VERIFIED --> FAILED: workflow_error
```
