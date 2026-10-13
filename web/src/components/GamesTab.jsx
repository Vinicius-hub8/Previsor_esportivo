import { Fragment, useEffect, useRef, useState } from 'react';
import GameCard from './GameCard.jsx';
import { dayLong, pct, rotTemp, usaLinha } from '../lib/format.js';
import { aplicarAoVivo, chaveEspn } from '../lib/aoVivo.js';

// Data e hora de Brasília (o Python manda db/hb); se faltarem, usa a data original.
const diaDe = (g) => g.db ?? g.data;
const horaDe = (g) => g.hb ?? '99:99';
const porHorario = (a, b) => (diaDe(a) + horaDe(a) + a.id).localeCompare(diaDe(b) + horaDe(b) + b.id);
const confianca = (g) => (g.p == null ? 0 : Math.max(g.p, 1 - g.p));
// Texto curto do botão da semana: o JSON pode trazer "curto"; senão (NFL) usa o número ou a sigla da fase.
const rotuloSemana = (w, info) =>
  info.curto ?? (info.tipo === 'REG' ? w : { WC: 'Wild Card', DIV: 'Divisional', CON: 'Conf.', SB: 'Super Bowl' }[info.tipo] || w);

export default function GamesTab({ data, live, season, week, onSelect }) {
  const { meta, semanas, times } = data;
  const temporadas = Object.keys(semanas).sort().reverse();
  const seasonKey = semanas[season] ? season : String(meta.temporada);
  const weeks = semanas[seasonKey];
  const semanaPadrao = seasonKey === String(meta.temporada) ? String(meta.semana_atual) : Object.keys(weeks)[0];
  const linha = usaLinha(meta);
  const weekKey = weeks[week] ? week : weeks[semanaPadrao] ? semanaPadrao : Object.keys(weeks)[0];
  const info = weeks[weekKey];

  const [ordem, setOrdem] = useState('data');
  const chipsRef = useRef(null);
  useEffect(() => {
    chipsRef.current?.querySelector('[aria-pressed=true]')?.scrollIntoView({ inline: 'center', block: 'nearest' });
  }, [seasonKey, weekKey]);

  // mescla o placar ao vivo (se houver) nos jogos desta semana
  const todos = info.jogos.map((g) => aplicarAoVivo(g, live?.[chaveEspn(g)]));
  const jogos = todos.slice().sort(porHorario);
  if (ordem === 'conf') jogos.sort((a, b) => confianca(b) - confianca(a));

  const feitos = todos.filter((g) => g.placar && !g.aoVivo);
  const avaliados = feitos.filter((g) => g.ok != null);
  const acertos = avaliados.filter((g) => g.ok).length;
  let resumo;
  const aoVivoN = todos.filter((g) => g.aoVivo).length;
  if (!feitos.length) resumo = `${todos.length} jogos · palpites ainda sem resultado`;
  else if (feitos.length < todos.length)
    resumo = `${feitos.length} de ${todos.length} jogos já foram disputados · acertos até agora: ${acertos} de ${avaliados.length}`;
  else resumo = `Acertamos ${acertos} de ${avaliados.length} (${pct(acertos / avaliados.length)}) · palpites feitos só com dados anteriores a cada jogo`;

  let ultimoDia = '';
  const cartoes = jogos.map((g) => {
    const novoDia = ordem === 'data' && diaDe(g) !== ultimoDia;
    if (novoDia) ultimoDia = diaDe(g);
    return (
      <Fragment key={g.id}>
        {novoDia && <div className="day">{dayLong(diaDe(g))}</div>}
        <GameCard g={g} times={times} usaLinha={linha} />
      </Fragment>
    );
  });

  const temSemLinha = jogos.some((g) => g.p != null && !g.linha);
  const titulo = info.rotulo;

  return (
    <>
      <div className="ctrls">
        <div className="seg" role="group" aria-label="Temporada">
          {temporadas.map((s) => (
            <button key={s} aria-pressed={s === seasonKey} onClick={() => onSelect(s)}>{rotTemp(meta, s)}</button>
          ))}
        </div>
        <div className="weeks" role="group" aria-label="Semana" ref={chipsRef}>
          {Object.keys(weeks).map((w) => {
            const atual = seasonKey === String(meta.temporada) && w === String(meta.semana_atual);
            const nome = weeks[w].rotulo;
            return (
              <button
                key={w}
                className={atual ? 'now' : ''}
                aria-pressed={w === weekKey}
                aria-label={nome + (atual ? ' (atual)' : '')}
                onClick={() => onSelect(seasonKey, w)}
              >
                {rotuloSemana(w, weeks[w])}
              </button>
            );
          })}
        </div>
      </div>

      <div className="wk-head">
        <div>
          <h2>{titulo} · {rotTemp(meta, seasonKey)}</h2>
          <div className="sum">{resumo}{aoVivoN > 0 && ` · ${aoVivoN} ao vivo agora`}</div>
        </div>
        <span className="tag" title="Todos os horários desta página estão no horário de Brasília.">Horário de Brasília</span>
        <div className="seg" role="group" aria-label="Ordenar">
          <button aria-pressed={ordem === 'data'} onClick={() => setOrdem('data')}>Por horário</button>
          <button aria-pressed={ordem === 'conf'} onClick={() => setOrdem('conf')}>Mais confiantes</button>
        </div>
      </div>

      <div className="games">{cartoes}</div>
      {linha && temSemLinha && (
        <p className="note">
          Jogos marcados com “sem linha de aposta” ainda não têm a linha divulgada. Nesses casos o palpite usa o modelo sem ela, que é menos preciso.
        </p>
      )}
    </>
  );
}
