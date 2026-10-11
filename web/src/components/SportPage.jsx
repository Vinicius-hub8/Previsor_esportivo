import AccuracyStrip from './AccuracyStrip.jsx';
import Tabs from './Tabs.jsx';
import GamesTab from './GamesTab.jsx';
import TeamTab from './TeamTab.jsx';
import TabelaTab from './TabelaTab.jsx';
import Notice from './Notice.jsx';
import { store } from '../lib/store.js';

// Rotas desta página (depois de #/<esporte>):
//   /jogos/<temporada>/<semana>      /time/<sigla>      /tabela (só esportes com simulação, como a NBA)
export default function SportPage({ sport, data, live, route, navigate }) {
  const { meta } = data;
  const abas = [
    { id: 'jogos', nome: 'Jogos da semana' },
    { id: 'time', nome: 'Projeção de time' },
    ...(data.simulacao ? [{ id: 'tabela', nome: 'Classificação e título' }] : []),
  ];
  const tab = abas.some((a) => a.id === route[0]) ? route[0] : 'jogos';

  const abrirAba = (id) => {
    if (id === 'tabela') navigate(sport.id, 'tabela');
    else if (id === 'time') navigate(sport.id, 'time', store.get('pv_team') || undefined);
    else navigate(sport.id, 'jogos');
  };

  return (
    <>
      <div className="crumb">
        <button className="back" onClick={() => navigate()}>← Esportes</button>
      </div>
      <h1 className="sport-title">
        {sport.nome} <span className="tag">Temporada {meta.temporada_rotulo ?? meta.temporada}</span>
      </h1>
      <AccuracyStrip meta={meta} />
      <Tabs tab={tab} onChange={abrirAba} abas={abas} />
      <div id="panel" role="tabpanel" aria-labelledby={`tab-${tab}`} className="panel">
        {tab === 'tabela' ? (
          <TabelaTab data={data} onTeam={(c) => { store.set('pv_team', c); navigate(sport.id, 'time', c); }} />
        ) : tab === 'time' ? (
          <TeamTab data={data} code={route[1]} onSelect={(c) => { store.set('pv_team', c); navigate(sport.id, 'time', c); }} />
        ) : (
          <GamesTab data={data} live={live} season={route[1]} week={route[2]} onSelect={(s, w) => navigate(sport.id, 'jogos', s, w)} />
        )}
      </div>
      <Notice meta={meta} />
    </>
  );
}
