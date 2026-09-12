# Vega Business Second Brain — Build Plan

## Product goal

Build an AI operating system for non-technical business owners. The owner communicates
with Vega, the Main Agent. Vega creates or reuses persistent specialist agents,
applies company policies, coordinates temporary executions, verifies outcomes, and
reports completion.

## Core rule

Agents persist. Tasks and executions are temporary.

Creating an agent means storing an approved configuration with a role, responsibilities,
tools, permissions, policies, preferences, memory, and lifecycle state. It never means
generating unrestricted executable code.

## Architecture

```text
Business Owner
  -> Main Agent
  -> Goal Planner
  -> Agent Registry
  -> Create or reuse approved specialists
  -> Policy and approval engine
  -> Execution engine
  -> External integrations
  -> Verification
  -> Persist state and audit events
  -> Main Agent response
```

## Platform records

- Company
- AgentDefinition
- AgentTemplate
- TaskExecution
- Capability and permission
- Business policy
- Event and trigger
- Approval request
- Verification result
- Agent memory
- Audit event

## Main Agent MVP

The first graph performs five steps:

1. Understand the owner's goal.
2. Select the smallest approved set of specialist roles.
3. Reuse matching agents or create persistent definitions.
4. Create a temporary task execution and apply approval rules.
5. Report the plan without claiming an external action occurred.

Approved initial roles:

- Meeting Agent
- Communication Agent
- Finance Collection Agent
- Sales Follow-up Agent
- Customer Support Agent
- Inventory Agent

## Safety model

- Specialists receive only template-approved tools.
- Allowed and forbidden tools cannot overlap.
- External communication and meeting creation require approval.
- Money transfer, refunds, invoice modification, contract signing, and unapproved
  purchasing remain forbidden.
- Deterministic code controls permissions and execution.
- The LLM may plan but cannot grant itself capabilities.
- Every external action must later produce a verification result.

## Persistence

- SQLite stores agent definitions, task executions, and audit events for the MVP.
- LangGraph checkpoints store temporary graph progress.
- Idle agents consume no model tokens.
- An event later loads the relevant persistent agent and starts a new execution.

## Model strategy

- Groq structured output plans the specialist roles.
- A deterministic planner supports tests and offline demos.
- Model IDs remain configurable through environment variables.
- No model receives unrestricted tool access.

## Delivery phases

### Phase 1 — Main Agent foundation

- Platform models
- Approved specialist templates
- Persistent registry
- Deterministic policy engine
- Main Agent LangGraph
- Offline planner and Groq planner
- Persistence and reuse tests

### Phase 2 — Approval and execution

- Approval interrupts (implemented)
- Tool adapter interface
- Idempotent execution records
- Verification results (implemented)
- Meeting and communication mock tools (implemented)
- Google Workspace OAuth and encrypted token storage (implemented)
- Real Calendar, Meet, and communication adapters

### Phase 3 — Proactive agents

- Event and trigger records
- Scheduler or webhook intake
- Finance overdue-invoice activation
- Retry and failure policies

### Phase 4 — Business owner interface

- One Main Agent conversation
- Agent activity overview
- Approval inbox
- Execution and audit timeline
- Business preferences

### Phase 5 — Real integrations

- Calendar and meeting provider
- Slack or email
- Finance data source
- OAuth connection management
- Integration-specific verification

## Demonstration

1. Owner requests a meeting and team notification.
2. Main Agent creates Meeting and Communication agents.
3. A second request reuses the same agents.
4. An overdue-invoice event creates or activates the Finance Collection Agent.
5. High-risk actions pause for approval.
6. The audit timeline distinguishes plans from completed external actions.

## Success criteria

- The owner uses only the Main Agent.
- Agent definitions survive application restarts.
- Repeated goals reuse existing agents.
- Unsupported specialist roles fail closed.
- Tasks never exceed stored permissions.
- Planned and completed actions are clearly distinguished.
- Tests prove persistence, reuse, and policy enforcement.
