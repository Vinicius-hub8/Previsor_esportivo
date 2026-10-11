import { useMemo } from 'react';
import WinChart from './WinChart.jsx';
import RestGames from './RestGames.jsx';
import { num1, pct, record, usaLinha } from '../lib/format.js';
import { store } from '../lib/store.js';

const GRUPOS_NFL = ['AFC Leste', 'AFC Norte', 'AFC Sul', 'AFC Oeste', 'NFC Leste', 'NFC Norte', 'NFC Sul', 'NFC Oeste'];

export default function TeamTab({ data, code, onSelect }) {
  const { meta, times, projecoes } = data;
  const grupos = meta.grupos ?? GRUPOS_NFL;
  const codigos = Object.keys(times);
  const maisForte = useMemo(() => [...codigos].sort((a, b) => times[a].elo_rank - times[b].elo_rank)[0], [times]); // eslint-disable-line react-hooks/exhaustive-deps
  const salvo = store.get('pv_team');
  const sigla = times[code] ? code : times[salvo] ? salvo : maisForte;
  const t = times[sigla];
  const p = projecoes[sigla];

  return (
    <>
      <div className="picker">
        <label htmlFor="team">Time</label>
        <select id="team" value={sigla} onChange={(e) => onSelect(e.target.value)}>
          {grupos.map((g) => (
            <optgroup key={g} label={g}>
              {codigos
                .filter((c) => `${times[c].conf} ${times[c].div}` === g)
                .sort((a, b) => times[a].nome.localeCompare(times[b].nome))
                .map((c) => (
                  <option key={c} value={c}>{times[c].nome}</option>
                ))}
            </optgroup>
          ))}
        </select>
      </div>

      <div className="team-head">
        <div className="badge" aria-hidden="true">{sigla}</div>
        <div>
          <h2>{t.nome}</h2>
          <p>
            {t.conf} {t.div} · Poder #{t.elo_rank} de {codigos.length} (Elo {t.elo}) · o modelo acertou {pct(t.acc, 1)} dos jogos desse time desde {meta.anos_ref[0]} ({t.acc_n} jogos)
          </p>
        </div>
        <div className="forma" aria-label="Últimos 5 jogos">
          Últimos 5
          {t.forma.map((r, i) => (
            <span key={i} className={`c ${r}`} title={{ V: 'Vitória', D: 'Derrota', E: 'Empate' }[r]}>{r}</span>
          ))}
        </div>
      </div>

      {!p.n_rest ? (
        <div className="card">
          <h3>Temporada regular</h3>
          <p className="note">Este time já terminou a temporada regular com {record(p.v, p.d, p.e)}.</p>
        </div>
      ) : (
        <>
          <div className="proj">
            <div className="card">
              <h3>Recorde projetado</h3>
              <div className="big" aria-label={`Recorde mais provável ${record(p.moda[0], p.moda[1], p.e)}`}>
                {record(p.moda[0], p.moda[1], p.e)}
              </div>
              <div className="kv">
                <div><span>Recorde atual</span><b>{record(p.v, p.d, p.e)}</b></div>
                <div><span>Vitórias esperadas</span><b>{num1(p.esperado)}</b></div>
                <div><span>Faixa provável (80%)</span><b>{p.faixa[0]} a {p.faixa[1]} vitórias</b></div>
                <div><span>Jogos restantes</span><b>{p.n_rest}</b></div>
              </div>
              {p.n_sem_data > 0 && (
                <p className="note" style={{ marginTop: 10 }}>
                  O calendário ainda não define {p.n_sem_data} jogos deste time (ligados à NBA Cup). Eles entram na conta com a chance média do time nos jogos já marcados.
                </p>
              )}
            </div>
            <div className="card">
              <h3>Chance de cada total de vitórias</h3>
              <WinChart p={p} />
            </div>
          </div>
          <RestGames p={p} times={times} usaLinha={usaLinha(meta)} />
        </>
      )}
    </>
  );
}
