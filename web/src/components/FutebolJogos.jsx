import { Fragment, useEffect, useRef, useState } from 'react';
import NoticiasLista from './NoticiasLista.jsx';
import { dayLong, dayShort, num1, pct } from '../lib/format.js';

const IconOk = () => (<svg viewBox="0 0 24 24" aria-hidden="true"><path d="M5 12.5l4.5 4.5L19 7.5" /></svg>);
const IconNo = () => (<svg viewBox="0 0 24 24" aria-hidden="true"><path d="M6 6l12 12M18 6L6 18" /></svg>);

const palpiteDe = (p) => p.indexOf(Math.max(...p)); // 0 casa, 1 empate, 2 fora

function Linha({ time, codigo, lado, gols, vence }) {
  return (
    <div className={`tm ${vence ? 'win' : ''}`}>
      <div className="badge" aria-hidden="true">{codigo}</div>
      <div className="nm">{time.nome}<small>{lado}</small></div>
      {gols != null && <div className="score">{gols}</div>}
    </div>
  );
}

function Forma({ lista }) {
  if (!lista?.length) return <b>sem jogos ainda</b>;
  return (
    <span className="forma" style={{ margin: 0 }}>
      {lista.map((r, i) => (<span key={i} className={`c ${r}`}>{r}</span>))}
    </span>
  );
}

function Cartao({ g, times }) {
  const [aberto, setAberto] = useState(false);
  const c = times[g.c];
  const f = times[g.f];
  const tem = g.p != null;
  const pal = tem ? palpiteDe(g.p) : null;
  const jogado = g.pl != null;
  const venc = jogado ? (g.pl[0] > g.pl[1] ? 'c' : g.pl[0] < g.pl[1] ? 'f' : 'e') : null;
  const nomePal = pal === 0 ? c.nome : pal === 2 ? f.nome : 'Empate';
  const quando = g.h ? `${dayShort(g.d)} · ${g.h}` : `${dayShort(g.d)} · horário a definir`;
  const aria = tem
    ? `${c.nome} contra ${f.nome}. Chances: ${c.nome} ${pct(g.p[0])}, empate ${pct(g.p[1])}, ${f.nome} ${pct(g.p[2])}.`
    : `${c.nome} contra ${f.nome}`;
  const acertou = g.ok;

  return (
    <article className="game fut" aria-label={aria}>
      <div className="g-top">
        <span>{quando}</span>
        {g.adiado && <span className="tag" title="O jogo foi adiado e a nova data ainda não saiu.">adiado</span>}
        {g.nt && <span className="tag news" title="A previsão foi ajustada por uma notícia (veja em Ver detalhes).">notícia considerada</span>}
      </div>
      <Linha time={c} codigo={g.c} lado="mandante" gols={jogado ? g.pl[0] : null} vence={venc === 'c'} />
      <Linha time={f} codigo={g.f} lado="visitante" gols={jogado ? g.pl[1] : null} vence={venc === 'f'} />
      {tem ? (
        <>
          <div className="tri" role="img" aria-label={`${c.nome} ${pct(g.p[0])}, empate ${pct(g.p[1])}, ${f.nome} ${pct(g.p[2])}`}>
            <i className={pal === 0 ? 'fav' : ''} style={{ flex: g.p[0] * 100 }} />
            <i className={`emp ${pal === 1 ? 'fav' : ''}`} style={{ flex: g.p[1] * 100 }} />
            <i className={pal === 2 ? 'fav' : ''} style={{ flex: g.p[2] * 100 }} />
          </div>
          <div className="tri-l" aria-hidden="true">
            <span className={pal === 0 ? 'on' : ''}>{pct(g.p[0])}</span>
            <span className={pal === 1 ? 'on' : ''}>empate {pct(g.p[1])}</span>
            <span className={pal === 2 ? 'on' : ''}>{pct(g.p[2])}</span>
          </div>
          <div className="pick">
            <span>Palpite <b>{nomePal}</b>{g.es && ` · placar provável ${g.es[0]}–${g.es[1]}`}</span>
            {jogado && (acertou ? (<span className="res ok"><IconOk /> Acertou</span>) : (<span className="res no"><IconNo /> Errou</span>))}
          </div>
        </>
      ) : (
        <div className="pick" style={{ marginTop: 8 }}>Sem previsão disponível</div>
      )}
      <button className="more" onClick={() => setAberto(!aberto)} aria-expanded={aberto}>{aberto ? 'Ocultar detalhes' : 'Ver detalhes'}</button>
      {aberto && (
        <div className="det">
          {g.g && <div><span>Gols esperados</span><b>{c.nome} {num1(g.g[0])} · {f.nome} {num1(g.g[1])}</b></div>}
          <div><span>Força (Elo)</span><b>{c.nome} {c.elo} · {f.nome} {f.elo}</b></div>
          <div><span>{c.nome}, últimos jogos</span><Forma lista={c.forma} /></div>
          <div><span>{f.nome}, últimos jogos</span><Forma lista={f.forma} /></div>
          {jogado && <div><span>Resultado</span><b>{g.pl[0]} a {g.pl[1]}</b></div>}
        </div>
      )}
      {aberto && <NoticiasLista nt={g.nt} nomeDe={(c) => times[c]?.nome ?? c} />}
    </article>
  );
}

export default function FutebolJogos({ data, rodada, onSelect }) {
  const { meta, rodadas, times } = data;
  const chaves = Object.keys(rodadas);
  const atual = String(meta.semana_atual);
  const chave = rodadas[rodada] ? rodada : rodadas[atual] ? atual : chaves[0];
  const jogos = rodadas[chave];
  const chipsRef = useRef(null);
  useEffect(() => {
    chipsRef.current?.querySelector('[aria-pressed=true]')?.scrollIntoView({ inline: 'center', block: 'nearest' });
  }, [chave]);

  const feitos = jogos.filter((g) => g.pl);
  const aval = feitos.filter((g) => g.ok != null);
  const acertos = aval.filter((g) => g.ok).length;
  let resumo;
  if (!feitos.length) resumo = `${jogos.length} jogos · horários de Brasília`;
  else if (feitos.length < jogos.length) resumo = `${feitos.length} de ${jogos.length} já disputados · acertos até agora: ${acertos} de ${aval.length}`;
  else resumo = `Acertamos ${acertos} de ${aval.length} (${pct(acertos / Math.max(aval.length, 1))}) · palpites feitos só com dados anteriores a cada jogo`;

  let ultimo = '';
  const cartoes = jogos.map((g) => {
    const novo = g.d !== ultimo;
    ultimo = g.d;
    return (
      <Fragment key={g.id}>
        {novo && <div className="day">{dayLong(g.d)}</div>}
        <Cartao g={g} times={times} />
      </Fragment>
    );
  });

  return (
    <>
      <div className="ctrls">
        <div className="weeks" role="group" aria-label="Rodada" ref={chipsRef}>
          {chaves.map((k) => (
            <button key={k} className={k === atual ? 'now' : ''} aria-pressed={k === chave} aria-label={`Rodada ${k}${k === atual ? ' (atual)' : ''}`} onClick={() => onSelect(k)}>
              {k}
            </button>
          ))}
        </div>
      </div>
      <div className="wk-head">
        <div>
          <h2>Rodada {chave} · {meta.nome}</h2>
          <div className="sum">{resumo}</div>
        </div>
        <span className="tag" title="Todos os horários desta página estão no horário de Brasília.">Horário de Brasília</span>
      </div>
      <div className="games">{cartoes}</div>
    </>
  );
}
