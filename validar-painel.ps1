$ErrorActionPreference = 'Stop'
$Python = Get-Command python -ErrorAction SilentlyContinue
if (-not $Python) {
    Write-Error "Python nao encontrado no PATH."
    exit 1
}

& $Python.Source (Join-Path $PSScriptRoot 'painel_local\guardiao_acervo.py') --raiz $PSScriptRoot
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

& $Python.Source -m unittest discover -s (Join-Path $PSScriptRoot 'tests') -p 'test_*.py'
exit $LASTEXITCODE
