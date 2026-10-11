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
- [x] Publicação automática (GitHub Pages) e placar ao vivo + atualização ao fim do jogo

**1. Analytics da NFL** (dados do nflverse)
- [ ] Página do recebedor: mapa de zonas do campo (esquerda/meio/direita × profundidade) e rotas (% dos alvos, % de recepção, jardas por alvo)
- [ ] Página do quarterback: onde no campo ele joga melhor (zona, profundidade, EPA, % de acerto, sob pressão)
- [ ] Rotas só existem de 2023 em diante; a temporada atual entra quando a fonte publicar

**2. Futebol**
- [ ] 6 ligas (Premier League, La Liga, Serie A, Bundesliga, Ligue 1 e uma sexta a definir, sugestão: Brasileirão)
- [ ] Modelo de 3 resultados (vitória, empate, derrota), simulação de tabela, título, vaga em copas e rebaixamento
- [ ] Botão **Analytics**: mapas de calor de jogadores (Bundesliga 2023/24, dados abertos IMPECT, com crédito) e o que mais for possível
- [ ] Mapa de chutes das temporadas atuais, se houver fonte estável e permitida

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

