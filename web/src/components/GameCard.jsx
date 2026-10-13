import { useState } from 'react';
import NoticiasLista from './NoticiasLista.jsx';
import { confLabel, dayShort, num1, pct } from '../lib/format.js';

const IconOk = () => (
  <svg viewBox="0 0 24 24" aria-hidden="true"><path d="M5 12.5l4.5 4.5L19 7.5" /></svg>
);
const IconNo = () => (
  <svg viewBox="0 0 24 24" aria-hidden="true"><path d="M6 6l12 12M18 6L6 18" /></svg>
);

function TeamRow({ lado, codigo, time, p, placar, favorito, vencedor }) {
  return (
    <div className={`tm ${vencedor === lado ? 'win' : ''}`}>
      <div className="badge" aria-hidden="true">{codigo}</div>
      <div className="nm">
        {time.apelido}
        <small>{lado === 'v' ? 'visitante' : 'mandante'}</small>
      </div>
      {placar != null ? (
        <div className="score">{placar}</div>
      ) : p != null ? (
        <div className={`pct ${favorito === lado ? '' : 'dim'}`}>{pct(p)}</div>
      ) : null}
    </div>
  );
}

function Resultado({ g }) {
  if (!g.placar) return null;
  if (g.aoVivo) return <span className="res na">em andamento</span>;
  if (g.ok == null) return <span className="res na">{g.p == null ? 'sem palpite' : 'empate'}</span>;
  return g.ok ? (
    <span className="res ok"><IconOk /> Acertou</span>
  ) : (
    <span className="res no"><IconNo /> Errou</span>
  );
}

const diasTxt = (d) => (d <= 1 ? 'jogo em dia seguido (back-to-back)' : d >= 7 ? '7 dias ou mais' : `${d} dias`);

// Detalhes da NBA: sem linha de aposta, mostra Elo, saldo médio recente e descanso.
function DetalhesSemLinha({ g, v, m }) {
  const forma = (i) =>
    g.nj[i] === 0 ? 'ainda sem jogos nesta temporada' : `saldo médio ${g.forma[i] > 0 ? '+' : ''}${num1(g.forma[i])} pts (${g.nj[i]} jogos)`;
  return (
    <div className="det">
      {g.elo != null && (
        <div>
          <span>Força (Elo)</span>
          <b>{g.elo === 0 ? 'iguais' : `${(g.elo > 0 ? m : v).apelido} +${Math.abs(g.elo)}`}</b>
        </div>
      )}
      <div><span>{v.apelido}, jogos recentes</span><b>{forma(0)}</b></div>
      <div><span>{m.apelido}, jogos recentes</span><b>{forma(1)}</b></div>
      <div><span>Descanso</span><b>{v.apelido}: {diasTxt(g.desc[0])} · {m.apelido}: {diasTxt(g.desc[1])}</b></div>
    </div>
  );
}

function Detalhes({ g, v, m }) {
  const sp = g.spread;
  const linha =
    sp == null ? 'Sem linha divulgada' : sp === 0 ? 'Jogo sem favorito na linha' : `${(sp > 0 ? m : v).apelido} favorito por ${num1(Math.abs(sp))} pts`;
  return (
    <div className="det">
      <div><span>Linha de aposta</span><b>{linha}</b></div>
      {g.elo != null && (
        <div>
          <span>Força (Elo)</span>
          <b>{g.elo === 0 ? 'iguais' : `${(g.elo > 0 ? m : v).apelido} +${Math.abs(g.elo)}`}</b>
        </div>
      )}
      {g.pf && (
        <>
          <div><span>{v.apelido}, últimos 5</span><b>{num1(g.pf[0])} feitos · {num1(g.pf[1])} sofridos</b></div>
          <div><span>{m.apelido}, últimos 5</span><b>{num1(g.pf[2])} feitos · {num1(g.pf[3])} sofridos</b></div>
        </>
      )}
    </div>
  );
}

export default function GameCard({ g, times, usaLinha = true }) {
  const [aberto, setAberto] = useState(false);
  const v = times[g.v];
  const m = times[g.m];
  const tem = g.p != null;
  const pm = tem ? g.p : null;
  const pv = tem ? 1 - g.p : null;
  const favorito = tem ? (pm >= 0.5 ? 'm' : 'v') : null;
  const q = tem ? Math.max(pm, pv) : 0;
  const vencedor = g.placar && !g.aoVivo ? (g.placar[1] > g.placar[0] ? 'm' : g.placar[0] > g.placar[1] ? 'v' : 'e') : null;
  const nomeFav = favorito === 'm' ? m : v;
  const aria = tem
    ? `${v.nome} contra ${m.nome}. Palpite: ${nomeFav.nome}, ${pct(q)}.`
    : `${v.nome} contra ${m.nome}`;

  return (
    <article className="game" aria-label={aria}>
      <div className="g-top">
        <span>{dayShort(g.db ?? g.data)}{g.hb ? ` · ${g.hb}` : g.hora && !g.db ? ` · ${g.hora} ET` : ''}</span>
        {g.aoVivo && (
          <span className="tag live" aria-live="polite">
            <i aria-hidden="true" /> AO VIVO{g.detalhe ? ` · ${g.detalhe}` : ''}
          </span>
        )}
        {g.nt && <span className="tag news" title="A previsão foi ajustada por uma notícia (veja em Ver detalhes).">notícia considerada</span>}
        {usaLinha && !g.linha && tem && !g.placar && (
          <span className="tag" title="A linha de aposta ainda não foi divulgada; o palpite usa o modelo sem ela.">
            sem linha de aposta
          </span>
        )}
      </div>
      <TeamRow lado="v" codigo={g.v} time={v} p={pv} placar={g.placar?.[0]} favorito={favorito} vencedor={vencedor} />
      <TeamRow lado="m" codigo={g.m} time={m} p={pm} placar={g.placar?.[1]} favorito={favorito} vencedor={vencedor} />
      {tem ? (
        <>
          <div className="split" role="img" aria-label={`${v.apelido} ${pct(pv)}, ${m.apelido} ${pct(pm)}`}>
            <i className={favorito === 'v' ? 'fav' : ''} style={{ flex: pv * 100 }} />
            <i className={favorito === 'm' ? 'fav' : ''} style={{ flex: pm * 100 }} />
          </div>
          <div className="pick">
            <span>
              Palpite <b>{nomeFav.apelido}</b> · {pct(q)} · {confLabel(q)}
              {g.ps && <> · placar previsto {g.ps[0]}–{g.ps[1]}</>}
            </span>
            <Resultado g={g} />
          </div>
        </>
      ) : (
        <div className="pick" style={{ marginTop: 8 }}>{g.placar ? <Resultado g={g} /> : 'Sem previsão disponível'}</div>
      )}
      <button className="more" onClick={() => setAberto(!aberto)} aria-expanded={aberto}>
        {aberto ? 'Ocultar detalhes' : 'Ver detalhes'}
      </button>
      {aberto && (usaLinha ? <Detalhes g={g} v={v} m={m} /> : <DetalhesSemLinha g={g} v={v} m={m} />)}
      {aberto && <NoticiasLista nt={g.nt} nomeDe={(c) => times[c]?.apelido ?? c} />}
    </article>
  );
}
