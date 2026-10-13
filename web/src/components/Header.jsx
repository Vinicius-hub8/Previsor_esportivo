import Logo from './Logo.jsx';

export default function Header({ onHome, onToggleTheme }) {
  return (
    <header className="top">
      <div className="wrap">
        <button className="brand" onClick={onHome} aria-label="Fator Casa: voltar à escolha de esporte">
          <Logo />
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
