// Logo Fator Casa: telhado em V + casa dividida como a barra de probabilidade (o mandante leva a fatia maior).
// As cores vêm dos tokens, então ele acompanha o tema claro/escuro.
export function CasaIcone({ className, title }) {
  return (
    <svg className={className} viewBox="0 0 48 48" role={title ? 'img' : undefined} aria-label={title} aria-hidden={title ? undefined : true}>
      <path d="M6 24 L24 8 L42 24" fill="none" stroke="var(--brand)" strokeWidth="5.5" strokeLinecap="round" strokeLinejoin="round" />
      <rect x="10" y="26.5" width="19" height="17" rx="3" fill="var(--brand)" />
      <rect x="31.5" y="26.5" width="6.5" height="17" rx="3" fill="var(--track)" />
    </svg>
  );
}

export default function Logo() {
  return (
    <>
      <CasaIcone className="brand-icon" />
      <span className="brand-txt">
        <b>Fator <i>Casa</i></b>
        <span>previsões esportivas</span>
      </span>
    </>
  );
}
