# Part 5D.1 Formatting Inventory

Analyzed file: `C:\AI_Projects\mcp_client_learning_project\src\mcp_client\client.py`

> Candidate classifications are heuristic recommendations. The final module-design decision should be reviewed manually.

## `display_tool_result`

### Defined in

- File: `C:\AI_Projects\mcp_client_learning_project\src\mcp_client\client.py`
- Lines: `163` through `238`

### Called from

- `invoke_add_numbers` at line `462` using `display_tool_result()`

### Dependencies

- `format_json`
- `get_structured_tool_content`
- `types.TextContent`

### Contains `print()`

- **Yes**
- Print call lines: `187`, `188`, `189`, `197`, `199`, `204`, `210`, `211`, `216`, `221`, `229`, `233`, `236`, `238`

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
- Lines: `531` through `557`

### Called from

- `read_application_configuration` at line `1710` using `display_resource_metadata()`

### Dependencies

- No non-built-in dependencies detected.

### Contains `print()`

- **Yes**
- Print call lines: `545`, `546`, `547`, `549`, `554`

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
- Lines: `745` through `779`

### Called from

- `test_product_resource_template` at line `1211` using `display_resource_template_metadata()`

### Dependencies

- `get_mime_type`
- `get_uri_template`

### Contains `print()`

- **Yes**
- Print call lines: `755`, `757`, `763`, `769`, `775`

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
- Lines: `1470` through `1569`

### Called from

- `read_json_resource` at line `882` using `display_resource_read_result()`
- `read_application_configuration` at line `1728` using `display_resource_read_result()`

### Dependencies

- `format_json`
- `get_resource_blob`
- `get_resource_text`
- `parse_json_resource_text`

### Contains `print()`

- **Yes**
- Print call lines: `1498`, `1499`, `1500`, `1505`, `1508`, `1513`, `1514`, `1515`, `1517`, `1518`, `1522`, `1532`, `1533`, `1534`, `1541`, `1542`, `1549`, `1550`, `1558`, `1561`, `1567`

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
- Lines: `1894` through `1964`

### Called from

- `retrieve_and_verify_prompt` at line `2459` using `display_prompt_metadata()`

### Dependencies

- `get_prompt_arguments`
- `is_prompt_argument_required`

### Contains `print()`

- **Yes**
- Print call lines: `1920`, `1921`, `1925`, `1931`, `1934`, `1953`, `1956`, `1960`

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
- Lines: `2219` through `2295`

### Called from

- `retrieve_and_verify_prompt` at line `2491` using `display_prompt_result()`

### Dependencies

- `get_prompt_content_text`
- `normalize_prompt_role`

### Contains `print()`

- **Yes**
- Print call lines: `2242`, `2243`, `2244`, `2250`, `2253`, `2277`, `2278`, `2282`, `2289`, `2290`, `2292`

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
