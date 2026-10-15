
from datetime import date
from coletar import coletar_periodo, salvar


def executar():
    for ano in range(2022, 2027):
        # Temporadas europeias: julho ate junho.
        # A de 2026/27 ainda esta em andamento.
        meses = (
            [(ano, m) for m in range(7, 13)]
            + [(ano + 1, m) for m in range(1, 7)]
        )

        for a, m in meses:
            if (a, m) > (2026, 10):
                continue

            if m == 12:
                proximo = date(a + 1, 1, 1)
            else:
                proximo = date(a, m + 1, 1)

            from datetime import timedelta

            inicio = date(a, m, 1)
            fim = proximo - timedelta(days=1)

            print(f"\nColetando {a}-{m:02d}...")

            try:
                jogos, _ = coletar_periodo(inicio, fim)
                lista = salvar(jogos, inicio, fim)
                print(f"Total acumulado: {len(lista)}")
            except Exception as erro:
                print(f"Erro no mes {a}-{m:02d}: {erro}")


if __name__ == "__main__":
    executar()
