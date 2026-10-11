import { SPORTS } from '../sports/registry.js';
import { pct } from '../lib/format.js';

function ActiveCard({ sport, meta, onOpen }) {
  return (
    <button className="sport on" onClick={() => onOpen(sport.id)}>
      <span className="sig">{sport.nome}</span>
      <span className="meta">
        Temporada {meta.temporada} · Semana {meta.semana_atual}
        <br />
        {sport.descricao}
      </span>
      <span className="fig">
        <b>{pct(meta.acc_com_linha, 1)}</b>
        <span>de acerto histórico ({meta.anos_ref[0]}–{meta.anos_ref[1]})</span>
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
          <p>Resultados e calendário vêm de uma base pública (nflverse) e se atualizam a cada rodada.</p>
        </div>
        <div>
          <h3>Modelo simples e explicável</h3>
          <p>Força dos times (Elo), pontos recentes, descanso e a linha de aposta entram numa regressão logística.</p>
        </div>
        <div>
          <h3>Acurácia medida de verdade</h3>
          <p>Cada temporada é prevista só com o que existia antes dela. Nada de olhar o futuro.</p>
        </div>
      </section>
    </>
  );
}
