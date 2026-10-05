# Auditoria dos nós científicos isolados

Data: 05/10/2026

## Escopo

Foram auditados os quatro nós classificados pelo Graphify como `paper` e sem arestas no grafo de 1.227 nós.

## Resultado

### 1. C.A. Tony Buffington

- Não é um artigo independente: é o autor do PDF *Feline idiopathic cystitis: current understanding of pathophysiology and management*.
- Autoria confirmada na primeira página do PDF.
- Correção: aresta `authored` para o nó do artigo.

### 2. Feline Idiopathic Cystitis: Current Understanding

- Não é um documento diferente do registro N45; o isolamento decorreu de caminho antigo (`PDF/29062026/`) coexistindo com o caminho atual (`PDF/Síndrome CIF/`).
- O artigo discute FIC, resposta ao estresse e enriquecimento ambiental nas pp. 1-3 do PDF.
- Correção: aresta `discusses` para o conceito canônico `westropp_2004_fic`.
- Correção persistente: o caminho antigo foi removido do manifesto e dos artefatos intermediários; as relações úteis foram redirecionadas para os nós canônicos do caminho atual.

### 3. Stella et al. (2011)

- O nó foi extraído de um mapa mental, não do artigo original.
- O mapa referencia explicitamente `#53 - Stella et al. 2011` na p. 1.
- Correção: aresta `references` entre o nó da Síndrome de Pandora no mapa e Stella et al.
- Cautela: o mapa é artefato derivado e não deve ser usado como evidência científica.

### 4. Machine Learning Algorithms for Cattle Behavior

- Não é um quarto PDF independente: é um estudo/tópico citado dentro da revisão de Hossein-Zadeh (2025).
- A revisão descreve classificação de comportamento bovino com RNN na p. 14 e cita trabalho com acelerômetro e giroscópio na p. 31.
- Correção: aresta `references` a partir do nó da revisão.
- Cautela: demonstra viabilidade tecnológica em bovinos; não é evidência direta para gatos com Síndrome de Pandora.

## Regra de interpretação

As arestas acima corrigem rastreabilidade e navegação. Elas não transformam relações do grafo em evidência para a tese. Afirmações científicas continuam dependendo da conferência no PDF original.

## Segunda rodada: conceitos e imagem isolados

- **Adriana da Silva Santos:** conectada ao relatório como orientadora, conforme pp. 1-2 do PDF S11.
- **Alessandra Aparecida Medeiros:** conectada ao relatório como supervisora, conforme p. 2 do PDF S11.
- **HOVET-UFU:** conectado como local das atividades descritas no relatório S11, conforme pp. 9 e 16-29.
- **Feliway:** conectado ao estresse felino como intervenção discutida pela revisão, conforme p. 6.
- **DTUIF:** conectado à tese de Reginaldo Pereira como tema discutido, conforme pp. 8-9, 21 e 44-49.
- **Thesis Study Mind Map:** conectado à Síndrome de Pandora como representação visual derivada, sem valor de evidência primária.
