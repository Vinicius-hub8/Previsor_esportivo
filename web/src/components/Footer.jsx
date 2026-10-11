import { dateBR } from '../lib/format.js';

export default function Footer({ metas = [] }) {
  const fontes = [...new Set(metas.map((m) => m.fonte))].join(' · ');
  const atualizado = metas.map((m) => m.atualizado).sort().at(-1);
  return (
    <footer>
      <div className="wrap">
        {metas.length > 0 && (
          <span>
            Dados: {fontes}. Atualizado em {dateBR(atualizado)}.
          </span>
        )}
        <span>Estudo estatístico e educacional. Não é recomendação de aposta.</span>
      </div>
    </footer>
  );
}
