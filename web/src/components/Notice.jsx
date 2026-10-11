import { useState } from 'react';
import { avisos } from '../lib/format.js';

export default function Notice({ meta }) {
  const [todos, setTodos] = useState(false);
  const lista = avisos(meta);
  return (
    <aside className="notice" aria-label="Avisos">
      <strong>Nuances que o modelo não enxerga</strong>
      <ul>
        {(todos ? lista : lista.slice(0, 2)).map((t) => (
          <li key={t}>{t}</li>
        ))}
      </ul>
      <button onClick={() => setTodos(!todos)} aria-expanded={todos}>
        {todos ? 'Mostrar menos' : 'Ver todos os avisos'}
      </button>
    </aside>
  );
}
