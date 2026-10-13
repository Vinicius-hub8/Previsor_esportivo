import { pct } from '../lib/format.js';

export function ZonaLegenda({ meta }) {
  return (
    <div className="key">
      <span><i style={{ background: 'var(--accent)' }} /> Vaga continental (top {meta.topo}, simplificado)</span>
      <span><i style={{ background: 'var(--bad)' }} /> Rebaixamento ({meta.rebaixa} últimos)</span>
    </div>
  );
}

export const zonaDe = (i, total, meta) => (i < meta.topo ? 'z-topo' : i >= total - meta.rebaixa ? 'z-reb' : '');

export default function FutebolTabela({ data }) {
  const { meta, tabela, times } = data;
  const feitos = Math.max(...tabela.map((L) => L.j));
  return (
    <div className="card">
      <h3>Tabela atual · {meta.nome} {meta.temporada_rotulo}</h3>
      <div className="table-wrap">
        <table className="tabela tbl-liga">
          <caption className="sr">Classificação depois de {feitos} rodadas</caption>
          <thead>
            <tr>
              <th>#</th>
              <th>Time</th>
              <th className="n" title="Pontos">Pts</th>
              <th className="n" title="Jogos">J</th>
              <th className="n" title="Vitórias">V</th>
              <th className="n hide-sm" title="Empates">E</th>
              <th className="n hide-sm" title="Derrotas">D</th>
              <th className="n hide-sm" title="Gols marcados">GP</th>
              <th className="n hide-sm" title="Gols sofridos">GC</th>
              <th className="n" title="Saldo de gols">SG</th>
              <th className="hide-sm" title="Últimos 5 jogos">Últimos 5</th>
            </tr>
          </thead>
          <tbody>
            {tabela.map((L, i) => (
              <tr key={L.t} className={zonaDe(i, tabela.length, meta)}>
                <td className="pos">{i + 1}</td>
                <td><span className="lnk"><span className="badge sm" aria-hidden="true">{L.t}</span>{times[L.t].nome}</span></td>
                <td className="n"><b>{L.pts}</b></td>
                <td className="n">{L.j}</td>
                <td className="n">{L.v}</td>
                <td className="n hide-sm">{L.e}</td>
                <td className="n hide-sm">{L.d}</td>
                <td className="n hide-sm">{L.gp}</td>
                <td className="n hide-sm">{L.gc}</td>
                <td className="n">{L.sg > 0 ? `+${L.sg}` : L.sg}</td>
                <td className="hide-sm">
                  <span className="forma" style={{ margin: 0 }}>
                    {L.forma.map((r, k) => (<span key={k} className={`c ${r}`}>{r}</span>))}
                  </span>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      <ZonaLegenda meta={meta} />
      <p className="note" style={{ marginTop: 8 }}>
        Desempate: {meta.desempate_vitorias ? 'pontos, vitórias, saldo de gols e gols marcados' : 'pontos, saldo de gols e gols marcados'}.
        Confronto direto não é considerado{meta.repescagem ? '. O 16º colocado disputa uma repescagem, que não está marcada aqui' : ''}.
        Baseada nos jogos já disputados ({pct(tabela.reduce((a, L) => a + L.j, 0) / (tabela.length * (meta.n_rodadas || 1)), 0)} da temporada).
      </p>
    </div>
  );
}
