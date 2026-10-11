import { dateBR } from '../lib/format.js';

export default function Footer({ meta }) {
  return (
    <footer>
      <div className="wrap">
        {meta && (
          <span>
            Dados: {meta.fonte}. Atualizado em {dateBR(meta.atualizado)}.
          </span>
        )}
        <span>Estudo estatístico e educacional. Não é recomendação de aposta.</span>
      </div>
    </footer>
  );
}
