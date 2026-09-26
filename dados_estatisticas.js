// Gerado por analise/estatisticas.py — não edite à mão.
window.DADOS_ESTATISTICAS = {
 "gerado_em": "2026-09-26",
 "total": 64,
 "aviso_geral": "Os anos vêm do inventário (gerado do .bib) e, na maioria, ainda não foram conferidos no PDF. O agrupamento por núcleo é proposto na tese, não declarado pelos autores.",
 "kpis": {
  "fichados": 3,
  "pct_fichados": 4.7,
  "com_arquivo": 32,
  "procedencia_confirmada": 4
 },
 "funil": [
  {
   "rotulo": "Não obtido",
   "n": 32
  },
  {
   "rotulo": "Arquivo obtido",
   "n": 29
  },
  {
   "rotulo": "Fichado",
   "n": 3
  }
 ],
 "funil_por_nucleo": {
  "Núcleo 1": [
   {
    "rotulo": "Não obtido",
    "n": 10
   },
   {
    "rotulo": "Arquivo obtido",
    "n": 11
   },
   {
    "rotulo": "Fichado",
    "n": 1
   }
  ],
  "Núcleo 2": [
   {
    "rotulo": "Não obtido",
    "n": 22
   },
   {
    "rotulo": "Arquivo obtido",
    "n": 18
   },
   {
    "rotulo": "Fichado",
    "n": 2
   }
  ]
 },
 "procedencia": [
  {
   "rotulo": "Confirmada",
   "n": 4
  },
  {
   "rotulo": "Parcial",
   "n": 4
  },
  {
   "rotulo": "A conferir",
   "n": 45
  },
  {
   "rotulo": "Sem procedência",
   "n": 11
  }
 ],
 "fase": [
  {
   "rotulo": "Ler primeiro",
   "n": 34
  },
  {
   "rotulo": "Ler depois",
   "n": 23
  },
  {
   "rotulo": "Ler com cautela",
   "n": 7
  }
 ],
 "anos": {
  "anos": [
   2003,
   2004,
   2005,
   2006,
   2007,
   2008,
   2009,
   2010,
   2011,
   2012,
   2013,
   2014,
   2015,
   2016,
   2017,
   2018,
   2019,
   2020,
   2021,
   2022,
   2023,
   2024,
   2025,
   2026
  ],
  "series": {
   "Núcleo 1": [
    1,
    0,
    0,
    0,
    0,
    0,
    1,
    0,
    2,
    0,
    0,
    1,
    1,
    1,
    0,
    1,
    1,
    0,
    1,
    1,
    0,
    2,
    1,
    3
   ],
   "Núcleo 2": [
    0,
    0,
    1,
    0,
    0,
    0,
    1,
    0,
    1,
    0,
    0,
    0,
    0,
    1,
    0,
    1,
    2,
    2,
    1,
    1,
    2,
    2,
    14,
    11
   ]
  },
  "sem_ano": 7
 },
 "resumo_ano": [
  {
   "nucleo": "Núcleo 1",
   "n": 17,
   "mediana": 2019.0,
   "q1": 2014.0,
   "q3": 2024.0,
   "min": 2003,
   "max": 2026,
   "pct_ultimos_3_anos": 35.3
  },
  {
   "nucleo": "Núcleo 2",
   "n": 40,
   "mediana": 2025.0,
   "q1": 2021.75,
   "q3": 2026.0,
   "min": 2005,
   "max": 2026,
   "pct_ultimos_3_anos": 67.5
  }
 ],
 "testes": [
  {
   "nome": "Mann–Whitney U (unilateral)",
   "pergunta": "As fontes do Núcleo 2 são mais recentes que as do Núcleo 1?",
   "n1": 17,
   "n2": 40,
   "U": 480.0,
   "p": 0.006654764064156558,
   "efeito_nome": "correlação rank-bisserial",
   "efeito": 0.412,
   "leitura": "p < 0,05 indica que, neste acervo, os anos do Núcleo 2 tendem a ser maiores. O efeito vai de −1 a 1; acima de 0,5 costuma ser lido como grande. Isso descreve o acervo que você reuniu, não a literatura inteira."
  },
  {
   "nome": "Qui-quadrado de independência",
   "pergunta": "A fase de leitura (Ler primeiro / depois / com cautela) depende do núcleo?",
   "tabela": {
    "linhas": [
     "Núcleo 1",
     "Núcleo 2"
    ],
    "colunas": [
     "Ler com cautela",
     "Ler depois",
     "Ler primeiro"
    ],
    "valores": [
     [
      4,
      9,
      9
     ],
     [
      3,
      14,
      25
     ]
    ]
   },
   "chi2": 2.781,
   "gl": 2,
   "p": 0.248977359718962,
   "efeito_nome": "V de Cramér",
   "efeito": 0.208,
   "aviso": "2 célula(s) com frequência esperada < 5: o qui-quadrado fica impreciso; trate o resultado como exploratório.",
   "leitura": "p ≥ 0,05 significa que não há evidência de que a prioridade de leitura dependa do núcleo. V de Cramér perto de 0 indica associação fraca; acima de 0,3, moderada."
  }
 ]
};
