import { pct } from '../lib/format.js';

export default function AccuracyStrip({ meta }) {
  return (
    <section className="acc" aria-label="Acurácia do modelo">
      <h2>Quanto o modelo acerta</h2>
      <div className="row">
        <div>
          <div className="n">{pct(meta.acc_com_linha, 1)}</div>
          <div className="l">com linha de aposta</div>
        </div>
        <div>
          <div className="n">{pct(meta.acc_sem_linha, 1)}</div>
          <div className="l">sem linha de aposta</div>
        </div>
        <div>
          <div className="n">{pct(meta.acc_temporada, 1)}</div>
          <div className="l">
            {meta.temporada} até agora ({meta.n_temporada} jogos)
          </div>
        </div>
      </div>
      <details>
        <summary>Como ler esses números</summary>
        <p>
          Para cada temporada de {meta.anos_ref[0]} a {meta.anos_ref[1]}, o modelo aprendeu só com os anos anteriores e previu os jogos
          daquele ano. Palpitar sempre no mandante acerta cerca de 55%. A linha de aposta é uma informação pública antes do jogo, mas já
          embute a opinião das casas, por isso o modelo com ela fica perto do mercado.
        </p>
      </details>
    </section>
  );
}
