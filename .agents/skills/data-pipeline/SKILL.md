---
name: data-pipeline
description: "Design a complete data pipeline architecture. A hierarchical 5-agent team covers schema design, ETL logic, validation rules, and monitoring setup — all coordinated by a top-level architect who produces a unified, implementable pipeline design. USE THIS SKILL when the user wants to design a data pipeline, plan ETL architecture, build a data ingestion system, or create a data engineering plan. Trigger phrases: 'design a data pipeline', 'plan ETL architecture', 'build a data ingestion system', 'design the data flow', 'create a pipeline for X data'. Do NOT trigger for: implementing existing pipeline code, debugging pipeline failures (those are code/ops tasks)."
---

# Data Pipeline Design Orchestrator

## Execution Mode
**Agent Team** — Hierarchical delegation pattern.
- `pipeline-architect` is the lead; all other agents receive scoped tasks from the architect
- Specialist agents work in parallel once the architect's topology is ready
- Architect reconciles and publishes the unified design

## Team Composition
| Agent | Role | Type |
|-------|------|------|
| `pipeline-architect` | Topology design + coordination + final synthesis | general-purpose |
| `schema-designer` | Source/intermediate/sink data models | general-purpose |
| `etl-engineer` | Extraction, transformation, loading logic | general-purpose |
| `validation-engineer` | Data quality rules and failure handling | general-purpose |
| `monitoring-engineer` | Metrics, alerts, dashboards, runbooks | general-purpose |

## Workspace
- `_workspace/00_pipeline_topology.md` — architect's topology decisions (input to all specialists)
- `_workspace/schema_design.md`
- `_workspace/etl_design.md`
- `_workspace/validation_rules.md`
- `_workspace/monitoring_design.md`

Final output: `pipeline_design.md`

## Workflow

### Phase 1 — Topology Design (Sequential)
The architect designs the top-level flow before specialists start. Specialists depend on these decisions.

```
TeamCreate: data-pipeline-team
Members: pipeline-architect, schema-designer, etl-engineer, validation-engineer, monitoring-engineer

TaskCreate (pipeline-architect): "The user needs a data pipeline for: {PROBLEM_DESCRIPTION}.
  Design the high-level topology (batch vs. streaming, stages, sources, sinks, SLAs).
  Write your topology decisions and constraints to _workspace/00_pipeline_topology.md.
  Then assign scoped tasks to each specialist via SendMessage."
```

### Phase 2 — Specialist Design (Parallel, Architect-Coordinated)
The architect uses SendMessage to dispatch to specialists once topology is written:

```
[architect → schema-designer]: "Design schemas based on _workspace/00_pipeline_topology.md.
  Write to _workspace/schema_design.md."

[architect → etl-engineer]: "Design ETL logic based on topology + schema (coordinate with 
  schema-designer). Write to _workspace/etl_design.md."

[architect → validation-engineer]: "Design validation rules based on schema + ETL stages.
  Write to _workspace/validation_rules.md."

[architect → monitoring-engineer]: "Design monitoring based on topology + validation events.
  Write to _workspace/monitoring_design.md."
```

Dependency order within specialists:
- schema-designer can start immediately
- etl-engineer should wait for schema-designer's key decisions (coordinate via SendMessage)
- validation-engineer reads schema + ETL
- monitoring-engineer reads topology + validation rules

### Phase 3 — Reconciliation & Final Design (Sequential)
After all specialists complete:

```
TaskCreate (pipeline-architect): "All specialist designs are complete in _workspace/.
  Read all four, identify conflicts (e.g., schema change that breaks ETL), resolve them,
  and produce the final unified pipeline design to pipeline_design.md."
```

## Data Flow
```
[User: domain, sources, sinks, SLAs]
                ↓
        [pipeline-architect]  ← Phase 1: topology
                ↓
   00_pipeline_topology.md
                ↓
[schema-designer] → [etl-engineer] → [validation-engineer]
                                          ↓
                                  [monitoring-engineer]
                ↓
     All _workspace/ design files
                ↓
        [pipeline-architect]  ← Phase 3: reconcile
                ↓
         pipeline_design.md
```

## Error Handling
- **Underspecified requirements:** Architect documents explicit assumptions, proceeds with common-case defaults, flags for user review
- **Specialist designs conflict** (e.g., ETL assumes schema that changed): Architect arbitrates — if tradeoff is significant, surfaces to user rather than guessing
- **Streaming topology needed but unclear SLA:** Architect asks user before proceeding — this decision shapes everything else
- **One specialist produces incomplete design:** Architect notes the gap in the final document rather than silently omitting it

## Agent Tool Call Pattern
```python
# Phase 1 — architect, foreground
Agent(
  subagent_type="general-purpose",
  model="opus",
  description="Pipeline architect: topology design",
  prompt="[Full task per pipeline-architect.md, including SendMessage instructions]"
)

# Phase 2 — specialists, launched by architect via SendMessage
# Architect dispatches via team task system, not direct Agent() calls from orchestrator

# Phase 3 — architect returns to reconcile
# Re-task architect with reconciliation prompt after specialists complete
```

## Test Scenarios

### Normal Flow
**Input:** "Design a pipeline that ingests click events from a web app (1M events/day) into a data warehouse for daily reporting"  
**Expected:**
- Architect chooses batch pipeline (daily volume, reporting SLA)
- Schema includes event_id, user_id, timestamp, event_type, properties
- ETL: daily batch extraction, deduplication, aggregation transforms
- Validation: null checks on required fields, volume anomaly detection
- Monitoring: daily job success/failure alert, row count dashboard, SLA breach notification
- Final doc is implementable without the workspace files

### Error Flow
**Input:** Requirements specify both real-time dashboards AND a batch warehouse  
**Expected:**
- Architect identifies the dual-path topology (streaming for dashboards, batch for warehouse)
- Flags the increased complexity and cost to user
- ETL engineer designs both paths
- Validation and monitoring cover both

## Trigger Examples
- "Design a pipeline for ingesting IoT sensor data"
- "Plan an ETL architecture for syncing our Postgres to BigQuery"
- "I need a data pipeline design for our analytics platform"
- "How should we design the data flow for this reporting system?"
- "Build a pipeline design for processing user events"
