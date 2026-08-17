# PART11_CONTEXT_20260812.md

**Project:** MCP Client Learning Project  
**Next Phase:** Part 11 — External Dependency and MCP SDK Boundary Review  
**Date:** 2026-08-12  
**Starting Regression Baseline:** 71 passing tests

---

## 1. Project Status

Parts 1 through 10C have established and reviewed the major architecture
of the reusable MCP client.

The following architectural areas are considered closed:

- Package Architecture
- Package Execution Interfaces
- Connection Architecture
- Discovery Architecture
- Application Composition
- Workflow Architecture
- Post-Workflow Architectural Review

The complete regression baseline is:

```text
71 passed
```

Do not reopen closed architectural areas without a genuine new
architectural requirement.

---

## 2. Current High-Level Architecture

```text
                         client.py
                            │
                     composition
                            │
          ┌─────────────────┼─────────────────┐
          ▼                 ▼                 ▼
     connection.py      discovery.py      workflows
          │                 │                 │
          │                 │         ┌───────┼─────────┐
          │                 │         │       │         │
          │                 │       tool   resource   prompt
          │                 │
          └─────────────────┴─────────────────┘
                            │
                            ▼
                       MCP Python SDK
                            │
                            ▼
                         MCP Server
```

Major ownership boundaries are intentionally separated.

---

## 3. Connection Architecture

`connection.py` owns the MCP connection lifecycle.

The established conceptual lifecycle is:

```text
Enter MCPConnection
        │
        ▼
open configured STDIO transport
        │
        ▼
create ClientSession
        │
        ▼
enter ClientSession context
        │
        ▼
initialize session
        │
        ▼
expose usable initialized connection
        │
        ▼
cleanly close lifecycle
```

The connection architecture was previously reviewed and protected.

Do not change it merely because a hypothetical future MCP API may differ.

---

## 4. Discovery Architecture

`discovery.py` owns application capability inventory discovery.

It discovers the server's available:

- tools
- static resources
- resource templates
- prompts

Conceptually:

```text
active ClientSession
        │
        ├── list_tools()
        ├── list_resources()
        ├── list_resource_templates()
        └── list_prompts()
```

This is distinct from protocol-level capability negotiation.

That distinction should remain explicit during Part 11.

---

## 5. Workflow Architecture

The Workflow Subsystem was formally closed in Part 10B.

It contains:

- `tool_workflow.py`
- `static_resource_workflow.py`
- `resource_template_workflow.py`
- `prompt_workflow.py`

Each workflow owns application-specific:

```text
select
   ↓
invoke
   ↓
validate
   ↓
present
```

behavior over an already-active MCP session.

Workflows do NOT own:

- connection lifecycle
- session initialization
- generic capability discovery
- generic MCP protocol implementation
- application composition
- server business logic

Do not reopen the Workflow Subsystem merely to add edge-case coverage or
create generic abstractions.

---

## 6. Part 10C Findings

Part 10C reviewed the remaining architectural territory after Workflow
Subsystem closure.

### formatters.py

Classified as presentation support.

It does not currently justify a major standalone subsystem.

### validation.py

Classified as shared correctness/validation support.

It is conceptually distinct from formatting but also does not currently
justify a major standalone subsystem.

Formatting and validation may be viewed as separate responsibilities
within a broad support layer.

Do not merge them merely for structural symmetry.

### Public API

The intentional reusable Python package API remains unresolved.

This is different from the already-protected application execution
interfaces.

Public API review remains important but has been deferred until the MCP
SDK dependency boundary is better understood.

---

## 7. MCP 2026 Compatibility Investigation

An MCP 2026 architecture-change bulletin raised a question about whether
the project's existing initialization architecture might eventually be
affected by a `server/discover` style capability-discovery mechanism.

The project deliberately did NOT modify production code in response.

Instead, the installed SDK was inspected.

---

## 8. Installed MCP SDK Baseline

The active project environment uses:

```text
mcp 1.28.0
```

`ClientSession` currently exposes methods including:

```text
initialize
get_server_capabilities
call_tool
complete
get_prompt
list_prompts
list_resource_templates
list_resources
list_tools
read_resource
send_request
...
```

The installed initialization signature is:

```python
ClientSession.initialize(self) -> mcp.types.InitializeResult
```

The implementation resides in:

```text
.venv\Lib\site-packages\mcp\client\session.py
```

Recursive searches of the installed MCP package produced no matches for:

```text
server/discover
discover_server
server_discover
DiscoverResult
```

Therefore the currently installed MCP SDK does not expose the
`server/discover` architecture under discussion.

---

## 9. MCP 2026 Decision

Do not implement speculative protocol migration.

For the current project:

```text
installed executable SDK contract
              >
hypothetical future SDK architecture
```

The current Connection Architecture remains valid against MCP SDK
1.28.0.

The MCP 2026 issue should remain a compatibility watch item.

If a future SDK upgrade changes the actual client API, that becomes a
new architectural requirement and may justify reopening the affected
boundary.

---

## 10. Why Part 11 Changed Direction

Before the MCP compatibility investigation, the likely next phase was a
Public API and Support-Layer review.

The investigation identified a more fundamental prerequisite:

```text
What does our package own?

          versus

What does the MCP SDK own?
```

A public reusable API should not be formalized until this external
dependency boundary is understood.

Therefore Part 11 is now:

# Part 11 — External Dependency and MCP SDK Boundary Review

Public API work remains important but is deferred until this review is
complete.

---

## 11. Central Part 11 Architectural Boundary

```text
                 MCP CLIENT PROJECT
                         │
                         │
          project-owned architecture
                         │
             ┌───────────┴───────────┐
             ▼                       ▼
        connection.py            discovery.py
             │                       │
             └──────────┬────────────┘
                        │
                        │ SDK API boundary
                        ▼
                 MCP Python SDK
                    version 1.28.0
                        │
                        ▼
               protocol implementation
```

Part 11 should determine which contracts on this boundary the project
actually depends upon.

---

## 12. Candidate Project-Owned Responsibilities

Current evidence suggests that the project owns responsibilities such as:

- application composition
- connection lifecycle orchestration
- workflow sequencing
- application-specific capability selection
- semantic validation
- presentation
- client-side application policy

These classifications must be reviewed rather than assumed.

---

## 13. Candidate MCP SDK-Owned Responsibilities

Current evidence suggests that the SDK owns responsibilities such as:

- `ClientSession`
- protocol message implementation
- `initialize()`
- initialization result structures
- server capability representation
- `list_tools()`
- `list_resources()`
- `list_resource_templates()`
- `list_prompts()`
- `call_tool()`
- `read_resource()`
- `get_prompt()`
- lower-level MCP protocol machinery

Part 11 must determine which of these SDK contracts are genuinely relied
upon by project architecture.

---

## 14. Dependency Declaration Observation

The project diagnostic identified:

```text
pyproject.toml
requirements.txt
```

The inspected `pyproject.toml` currently contains pytest configuration
but did not show project dependency metadata.

The project also did not reveal an obvious dedicated project lock file
during the diagnostic inventory.

Do NOT immediately introduce dependency pinning or packaging changes.

First inspect:

- `requirements.txt`
- how the environment was created
- whether MCP is currently constrained there
- what reproducibility guarantee the learning project actually needs

Dependency pinning should only be introduced if Part 11 determines that
it protects a genuine project contract.

---

## 15. Regression Philosophy

The current baseline is:

```text
71 passed
```

Continue the established regression philosophy:

```text
architecture-driven protection
             not
coverage-driven protection
```

Do not add tests for every MCP SDK method.

Only protect SDK-boundary behavior if the project genuinely depends upon
that behavior as an architectural contract.

A test that merely asserts a particular SDK implementation mechanism may
become brittle when the SDK evolves.

Part 11 should distinguish:

```text
project architectural contract
```

from:

```text
current SDK implementation mechanism
```

before changing tests.

---

## 16. Part 11 Proposed Structure

Tentative structure:

```text
Part 11
│
├── 11A — External Dependency Boundary Review
│
├── 11B — MCP SDK Contract Inventory
│
├── 11C — Dependency Version / Reproducibility Review
│
├── 11D — SDK Compatibility Protection Review
│
└── 11E — Part 11 Closure
```

This structure is provisional.

Architecture review may determine that some sections require no
implementation.

Do not assume that Part 11 must produce code changes.

---

## 17. Part 11A Objective

Begin with:

# Part 11A — External Dependency Boundary Review

The purpose is to establish:

```text
OUR APPLICATION OWNS
        │
        │ SDK boundary
        ▼
MCP SDK OWNS
```

Review actual code and dependency direction before proposing changes.

Questions should include:

1. Which modules directly depend on `mcp`?
2. Which MCP SDK types and methods cross project module boundaries?
3. Which SDK behaviors are hidden behind project abstractions?
4. Which SDK behaviors leak into application composition or workflows?
5. Does `MCPConnection` provide a useful abstraction boundary over the
   SDK?
6. Does `discovery.py` remain properly separated from protocol-level
   capability handling?
7. Are any project tests protecting SDK mechanisms rather than project
   contracts?
8. Does the dependency declaration adequately describe the environment
   the project requires?
9. Is any implementation change genuinely necessary?
10. What should remain deferred to the later Public API review?

---

## 18. Teaching / Implementation Contract

Continue using the established project method:

- architecture before implementation
- professor/software-architect style
- extremely small milestones
- preserve behavior exactly
- compile after every implementation change
- run the complete regression suite after every implementation milestone
- stop after every checkpoint
- distinguish architectural decisions from implementation
- do not refactor for symmetry
- do not add tests merely for coverage
- do not modify production code until the architectural reason is clear

---

## 19. Starting State for New Conversation

Part 10C is complete.

Regression baseline:

```text
71 passed
```

Installed MCP SDK:

```text
1.28.0
```

No `server/discover` implementation was found in the installed SDK.

No connection/discovery migration has been authorized.

Begin with:

# Part 11A — External Dependency Boundary Review

Do not begin implementation until the boundary review is complete.