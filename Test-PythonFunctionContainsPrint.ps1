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

$printCalls = @()

for ($i = $startIndex; $i -le $endIndex; $i++) {
    $line = $lines[$i]

    # Ignore full-line comments.
    if ($line -match '^\s*#') {
        continue
    }

    if ($line -match '\bprint\s*\(') {
        $printCalls += [pscustomobject]@{
            LineNumber = $i + 1
            Code       = $line.Trim()
        }
    }
}

[pscustomobject]@{
    Function      = $FunctionName
    File          = (Resolve-Path -LiteralPath $Path).Path
    StartLine     = $startIndex + 1
    EndLine       = $endIndex + 1
    ContainsPrint = $printCalls.Count -gt 0
    PrintCount    = $printCalls.Count
}

if ($printCalls.Count -gt 0) {
    Write-Host ""
    Write-Host "Print statements:" -ForegroundColor Cyan

    $printCalls |
        Format-Table LineNumber, Code -AutoSize
}