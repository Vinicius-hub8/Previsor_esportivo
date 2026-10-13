import { SPORTS } from '../sports/registry.js';
import { accPrincipal, pct, semanaAtualRotulo } from '../lib/format.js';

function ActiveCard({ sport, meta, onOpen }) {
  const fut = sport.id === 'futebol';
  return (
    <button className="sport on" data-sport={sport.id} onClick={() => onOpen(sport.id)}>
      <span className="sig">{sport.nome}</span>
      <span className="meta">
        {fut ? 'Premier League, La Liga, Serie A, Bundesliga, Ligue 1 e Brasileirão' : `Temporada ${meta.temporada_rotulo ?? meta.temporada} · ${semanaAtualRotulo(meta)}`}
        <br />
        {sport.descricao}
      </span>
      <span className="fig">
        <b>{pct(accPrincipal(meta), 1)}</b>
        <span>
          {fut ? `de acerto nos 3 resultados: vitória, empate ou derrota (${meta.anos_ref[0]}–${meta.anos_ref[1]})` : `de acerto histórico (${meta.anos_ref[0]}–${meta.anos_ref[1]})`}
        </span>
      </span>
      <span className="cta">
        Abrir {sport.nome}
        <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.2" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
          <path d="M5 12h14M13 6l6 6-6 6" />
        </svg>
      </span>
    </button>
  );
}

function SoonCard({ sport }) {
  return (
    <div className="sport off" aria-disabled="true">
      <span className="sig">{sport.nome}</span>
      <span className="meta">{sport.descricao}</span>
      <span>
        <span className="tag">Em breve</span>
      </span>
    </div>
  );
}

export default function Home({ datas, onOpen }) {
  return (
    <>
      <section className="hero">
        <h1>Qual esporte você quer prever?</h1>
        <p>Probabilidades calculadas a partir de dados históricos, sempre com a acurácia real do modelo à mostra.</p>
      </section>
      <section className="sports" aria-label="Esportes">
        {SPORTS.map((s) =>
          s.ativo && datas[s.id] ? (
            <ActiveCard key={s.id} sport={s} meta={datas[s.id].meta} onOpen={onOpen} />
          ) : (
            <SoonCard key={s.id} sport={s} />
          )
        )}
      </section>
      <section className="how" aria-label="Como funciona">
        <div>
          <h3>Dados abertos</h3>
          <p>Resultados e calendários vêm de bases públicas (nflverse, hoopR, openfootball e ESPN) e se atualizam todo dia.</p>
        </div>
        <div>
          <h3>Modelo simples e explicável</h3>
          <p>Força dos times (Elo), desempenho recente, descanso e, quando existe, a linha de aposta entram numa regressão logística.</p>
        </div>
        <div>
          <h3>Acurácia medida de verdade</h3>
          <p>Cada temporada é prevista só com o que existia antes dela. Nada de olhar o futuro.</p>
        </div>
      </section>
    </>
  );
}
