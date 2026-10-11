const ABAS = [
  { id: 'jogos', nome: 'Jogos da semana' },
  { id: 'time', nome: 'Projeção de time' },
];

export default function Tabs({ tab, onChange }) {
  return (
    <div className="tabs" role="tablist" aria-label="Seções">
      {ABAS.map((a) => (
        <button key={a.id} role="tab" id={`tab-${a.id}`} aria-selected={tab === a.id} onClick={() => onChange(a.id)}>
          {a.nome}
        </button>
      ))}
    </div>
  );
}
