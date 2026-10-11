import { pct, record } from '../lib/format.js';

// Colunas = total de vitórias no fim da temporada regular. Altura = chance (%).
export default function WinChart({ p }) {
  const linhas = p.dist.map((x, k) => ({ w: p.v + k, x }));
  let a = 0;
  let b = linhas.length - 1;
  while (a < b && linhas[a].x < 0.001) a++;
  while (b > a && linhas[b].x < 0.001) b--;
  const R = linhas.slice(a, b + 1);

  const max = Math.max(...R.map((r) => r.x));
  const topPct = Math.ceil((max * 100) / 5) * 5;
  const passo = topPct > 20 ? 10 : 5;
  const topo = Math.ceil(topPct / passo) * passo;
  const altura = (x) => (x * 10000) / topo; // % da altura do gráfico
  const moda = p.moda[0];
  const derrotas = (w) => p.v + p.d + p.n_rest - w;

  const marcas = [];
  for (let v = passo; v <= topo; v += passo) marcas.push(v);

  return (
    <>
      <div className="chart">
        <div className="yax">
          {marcas.map((v) => (
            <span key={v} style={{ bottom: `${(v / topo) * 100}%` }}>{v}%</span>
          ))}
        </div>
        <div className="plot">
          {marcas.map((v) => (
            <div key={v} className="gl" style={{ bottom: `${(v / topo) * 100}%` }} />
          ))}
          {R.map((r) => {
            const cls = r.w === moda ? 'mode' : r.w >= p.faixa[0] && r.w <= p.faixa[1] ? 'in' : '';
            return (
              <div key={r.w} className={`col ${cls}`} tabIndex={0} role="img" aria-label={`${r.w} vitórias: ${pct(r.x, 1)}`}>
                <i style={{ height: `${altura(r.x)}%` }} />
                {r.w === moda && <em style={{ bottom: `${altura(r.x)}%` }}>{pct(r.x, 0)}</em>}
                <span className="tip" style={{ bottom: `${altura(r.x)}%` }}>
                  <b>{pct(r.x, 1)}</b> de chance
                  <br />
                  {r.w} vitórias ({record(r.w, derrotas(r.w), p.e)})
                </span>
              </div>
            );
          })}
        </div>
        <div className="xax">
          {R.map((r) => (
            <span key={r.w}>{r.w}</span>
          ))}
        </div>
        <div className="xtitle">Vitórias no fim da temporada regular</div>
      </div>
      <div className="key">
        <span><i style={{ background: 'var(--accent)' }} />Mais provável</span>
        <span><i style={{ background: 'var(--accent-mid)' }} />Faixa provável de 80%</span>
        <span><i style={{ background: 'var(--accent-soft)' }} />Demais</span>
      </div>
      <details className="table-v">
        <summary>Ver em tabela</summary>
        <div className="table-wrap">
          <table>
            <thead>
              <tr><th>Total</th><th>Recorde</th><th className="n">Chance</th></tr>
            </thead>
            <tbody>
              {R.map((r) => (
                <tr key={r.w}>
                  <td>{r.w} vitórias</td>
                  <td>{record(r.w, derrotas(r.w), p.e)}</td>
                  <td className="n">{pct(r.x, 1)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </details>
    </>
  );
}
