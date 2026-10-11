# Previsor Esportivo

Previsões de jogos da NFL e da NBA com Python (pandas + scikit-learn) e um site em React para consultar os resultados:
palpites de cada semana, projeção de recorde de cada time e a acurácia real do modelo.

## Estrutura

```
previsor-esportivo/
├── previsor_nfl.py        # modelo da NFL + menu no terminal
├── exportar_dados.py      # roda o modelo da NFL e gera web/public/dados/nfl.json
├── previsor_nba.py        # modelo da NBA + terminal
├── exportar_nba.py        # roda o modelo da NBA e gera web/public/dados/nba.json
├── atualizar.py           # atualiza os dados de todos os esportes
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

python atualizar.py        # baixa os dados e gera os JSONs (NFL e NBA)
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
| Time da casa sempre vence | ~55% |
| Elo + médias + descanso (sem linha) | 64,4% |
| Com linha de aposta | 66,6% |

A linha de aposta já embute a opinião das casas, então o modelo completo fica perto do mercado.
Chegar a 70% de forma honesta não é realista na NFL; um número assim indicaria vazamento de dados.

## NBA

- **Dados:** calendário e placares do [hoopR](https://github.com/sportsdataverse/hoopR-nba-data) (ESPN), de 2002-03 até a temporada atual.
- **Features:** Elo (com margem de vitória), saldo médio dos últimos 10 jogos, dias de descanso, back-to-back e fase (temporada regular ou mata-mata).
- **Sem linha de aposta:** a base aberta não tem. Resultado, 2016-17 a 2025-26: **65,2%** de acerto (se o time da casa sempre vencesse: 56,3%).
- Quando o modelo dá 70% ou mais para um lado, ele acerta cerca de 72% a 83% (a tabela está no site, em "Como ler esses números").
- **Classificação e título:** a aba simula a temporada 10 mil vezes (jogos restantes, play-in e playoffs melhor de 7) e mostra a chance de cada time chegar aos playoffs, à final e ao título. Cada simulação sorteia também uma variação na força dos times, medida no histórico (o Elo de pré-temporada erra ~105 pontos), para o favorito não ficar favorito demais.
- Terminal: `python previsor_nba.py time BOS` ou `python previsor_nba.py dia 2026-10-20`.

## Limitações

- Lesões, troca de quarterback, clima e suspensões não entram no modelo.
- Na projeção de recorde, a força dos times fica "congelada" no estado atual e os jogos são tratados como independentes. Playoffs não entram.
- A simulação da NBA usa a força atual dos times e não leva em conta playoffs já disputados.
- Na NBA, lesões e descanso de astros pesam muito e não entram; no começo da temporada, o Elo vem do ano anterior.
- Só as próximas semanas têm linha de aposta; as demais usam o modelo sem ela.
- Estudo estatístico e educacional. Não é recomendação de aposta.

## Próximos passos

- [ ] Guardar cada previsão antes do jogo (SQLite, depois PostgreSQL) para medir a acurácia real ao vivo
- [ ] Testes automatizados (pytest), principalmente contra vazamento de dados
- [ ] Comparar com Gradient Boosting e gráfico de calibração das probabilidades
- [ ] NBA: linha de aposta e boletim de lesões para passar de 65% (hoje o teto com dados só de calendário)
- [ ] Futebol: um JSON por esporte + uma linha em `web/src/sports/registry.js`
