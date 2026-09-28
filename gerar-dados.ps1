# Exportador seguro do cofre para o painel.
# Gera em area temporaria, valida as relacoes e somente depois substitui os
# arquivos publicados. Em caso de erro, o painel atual permanece intacto.
param(
    [string]$Cofre = "C:\Users\rcmin\OneDrive\Documents\Pos-Graduacao\Doutorado UFC\Síndrome de Pandora",
    [switch]$Check
)

$ErrorActionPreference = 'Stop'
$Python = Get-Command python -ErrorAction SilentlyContinue
if (-not $Python) {
    Write-Error "Python nao encontrado no PATH."
    exit 1
}

$ArgsExportacao = @(
    (Join-Path $PSScriptRoot 'painel_local\sincronizar_acervo.py'),
    '--cofre', $Cofre,
    '--painel', $PSScriptRoot
)
if (-not $Check) { $ArgsExportacao += '--write' }

& $Python.Source @ArgsExportacao
exit $LASTEXITCODE
