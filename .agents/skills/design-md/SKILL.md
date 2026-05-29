---
name: design-md
description: "특정 브랜드/제품의 디자인 시스템을 참고하여 UI를 생성할 때 반드시 사용. 사용자가 'Codex 스타일로', 'Apple 느낌으로', 'Figma처럼', 'Stripe 디자인 참고해서', 'Linear 스타일 UI' 같이 특정 브랜드의 디자인 언어를 요청하거나, '이 DESIGN.md 참고해서', '디자인 시스템 적용해서' 같이 명시할 때 트리거. 사용 가능한 브랜드: airbnb, airtable, apple, bmw, cal, Codex, clay, clickhouse, cohere, coinbase, composio, cursor, elevenlabs, expo, ferrari, figma, framer, hashicorp, ibm, intercom, kraken, lamborghini, linear.app, lovable, minimax, mintlify, miro, mistral.ai, mongodb, notion, nvidia, ollama, opencode.ai, pinterest, posthog, raycast, renault, replicate, resend, revolut, runwayml, sanity, sentry, spacex, spotify, stripe, supabase, superhuman, tesla, together.ai, uber, vercel, voltagent, warp, webflow, wise, x.ai, zapier"
---

# Design-MD Skill

특정 브랜드의 DESIGN.md를 로드하여 해당 디자인 시스템에 맞는 UI를 생성하는 스킬.

## 사용 가능한 브랜드

총 58개. 전체 목록과 각 브랜드 특성 요약은 `references/catalog.md` 참조.

**빠른 참조:**
- AI/LLM: Codex, cohere, elevenlabs, minimax, mistral.ai, ollama, opencode.ai, replicate, runwayml, together.ai, voltagent, x.ai
- 개발 툴: cursor, expo, linear.app, lovable, mintlify, posthog, raycast, resend, sentry, supabase, superhuman, vercel, warp, zapier
- 인프라/클라우드: clickhouse, composio, hashicorp, mongodb, sanity, stripe
- 디자인/협업: airtable, cal, clay, figma, framer, intercom, miro, notion, pinterest, webflow
- 핀테크/크립토: coinbase, kraken, revolut, wise
- 엔터프라이즈/소비재: airbnb, apple, ibm, nvidia, spacex, spotify, uber
- 자동차: bmw, ferrari, lamborghini, renault, tesla

## 워크플로우

### 1. 브랜드 식별

사용자 요청에서 브랜드명을 파악한다. 명시되지 않은 경우 `references/catalog.md`를 읽고 요청 맥락(분위기, 색상, 사용 목적)에 가장 잘 맞는 브랜드를 추천한 뒤 확인받는다.

### 2. DESIGN.md 로드

해당 브랜드의 DESIGN.md를 읽는다:

```
E:/script/pythonWorkSpace/main/utils/awesome-design-md-main/awesome-design-md-main/design-md/{brand}/DESIGN.md
```

예시:
- `Codex` → `design-md/Codex/DESIGN.md`
- `linear.app` → `design-md/linear.app/DESIGN.md`
- `mistral.ai` → `design-md/mistral.ai/DESIGN.md`

### 3. 디자인 시스템 적용

DESIGN.md의 9개 섹션을 모두 숙지하고 UI를 생성한다:

| 섹션 | 활용 포인트 |
|------|-----------|
| Visual Theme | 전체 분위기와 철학 설정 |
| Color Palette | hex 값 그대로 사용, 임의 색상 금지 |
| Typography | font-family, size, weight, line-height 명세 준수 |
| Component Styling | 버튼/카드/인풋/네비 스타일 직접 적용 |
| Layout Principles | spacing scale, grid, whitespace 철학 따름 |
| Depth & Elevation | shadow 시스템 준수 |
| Do's and Don'ts | 금지 패턴 반드시 회피 |
| Responsive | breakpoint와 collapsing 전략 적용 |
| Agent Prompt Guide | DESIGN.md의 Example Prompt를 구현 레퍼런스로 활용 |

## 핵심 원칙

- **색상은 반드시 DESIGN.md의 hex 값 사용** — 임의로 "비슷한 색" 사용 금지
- **Do's and Don'ts 섹션 필수 확인** — 해당 브랜드가 절대 하지 않는 것들이 정의되어 있음
- **폰트가 커스텀 패밀리인 경우** DESIGN.md에 명시된 폴백 폰트를 사용
- **DESIGN.md에 없는 요소** (브랜드가 정의하지 않은 컴포넌트)는 해당 브랜드의 Visual Theme와 Color Palette 철학에서 유추하여 일관성 유지
