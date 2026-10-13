# Fator Casa

Previsões de jogos da NFL, da NBA e de 6 ligas de futebol com Python (pandas + scikit-learn) e um site em React para consultar os resultados:
palpites de cada semana, projeção de recorde de cada time e a acurácia real do modelo.

## Estrutura

O nome do repositório continua `Previsor_esportivo` (renomear no GitHub é opcional e mudaria o endereço do site e a prévia de link).

```
previsor-esportivo/
├── previsor_nfl.py        # modelo da NFL + menu no terminal
├── exportar_dados.py      # roda o modelo da NFL e gera web/public/dados/nfl.json
├── previsor_nba.py        # modelo da NBA + terminal
├── exportar_nba.py        # roda o modelo da NBA e gera web/public/dados/nba.json
├── previsor_futebol.py    # modelo de futebol (6 ligas): Elo + gols (Poisson) + simulação da tabela
├── exportar_futebol.py    # gera web/public/dados/futebol.json e futebol/<liga>.json
├── noticias.py            # ajustes por notícia (lesões etc.) lidos de ajustes_noticias.csv
├── ajustes_noticias.csv   # onde você registra as notícias que mudam a previsão
├── placar.py              # placar previsto (NFL/NBA) e horário de Brasília
├── docs/                  # paleta de cores (md + png) e logos (svg + png)
├── atualizar.py           # atualiza os dados de todos os esportes
├── espn.py                # placares da ESPN (completa jogos recém-terminados)
├── verificar_novos.py     # detecta jogo terminado que o site ainda não mostra
├── tests/                 # testes (python tests/test_tempo_real.py)
├── cloudflare/            # intermediário opcional para o placar ao vivo
├── requirements.txt       # dependências Python
├── notebooks/             # versão para o Google Colab
├── .github/workflows/     # publicar.yml (site) e ao-fim-do-jogo.yml (verifica jogos terminados)
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

## Tempo real

Duas camadas, sem servidor:

1. **Placar ao vivo na tela (cerca de 1 minuto).** O navegador consulta o placar público da ESPN (`web/src/lib/useAoVivo.js`).
   Jogo em andamento aparece com a etiqueta **AO VIVO** e o placar; quando termina, o cartão já mostra **Acertou/Errou**.
   Consulta a cada 30 s com jogo rolando e espaça quando não há jogo. Se a ESPN falhar, o site segue com os dados do dia.
   Se o navegador bloquear a consulta (erro de CORS no console), use o intermediário gratuito de `cloudflare/placar-worker.js`
   (instruções no próprio arquivo) e defina `VITE_PLACAR_PROXY` em `web/.env.production`.
2. **Modelo e tabelas refeitos depois do jogo (10 a 20 minutos).** `ao-fim-do-jogo.yml` roda a cada 15 minutos, compara a ESPN com o
   site publicado e, se algum jogo terminou e ainda não tem placar, dispara `publicar.yml` (Elo, projeção de recorde, tabela e chance
   de título). As bases abertas demoram horas, então `espn.py` completa os placares que faltam. Há um intervalo mínimo de 20 min entre
   publicações. O GitHub pode atrasar execuções agendadas e as desativa após 60 dias sem atividade no repositório.

O endereço da ESPN é público, mas não oficial: pode mudar sem aviso. Por isso ele é um extra e nunca uma dependência.

## Testes

```
python tests/test_tempo_real.py
python tests/test_futebol.py
python tests/test_noticias.py
python tests/test_placar.py
```

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

## Futebol

Seis ligas: Premier League, La Liga, Serie A, Bundesliga, Ligue 1 e Brasileirão Série A. Cada uma tem três abas: **Jogos da rodada** (horário de Brasília), **Tabela atual** e **Tabela prevista**.

- **Dados:** calendário e placares do [openfootball](https://github.com/openfootball) (domínio público), 2018-19 em diante. Quando eles ainda não têm um resultado recente, a ESPN completa (o jogo é achado pelo nome dos times e pela data).
- **Modelo:** Elo de cada time (peso maior para goleada, vantagem de casa, regressão à média a cada temporada) alimenta uma regressão de Poisson que dá os gols esperados de cada lado; daí saem as chances de vitória, empate e derrota e o placar mais provável.
- **Acurácia (2020-21 a 2025-26, só com dados anteriores a cada temporada):** cerca de 53% nas ligas da Inglaterra, Espanha e Itália, 51% na Alemanha e na França e 48% no Brasileirão (o mandante vence 44% a 47% das vezes, e 1 jogo em 4 termina empatado). É normal: futebol tem três resultados e muito acaso. O Elo ficou num platô, e K, vantagem de casa e reversão à média quase não mudam o resultado.
- **Tabela prevista:** simula os jogos restantes 10 mil vezes (gols sorteados + variação na força dos times, calibrada em backtest) e mostra pontos esperados, faixa de 80%, chance de título, de vaga continental (simplificada: top 4, top 3 na França, top 6 no Brasil) e de rebaixamento, além da chance de cada posição.
- **Horários:** convertidos do fuso de cada país para Brasília. Jogo sem horário divulgado aparece como "horário a definir"; jogo adiado sem nova data aparece como "adiado".
- Terminal: `python previsor_futebol.py premier` (ou `laliga`, `seriea`, `bundesliga`, `ligue1`, `brasileirao`) e `python atualizar.py futebol`.
- Ainda não tem placar ao vivo no futebol; a tabela atualiza quando o site é publicado de novo.
- Ao entrar em Futebol, o site mostra as 6 ligas para você escolher.

## Placar previsto e horários

- **Horário de Brasília** em todos os esportes: NFL e NBA (originalmente em horário do leste dos EUA) e as ligas de futebol (fuso de cada país) são convertidos no Python. Os jogos de cada rodada aparecem agrupados por dia e ordenados por horário (na NFL e na NBA ainda dá para ordenar por "Mais confiantes").
- **Placar previsto (NFL e NBA):** a chance de vitória vira uma margem esperada (ajustada no histórico) e o total de pontos sai do ritmo recente dos dois times. É a estimativa do placar mais típico, não do exato: nos jogos testados, a margem errou em média cerca de 9,8 pontos na NFL e 11,4 na NBA. No futebol o cartão mostra o placar mais provável do modelo de gols.

## Notícias que mudam a previsão

O modelo só enxerga resultados passados e não lê notícia sozinho. Para uma lesão, suspensão ou descanso de astro entrar na conta, registre uma linha em `ajustes_noticias.csv` (time, ajuste de força em pontos de Elo, motivo, link da fonte e até que dia vale) e rode `python atualizar.py`. O ajuste vale só para os jogos dentro da janela, muda as chances (e a tabela prevista, no futebol) e aparece no cartão do jogo como "notícia considerada", com o motivo e o link.

Ordem de grandeza sugerida (julgamento, **não testado no histórico**): quarterback titular da NFL fora, −90; astro da NBA fora, −40; craque ou goleiro titular no futebol, −25. Na NFL, jogos que já têm linha de aposta não são ajustados, porque a linha já embute a notícia. O arquivo vem vazio de propósito: só entra notícia que alguém conferiu (fonte e data).

## Tentativas de subir a acurácia

Testadas com o mesmo método do site (cada temporada prevista só com o que existia antes dela). Resultado: **sem ganho**, então nada disso entrou.
- Futebol, 6 ligas: regressão logística direta, com forma recente, ataque/defesa e descanso, e árvores de gradiente (HistGradientBoosting) ficaram iguais ou piores que o Elo + gols de Poisson (perda logarítmica: 1,000 no Poisson, 1,000 a 1,005 nas regressões e 1,065 nas árvores; acerto: 51,5% no Poisson, 51,4% a 51,5% nas regressões e 48,9% nas árvores). Variar K, vantagem de casa e reversão do Elo também não muda.
- NFL e NBA: o ajuste fino das features já estava num platô (NBA 65,2%; NFL 66,6% com linha).
Para subir de verdade falta informação nova (odds de mercado no futebol e na NBA, gols esperados, escalações e lesões). O caminho já aberto é o das notícias acima.

## Limitações

- Lesões, troca de quarterback, clima e suspensões não entram no modelo.
- Na projeção de recorde, a força dos times fica "congelada" no estado atual e os jogos são tratados como independentes. Playoffs não entram.
- A simulação da NBA usa a força atual dos times e não leva em conta playoffs já disputados.
- Na NBA, lesões e descanso de astros pesam muito e não entram; no começo da temporada, o Elo vem do ano anterior.
- Só as próximas semanas têm linha de aposta; as demais usam o modelo sem ela.
- Estudo estatístico e educacional. Não é recomendação de aposta.

## Upgrades planejados

Ordem sugerida: terminar cada frente antes de abrir a próxima.

**Feito**
- [x] NFL e NBA com palpites, projeção de recorde e acurácia medida (walk-forward)
- [x] NBA: simulação da temporada (classificação, play-in, playoffs e chance de título)
- [x] Futebol: 6 ligas com palpite de 3 resultados, tabela atual, tabela prevista e horário de Brasília
- [x] Marca Fator Casa (logo, paleta, cores por esporte), placar previsto, horário de Brasília em tudo e ajustes por notícias
- [x] NFL: classificação por divisão com recorde previsto
- [x] Publicação automática (GitHub Pages) e placar ao vivo + atualização ao fim do jogo

**1. Analytics da NFL** (dados do nflverse)
- [ ] Página do recebedor: mapa de zonas do campo (esquerda/meio/direita × profundidade) e rotas (% dos alvos, % de recepção, jardas por alvo)
- [ ] Página do quarterback: onde no campo ele joga melhor (zona, profundidade, EPA, % de acerto, sob pressão)
- [ ] Rotas só existem de 2023 em diante; a temporada atual entra quando a fonte publicar

**2. Futebol** (as 6 ligas já estão no ar; falta o resto)
- [ ] Placar ao vivo e atualização ao fim do jogo no futebol
- [ ] Simulação dos playoffs da NFL (chance de título e de playoff por time)
- [ ] Coletor automático de lesões (ESPN) para preencher os ajustes por notícia
- [ ] Botão **Analytics**: mapas de calor de jogadores (Bundesliga 2023/24, dados abertos IMPECT, com crédito) e o que mais for possível
- [ ] Mapa de chutes das temporadas atuais, se houver fonte estável e permitida
- [ ] Confronto direto como desempate (La Liga e Serie A) e regras de vaga continental por liga

**3. Previsões de jogadores**
- [ ] Líderes de estatística: artilheiro e assistências (futebol), pontos (NBA), jardas e sacks (NFL), projetados pelo ritmo atual
- [ ] Candidatos a prêmios (MVP, OPOY, DPOY): ranking transparente com os critérios do histórico, sem fingir uma probabilidade validada

**4. Dados e arquitetura**
- [ ] Guardar cada palpite antes do jogo (SQLite, depois PostgreSQL) para medir a acurácia ao vivo de verdade
- [ ] Backend (Spring Boot + PostgreSQL) servindo a API; Python continua rodando os modelos
- [ ] Redes neurais para estudar os dados (comparar com a regressão logística e o gradient boosting)
- [ ] Testes automatizados contra vazamento de dados (pytest)

**5. Identidade e acabamento**
- [ ] Escolher o nome do projeto e criar a logo (favicon, cabeçalho e imagem de compartilhamento)
- [ ] Gráfico de calibração das probabilidades
- [ ] Modo offline/PWA no celular

