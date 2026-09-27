# gerar-dados.ps1 — Sincroniza dados_inventario.js e dados_pdfs.js com o cofre
#
# Uso normal (cofre padrão):
#   cd C:\Users\rcmin\Projetos\S-ndrome-Pandora
#   .\gerar-dados.ps1
#
# Uso com caminho alternativo:
#   .\gerar-dados.ps1 -Cofre "D:\outro\caminho"
#
# Após executar, revise e faça commit:
#   git diff dados_inventario.js dados_pdfs.js
#   git add dados_inventario.js dados_pdfs.js
#   git commit -m "dados: sincronizar com cofre"
#   git push origin main

param(
    [string]$Cofre = "C:\Users\rcmin\OneDrive\Documents\Pos-Graduacao\Doutorado UFC\Síndrome de Pandora"
)

$ErrorActionPreference = 'Stop'
$Painel = $PSScriptRoot

# ──────────────────────────────────────────────────────────────────
# Helpers
# ──────────────────────────────────────────────────────────────────

# Escapa uma string para JSON sem converter não-ASCII em \uXXXX
function To-JsonStr([string]$s) {
    if ($null -eq $s) { return 'null' }
    $s = $s.Replace('\', '\\').Replace('"', '\"')
    $s = $s -replace [char]0x08, '\b' -replace [char]0x0C, '\f'
    $s = $s.Replace("`n", '\n').Replace("`r", '\r').Replace("`t", '\t')
    return "`"$s`""
}

# ──────────────────────────────────────────────────────────────────
# 1. Verificações
# ──────────────────────────────────────────────────────────────────

if (-not (Test-Path $Cofre)) {
    Write-Error "Cofre não encontrado: $Cofre"
    exit 1
}
$csvPath = Join-Path $Cofre "01_Inventario_Artigo_cat.csv"
if (-not (Test-Path $csvPath)) {
    Write-Error "CSV não encontrado: $csvPath"
    exit 1
}

# ──────────────────────────────────────────────────────────────────
# 2. Ler CSV
# ──────────────────────────────────────────────────────────────────

$registros = Import-Csv -Path $csvPath -Delimiter ';' -Encoding UTF8
Write-Host "CSV: $($registros.Count) registros lidos"

# ──────────────────────────────────────────────────────────────────
# 3. Carregar dados das notas Fontes\ (indexadas por código)
# ──────────────────────────────────────────────────────────────────

$fontesDir = Join-Path $Cofre "Fontes"
$fontes    = @{}   # codigo -> { corpo, arquivo, fichamento }

if (Test-Path $fontesDir) {
    Get-ChildItem $fontesDir -Filter "*.md" | ForEach-Object {
        $txt = [System.IO.File]::ReadAllText($_.FullName, [System.Text.Encoding]::UTF8)

        # Extrair código do frontmatter
        if (-not ($txt -match '(?m)^codigo:\s*"?([^"\s]+)"?\s*$')) { return }
        $cod = $Matches[1].Trim()

        # Corpo = tudo após o segundo ---
        $corpo = ''
        if ($txt -match '(?s)^---.*?---\s*(.+)$') {
            $corpo = $Matches[1].Trim()
        }

        # Extrair caminho do PDF da linha "**PDF:** [[...]]"
        $arq = ''
        if ($corpo -match '\*\*PDF:\*\*\s*\[\[([^\]|]+\.pdf)\]\]') {
            $arq = $Matches[1].Trim()
        }

        # Extrair nome do fichamento markdown da linha "**Fichamento:**"
        $fich = ''
        if ($corpo -match '\*\*Fichamento[^:]*:\*\*[^[]*\[\[([^\]|]+)\]\]') {
            $fich = $Matches[1].Trim() + '.md'
        }

        $fontes[$cod] = @{ corpo = $corpo; arquivo = $arq; fichamento = $fich }
    }
    Write-Host "Fontes: $($fontes.Count) notas carregadas"
}

# ──────────────────────────────────────────────────────────────────
# 4. Scan de fichamentos markdown (fallback se a nota Fonte não tiver o link)
# ──────────────────────────────────────────────────────────────────

$fichDir  = Join-Path $Cofre "Fichamentos"
$fichIdx  = @{}   # codigo -> nome do arquivo .md

if (Test-Path $fichDir) {
    Get-ChildItem $fichDir -Filter "*.md" | ForEach-Object {
        if ($_.Name -match '^([A-Za-z0-9]+)\s*[—\-]') {
            $cod = $Matches[1].Trim()
            $fichIdx[$cod] = $_.Name
        }
    }
}

# ──────────────────────────────────────────────────────────────────
# 5. Normalizar núcleo
# ──────────────────────────────────────────────────────────────────

function Normalize-Nucleo([string]$n) {
    if ($n -match '1') { return 'Núcleo 1' }
    if ($n -match '2') { return 'Núcleo 2' }
    return $n
}

# ──────────────────────────────────────────────────────────────────
# 6. Gerar dados_inventario.js
# ──────────────────────────────────────────────────────────────────

$linhas = [System.Collections.Generic.List[string]]::new()
$linhas.Add('window.DADOS_INVENTARIO = [')

$total = $registros.Count
$i = 0
foreach ($r in $registros) {
    $i++
    $sep = if ($i -lt $total) { ',' } else { '' }

    $cod  = $r.Codigo.Trim()
    $info = $fontes[$cod]

    # Referência: corpo da nota Fonte (mais rico) ou ABNT do CSV
    $ref = if ($info -and $info.corpo) { $info.corpo } else { $r.'Referencia ABNT' }

    # Arquivo: nota Fonte (mais atualizado) ou CSV
    $arq = if ($info -and $info.arquivo) { $info.arquivo } else { $r.'Arquivo na pasta' }

    # Fichamento: nota Fonte > scan Fichamentos\ > CSV
    $fich = ''
    if ($info -and $info.fichamento) { $fich = $info.fichamento }
    elseif ($fichIdx.ContainsKey($cod)) { $fich = $fichIdx[$cod] }
    else { $fich = $r.Fichamento }

    $linhas.Add('    {')
    $linhas.Add("        `"fase`": $(To-JsonStr $r.Fase),")
    $linhas.Add("        `"fichamento`": $(To-JsonStr $fich),")
    $linhas.Add("        `"cautelas`": $(To-JsonStr $r.Cautelas),")
    $linhas.Add("        `"codigo`": $(To-JsonStr $cod),")
    $linhas.Add("        `"grupo`": $(To-JsonStr $r.'Grupo (tema)'),")
    $linhas.Add("        `"tipoEstudo`": $(To-JsonStr $r.'Tipo de estudo'),")
    $linhas.Add("        `"procedencia`": $(To-JsonStr $r.'Procedencia da referencia'),")
    $linhas.Add("        `"porQueLer`": $(To-JsonStr $r.'Por que ler'),")
    $linhas.Add("        `"comoUsar`": $(To-JsonStr $r.'Como usar na tese'),")
    $linhas.Add("        `"arquivo`": $(To-JsonStr $arq),")
    $linhas.Add("        `"referencia`": $(To-JsonStr $ref),")
    $linhas.Add("        `"status`": $(To-JsonStr $r.Status),")
    $linhas.Add("        `"ano`": $(To-JsonStr $r.Ano),")
    $linhas.Add("        `"titulo`": $(To-JsonStr $r.Titulo),")
    $linhas.Add("        `"nucleo`": $(To-JsonStr (Normalize-Nucleo $r.'Nucleo (proposto)'))")
    $linhas.Add("    }$sep")
}
$linhas.Add('];')

$saida = $linhas -join "`n"
[System.IO.File]::WriteAllText((Join-Path $Painel "dados_inventario.js"), $saida, [System.Text.Encoding]::UTF8)
Write-Host "✓ dados_inventario.js: $total registros gerados"

# ──────────────────────────────────────────────────────────────────
# 7. Gerar dados_pdfs.js — varrer todos os PDFs do cofre
# ──────────────────────────────────────────────────────────────────

# Pastas a ignorar completamente
$pastasIgnorar = [System.Collections.Generic.HashSet[string]]@(
    '.obsidian', '.claude', '.git',
    '_Versoes_a_comparar', '_Duplicatas_confirmadas', 'IA'
)

$pdfs = [System.Collections.Generic.List[hashtable]]::new()

Get-ChildItem $Cofre -Recurse -Filter "*.pdf" | Where-Object {
    # Verificar se algum segmento do caminho relativo está na lista de ignorados
    $rel = $_.FullName.Substring($Cofre.Length + 1)
    $segmentos = $rel.Split('\')
    -not ($segmentos | Where-Object { $pastasIgnorar.Contains($_) })
} | ForEach-Object {
    $rel      = $_.FullName.Substring($Cofre.Length + 1).Replace('\', '/')
    $partes   = $rel.Split('/')
    $pasta    = ($partes[0..($partes.Count - 2)] -join '/')
    $pdfs.Add(@{
        pasta   = $pasta
        nome    = $_.BaseName
        arquivo = $rel
        kb      = [math]::Round($_.Length / 1024)
    })
}

$linhasPdf = [System.Collections.Generic.List[string]]::new()
$linhasPdf.Add('// Gerado automaticamente — PDFs do cofre Síndrome de Pandora')
$linhasPdf.Add('window.DADOS_PDFS = [')

$total2 = $pdfs.Count
$j = 0
foreach ($p in $pdfs) {
    $j++
    $sep = if ($j -lt $total2) { ',' } else { '' }
    $linhasPdf.Add(' {')
    $linhasPdf.Add("  `"pasta`": $(To-JsonStr $p.pasta),")
    $linhasPdf.Add("  `"nome`": $(To-JsonStr $p.nome),")
    $linhasPdf.Add("  `"arquivo`": $(To-JsonStr $p.arquivo),")
    $linhasPdf.Add("  `"kb`": $($p.kb)")
    $linhasPdf.Add(" }$sep")
}
$linhasPdf.Add('];')

$saidaPdf = $linhasPdf -join "`n"
[System.IO.File]::WriteAllText((Join-Path $Painel "dados_pdfs.js"), $saidaPdf, [System.Text.Encoding]::UTF8)
Write-Host "✓ dados_pdfs.js: $total2 PDFs gerados"

# ──────────────────────────────────────────────────────────────────
# 8. Resumo
# ──────────────────────────────────────────────────────────────────

Write-Host ""
Write-Host "Pronto. Próximos passos:"
Write-Host "  git diff dados_inventario.js dados_pdfs.js"
Write-Host "  git add dados_inventario.js dados_pdfs.js"
Write-Host "  git commit -m 'dados: sincronizar com cofre'"
Write-Host "  git push origin main"
