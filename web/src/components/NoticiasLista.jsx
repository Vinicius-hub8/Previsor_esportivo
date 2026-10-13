// Notícias que ajustaram a previsão deste jogo (vêm do arquivo ajustes_noticias.csv).
export default function NoticiasLista({ nt, nomeDe }) {
  if (!nt?.length) return null;
  return (
    <div className="det news-list">
      {nt.map((n, i) => (
        <div key={i}>
          <span>{nomeDe(n.t)}: {n.d > 0 ? '+' : '−'}{Math.abs(n.d)} de força</span>
          <b>
            {n.m || 'ajuste manual'}
            {n.f && (<> · <a href={n.f} target="_blank" rel="noreferrer noopener">fonte</a></>)}
          </b>
        </div>
      ))}
    </div>
  );
}
