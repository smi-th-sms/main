---
name: deep-research
description: "Deep multi-angle research on any topic. Deploys a 4-agent team (web scout, academic researcher, community sentiment analyst, synthesizer) to investigate from all angles, cross-validate findings, and produce a comprehensive report with confidence ratings. USE THIS SKILL whenever the user asks to research, investigate, analyze, or deep-dive a topic — especially when they want multiple perspectives, want to understand public opinion alongside official sources, or need a thorough written report. Trigger phrases: 'research X', 'investigate X', 'deep dive on X', 'what do people think about X', 'comprehensive overview of X'."
---

# Deep Research Orchestrator

## Execution Mode
**Agent Team** — Fan-out/Fan-in pattern. Three parallel researchers investigate simultaneously, then a synthesizer cross-validates and writes the final report.

## Team Composition
| Agent | Role | Type |
|-------|------|------|
| `research-web-scout` | Current web/news sources | general-purpose |
| `research-academic` | Academic/technical sources | general-purpose |
| `research-community` | Community sentiment & practitioner views | general-purpose |
| `research-synthesizer` | Cross-validation & final report | general-purpose |

## Workspace
All intermediate files go to `_workspace/` in the current directory:
- `_workspace/01_web_scout_findings.md`
- `_workspace/02_academic_findings.md`
- `_workspace/03_community_findings.md`

Final output: `deep_research_report_{topic_slug}.md`

## Workflow

### Phase 1 — Team Formation & Parallel Research
Spin up the three researchers as a team simultaneously. Each receives the same topic + any focus areas specified by the user.

```
TeamCreate: deep-research-team
Members: research-web-scout, research-academic, research-community, research-synthesizer

TaskCreate (research-web-scout): "Research topic: {TOPIC}. Focus: {FOCUS_AREAS}. 
  Write findings to _workspace/01_web_scout_findings.md per your agent definition."

TaskCreate (research-academic): "Research topic: {TOPIC}. Focus: {FOCUS_AREAS}.
  Write findings to _workspace/02_academic_findings.md per your agent definition."

TaskCreate (research-community): "Research topic: {TOPIC}. Focus: {FOCUS_AREAS}.
  Write findings to _workspace/03_community_findings.md per your agent definition."
```

All three run in parallel. Encourage cross-communication: when any researcher finds something surprising, they should SendMessage to teammates immediately.

### Phase 2 — Synthesis
Once all three researchers signal completion (via TaskUpdate or SendMessage):

```
TaskCreate (research-synthesizer): "All three findings files are ready in _workspace/.
  Read all three, cross-validate, resolve contradictions, and write the final report
  to deep_research_report_{topic_slug}.md per your agent definition."
```

### Phase 3 — Cleanup
After synthesizer completes:
- Preserve `_workspace/` files for audit trail
- Present final report location to user

## Data Flow
```
[User: topic + focus areas]
        ↓
[web-scout]  [academic]  [community]   ← parallel, cross-communicate
        ↓         ↓          ↓
  _workspace/ findings files
        ↓
[synthesizer]
        ↓
deep_research_report_{slug}.md
```

## Error Handling
- **One researcher fails or returns thin results:** Synthesizer proceeds with available findings; notes the gap in the report under "Coverage Limitations"
- **All web searches return irrelevant results:** Expand query formulations before giving up; if still thin, note the topic may be too niche or too new for current web coverage
- **Irreconcilable contradiction between sources:** Synthesizer surfaces both positions with attribution — do not silently resolve
- **Topic too broad:** Synthesizer notes this in the executive summary and recommends narrowing for a follow-up

## Agent Tool Call Pattern
```python
Agent(
  subagent_type="general-purpose",
  model="opus",
  description="Web Scout: research {topic}",
  prompt="[Full task with file paths and output structure per research-web-scout.md]",
  run_in_background=True
)
```
All three researchers launch with `run_in_background=True`. Synthesizer launches after all three complete (do NOT run in background).

## Test Scenarios

### Normal Flow
**Input:** "Research the current state of quantum computing for practical business applications"  
**Expected:**
- Three `_workspace/` files created within the research phase
- Synthesizer produces a report with: executive summary, cross-validated findings, contradictions section (e.g., hype vs. actual capability), community sentiment (practitioners vs. media)
- Confidence ratings on major claims
- Report is readable without reference to workspace files

### Error Flow
**Input:** "Research a very obscure niche topic with minimal online presence"  
**Expected:**
- Web scout and community researcher flag sparse results
- Academic researcher may find more
- Synthesizer notes coverage limitations prominently
- Report still produced — never silent failure

## Trigger Examples
- "Research the pros and cons of Rust for systems programming"
- "Deep dive on the current state of LLM fine-tuning"  
- "Investigate community sentiment around React Server Components"
- "Give me a comprehensive overview of CRISPR gene editing"
