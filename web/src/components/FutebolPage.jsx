
import AccuracyStrip from './AccuracyStrip.jsx';
import Tabs from './Tabs.jsx';
import Notice from './Notice.jsx';
import FutebolJogos from './FutebolJogos.jsx';
import FutebolTabela from './FutebolTabela.jsx';
import FutebolPrevisao from './FutebolPrevisao.jsx';

import { pct } from '../lib/format.js';
import { useLiga } from '../lib/useLiga.js';
import { store } from '../lib/store.js';

const ABAS = [
  { id: 'jogos', nome: 'Jogos da rodada' },
  { id: 'tabela', nome: 'Tabela atual' },
  { id: 'previsao', nome: 'Tabela prevista' },
];

export default function FutebolPage({
  indice,
  route,
  navigate
}) {
  const ligas = indice.ligas;

  const valida = (id) =>
    ligas.some((l) => l.id === id);

  const lid = valida(route[0]) ? route[0] : null;

  const tab = ABAS.some(
    (a) => a.id === route[1]
  ) ? route[1] : 'jogos';

  const { data, loading, error } = useLiga(lid);

  const ligaAberta = lid !== null;

  const abrirLiga = (id) => {
    store.set('pv_liga', id);
    navigate('futebol', id, tab);
  };

  const abrirAba = (id) =>
    navigate('futebol', lid, id);

  if (!ligaAberta) {
    return (
      <>
        <div className="crumb">
          <button
            className="back"
            onClick={() => navigate()}
          >
            ← Esportes
          </button>
        </div>

        <h1 className="sport-title">
          Futebol
        </h1>

        <p className="note">
          Escolha uma competição para visualizar
          os jogos e as previsões.
        </p>

        <div className="liga-grid">
          {ligas.map((l) => (
            <button
              key={l.id}
              className="liga-card"
              onClick={() => abrirLiga(l.id)}
            >
              <span className="pais">
                {l.pais}
              </span>

              <span className="nm">
                {l.nome.replace(' Série A', '')}
              </span>

              <span className="lin">
                {l.rodada}
                {' · '}
                temporada {l.temporada_rotulo}
              </span>

              <span className="lin">
                Líder:{' '}
                <b>{l.lider.nome}</b>
                {' '}
                ({l.lider.pts} pts em {l.lider.j} jogos)
              </span>

              <span className="lin">
                Favorito ao título:{' '}
                <b>{l.favorito.nome}</b>
                {' '}
                ({pct(l.favorito.tit, 0)})
              </span>

              <span className="lin dim">
                {pct(l.acc, 0)} de acerto nos palpites
              </span>
            </button>
          ))}
        </div>
      </>
    );
  }

  return (
    <>
      <div className="crumb">
        <button
          className="back"
          onClick={() => navigate('futebol')}
        >
          ← Competições
        </button>
      </div>

      <h1 className="sport-title">
        Futebol{' '}
        {data && (
          <span className="tag">
            {data.meta.nome}
            {' · '}
            {data.meta.temporada_rotulo}
          </span>
        )}
      </h1>

      <div
        className="ligas"
        role="group"
        aria-label="Competição"
      >
        {ligas.map((l) => (
          <button
            key={l.id}
            aria-pressed={l.id === lid}
            onClick={() => abrirLiga(l.id)}
          >
            {l.nome.replace(' Série A', '')}
          </button>
        ))}
      </div>

      {loading && (
        <p className="state">
          Carregando a competição…
        </p>
      )}

      {error && (
        <p className="state">
          Não consegui carregar esta competição ({error}).
          Rode <code>python atualizar.py futebol</code>
          {' '}e recarregue.
        </p>
      )}

      {data && (
        <>
          <AccuracyStrip meta={data.meta} />

          <Tabs
            tab={tab}
            onChange={abrirAba}
            abas={ABAS}
          />

          <div
            id="panel"
            role="tabpanel"
            aria-labelledby={`tab-${tab}`}
            className="panel"
          >
            {tab === 'tabela' ? (
              <FutebolTabela data={data} />
            ) : tab === 'previsao' ? (
              <FutebolPrevisao data={data} />
            ) : (
              <FutebolJogos
                key={lid}
                data={data}
                rodada={route[2]}
                onSelect={(r) =>
                  navigate(
                    'futebol',
                    lid,
                    'jogos',
                    r
                  )
                }
              />
            )}
          </div>

          <Notice meta={data.meta} />
        </>
      )}
    </>
  );
}
