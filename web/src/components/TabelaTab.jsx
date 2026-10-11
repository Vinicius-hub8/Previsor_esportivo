import { useState } from 'react';
import { pct, record } from '../lib/format.js';

const CONFS = ['Leste', 'Oeste'];
const PCT = (x) => (x < 0.005 ? '<1%' : x > 0.995 ? '>99%' : pct(x, 0));

function Celula({ x }) {
  return (
    <td className="pc n" style={{ '--w': `${Math.round(x * 100)}%` }}>
      {PCT(x)}
    </td>
  );
}

function Campeoes({ data }) {
  const [todos, setTodos] = useState(false);
  const { times, simulacao } = data;
  const lista = Object.keys(times).sort((a, b) => simulacao.times[b].tit - simulacao.times[a].tit);
  const topo = simulacao.times[lista[0]].tit || 1;
  return (
    <div className="card">
      <h3>Quem tem mais chance de ser campeão</h3>
      <div className="rank">
        {(todos ? lista : lista.slice(0, 8)).map((c, i) => {
          const x = simulacao.times[c].tit;
          return (
            <div className="rk" key={c}>
              <span className="pos">{i + 1}</span>
              <span className="nm">{times[c].apelido}</span>
              <span className="trk" role="img" aria-label={`${times[c].nome}: ${PCT(x)} de chance de título`}>
                <i style={{ width: `${(x / topo) * 100}%` }} />
              </span>
              <b>{PCT(x)}</b>
            </div>
          );
        })}
      </div>
      <button className="more" onClick={() => setTodos(!todos)} aria-expanded={todos}>
        {todos ? 'Mostrar só os 8 primeiros' : `Ver os ${lista.length} times`}
      </button>
    </div>
  );
}

function Conferencia({ conf, data, onTeam }) {
  const { times, simulacao, projecoes } = data;
  const total = (c) => projecoes[c].v + projecoes[c].d + (projecoes[c].n_rest || 0);
  const lista = Object.keys(times)
    .filter((c) => times[c].conf === conf)
    .sort((a, b) => simulacao.times[b].v - simulacao.times[a].v);
  return (
    <div className="card">
      <h3>Conferência {conf}: classificação simulada</h3>
      <div className="table-wrap">
        <table className="tabela">
          <thead>
            <tr>
              <th>#</th>
              <th>Time</th>
              <th className="n">Recorde</th>
              <th className="n" title="Chance de terminar entre os 6 primeiros">Top 6</th>
              <th className="n" title="Chance de estar nos playoffs (direto ou pelo play-in)">Playoffs</th>
              <th className="n">Final</th>
              <th className="n">Título</th>
            </tr>
          </thead>
          <tbody>
            {lista.map((c, i) => {
              const s = simulacao.times[c];
              const v = Math.round(s.v);
              return (
                <tr key={c} className={i === 6 || i === 10 ? 'corte' : ''}>
                  <td className="pos">{i + 1}</td>
                  <td>
                    <button className="lnk" onClick={() => onTeam(c)}>
                      <span className="badge sm" aria-hidden="true">{c}</span>
                      {times[c].apelido}
                    </button>
                  </td>
                  <td className="n">{record(v, total(c) - v)}</td>
                  <Celula x={s.dir} />
                  <Celula x={s.pof} />
                  <Celula x={s.fin} />
                  <Celula x={s.tit} />
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>
      <p className="note" style={{ marginTop: 8 }}>
        1º a 6º vão direto aos playoffs; 7º a 10º disputam o play-in. As linhas separam essas zonas.
      </p>
    </div>
  );
}

export default function TabelaTab({ data, onTeam }) {
  const n = data.simulacao.n.toLocaleString('pt-BR');
  return (
    <>
      <p className="note">
        Simulamos a temporada {n} vezes com as chances do modelo: jogos restantes, classificação, play-in e playoffs em séries
        melhor de 7. O resultado é um cenário, não uma previsão exata. Para refletir a incerteza, cada simulação sorteia também
        quanto a força de cada time pode mudar (lesões, trocas, evolução), e isso pesa mais no começo do ano.
      </p>
      <Campeoes data={data} />
      {CONFS.map((c) => (
        <Conferencia key={c} conf={c} data={data} onTeam={onTeam} />
      ))}
    </>
  );
}
