
import { useEffect, useState } from 'react';

const URL = `${import.meta.env.BASE_URL}dados/champions.json`;

function formatarData(data) {
  const [ano, mes, dia] = data.split('-');
  return `${dia}/${mes}/${ano}`;
}

function formatarProbabilidade(valor) {
  return `${Number(valor).toFixed(1).replace('.', ',')}%`;
}

export default function ChampionsPage({ navigate }) {
  const [dados, setDados] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  useEffect(() => {
    const controlador = new AbortController();

    async function carregar() {
      try {
        setLoading(true);
        setError(null);

        const resposta = await fetch(URL, {
          signal: controlador.signal,
          cache: 'no-store'
        });

        if (!resposta.ok) {
          throw new Error(
            `Erro ao carregar Champions (${resposta.status})`
          );
        }

        const json = await resposta.json();
        setDados(json);
      } catch (erro) {
        if (erro.name !== 'AbortError') {
          setError(erro.message);
        }
      } finally {
        if (!controlador.signal.aborted) {
          setLoading(false);
        }
      }
    }

    carregar();

    return () => controlador.abort();
  }, []);

  const jogos = dados?.jogos ?? [];

  return (
    <>
      <div className="crumb">
        <button
          className="back"
          onClick={() => navigate('futebol')}
        >
          ← Voltar às competições
        </button>
      </div>

      <h1 className="sport-title">
        🏆 UEFA Champions League
      </h1>

      <p className="note">
        Previsões experimentais com Elo + Poisson.
        Horários de Brasília. As probabilidades indicam
        vitória do mandante, empate ou vitória do visitante.
      </p>

      {loading && (
        <p className="state">
          Carregando previsões da Champions…
        </p>
      )}

      {error && (
        <p className="state">
          Não foi possível carregar as previsões: {error}.
          Execute o exportador da Champions e atualize a página.
        </p>
      )}

      {!loading && !error && (
        <>
          <p className="note">
            {jogos.length} partidas com previsão
            {' · '}
            Gerado em:{' '}
            {dados?.meta?.gerado_em
              ? new Date(
                  dados.meta.gerado_em
                ).toLocaleString('pt-BR', {
                  timeZone: 'America/Sao_Paulo'
                })
              : 'Não informado'}
          </p>

          {jogos.length === 0 && (
            <p className="state">
              Nenhuma partida futura disponível.
            </p>
          )}

          <div
            style={{
              display: 'grid',
              gap: '16px',
              marginTop: '20px'
            }}
          >
            {jogos.map((jogo) => {
              const p = jogo.probabilidades;

              const opcoes = [
                {
                  nome: 'Mandante',
                  valor: p.mandante
                },
                {
                  nome: 'Empate',
                  valor: p.empate
                },
                {
                  nome: 'Visitante',
                  valor: p.visitante
                }
              ];

              const maior = Math.max(
                ...opcoes.map((opcao) => opcao.valor)
              );

              return (
                <article
                  key={jogo.id}
                  style={{
                    border: '1px solid var(--border, #8885)',
                    borderRadius: '14px',
                    padding: '20px'
                  }}
                >
                  <p
                    className="note"
                    style={{ marginBottom: '12px' }}
                  >
                    {formatarData(jogo.data)}
                    {' · '}
                    {jogo.hora}
                    {' · '}
                    Temporada{' '}
                    {jogo.temporada.replace('-', '/')}
                  </p>

                  <h2
                    style={{
                      fontSize: '1.2rem',
                      marginBottom: '18px',
                      textAlign: 'center'
                    }}
                  >
                    {jogo.mandante}
                    {' × '}
                    {jogo.visitante}
                  </h2>

                  <div
                    style={{
                      display: 'grid',
                      gridTemplateColumns:
                        'repeat(3, minmax(0, 1fr))',
                      gap: '8px',
                      textAlign: 'center'
                    }}
                  >
                    {opcoes.map((opcao) => (
                      <div
                        key={opcao.nome}
                        style={{
                          border: '1px solid var(--border, #8885)',
                          borderRadius: '10px',
                          padding: '12px 5px',
                          fontWeight:
                            opcao.valor === maior
                              ? 'bold'
                              : 'normal'
                        }}
                      >
                        <div
                          style={{
                            fontSize: '0.8rem',
                            marginBottom: '8px'
                          }}
                        >
                          {opcao.nome}
                        </div>
                        <div
                          style={{
                            fontSize: '1.3rem'
                          }}
                        >
                          {formatarProbabilidade(
                            opcao.valor
                          )}
                        </div>
                      </div>
                    ))}
                  </div>

                  <p
                    className="note"
                    style={{
                      textAlign: 'center',
                      marginTop: '15px'
                    }}
                  >
                    Placar mais provável:{' '}
                    <strong>
                      {jogo.placar_provavel[0]}
                      {' × '}
                      {jogo.placar_provavel[1]}
                    </strong>
                  </p>
                </article>
              );
            })}
          </div>
        </>
      )}
    </>
  );
}
