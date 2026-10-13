import { useState } from 'react';
import { pct, num1 } from '../lib/format.js';
import { ZonaLegenda, zonaDe } from './FutebolTabela.jsx';

const PCT = (x) => (x < 0.005 ? '<1%' : x > 0.995 ? '>99%' : pct(x, 0));

function Celula({ x }) {
  return <td className="pc n" style={{ '--w': `${Math.round(x * 100)}%` }}>{PCT(x)}</td>;
}

function Favoritos({ data }) {
  const { times, previsao } = data;
  const [todos, setTodos] = useState(false);
  const lista = [...previsao.times].sort((a, b) => b.tit - a.tit).filter((x) => todos || x.tit >= 0.005);
  const topo = lista[0]?.tit || 1;
  return (
    <div className="card">
      <h3>Quem tem mais chance de ser campeão</h3>
      <div className="rank">
        {lista.slice(0, todos ? 99 : 8).map((x, i) => (
          <div className="rk" key={x.t}>
            <span className="pos">{i + 1}</span>
            <span className="nm">{times[x.t].nome}</span>
            <span className="trk" role="img" aria-label={`${times[x.t].nome}: ${PCT(x.tit)} de chance de título`}><i style={{ width: `${(x.tit / topo) * 100}%` }} /></span>
            <b>{PCT(x.tit)}</b>
          </div>
        ))}
      </div>
      <button className="more" onClick={() => setTodos(!todos)} aria-expanded={todos}>{todos ? 'Mostrar menos' : 'Ver todos os times'}</button>
    </div>
  );
}

function MapaPosicoes({ data }) {
  const { times, previsao } = data;
  const N = previsao.times.length;
  return (
    <details className="card table-v">
      <summary>Chance de cada posição final</summary>
      <div className="table-wrap">
        <table className="mapa">
          <thead>
            <tr><th>Time</th>{Array.from({ length: N }, (_, i) => (<th key={i} className="n">{i + 1}º</th>))}</tr>
          </thead>
          <tbody>
            {previsao.times.map((x) => (
              <tr key={x.t}>
                <td className="nm">{times[x.t].nome}</td>
                {x.dist.map((p, i) => (
                  <td key={i} className="n" style={{ '--a': p }} title={`${times[x.t].nome} terminar em ${i + 1}º: ${PCT(p)}`}>
                    {p >= 0.1 ? Math.round(p * 100) : ''}
                  </td>
                ))}
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      <p className="note" style={{ marginTop: 8 }}>Cada linha soma 100%. Os números dentro das células são porcentagens (só aparecem as de 10% ou mais).</p>
    </details>
  );
}

export default function FutebolPrevisao({ data }) {
  const { meta, previsao, times } = data;
  const total = previsao.times.length;
  return (
    <>
      <p className="note">
        Simulamos o resto da temporada {previsao.n.toLocaleString('pt-BR')} vezes: os {previsao.n_rest} jogos que faltam são sorteados com as
        chances do modelo (vitória, empate e derrota, com gols) e, para refletir a incerteza, cada simulação também sorteia o quanto a força de
        cada time pode mudar. O resultado é um cenário, não uma previsão exata.
      </p>
      <Favoritos data={data} />
      <div className="card">
        <h3>Tabela prevista · {meta.nome} {meta.temporada_rotulo}</h3>
        <div className="table-wrap">
          <table className="tabela tbl-liga">
            <caption className="sr">Tabela prevista no fim da temporada</caption>
            <thead>
              <tr>
                <th>#</th>
                <th>Time</th>
                <th className="n" title="Pontos de hoje">Hoje</th>
                <th className="n" title="Pontos esperados no fim da temporada (média das simulações)">Pts previstos</th>
                <th className="n hide-sm" title="Faixa em que ficam 80% das simulações">Faixa (80%)</th>
                <th className="n" title="Chance de ser campeão">Título</th>
                <th className="n" title={`Chance de terminar entre os ${meta.topo} primeiros`}>Top {meta.topo}</th>
                <th className="n" title={`Chance de terminar entre os ${meta.rebaixa} últimos`}>Rebaixa</th>
              </tr>
            </thead>
            <tbody>
              {previsao.times.map((x, i) => (
                <tr key={x.t} className={zonaDe(i, total, meta)}>
                  <td className="pos">{i + 1}</td>
                  <td><span className="lnk"><span className="badge sm" aria-hidden="true">{x.t}</span>{times[x.t].nome}</span></td>
                  <td className="n">{x.pts}</td>
                  <td className="n"><b>{Math.round(x.esp)}</b></td>
                  <td className="n hide-sm">{x.faixa[0]}–{x.faixa[1]}</td>
                  <Celula x={x.tit} />
                  <Celula x={x.topo} />
                  <Celula x={x.reb} />
                </tr>
              ))}
            </tbody>
          </table>
        </div>
        <ZonaLegenda meta={meta} />
        <p className="note" style={{ marginTop: 8 }}>
          A ordem é pela média de pontos das simulações (média de posição: {num1(previsao.times[0].pos)} para o 1º da lista). Faltam {previsao.n_rest} jogos.
        </p>
      </div>
      <MapaPosicoes data={data} />
    </>
  );
}
