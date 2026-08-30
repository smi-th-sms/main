---
name: api-docs
description: "Generate complete API documentation from a codebase. A 4-agent pipeline scans endpoints, writes descriptions and parameter docs, generates usage examples, and validates completeness — producing a ready-to-publish API reference. USE THIS SKILL when the user wants to document API endpoints, generate an API reference, create developer docs from code, or produce OpenAPI-style documentation. Trigger phrases: 'document the API', 'generate API docs', 'write endpoint documentation', 'create API reference', 'document these routes'. Do NOT trigger for: explaining how to USE an API (that's general assistance), writing code that calls an API."
---

# API Documentation Orchestrator

## Execution Mode
**Agent Team** — Pipeline pattern with a parallel middle phase.
```
Phase 1: api-analyzer (scan, sequential)
Phase 2: api-writer + api-examples (parallel, both read analyzer output)
Phase 3: api-reviewer (validate + publish, sequential)
```

## Team Composition
| Agent | Role | Type |
|-------|------|------|
| `api-analyzer` | Scan codebase, extract endpoint inventory | Explore |
| `api-writer` | Write descriptions, params, responses | general-purpose |
| `api-examples` | Generate usage examples and code snippets | general-purpose |
| `api-reviewer` | Validate completeness/accuracy, produce final | general-purpose |

## Workspace
- `_workspace/api_inventory.json` — structured endpoint data
- `_workspace/api_inventory_summary.md` — human-readable inventory  
- `_workspace/api_docs_draft.md` — written documentation (from api-writer)
- `_workspace/api_examples.md` — usage examples (from api-examples)
- `_workspace/review_feedback.md` — reviewer notes

Final output: `api_documentation.md`

## Workflow

### Phase 1 — Analysis (Sequential)
```
TeamCreate: api-docs-team
Members: api-analyzer, api-writer, api-examples, api-reviewer

TaskCreate (api-analyzer): "Scan the codebase at {ROOT_PATH} and extract all API
  endpoints. Write structured inventory to _workspace/api_inventory.json and
  _workspace/api_inventory_summary.md per your agent definition."
```
Wait for api-analyzer to complete before starting Phase 2. The inventory is the foundation.

### Phase 2 — Writing + Examples (Parallel)
Once inventory is ready:
```
TaskCreate (api-writer): "Read _workspace/api_inventory.json and write full
  endpoint documentation to _workspace/api_docs_draft.md per your agent definition."

TaskCreate (api-examples): "Read _workspace/api_inventory.json and 
  _workspace/api_docs_draft.md (when available) and write usage examples to 
  _workspace/api_examples.md per your agent definition."
```
Both run with `run_in_background=True`. api-examples can start from inventory even before writer finishes.

### Phase 3 — Review + Publish (Sequential)
After writer and examples both complete:
```
TaskCreate (api-reviewer): "Read _workspace/api_docs_draft.md, _workspace/api_examples.md,
  and _workspace/api_inventory.json. Validate completeness and accuracy against the
  codebase. Write review notes to _workspace/review_feedback.md and produce the final
  merged documentation to api_documentation.md per your agent definition."
```

## Data Flow
```
[User: repo path]
       ↓
  [api-analyzer]  ← sequential
       ↓
  api_inventory.json
       ↓
[api-writer]  [api-examples]  ← parallel
       ↓             ↓
  api_docs_draft.md  api_examples.md
              ↓
        [api-reviewer]
              ↓
      api_documentation.md
```

## Error Handling
- **Framework not recognized:** api-analyzer notes it and searches broadly (route patterns, decorator names); flags uncertainty in inventory
- **Analyzer finds no endpoints:** Stop and report to user — wrong directory or unsupported framework
- **Writer and examples disagree on parameter type:** Reviewer resolves by checking source code; notes the conflict
- **Undocumented internal endpoints:** Include with a note "internal — not for public API consumers" unless user specifies to exclude

## Agent Tool Call Pattern
```python
# Phase 1 — foreground (must complete before Phase 2)
Agent(
  subagent_type="Explore",
  model="opus",
  description="API endpoint analysis",
  prompt="[Full task per api-analyzer.md]"
)

# Phase 2 — parallel background
Agent(subagent_type="general-purpose", model="opus", run_in_background=True, ...)
Agent(subagent_type="general-purpose", model="opus", run_in_background=True, ...)

# Phase 3 — foreground
Agent(subagent_type="general-purpose", model="opus", ...)
```

## Test Scenarios

### Normal Flow
**Input:** "Document the API in src/routes/"  
**Expected:**
- Inventory covers all route files found
- Every endpoint has: description, all parameters with types, request/response examples
- Examples are syntactically correct and use realistic values
- Final doc is self-contained — no reference to internal code needed

### Error Flow
**Input:** Mixed REST + GraphQL codebase  
**Expected:**
- api-analyzer detects both and flags the mixed architecture
- Documents each with appropriate format (REST vs. GraphQL conventions)
- Reviewer notes any coverage gaps between the two API styles

## Trigger Examples
- "Generate API documentation for this project"
- "Document all the endpoints in the routes/ folder"
- "Create an API reference from the codebase"
- "Write developer docs for our REST API"
- "I need OpenAPI-style docs for these handlers"
