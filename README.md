# Previsor Esportivo

Previsões de jogos da NFL com Python (pandas + scikit-learn) e um site em React para consultar os resultados:
palpites de cada semana, projeção de recorde de cada time e a acurácia real do modelo.

## Estrutura

```
previsor-esportivo/
├── previsor_nfl.py        # modelo + menu no terminal
├── exportar_dados.py      # roda o modelo e gera web/public/dados/nfl.json
├── atualizar.py           # atalho para atualizar os dados
├── requirements.txt       # dependências Python
├── notebooks/             # versão para o Google Colab
├── .github/workflows/     # publicação automática no GitHub Pages
└── web/                   # site em React (Vite)
    ├── public/dados/nfl.json     # dados gerados pelo Python
    └── src/
        ├── components/    # Home, SportPage, GamesTab, GameCard, TeamTab, WinChart...
        ├── lib/           # formatação, rotas por hash, tema, carga de dados
        ├── sports/registry.js    # lista de esportes (adicione novos aqui)
        └── styles/        # CSS dividido: tokens, base, ui, home, games, team
```

## Ver o site (jeito mais fácil)

Python 3.11 ou 3.12 (o 3.15 é novo demais para o pandas) e Node 18+.

```
py -3.12 -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt

python atualizar.py        # baixa os dados e gera o JSON
cd web
npm install                # só na primeira vez
npm run dev                # abre o site no navegador, com recarga automática
```

Mexeu em qualquer arquivo de `web/src`? O navegador atualiza sozinho.
Para atualizar os dados depois de cada rodada da NFL: `python atualizar.py` e recarregue a página.

Cada tela tem um link próprio, então dá para mandar a tela exata para alguém:
`#/nfl/jogos/2026/6` (semana 6 de 2026) e `#/nfl/time/KC` (projeção do Kansas City).

## Mostrar para outras pessoas (um link, sem instalar nada)

O arquivo `.github/workflows/publicar.yml` compila o site e publica no GitHub Pages a cada push,
e atualiza os dados todo dia sozinho.

1. Suba o projeto para um repositório no GitHub (branch `main`).
2. No repositório: **Settings > Pages > Source = GitHub Actions**.
3. Pronto: o link aparece na aba **Actions** depois do primeiro deploy.

## Usar no terminal

```
python previsor_nfl.py                 # menu interativo
python previsor_nfl.py semana 6        # previsões da semana 6
python previsor_nfl.py semana 10 2025  # semana 10 de 2025
python previsor_nfl.py time KC         # recorde projetado do Kansas City
```

## Como o modelo funciona

- **Dados:** calendário e resultados do [nflverse](https://github.com/nflverse/nfldata), de 2006 até hoje.
- **Features:** Elo dos times, pontos feitos e sofridos nos últimos 5 jogos, descanso e a linha de aposta (spread).
- **Modelo:** regressão logística. Sem linha de aposta (jogos distantes), usa uma versão sem ela.
- **Sem vazamento:** cada feature de um jogo só usa jogos anteriores a ele.
- **Avaliação:** cada temporada é prevista com o modelo treinado só nas anteriores (walk-forward).

## Resultados (2016 a 2025, fora da amostra)

| Modelo | Acurácia |
|---|---|
| Sempre apostar no mandante | ~55% |
| Elo + médias + descanso (sem linha) | 64,4% |
| Com linha de aposta | 66,6% |

A linha de aposta já embute a opinião das casas, então o modelo completo fica perto do mercado.
Chegar a 70% de forma honesta não é realista na NFL; um número assim indicaria vazamento de dados.

## Limitações

- Lesões, troca de quarterback, clima e suspensões não entram no modelo.
- Na projeção de recorde, a força dos times fica "congelada" no estado atual e os jogos são tratados como independentes. Playoffs não entram.
- Só as próximas semanas têm linha de aposta; as demais usam o modelo sem ela.
- Estudo estatístico e educacional. Não é recomendação de aposta.

## Próximos passos

- [ ] Guardar cada previsão antes do jogo (SQLite, depois PostgreSQL) para medir a acurácia real ao vivo
- [ ] Testes automatizados (pytest), principalmente contra vazamento de dados
- [ ] Comparar com Gradient Boosting e gráfico de calibração das probabilidades
- [ ] Novos esportes (NBA, futebol): um JSON por esporte + uma linha em `web/src/sports/registry.js`
