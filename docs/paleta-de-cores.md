# Paleta de cores · Fator Casa

Imagem para consulta: `docs/paleta-de-cores.png`. Os valores abaixo estão em `web/src/styles/tokens.css`; mude lá para mudar o site inteiro.
Todo texto sobre cor de destaque passa em contraste AA (4,5:1). Os valores de contraste são calculados contra branco (claro) ou `#0B1220` (escuro).

## Marca e esportes

| Papel | Claro | Escuro | Onde aparece |
|---|---|---|---|
| Azul Casa (marca) | `#2671D0` | `#4A93EA` | logo, página inicial, botões da marca |
| Azul Casa, texto | `#1C5CAB` | `#9CC4F5` | links, títulos de destaque |
| NFL (azul-índigo) | `#3556D3` | `#7B97FF` | tudo que está dentro da NFL |
| NBA (laranja) | `#B84F08` | `#F08A3C` | tudo que está dentro da NBA |
| Futebol (verde) | `#157A3A` | `#3BBF72` | tudo que está dentro do futebol |
| Ao vivo | `#C9184A` | `#FF5A86` | chip AO VIVO (texto branco no claro, `#2A0010` no escuro) |

As cores de esporte têm também uma versão para texto (`--c-nfl-ink`, `--c-nba-ink`, `--c-fut-ink`): `#2B46B0 / #AEBFFF`, `#9A4106 / #F7B07A`, `#0F6330 / #86DBA7`.
O destaque da tela muda sozinho: o atributo `data-sport` vai no `<html>` quando um esporte está aberto e nos cartões da página inicial. Os tons suaves (`--accent-soft`, `--accent-mid`) são calculados com `color-mix` a partir do destaque.

## Neutros

| Papel | Claro | Escuro |
|---|---|---|
| Fundo da página | `#F2F4F8` | `#0D1218` |
| Cartão | `#FFFFFF` | `#151B23` |
| Cartão 2 | `#F7F9FC` | `#1A212B` |
| Texto | `#0E1620` | `#EEF1F5` |
| Texto secundário | `#475467` | `#B6BFCB` |
| Texto apagado | `#6B7686` | `#8B95A3` |
| Linhas | `#E0E5EC` | `#26303B` |
| Trilho de barras | `#D9DFE8` | `#2B3541` |
| Chip | `#E9EEF5` | `#212A35` |

## Resultado e avisos (sempre com ícone e texto, nunca só cor)

| Papel | Claro (texto / fundo) | Escuro (texto / fundo) |
|---|---|---|
| Acerto | `#006300` / `#E3F4E3` | `#4CC24C` / `#12301A` |
| Erro | `#B32D2D` / `#FBE8E8` | `#EE8A8A` / `#3A1C1F` |
| Aviso | `#6B4A00` / `#FFF4D6` | `#F0D48A` / `#2F2710` |

## Tipografia

- Títulos e números: **Barlow Condensed** 700, caixa alta.
- Texto: **Public Sans** 400 a 700.

## Logo

Casa com telhado em V. O corpo é dividido como a barra de probabilidade do site: o mandante leva a fatia maior (o “fator casa”).
Arquivos em `docs/logo/`: lockup horizontal (claro e escuro, SVG e PNG), ícone (claro e escuro) e ícone de aplicativo. Em `web/public/`: `favicon.svg` (acompanha o tema do navegador), `favicon-32.png`, `apple-touch-icon.png`, `icon-192.png`, `icon-512.png`, `icon-maskable-512.png`, `og-image.png` (prévia de link, 1200×630) e `manifest.webmanifest`.
O texto do logo está convertido em curvas nos SVGs, então eles não dependem de fonte instalada.
Uso: deixe uma margem livre em volta do logo de pelo menos a altura do “F”; no fundo escuro use a versão escura.
