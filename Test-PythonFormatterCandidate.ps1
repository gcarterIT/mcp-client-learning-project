param(
    [Parameter(Mandatory)]
    [string]$Path,

    [Parameter(Mandatory)]
    [string]$FunctionName
)

if (-not (Test-Path -LiteralPath $Path)) {
    throw "File not found: $Path"
}

$lines = Get-Content -LiteralPath $Path

$definitionPattern =
    "^(?<indent>\s*)(?:async\s+)?def\s+$([regex]::Escape($FunctionName))\s*\("

$startIndex = $null
$functionIndent = $null

for ($i = 0; $i -lt $lines.Count; $i++) {
    if ($lines[$i] -match $definitionPattern) {
        $startIndex = $i
        $functionIndent = $Matches.indent.Length
        break
    }
}

if ($null -eq $startIndex) {
    throw "Function '$FunctionName' was not found in '$Path'."
}

$endIndex = $lines.Count - 1

for ($i = $startIndex + 1; $i -lt $lines.Count; $i++) {
    $line = $lines[$i]

    if ($line -match '^\s*$' -or $line -match '^\s*#') {
        continue
    }

    if (
        $line -match '^(?<indent>\s*)(?:async\s+)?def\s+' -or
        $line -match '^(?<indent>\s*)class\s+'
    ) {
        $indent = $Matches.indent.Length

        if ($indent -le $functionIndent) {
            $endIndex = $i - 1
            break
        }
    }
}

$functionLines = $lines[$startIndex..$endIndex]
$functionText = $functionLines -join "`n"

$containsPrint = $functionText -match '\bprint\s*\('
$containsReturnValue =
    $functionText -match '(?m)^\s+return\s+(?!None\b)[^\r\n]+'

$containsAwait = $functionText -match '\bawait\b'

$containsRaise = $functionText -match '\braise\b'

$containsAssertion =
    $functionText -match '\bassert\b|AssertionError'

$containsNetworkOrMcpCall =
    $functionText -match '\b(session|client)\s*\.\s*(call_tool|read_resource|get_prompt|list_[A-Za-z_]+)\s*\('

$containsParsing =
    $functionText -match '\bjson\s*\.\s*loads\s*\(|\bparse_[A-Za-z_]+\s*\('

$containsMutation =
    $functionText -match '\.(append|extend|update|add|remove|pop|clear)\s*\('

$score = 0
$reasons = @()

if ($FunctionName -match '^(display_|format_|render_|print_)') {
    $score += 3
    $reasons += "Name indicates presentation or formatting."
}

if ($containsPrint) {
    $score += 3
    $reasons += "Contains print output."
}
else {
    $score -= 2
    $reasons += "Does not contain print output."
}

if ($containsAwait) {
    $score -= 3
    $reasons += "Contains await; may perform workflow or I/O."
}

if ($containsNetworkOrMcpCall) {
    $score -= 5
    $reasons += "Appears to make an MCP or client call."
}

if ($containsRaise -or $containsAssertion) {
    $score -= 3
    $reasons += "Contains validation or exception behavior."
}

if ($containsParsing) {
    $score -= 2
    $reasons += "Contains parsing logic."
}

if ($containsReturnValue) {
    $score -= 2
    $reasons += "Returns a meaningful value rather than only displaying."
}

if ($containsMutation) {
    $score -= 1
    $reasons += "Mutates or accumulates data."
}

$candidate = if ($score -ge 4) {
    'Yes'
}
elseif ($score -ge 1) {
    'Mixed / Review manually'
}
else {
    'No'
}

[pscustomobject]@{
    Function          = $FunctionName
    File              = (Resolve-Path -LiteralPath $Path).Path
    StartLine         = $startIndex + 1
    EndLine           = $endIndex + 1
    FormatterScore    = $score
    Candidate         = $candidate
    ContainsPrint     = $containsPrint
    ReturnsValue      = $containsReturnValue
    ContainsAwait     = $containsAwait
    ContainsParsing   = $containsParsing
    ContainsValidation = ($containsRaise -or $containsAssertion)
    PerformsMcpCall   = $containsNetworkOrMcpCall
    Reasons           = $reasons -join ' '
}