import { num1, record } from '../lib/format.js';

const DIVS = ['Leste', 'Norte', 'Sul', 'Oeste'];
const pctV = (v, d, e) => (v + d + e ? (v + e / 2) / (v + d + e) : 0);

function Divisao({ conf, div, data, onTeam }) {
  const { times, projecoes } = data;
  const lista = Object.keys(times)
    .filter((c) => times[c].conf === conf && times[c].div === div)
    .sort((a, b) => {
      const pa = projecoes[a], pb = projecoes[b];
      return pctV(pb.v, pb.d, pb.e) - pctV(pa.v, pa.d, pa.e) || (pb.esperado ?? pb.v) - (pa.esperado ?? pa.v);
    });
  return (
    <div className="card">
      <h3>{conf} {div}</h3>
      <div className="table-wrap">
        <table className="tabela tbl-liga">
          <thead>
            <tr>
              <th>#</th><th>Time</th>
              <th className="n" title="Campanha até agora">Recorde</th>
              <th className="n" title="Vitórias esperadas no fim da temporada regular">Previsto</th>
              <th className="n hide-sm" title="Faixa em que ficam 80% das projeções">Faixa (80%)</th>
            </tr>
          </thead>
          <tbody>
            {lista.map((c, i) => {
              const p = projecoes[c];
              const total = p.v + p.d + p.e + (p.n_rest || 0);
              return (
                <tr key={c} className={i === 0 ? 'z-topo' : ''}>
                  <td className="pos">{i + 1}</td>
                  <td>
                    <button className="lnk" onClick={() => onTeam(c)}>
                      <span className="badge sm" aria-hidden="true">{c}</span>{times[c].apelido}
                    </button>
                  </td>
                  <td className="n">{record(p.v, p.d, p.e)}</td>
                  <td className="n"><b>{p.esperado != null ? `${num1(p.esperado)}–${num1(total - p.esperado)}` : record(p.v, p.d, p.e)}</b></td>
                  <td className="n hide-sm">{p.faixa ? `${p.faixa[0]} a ${p.faixa[1]} vitórias` : '—'}</td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>
    </div>
  );
}

export default function TabelaNfl({ data, onTeam }) {
  return (
    <>
      <p className="note">
        Classificação por divisão, ordenada pela campanha de hoje. “Previsto” é o recorde esperado no fim da temporada regular
        (jogos já feitos mais as chances do modelo para os que faltam). O líder de cada divisão tem a barra azul. Não simulamos os
        playoffs da NFL ainda; essa é uma das próximas etapas.
      </p>
      {['AFC', 'NFC'].map((conf) => (
        <div key={conf} className="conf-bloco">
          <h2 className="conf-t">{conf}</h2>
          <div className="div-grid">
            {DIVS.map((d) => (<Divisao key={d} conf={conf} div={d} data={data} onTeam={onTeam} />))}
          </div>
        </div>
      ))}
    </>
  );
}
