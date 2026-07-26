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

    if ($line -match '^(?<indent>\s*)(?:async\s+)?def\s+') {
        $indent = $Matches.indent.Length

        if ($indent -le $functionIndent) {
            $endIndex = $i - 1
            break
        }
    }

    if ($line -match '^(?<indent>\s*)class\s+') {
        $indent = $Matches.indent.Length

        if ($indent -le $functionIndent) {
            $endIndex = $i - 1
            break
        }
    }
}

$functionLines = $lines[$startIndex..$endIndex]
$functionText = $functionLines -join "`n"

# Extract parameter names from the function signature.
$signatureText = ""
for ($i = 0; $i -lt $functionLines.Count; $i++) {
    $signatureText += " " + $functionLines[$i]

    if ($functionLines[$i] -match '\)\s*(?:->.*?)?:\s*$') {
        break
    }
}

$parameterNames = @()

if ($signatureText -match '\((?<parameters>.*?)\)\s*(?:->.*?)?:') {
    $parameterText = $Matches.parameters

    $parameterNames = [regex]::Matches(
        $parameterText,
        '(?:^|,)\s*\*{0,2}(?<name>[A-Za-z_][A-Za-z0-9_]*)'
    ) | ForEach-Object {
        $_.Groups['name'].Value
    }
}

# Find apparent function calls, including:
# helper_name(...)
# module.helper_name(...)
$callMatches = [regex]::Matches(
    $functionText,
    '(?<!\bdef\s)(?<!\bclass\s)(?<name>[A-Za-z_][A-Za-z0-9_\.]*)\s*\('
)

$ignoredNames = @(
    'print',
    'len',
    'range',
    'enumerate',
    'getattr',
    'setattr',
    'hasattr',
    'isinstance',
    'str',
    'int',
    'float',
    'bool',
    'list',
    'dict',
    'tuple',
    'set',
    'sorted',
    'min',
    'max',
    'sum',
    'zip',
    'type',
    'super',
    'open',
    'repr',
    'next',
    'iter'
)

$dependencies = $callMatches |
    ForEach-Object {
        $_.Groups['name'].Value
    } |
    Where-Object {
        $_ -ne $FunctionName -and
        $_ -notin $parameterNames -and
        $_ -notin $ignoredNames
    } |
    Sort-Object -Unique

[pscustomobject]@{
    Function     = $FunctionName
    File         = (Resolve-Path -LiteralPath $Path).Path
    StartLine    = $startIndex + 1
    EndLine      = $endIndex + 1
    Dependencies = if ($dependencies) {
        $dependencies -join ', '
    }
    else {
        '<none detected>'
    }
}