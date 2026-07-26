<#

This PowerShell function scans a Python file, 
finds every call to a named function, and reports 
the enclosing def or async def.

to use, example:

. .\Find-PythonFunctionCalls.ps1

Find-PythonFunctionCalls `
    -Path .\src\mcp_client\client.py `
    -FunctionName "format_json"

client.py - file to be searched
function name searched for: "format_json"

#>


function Find-PythonFunctionCalls {
    param(
        [Parameter(Mandatory)]
        [string]$Path,

        [Parameter(Mandatory)]
        [string]$FunctionName
    )

    if (-not (Test-Path -LiteralPath $Path)) {
        throw "File not found: $Path"
    }

    $resolvedPath = (Resolve-Path -LiteralPath $Path).Path
    $lines = Get-Content -LiteralPath $resolvedPath

    # Matches:
    # def function_name(...):
    # async def function_name(...):
    #
    # It also records indentation so nested functions can be distinguished.
    $definitionPattern =
        '^(?<indent>\s*)(?:async\s+)?def\s+(?<name>[A-Za-z_][A-Za-z0-9_]*)\s*\('

    $functions = @()
    $functionStack = @()

    for ($index = 0; $index -lt $lines.Count; $index++) {
        $line = $lines[$index]
        $lineNumber = $index + 1

        if ($line -match $definitionPattern) {
            $indentLength = $Matches.indent.Length

            # Remove functions from the stack when the new definition
            # is at the same or a lower indentation level.
            while (
                $functionStack.Count -gt 0 -and
                $functionStack[-1].Indent -ge $indentLength
            ) {
                $completedFunction = $functionStack[-1]
                $completedFunction.EndLine = $lineNumber - 1

                $functions += $completedFunction

                if ($functionStack.Count -eq 1) {
                    $functionStack = @()
                }
                else {
                    $functionStack =
                        $functionStack[0..($functionStack.Count - 2)]
                }
            }

            $parentName = $null

            if ($functionStack.Count -gt 0) {
                $parentName = $functionStack[-1].QualifiedName
            }

            $qualifiedName = if ($parentName) {
                "$parentName.$($Matches.name)"
            }
            else {
                $Matches.name
            }

            $functionInfo = [pscustomobject]@{
                Name          = $Matches.name
                QualifiedName = $qualifiedName
                StartLine     = $lineNumber
                EndLine       = $lines.Count
                Indent        = $indentLength
            }

            $functionStack += $functionInfo
        }
    }

    # Close any functions still open at the end of the file.
    while ($functionStack.Count -gt 0) {
        $completedFunction = $functionStack[-1]
        $completedFunction.EndLine = $lines.Count
        $functions += $completedFunction

        if ($functionStack.Count -eq 1) {
            $functionStack = @()
        }
        else {
            $functionStack =
                $functionStack[0..($functionStack.Count - 2)]
        }
    }

    # Match the requested function when followed by "(".
    # This also catches forms such as:
    # await display_tool_result(...)
    # module.display_tool_result(...)
    $escapedFunctionName = [regex]::Escape($FunctionName)
    $callPattern = "(?<!def\s)(?<!class\s)\b$escapedFunctionName\s*\("

    $results = for ($index = 0; $index -lt $lines.Count; $index++) {
        $line = $lines[$index]
        $lineNumber = $index + 1

        # Ignore blank lines, comments, and the function's own definition.
        if (
            $line -match '^\s*#' -or
            $line -match "^\s*(?:async\s+)?def\s+$escapedFunctionName\s*\("
        ) {
            continue
        }

        if ($line -match $callPattern) {
            # A line may theoretically be inside multiple functions when
            # nested functions are present. Choose the most deeply nested.
            $containingFunction = $functions |
                Where-Object {
                    $lineNumber -ge $_.StartLine -and
                    $lineNumber -le $_.EndLine
                } |
                Sort-Object Indent -Descending |
                Select-Object -First 1

            [pscustomobject]@{
                File               = $resolvedPath
                CallLine           = $lineNumber
                ContainingFunction = if ($containingFunction) {
                    $containingFunction.QualifiedName
                }
                else {
                    '<module level>'
                }
                FunctionStartLine  = if ($containingFunction) {
                    $containingFunction.StartLine
                }
                else {
                    $null
                }
                Code               = $line.Trim()
            }
        }
    }

    if (-not $results) {
        Write-Warning "No calls to '$FunctionName' were found in '$resolvedPath'."
        return
    }

    $results
}

