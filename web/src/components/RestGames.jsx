import { dayShort, pct } from '../lib/format.js';

export default function RestGames({ p, times }) {
  const semLinha = p.jogos.filter((j) => !j.linha).length;
  return (
    <div className="card">
      <h3>Jogos restantes e chance de vitória</h3>
      <div className="rest">
        {p.jogos.map((j) => (
          <div className="rg" key={`${j.sem}-${j.adv}`}>
            <div className="when">
              Semana {j.sem}
              <br />
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
                {!j.linha && <sup>*</sup>}
              </div>
            </div>
          </div>
        ))}
      </div>
      <p className="note" style={{ marginTop: 10 }}>
        {semLinha > 0 && `${semLinha} de ${p.jogos.length} jogos estão sem linha de aposta (marcados com *). Nesses, a chance vem do modelo sem ela, que é menos preciso. `}
        A projeção trata os jogos como independentes e não inclui playoffs.
      </p>
    </div>
  );
}
