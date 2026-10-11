import AccuracyStrip from './AccuracyStrip.jsx';
import Tabs from './Tabs.jsx';
import GamesTab from './GamesTab.jsx';
import TeamTab from './TeamTab.jsx';
import Notice from './Notice.jsx';
import { store } from '../lib/store.js';

// Rotas desta página (depois de #/<esporte>):
//   /jogos/<temporada>/<semana>      /time/<sigla>
export default function SportPage({ sport, data, route, navigate }) {
  const tab = route[0] === 'time' ? 'time' : 'jogos';
  const { meta } = data;

  const abrirAba = (id) => {
    if (id === 'time') navigate(sport.id, 'time', store.get('pv_team') || undefined);
    else navigate(sport.id, 'jogos');
  };

  return (
    <>
      <div className="crumb">
        <button className="back" onClick={() => navigate()}>← Esportes</button>
      </div>
      <h1 className="sport-title">
        {sport.nome} <span className="tag">Temporada {meta.temporada}</span>
      </h1>
      <AccuracyStrip meta={meta} />
      <Tabs tab={tab} onChange={abrirAba} />
      <div id="panel" role="tabpanel" aria-labelledby={`tab-${tab}`} className="panel">
        {tab === 'time' ? (
          <TeamTab data={data} code={route[1]} onSelect={(c) => { store.set('pv_team', c); navigate(sport.id, 'time', c); }} />
        ) : (
          <GamesTab data={data} season={route[1]} week={route[2]} onSelect={(s, w) => navigate(sport.id, 'jogos', s, w)} />
        )}
      </div>
      <Notice meta={meta} />
    </>
  );
}
