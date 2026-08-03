# Part 6A.1 Import Inventory

| Importing file | Line | Current statement | Imported sibling | Current style | Package-safe? |
|---|---:|---|---|---|---|
| client.py | 54 | `from discovery import (discover_capabilities,)` | discovery.py | Bare sibling | No |
| client.py | 58 | `from connection import MCPConnection` | connection.py | Bare sibling | No |
| formatters.py | 5 | `from validation import (get_prompt_arguments, ...)` | validation.py | Bare sibling | No |
| client.py | 60 | `from formatters import (...)` | formatters.py | Bare sibling | No |
| discovery.py | 1 | `from formatters import (...)` | formatters.py | Bare sibling | No |
| prompt_workflow.py | 32 | `from formatters import (...)` | formatters.py | Bare sibling | No |
| resource_template_workflow.py | 32 | `from formatters import (...)` | formatters.py | Bare sibling | No |
| static_resource_workflow.py | 29 | `from formatters import (...)` | formatters.py | Bare sibling | No |
| tool_workflow.py | 28 | `from formatters import (...)` | formatters.py | Bare sibling | No |





----                                                                                    ---------- ----

C:\AI_Projects\mcp_client_learning_project\src\mcp_client\discovery.py                           1 from formatters import format_json
C:\AI_Projects\mcp_client_learning_project\src\mcp_client\prompt_workflow.py                    32 from formatters import (
C:\AI_Projects\mcp_client_learning_project\src\mcp_client\resource_template_workflow.py         32 from formatters import (
C:\AI_Projects\mcp_client_learning_project\src\mcp_client\static_resource_workflow.py           29 from formatters import (
C:\AI_Projects\mcp_client_learning_project\src\mcp_client\tool_workflow.py                      28 from formatters import (
C:\AI_Projects\mcp_client_learning_project\src\mcp_client\client.py                             82 from validation import (
C:\AI_Projects\mcp_client_learning_project\src\mcp_client\prompt_workflow.py                    40 from validation import (
C:\AI_Projects\mcp_client_learning_project\src\mcp_client\resource_template_workflow.py         40 from validation import (
C:\AI_Projects\mcp_client_learning_project\src\mcp_client\static_resource_workflow.py           35 from validation import (



C:\AI_Projects\mcp_client_learning_project\src\mcp_client\client.py                             58 from connection import MCPConnection
C:\AI_Projects\mcp_client_learning_project\src\mcp_client\client.py                             54 from discovery import (
C:\AI_Projects\mcp_client_learning_project\src\mcp_client\formatters.py                          5 from validation import (
C:\AI_Projects\mcp_client_learning_project\src\mcp_client\client.py                             60 from formatters import (
