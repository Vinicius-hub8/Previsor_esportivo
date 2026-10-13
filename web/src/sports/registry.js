// Lista de esportes do site. Para adicionar um esporte:
//   1) gere public/dados/<id>.json com o mesmo formato do nfl.json
//   2) troque ativo para true aqui; "espn" é o caminho do placar ao vivo (ex.: 'basketball/nba')
export const SPORTS = [
  { id: 'nfl', nome: 'NFL', espn: 'football/nfl', ativo: true, descricao: 'Jogos da semana e projeção de recorde por time' },
  { id: 'nba', nome: 'NBA', espn: 'basketball/nba', ativo: true, descricao: 'Jogos de cada semana e projeção de recorde por time' },
  { id: 'futebol', nome: 'Futebol', ativo: true, descricao: 'Chance de vitória, empate e derrota, tabela atual e tabela prevista, com horários de Brasília.' },
];

export const sportById = (id) => SPORTS.find((s) => s.id === id);
