export default function Header({ onHome, onToggleTheme }) {
  return (
    <header className="top">
      <div className="wrap">
        <button className="brand" onClick={onHome} aria-label="Voltar à escolha de esporte">
          <svg viewBox="0 0 34 20" aria-hidden="true">
            <rect x="0" y="5" width="21" height="10" rx="5" fill="var(--accent)" />
            <rect x="23" y="5" width="11" height="10" rx="5" fill="var(--track)" />
          </svg>
          <b>Previsor</b>
          <span>esportivo</span>
        </button>
        <button className="icon-btn" onClick={onToggleTheme} aria-label="Alternar tema claro e escuro" title="Alternar tema">
          <svg viewBox="0 0 24 24" aria-hidden="true">
            <path d="M20 14.5A8 8 0 0 1 9.5 4a8 8 0 1 0 10.5 10.5z" />
          </svg>
        </button>
      </div>
    </header>
  );
}
