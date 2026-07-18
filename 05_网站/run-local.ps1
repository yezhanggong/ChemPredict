param([int]$Port = 8788)

Set-Location -LiteralPath $PSScriptRoot

if ($env:PYTHON_EXE) {
    & $env:PYTHON_EXE -m http.server $Port --bind 127.0.0.1
} elseif (Get-Command python -ErrorAction SilentlyContinue) {
    & python -m http.server $Port --bind 127.0.0.1
} elseif (Get-Command py -ErrorAction SilentlyContinue) {
    & py -3 -m http.server $Port --bind 127.0.0.1
} else {
    throw 'Python 3 was not found. Install Python or set PYTHON_EXE.'
}
