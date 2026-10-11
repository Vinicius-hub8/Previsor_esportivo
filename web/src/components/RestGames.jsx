import { useState } from 'react';
import { dayShort, pct } from '../lib/format.js';

const LIMITE = 12; // com 82 jogos (NBA) a lista fica longa; mostra os primeiros e deixa abrir o resto

export default function RestGames({ p, times, usaLinha = true }) {
  const [todos, setTodos] = useState(false);
  const semLinha = p.jogos.filter((j) => !j.linha).length;
  const lista = todos ? p.jogos : p.jogos.slice(0, LIMITE);
  return (
    <div className="card">
      <h3>Jogos restantes e chance de vitória</h3>
      <div className="rest">
        {lista.map((j) => (
          <div className="rg" key={`${j.data}-${j.adv}`}>
            <div className="when">
              {j.sem != null && <>Semana {j.sem}<br /></>}
              {dayShort(j.data)}
            </div>
            <div className="opp">
              {j.casa ? 'vs' : '@'} {j.adv}
              <br />
              <small>{times[j.adv].apelido}</small>
            </div>
            <div className="meter">
              <div className="trk" role="img" aria-label={`Chance de vitória ${pct(j.p)}`}>
                <i style={{ width: `${j.p * 100}%` }} />
              </div>
              <div className="v">
                {pct(j.p)}
                {usaLinha && !j.linha && <sup>*</sup>}
              </div>
            </div>
          </div>
        ))}
      </div>
      {p.jogos.length > LIMITE && (
        <button className="more" onClick={() => setTodos(!todos)} aria-expanded={todos}>
          {todos ? 'Mostrar só os primeiros' : `Ver os ${p.jogos.length} jogos marcados`}
        </button>
      )}
      <p className="note" style={{ marginTop: 10 }}>
        {usaLinha && semLinha > 0 && `${semLinha} de ${p.jogos.length} jogos estão sem linha de aposta (marcados com *). Nesses, a chance vem do modelo sem ela, que é menos preciso. `}
        A projeção trata os jogos como independentes e não inclui playoffs.
      </p>
    </div>
  );
}
