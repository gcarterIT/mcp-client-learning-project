# Part 5D.1 Formatting Inventory

Analyzed file: `C:\AI_Projects\mcp_client_learning_project\src\mcp_client\client.py`

> Candidate classifications are heuristic recommendations. The final module-design decision should be reviewed manually.

## `display_tool_result`

### Defined in

- File: `C:\AI_Projects\mcp_client_learning_project\src\mcp_client\client.py`
- Lines: `162` through `237`

### Called from

- `invoke_add_numbers` at line `461` using `display_tool_result()`

### Dependencies

- `format_json`
- `get_structured_tool_content`
- `types.TextContent`

### Contains `print()`

- **Yes**
- Print call lines: `186`, `187`, `188`, `196`, `198`, `203`, `209`, `210`, `215`, `220`, `228`, `232`, `235`, `237`

### Candidate for `formatters.py`

- **Yes**
- Heuristic score: `6`
- Reason: Its name indicates a presentation responsibility. It writes human-readable terminal output.

### Additional review signals

- Returns meaningful value: `False`
- Contains `await`: `False`
- Contains raise/assert: `False`
- Performs MCP/session call: `False`
- Contains parsing logic: `False`
- Mutates or accumulates data: `False`

---

## `display_resource_metadata`

### Defined in

- File: `C:\AI_Projects\mcp_client_learning_project\src\mcp_client\client.py`
- Lines: `530` through `556`

### Called from

- `read_application_configuration` at line `1709` using `display_resource_metadata()`

### Dependencies

- No non-built-in dependencies detected.

### Contains `print()`

- **Yes**
- Print call lines: `544`, `545`, `546`, `548`, `553`

### Candidate for `formatters.py`

- **Yes**
- Heuristic score: `6`
- Reason: Its name indicates a presentation responsibility. It writes human-readable terminal output.

### Additional review signals

- Returns meaningful value: `False`
- Contains `await`: `False`
- Contains raise/assert: `False`
- Performs MCP/session call: `False`
- Contains parsing logic: `False`
- Mutates or accumulates data: `False`

---

## `display_resource_template_metadata`

### Defined in

- File: `C:\AI_Projects\mcp_client_learning_project\src\mcp_client\client.py`
- Lines: `744` through `778`

### Called from

- `test_product_resource_template` at line `1210` using `display_resource_template_metadata()`

### Dependencies

- `get_mime_type`
- `get_uri_template`

### Contains `print()`

- **Yes**
- Print call lines: `754`, `756`, `762`, `768`, `774`

### Candidate for `formatters.py`

- **Yes**
- Heuristic score: `6`
- Reason: Its name indicates a presentation responsibility. It writes human-readable terminal output.

### Additional review signals

- Returns meaningful value: `False`
- Contains `await`: `False`
- Contains raise/assert: `False`
- Performs MCP/session call: `False`
- Contains parsing logic: `False`
- Mutates or accumulates data: `False`

---

## `display_resource_read_result`

### Defined in

- File: `C:\AI_Projects\mcp_client_learning_project\src\mcp_client\client.py`
- Lines: `1469` through `1568`

### Called from

- `read_json_resource` at line `881` using `display_resource_read_result()`
- `read_application_configuration` at line `1727` using `display_resource_read_result()`

### Dependencies

- `format_json`
- `get_resource_blob`
- `get_resource_text`
- `parse_json_resource_text`

### Contains `print()`

- **Yes**
- Print call lines: `1497`, `1498`, `1499`, `1504`, `1507`, `1512`, `1513`, `1514`, `1516`, `1517`, `1521`, `1531`, `1532`, `1533`, `1540`, `1541`, `1548`, `1549`, `1557`, `1560`, `1566`

### Candidate for `formatters.py`

- **Mixed / manual review required**
- Heuristic score: `1`
- Reason: Its name indicates a presentation responsibility. It writes human-readable terminal output. It returns a meaningful value. It contains parsing logic. It accumulates or mutates data.

### Additional review signals

- Returns meaningful value: `True`
- Contains `await`: `False`
- Contains raise/assert: `False`
- Performs MCP/session call: `False`
- Contains parsing logic: `True`
- Mutates or accumulates data: `True`

---

## `display_prompt_metadata`

### Defined in

- File: `C:\AI_Projects\mcp_client_learning_project\src\mcp_client\client.py`
- Lines: `1893` through `1963`

### Called from

- `retrieve_and_verify_prompt` at line `2458` using `display_prompt_metadata()`

### Dependencies

- `get_prompt_arguments`
- `is_prompt_argument_required`

### Contains `print()`

- **Yes**
- Print call lines: `1919`, `1920`, `1924`, `1930`, `1933`, `1952`, `1955`, `1959`

### Candidate for `formatters.py`

- **Yes**
- Heuristic score: `6`
- Reason: Its name indicates a presentation responsibility. It writes human-readable terminal output.

### Additional review signals

- Returns meaningful value: `False`
- Contains `await`: `False`
- Contains raise/assert: `False`
- Performs MCP/session call: `False`
- Contains parsing logic: `False`
- Mutates or accumulates data: `False`

---

## `display_prompt_result`

### Defined in

- File: `C:\AI_Projects\mcp_client_learning_project\src\mcp_client\client.py`
- Lines: `2218` through `2294`

### Called from

- `retrieve_and_verify_prompt` at line `2490` using `display_prompt_result()`

### Dependencies

- `get_prompt_content_text`
- `normalize_prompt_role`

### Contains `print()`

- **Yes**
- Print call lines: `2241`, `2242`, `2243`, `2249`, `2252`, `2276`, `2277`, `2281`, `2288`, `2289`, `2291`

### Candidate for `formatters.py`

- **Yes**
- Heuristic score: `6`
- Reason: Its name indicates a presentation responsibility. It writes human-readable terminal output.

### Additional review signals

- Returns meaningful value: `False`
- Contains `await`: `False`
- Contains raise/assert: `False`
- Performs MCP/session call: `False`
- Contains parsing logic: `False`
- Mutates or accumulates data: `False`

---
