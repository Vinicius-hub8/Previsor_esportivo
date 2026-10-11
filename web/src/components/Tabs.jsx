const ABAS_PADRAO = [
  { id: 'jogos', nome: 'Jogos da semana' },
  { id: 'time', nome: 'Projeção de time' },
];

export default function Tabs({ tab, onChange, abas = ABAS_PADRAO }) {
  return (
    <div className="tabs" role="tablist" aria-label="Seções">
      {abas.map((a) => (
        <button key={a.id} role="tab" id={`tab-${a.id}`} aria-selected={tab === a.id} onClick={() => onChange(a.id)}>
          {a.nome}
        </button>
      ))}
    </div>
  );
}
