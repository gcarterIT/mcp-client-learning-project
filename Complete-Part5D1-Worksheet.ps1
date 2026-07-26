param(
    [Parameter(Mandatory = $false)]
    [string]$Path = ".\src\mcp_client\client.py",

    [Parameter(Mandatory = $false)]
    [string]$OutputDirectory = "."
)

$ErrorActionPreference = "Stop"

# ------------------------------------------------------------
# Validate inputs
# ------------------------------------------------------------

if (-not (Test-Path -LiteralPath $Path)) {
    throw "Python file not found: $Path"
}

if (-not (Test-Path -LiteralPath $OutputDirectory)) {
    New-Item `
        -ItemType Directory `
        -Path $OutputDirectory `
        -Force |
        Out-Null
}

$resolvedPythonPath = (Resolve-Path -LiteralPath $Path).Path
$resolvedOutputDirectory = (Resolve-Path -LiteralPath $OutputDirectory).Path

$markdownOutputPath = Join-Path `
    $resolvedOutputDirectory `
    "part_5d1_formatting_inventory.md"

$jsonOutputPath = Join-Path `
    $resolvedOutputDirectory `
    "part_5d1_formatting_inventory.json"

$tempPythonScript = Join-Path `
    ([System.IO.Path]::GetTempPath()) `
    ("analyze_python_functions_{0}.py" -f ([guid]::NewGuid().ToString("N")))

# ------------------------------------------------------------
# Python AST analyzer
# ------------------------------------------------------------

$pythonAnalyzer = @'
import ast
import json
import os
import sys
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Optional


TARGET_FUNCTIONS = [
    "display_tool_result",
    "display_resource_metadata",
    "display_resource_template_metadata",
    "display_resource_read_result",
    "display_prompt_metadata",
    "display_prompt_result",
]


BUILTIN_NAMES = {
    "print",
    "len",
    "range",
    "enumerate",
    "getattr",
    "setattr",
    "hasattr",
    "isinstance",
    "str",
    "int",
    "float",
    "bool",
    "list",
    "dict",
    "tuple",
    "set",
    "frozenset",
    "sorted",
    "min",
    "max",
    "sum",
    "zip",
    "type",
    "super",
    "open",
    "repr",
    "next",
    "iter",
    "any",
    "all",
    "abs",
    "round",
    "map",
    "filter",
    "reversed",
    "slice",
    "object",
    "Exception",
    "ValueError",
    "TypeError",
    "RuntimeError",
}


@dataclass
class FunctionRecord:
    function: str
    defined_in: str
    definition_line: Optional[int]
    end_line: Optional[int]
    called_from: list[dict]
    dependencies: list[str]
    contains_print: bool
    print_lines: list[int]
    candidate_for_formatters: str
    candidate_reason: str
    formatter_score: int
    returns_meaningful_value: bool
    contains_await: bool
    contains_raise_or_assert: bool
    performs_mcp_or_session_call: bool
    contains_parsing_logic: bool
    mutates_or_accumulates_data: bool


def dotted_name(node: ast.AST) -> Optional[str]:
    """Convert Name/Attribute nodes into dotted names."""
    if isinstance(node, ast.Name):
        return node.id

    if isinstance(node, ast.Attribute):
        parent = dotted_name(node.value)
        if parent:
            return f"{parent}.{node.attr}"
        return node.attr

    return None


def get_function_parameters(node: ast.FunctionDef | ast.AsyncFunctionDef) -> set[str]:
    parameters: set[str] = set()

    argument_groups = [
        node.args.posonlyargs,
        node.args.args,
        node.args.kwonlyargs,
    ]

    for group in argument_groups:
        for argument in group:
            parameters.add(argument.arg)

    if node.args.vararg:
        parameters.add(node.args.vararg.arg)

    if node.args.kwarg:
        parameters.add(node.args.kwarg.arg)

    return parameters


def get_local_names(node: ast.FunctionDef | ast.AsyncFunctionDef) -> set[str]:
    local_names = get_function_parameters(node)

    for child in ast.walk(node):
        if isinstance(child, ast.Name) and isinstance(
            child.ctx,
            (ast.Store, ast.Del),
        ):
            local_names.add(child.id)

        elif isinstance(child, ast.comprehension):
            for target_node in ast.walk(child.target):
                if isinstance(target_node, ast.Name):
                    local_names.add(target_node.id)

        elif isinstance(child, (ast.FunctionDef, ast.AsyncFunctionDef)):
            if child is not node:
                local_names.add(child.name)

        elif isinstance(child, ast.ClassDef):
            local_names.add(child.name)

    return local_names


def get_containing_functions(
    tree: ast.AST,
    target_name: str,
) -> list[dict]:
    results: list[dict] = []

    class CallVisitor(ast.NodeVisitor):
        def __init__(self) -> None:
            self.function_stack: list[str] = []

        def visit_FunctionDef(self, node: ast.FunctionDef) -> None:
            self.function_stack.append(node.name)
            self.generic_visit(node)
            self.function_stack.pop()

        def visit_AsyncFunctionDef(self, node: ast.AsyncFunctionDef) -> None:
            self.function_stack.append(node.name)
            self.generic_visit(node)
            self.function_stack.pop()

        def visit_Call(self, node: ast.Call) -> None:
            called_name = dotted_name(node.func)

            if called_name:
                final_component = called_name.split(".")[-1]

                if final_component == target_name:
                    caller = (
                        ".".join(self.function_stack)
                        if self.function_stack
                        else "<module level>"
                    )

                    results.append(
                        {
                            "containing_function": caller,
                            "line": getattr(node, "lineno", None),
                            "call_expression": called_name,
                        }
                    )

            self.generic_visit(node)

    CallVisitor().visit(tree)

    # Exclude the function definition itself. AST Call nodes do not normally
    # include definitions, but this also removes accidental self-recursion
    # from the caller inventory.
    return [
        item
        for item in results
        if item["containing_function"].split(".")[-1] != target_name
    ]


def analyze_dependencies(
    node: ast.FunctionDef | ast.AsyncFunctionDef,
) -> list[str]:
    local_names = get_local_names(node)
    dependencies: set[str] = set()

    for child in ast.walk(node):
        if not isinstance(child, ast.Call):
            continue

        called_name = dotted_name(child.func)

        if not called_name:
            continue

        root_name = called_name.split(".")[0]
        final_name = called_name.split(".")[-1]

        if final_name in BUILTIN_NAMES:
            continue

        if root_name in local_names:
            # Method calls on local values are implementation details rather
            # than external module dependencies.
            continue

        if final_name == node.name:
            continue

        dependencies.add(called_name)

    # Also capture important referenced module attributes such as
    # types.TextContent, even when they are not called as functions.
    for child in ast.walk(node):
        if isinstance(child, ast.Attribute):
            name = dotted_name(child)

            if not name:
                continue

            root_name = name.split(".")[0]

            if (
                root_name not in local_names
                and root_name not in BUILTIN_NAMES
                and "." in name
            ):
                dependencies.add(name)

    return sorted(dependencies)


def returns_meaningful_value(
    node: ast.FunctionDef | ast.AsyncFunctionDef,
) -> bool:
    for child in ast.walk(node):
        if isinstance(child, ast.Return):
            if child.value is not None:
                if isinstance(child.value, ast.Constant):
                    if child.value.value is None:
                        continue

                return True

    return False


def get_print_lines(
    node: ast.FunctionDef | ast.AsyncFunctionDef,
) -> list[int]:
    lines: list[int] = []

    for child in ast.walk(node):
        if not isinstance(child, ast.Call):
            continue

        name = dotted_name(child.func)

        if name == "print":
            line = getattr(child, "lineno", None)

            if line is not None:
                lines.append(line)

    return sorted(set(lines))


def contains_mcp_or_session_call(
    node: ast.FunctionDef | ast.AsyncFunctionDef,
) -> bool:
    protocol_method_names = {
        "call_tool",
        "read_resource",
        "get_prompt",
        "list_tools",
        "list_resources",
        "list_resource_templates",
        "list_prompts",
        "initialize",
    }

    for child in ast.walk(node):
        if not isinstance(child, ast.Call):
            continue

        name = dotted_name(child.func)

        if not name:
            continue

        components = name.split(".")

        if components[-1] in protocol_method_names:
            return True

        if components[0] in {"session", "client", "connection"}:
            return True

    return False


def contains_parsing_logic(
    node: ast.FunctionDef | ast.AsyncFunctionDef,
) -> bool:
    parsing_names = {
        "json.loads",
        "json.load",
        "ast.literal_eval",
    }

    for child in ast.walk(node):
        if not isinstance(child, ast.Call):
            continue

        name = dotted_name(child.func)

        if not name:
            continue

        final_name = name.split(".")[-1]

        if name in parsing_names or final_name.startswith("parse_"):
            return True

    return False


def mutates_or_accumulates(
    node: ast.FunctionDef | ast.AsyncFunctionDef,
) -> bool:
    mutation_methods = {
        "append",
        "extend",
        "update",
        "add",
        "remove",
        "discard",
        "pop",
        "clear",
        "insert",
        "setdefault",
    }

    for child in ast.walk(node):
        if not isinstance(child, ast.Call):
            continue

        name = dotted_name(child.func)

        if name and name.split(".")[-1] in mutation_methods:
            return True

    return False


def classify_formatter_candidate(
    function_name: str,
    contains_print: bool,
    meaningful_return: bool,
    contains_await: bool,
    contains_validation: bool,
    performs_mcp_call: bool,
    parsing_logic: bool,
    mutation: bool,
) -> tuple[str, str, int]:
    score = 0
    reasons: list[str] = []

    if function_name.startswith(
        ("display_", "format_", "render_", "print_")
    ):
        score += 3
        reasons.append("Its name indicates a presentation responsibility.")

    if contains_print:
        score += 3
        reasons.append("It writes human-readable terminal output.")
    else:
        score -= 2
        reasons.append("It does not directly print output.")

    if meaningful_return:
        score -= 2
        reasons.append("It returns a meaningful value.")

    if contains_await:
        score -= 3
        reasons.append("It contains asynchronous workflow activity.")

    if contains_validation:
        score -= 3
        reasons.append("It contains assertion or exception behavior.")

    if performs_mcp_call:
        score -= 5
        reasons.append("It appears to perform an MCP/session operation.")

    if parsing_logic:
        score -= 2
        reasons.append("It contains parsing logic.")

    if mutation:
        score -= 1
        reasons.append("It accumulates or mutates data.")

    if score >= 4:
        candidate = "Yes"
    elif score >= 1:
        candidate = "Mixed / manual review required"
    else:
        candidate = "No"

    return candidate, " ".join(reasons), score


def analyze_function(
    source_path: Path,
    tree: ast.Module,
    function_name: str,
) -> FunctionRecord:
    function_node = None

    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            if node.name == function_name:
                function_node = node
                break

    if function_node is None:
        return FunctionRecord(
            function=function_name,
            defined_in="<not found>",
            definition_line=None,
            end_line=None,
            called_from=[],
            dependencies=[],
            contains_print=False,
            print_lines=[],
            candidate_for_formatters="Cannot determine",
            candidate_reason="The function was not found in the analyzed file.",
            formatter_score=0,
            returns_meaningful_value=False,
            contains_await=False,
            contains_raise_or_assert=False,
            performs_mcp_or_session_call=False,
            contains_parsing_logic=False,
            mutates_or_accumulates_data=False,
        )

    print_lines = get_print_lines(function_node)
    meaningful_return = returns_meaningful_value(function_node)

    contains_await = any(
        isinstance(child, (ast.Await, ast.AsyncFor, ast.AsyncWith))
        for child in ast.walk(function_node)
    )

    contains_validation = any(
        isinstance(child, (ast.Raise, ast.Assert))
        for child in ast.walk(function_node)
    )

    performs_mcp_call = contains_mcp_or_session_call(function_node)
    parsing_logic = contains_parsing_logic(function_node)
    mutation = mutates_or_accumulates(function_node)

    candidate, reason, score = classify_formatter_candidate(
        function_name=function_name,
        contains_print=bool(print_lines),
        meaningful_return=meaningful_return,
        contains_await=contains_await,
        contains_validation=contains_validation,
        performs_mcp_call=performs_mcp_call,
        parsing_logic=parsing_logic,
        mutation=mutation,
    )

    return FunctionRecord(
        function=function_name,
        defined_in=str(source_path),
        definition_line=getattr(function_node, "lineno", None),
        end_line=getattr(function_node, "end_lineno", None),
        called_from=get_containing_functions(tree, function_name),
        dependencies=analyze_dependencies(function_node),
        contains_print=bool(print_lines),
        print_lines=print_lines,
        candidate_for_formatters=candidate,
        candidate_reason=reason,
        formatter_score=score,
        returns_meaningful_value=meaningful_return,
        contains_await=contains_await,
        contains_raise_or_assert=contains_validation,
        performs_mcp_or_session_call=performs_mcp_call,
        contains_parsing_logic=parsing_logic,
        mutates_or_accumulates_data=mutation,
    )


def markdown_list(values: list[str], empty_text: str) -> str:
    if not values:
        return f"- {empty_text}"

    return "\n".join(f"- `{value}`" for value in values)


def create_markdown_report(
    source_path: Path,
    records: list[FunctionRecord],
) -> str:
    sections: list[str] = []

    sections.append("# Part 5D.1 Formatting Inventory")
    sections.append("")
    sections.append(f"Analyzed file: `{source_path}`")
    sections.append("")
    sections.append(
        "> Candidate classifications are heuristic recommendations. "
        "The final module-design decision should be reviewed manually."
    )
    sections.append("")

    for record in records:
        sections.append(f"## `{record.function}`")
        sections.append("")

        sections.append("### Defined in")
        sections.append("")
        sections.append(
            f"- File: `{record.defined_in}`"
        )
        sections.append(
            f"- Lines: `{record.definition_line}` through `{record.end_line}`"
        )
        sections.append("")

        sections.append("### Called from")
        sections.append("")

        if record.called_from:
            for call in record.called_from:
                sections.append(
                    "- "
                    f"`{call['containing_function']}` "
                    f"at line `{call['line']}` "
                    f"using `{call['call_expression']}()`"
                )
        else:
            sections.append("- No external call sites detected.")

        sections.append("")
        sections.append("### Dependencies")
        sections.append("")
        sections.append(
            markdown_list(
                record.dependencies,
                "No non-built-in dependencies detected.",
            )
        )
        sections.append("")

        sections.append("### Contains `print()`")
        sections.append("")
        sections.append(
            f"- **{'Yes' if record.contains_print else 'No'}**"
        )

        if record.print_lines:
            formatted_lines = ", ".join(
                f"`{line}`" for line in record.print_lines
            )
            sections.append(f"- Print call lines: {formatted_lines}")

        sections.append("")
        sections.append("### Candidate for `formatters.py`")
        sections.append("")
        sections.append(
            f"- **{record.candidate_for_formatters}**"
        )
        sections.append(
            f"- Heuristic score: `{record.formatter_score}`"
        )
        sections.append(
            f"- Reason: {record.candidate_reason}"
        )
        sections.append("")

        sections.append("### Additional review signals")
        sections.append("")
        sections.append(
            f"- Returns meaningful value: "
            f"`{record.returns_meaningful_value}`"
        )
        sections.append(
            f"- Contains `await`: `{record.contains_await}`"
        )
        sections.append(
            f"- Contains raise/assert: "
            f"`{record.contains_raise_or_assert}`"
        )
        sections.append(
            f"- Performs MCP/session call: "
            f"`{record.performs_mcp_or_session_call}`"
        )
        sections.append(
            f"- Contains parsing logic: "
            f"`{record.contains_parsing_logic}`"
        )
        sections.append(
            f"- Mutates or accumulates data: "
            f"`{record.mutates_or_accumulates_data}`"
        )
        sections.append("")
        sections.append("---")
        sections.append("")

    return "\n".join(sections)


def main() -> int:
    if len(sys.argv) != 4:
        print(
            "Usage: analyzer.py "
            "<python-file> <markdown-output> <json-output>",
            file=sys.stderr,
        )
        return 2

    source_path = Path(sys.argv[1]).resolve()
    markdown_path = Path(sys.argv[2]).resolve()
    json_path = Path(sys.argv[3]).resolve()

    source_text = source_path.read_text(encoding="utf-8")
    tree = ast.parse(source_text, filename=str(source_path))

    records = [
        analyze_function(source_path, tree, function_name)
        for function_name in TARGET_FUNCTIONS
    ]

    json_data = {
        "analyzed_file": str(source_path),
        "functions": [asdict(record) for record in records],
    }

    json_path.write_text(
        json.dumps(json_data, indent=2),
        encoding="utf-8",
    )

    markdown_path.write_text(
        create_markdown_report(source_path, records),
        encoding="utf-8",
    )

    print("Part 5D.1 worksheet analysis completed.")
    print(f"Markdown report: {markdown_path}")
    print(f"JSON report:     {json_path}")
    print("")
    print("Summary:")
    print("")

    for record in records:
        print(
            f"- {record.function}: "
            f"{record.candidate_for_formatters}; "
            f"print={record.contains_print}; "
            f"dependencies={len(record.dependencies)}; "
            f"call-sites={len(record.called_from)}"
        )

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
'@

try {
    Set-Content `
        -LiteralPath $tempPythonScript `
        -Value $pythonAnalyzer `
        -Encoding UTF8

    Write-Host "Analyzing:" -ForegroundColor Cyan
    Write-Host "  $resolvedPythonPath"
    Write-Host ""

    & python `
        $tempPythonScript `
        $resolvedPythonPath `
        $markdownOutputPath `
        $jsonOutputPath

    if ($LASTEXITCODE -ne 0) {
        throw "The Python analyzer exited with code $LASTEXITCODE."
    }

    Write-Host ""
    Write-Host "Review-ready report created:" -ForegroundColor Green
    Write-Host "  $markdownOutputPath"
    Write-Host ""
    Write-Host "Structured JSON report created:" -ForegroundColor Green
    Write-Host "  $jsonOutputPath"
}
finally {
    if (Test-Path -LiteralPath $tempPythonScript) {
        Remove-Item -LiteralPath $tempPythonScript -Force
    }
}