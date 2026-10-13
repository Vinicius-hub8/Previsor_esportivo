import { num1, pct, rotTemp, usaLinha } from '../lib/format.js';

// Três números de destaque. Com linha de aposta (NFL): com linha / sem linha / temporada.
// Sem linha (NBA): modelo / "sempre no mandante" / temporada.
export default function AccuracyStrip({ meta }) {
  const linha = usaLinha(meta);
  const temporada =
    meta.n_temporada > 0
      ? { n: pct(meta.acc_temporada, 1), l: `${rotTemp(meta, meta.temporada)} até agora (${meta.n_temporada} jogos)` }
      : { n: '—', l: `${rotTemp(meta, meta.temporada)}: ainda sem jogos disputados` };
  const tiles = linha
    ? [{ n: pct(meta.acc_com_linha, 1), l: 'com linha de aposta' }, { n: pct(meta.acc_sem_linha, 1), l: 'sem linha de aposta' }, temporada]
    : [{ n: pct(meta.acc, 1), l: `modelo, ${meta.anos_ref[0]} a ${meta.anos_ref[1]}` }, { n: pct(meta.acc_mandante, 1), l: 'se o time da casa sempre vencesse' }, temporada];

  return (
    <section className="acc" aria-label="Acurácia do modelo">
      <h2>Quanto o modelo acerta</h2>
      <div className="row">
        {tiles.map((t) => (
          <div key={t.l}>
            <div className="n">{t.n}</div>
            <div className="l">{t.l}</div>
          </div>
        ))}
      </div>
      <details>
        <summary>Como ler esses números</summary>
        {meta.como_ler ? <p>{meta.como_ler}</p> : (
        <p>
          Para cada temporada de {meta.anos_ref[0]} a {meta.anos_ref[1]}, o modelo aprendeu só com os anos anteriores e previu os jogos
          daquele ano.{' '}
          {linha
            ? 'Se o time da casa sempre vencesse, acertaria cerca de 55% dos jogos. A linha de aposta é uma informação pública antes do jogo, mas já embute a opinião das casas, por isso o modelo com ela fica perto do mercado.'
            : `Se o time da casa sempre vencesse, acertaria ${pct(meta.acc_mandante, 0)} dos jogos. O modelo usa a força dos times, a forma recente e o descanso.`}
        </p>
        )}
        {meta.mae_margem != null && (
          <p>Placar previsto: nos jogos testados, a margem prevista errou em média {num1(meta.mae_margem)} pontos. Acertar o placar exato é raro; o número serve como ordem de grandeza.</p>
        )}
        {meta.faixas && (
          <div className="table-wrap">
            <table>
              <caption>Quando o modelo diz que um time tem tal chance, quanto ele acerta de fato</caption>
              <thead>
                <tr><th>Confiança do palpite</th><th className="n">Jogos</th><th className="n">Acertos</th></tr>
              </thead>
              <tbody>
                {meta.faixas.map((f) => (
                  <tr key={f.de}>
                    <td>{pct(f.de)} a {pct(f.ate)}</td>
                    <td className="n">{f.n.toLocaleString('pt-BR')}</td>
                    <td className="n">{pct(f.acc, 1)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </details>
    </section>
  );
}
