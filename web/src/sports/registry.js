// Lista de esportes do site. Para adicionar um esporte:
//   1) gere public/dados/<id>.json com o mesmo formato do nfl.json
//   2) troque ativo para true aqui
export const SPORTS = [
  { id: 'nfl', nome: 'NFL', ativo: true, descricao: 'Jogos da semana e projeção de recorde por time' },
  { id: 'nba', nome: 'NBA', ativo: false, descricao: 'Mesma lógica da NFL, com dados abertos da liga.' },
  { id: 'futebol', nome: 'Futebol', ativo: false, descricao: 'Principais ligas, com chance de vitória, empate e derrota.' },
];

export const sportById = (id) => SPORTS.find((s) => s.id === id);
