---
name: code-review
description: "Comprehensive parallel code review across 4 specialist dimensions: architecture, security vulnerabilities, performance bottlenecks, and code style/maintainability. All specialists run simultaneously, then a merger agent deduplicates and produces a single prioritized report. USE THIS SKILL when the user asks to review code, audit a codebase, check for bugs or vulnerabilities, or wants a code quality assessment. Trigger phrases: 'review this code', 'audit the codebase', 'check for security issues', 'performance review', 'code quality check', 'pre-merge review'. Do NOT trigger for: running tests, debugging a specific bug, explaining code."
---

# Code Review Orchestrator

## Execution Mode
**Agent Team** — Fan-out/Fan-in pattern. Four specialist reviewers run in parallel, then a merger produces the unified report.

## Team Composition
| Agent | Speciality | Type |
|-------|-----------|------|
| `review-architect` | Structure, coupling, design patterns | general-purpose |
| `review-security` | Vulnerabilities, OWASP, secrets | general-purpose |
| `review-performance` | Bottlenecks, complexity, scalability | general-purpose |
| `review-style` | Readability, naming, consistency, tests | general-purpose |
| `review-merger` | Aggregation, deduplication, final report | general-purpose |

## Workspace
Intermediate files: `_workspace/{arch,security,performance,style}_findings.md`  
Final output: `code_review_report.md`

## Workflow

### Phase 1 — Parallel Review
All four reviewers launch simultaneously. Each reads the target files independently.

```
TeamCreate: code-review-team
Members: review-architect, review-security, review-performance, review-style, review-merger

TaskCreate (review-architect): "Review the code at {PATH}. Write findings to 
  _workspace/arch_findings.md per your agent definition."

TaskCreate (review-security): "Review the code at {PATH}. Write findings to 
  _workspace/security_findings.md per your agent definition."

TaskCreate (review-performance): "Review the code at {PATH}. Write findings to 
  _workspace/performance_findings.md per your agent definition."

TaskCreate (review-style): "Review the code at {PATH}. Write findings to 
  _workspace/style_findings.md per your agent definition."
```

Cross-communication encouraged: if a reviewer spots something in another reviewer's domain, they send a note rather than duplicating the finding.

### Phase 2 — Merge
After all four reviewers complete:

```
TaskCreate (review-merger): "All four findings files are ready in _workspace/.
  Read all four, deduplicate, prioritize by severity, and write the unified
  report to code_review_report.md per your agent definition."
```

### Phase 3 — Present
- Report location shown to user
- `_workspace/` preserved for per-dimension reference

## Data Flow
```
[User: path/files to review]
         ↓
[architect] [security] [performance] [style]   ← parallel, cross-notify
         ↓        ↓          ↓          ↓
     _workspace/ findings files
              ↓
          [merger]
              ↓
      code_review_report.md
```

## Error Handling
- **Reviewer cannot access file:** Notes the gap, reviews what's accessible
- **Findings conflict on severity:** Merger uses the higher severity, notes the disagreement
- **Finding appears in multiple reviewers:** Merger deduplicates with attribution from all reviewers (strengthens the finding)
- **Scope unclear (whole repo vs. changed files):** Ask user before starting — scoping errors waste all reviewers

## Agent Tool Call Pattern
```python
Agent(
  subagent_type="general-purpose",
  model="opus",
  description="Architecture review: {path}",
  prompt="[Full task per review-architect.md]",
  run_in_background=True
)
```
All four reviewers: `run_in_background=True`. Merger: foreground (wait for all four).

## Test Scenarios

### Normal Flow
**Input:** "Review the code in src/api/"  
**Expected:**
- Four `_workspace/` findings files created in parallel
- Merger produces `code_review_report.md` with severity tiers
- Cross-reviewer findings (e.g., security + architecture flagged same module) noted with dual attribution
- Executive summary enables fast triage

### Error Flow  
**Input:** Review scope includes generated/minified files  
**Expected:**
- Style and architecture reviewers skip or flag generated files explicitly
- Security reviewer still scans for secrets even in generated files
- Report notes which files were excluded and why

## Trigger Examples
- "Review the code in this PR"
- "Audit src/ for security vulnerabilities"  
- "Performance review of the database layer"
- "Check code quality before we merge this"
- "Review all changes in the last commit"
