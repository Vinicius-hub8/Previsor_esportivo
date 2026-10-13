import Header from './components/Header.jsx';
import Footer from './components/Footer.jsx';
import Home from './components/Home.jsx';
import SportPage from './components/SportPage.jsx';
import FutebolPage from './components/FutebolPage.jsx';
import { SPORTS, sportById } from './sports/registry.js';
import { useHashRoute } from './lib/useHashRoute.js';
import { useTheme } from './lib/useTheme.js';
import { useSportsData } from './lib/useSportsData.js';
import { useEffect } from 'react';
import { useAoVivo } from './lib/useAoVivo.js';

const ATIVOS = SPORTS.filter((s) => s.ativo).map((s) => s.id);
const COM_PLACAR = SPORTS.filter((s) => s.ativo && s.espn);

export default function App() {
  const [route, navigate] = useHashRoute();
  const { toggle } = useTheme();
  const { datas, loading, error } = useSportsData(ATIVOS);
  const aoVivo = useAoVivo(COM_PLACAR);
  const [sportId, ...resto] = route;
  const sport = sportById(sportId);
  // cor de destaque do esporte aberto (tokens.css)
  useEffect(() => {
    if (sport?.ativo) document.documentElement.dataset.sport = sport.id;
    else delete document.documentElement.dataset.sport;
  }, [sport]);

  let conteudo;
  if (loading) {
    conteudo = <p className="state">Carregando dados…</p>;
  } else if (error) {
    conteudo = (
      <p className="state">
        Não consegui carregar os dados ({error}). Rode <code>python atualizar.py</code> na pasta do projeto e recarregue a página.
      </p>
    );
  } else if (sport && sport.ativo && sport.id === 'futebol' && datas.futebol) {
    conteudo = <FutebolPage sport={sport} indice={datas.futebol} route={resto} navigate={navigate} />;
  } else if (sport && sport.ativo && datas[sport.id]) {
    conteudo = <SportPage sport={sport} data={datas[sport.id]} live={aoVivo[sport.id]} route={resto} navigate={navigate} />;
  } else {
    conteudo = <Home datas={datas} onOpen={(id) => navigate(id)} />;
  }

  const metas = Object.values(datas).map((d) => d.meta);
  return (
    <>
      <Header onHome={() => navigate()} onToggleTheme={toggle} />
      <div className="wrap">
        <main>{conteudo}</main>
      </div>
      <Footer metas={metas} />
    </>
  );
}
