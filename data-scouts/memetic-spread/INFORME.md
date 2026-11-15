# Informe para decidir: ¿seguimos con "propagación memética" o cambiamos de ángulo?

Fecha: 2026-11-15. Caso `data-scouts/memetic-spread`. Detalle técnico en [FINDINGS.md](FINDINGS.md), definiciones en
[HYPOTHESIS.md](HYPOTHESIS.md), lecturas a mano en [VERIFICATION.md](VERIFICATION.md).

## Para qué es este informe

David vuelve a postular al AI Village Data Exploration Grant (AI Digest) con un tema nuevo, después de que rechazaran
el pitch sobre reconocimiento de autoridad. El pitch tiene 200 palabras y debe abrir con un número sorprendente y
defendible. Esta exploración (unas tres horas) buscó ese número en el tema "cómo viajan las ideas entre agentes".

**Resultado en una línea:** encontramos un número sólido pero poco sorprendente, y los contrastes que sí habrían
sorprendido salieron nulos. Hay que decidir entre una prueba corta más sobre este tema o cambiar de ángulo.

## Contexto mínimo

El AI Village es un experimento donde entre 4 y 42 agentes de IA (Claude, GPT, Gemini y otros) conversan en un chat
común, usan computadoras y mantienen una "memoria de largo plazo": un texto que cada agente reescribe varias veces
por hora. El dataset guarda cada versión de esa memoria (279.339 snapshots) y los 205.625 mensajes del chat, de
abril de 2025 a octubre de 2026.

Un "meme" aquí es una idea con redacción reconocible (una afirmación, una regla, un término acuñado) que se puede
buscar por texto. La unidad de todos los conteos es el **par (término, agente)**: un término y un agente que pudo
haberlo recibido.

## Qué se preguntó

Se fijaron por escrito, antes de calcular resultados, siete hipótesis y qué contaría como nulo:

| | Hipótesis | Criterio fijado de antemano |
|---|---|---|
| H1 | Un meme llega a la memoria de la mayoría de los agentes presentes | mediana por meme ≥ 50 % en 7 días |
| H2 | Las afirmaciones falsas y las verdaderas se propagan distinto | diferencia ≥ 25 puntos, estable, p ≤ 0,10 |
| H3 | Los memes iniciados por agentes y por humanos se propagan distinto | igual que H2 |
| H4 | Una familia de modelos adopta más que las otras | diferencia ≥ 20 puntos, p ≤ 0,10 |
| H5 | Los memes de 2026 se propagan distinto que los de 2025 | igual que H2 |
| H6 | Los memes sobreviven a su origen: los adoptan agentes que llegaron después | al menos la mitad de los memes, leído a mano |
| H7 | Tras una corrección del organizador, quienes acuñaron la idea falsa la sueltan y los demás la conservan | diferencia ≥ 25 puntos y que los términos de control no muestren lo mismo |

H7 se añadió a mitad de la exploración, después de ver un caso, y así está declarado.

## Qué se hizo

1. **15 memes elegidos a mano** con origen claro en el chat: 6 afirmaciones falsas (desmentidas en el propio
   chat), 4 verdaderas o reglas de organizadores, 5 términos sin valor de verdad. Se descartaron 7 de 22 candidatos
   porque la redacción ya existía en alguna memoria antes del supuesto origen.
2. **130 términos tomados al azar** entre 27.746 acuñados por agentes, para medir la tasa base sin sesgo de
   selección (1.895 pares).
3. **Un experimento natural:** el 2025-12-09 un organizador desmintió una familia de 22 términos sobre supuestos
   fallos del entorno que dos agentes Gemini venían acuñando. Se comparó cuánto duraron en memoria esos términos frente a términos de
   control de las mismas semanas (132 y 32 pares).

## Qué salió

| | Resultado | Lectura |
|---|---|---|
| Tasa base | 576 de 1.895 pares (30,4 %) tienen el término en memoria en 24 h; demora mediana 16 minutos; el 57 % de esas copias desaparece en menos de un día | Sólido. Es el número candidato |
| H1 | Mediana 87,5 % en los 15 memes elegidos, pero 33,8 % en la muestra al azar | Cierto solo para memes elegidos a mano: sesgo de selección |
| H2 | Falsas 80,8 % frente a verdaderas 71,6 % (6 y 4 memes, p = 0,62) | Nulo |
| H3 | Agente 81,8 % frente a humano 74,4 % (p = 0,59) | Nulo |
| H4 | Claude 84,1 % (53 de 63) frente a 69,0 % (60 de 87), p = 0,022 | No alcanza el umbral; la variación es por agente (0 % a 63 %), no por familia |
| H5 | 2026 74,0 % frente a 2025 81,3 % (p = 0,63) | Nulo |
| H6 | 13 de 15 memes por búsqueda de texto; leído a mano solo en 2 | Indicios, sin verificar en la mayoría |
| H7 | Diferencia de 16 puntos; los términos de control muestran 20 | Nulo: es rotación normal de memoria, no efecto de la corrección |

Tres observaciones que no son tasas pero orientan la decisión:

- **Una coincidencia en memoria es una nota, no una creencia.** En las cinco instancias leídas a mano, el agente
  anotó lo que otro dijo o hizo. Solo el 5,3 % de los pares (100 de 1.895) lleva el término a su siguiente plan de
  trabajo.
- **La corrección no aceleró el olvido.** De los 132 pares con un término desmentido, el 36 % lo conservaba al día
  siguiente y el 18 % a 30 días o más; en los términos de control, 34 % y 16 %. Entre los días 30 y 37 solo un
  agente (Claude Sonnet 4.5) mantenía los términos desmentidos como hechos, mientras la única afirmación que el
  organizador confirmó seguía en 6 de 8 pares.
- **Una alucinación se volvió folclore con su corrección adjunta.** Una lista de 93 contactos que nunca existió
  (junio de 2025) aparece en la memoria de 10 agentes que llegaron después, entre 254 y 456 días más tarde; 9 la
  registran como alucinación.

## Qué tan confiable es

- El número de tasa base aguanta definiciones alternativas: 33,8 % con ventana de 7 días, 37,3 % entre agentes de
  la misma sala, 26 % a 48 % según el trimestre. Con la definición estricta (presente en dos días distintos) baja a
  16,1 %.
- La búsqueda es literal: no detecta paráfrasis y sí detecta otros sentidos de las mismas palabras. Leer las líneas
  corrigió varios errores (un patrón sobre "sandcastle" encontraba castillos de arena de un mundo 3D).
- El 87 % de los pares es de 2026. Los modelos, la forma de guardar memoria y las reglas de los organizadores
  cambiaron en el periodo, así que nada de esto es causal.
- Las comparaciones H2 a H5 usan entre 4 y 11 memes por grupo. Un nulo con esa muestra no descarta efectos
  pequeños; descarta el contraste grande que un pitch necesitaría.

## Recomendación

**No abrir el pitch con "las ideas falsas se propagan más" ni con ninguna comparación entre grupos: los datos no la
sostienen.** El número de tasa base se puede defender, pero describe sobre todo cómo funciona la memoria (una
bitácora del chat) y no sorprende por sí solo.

Opciones, de la que recomiendo a la que menos:

| Opción | Qué es | Costo | Por qué sí | Riesgo |
|---|---|---|---|---|
| A. Una prueba corta más, sobre correcciones | Repetir el experimento natural sobre las 144 correcciones de organizadores ya listadas, con términos de control | 2 a 3 horas | Es lo más cercano a "cómo dirigir a los agentes", que es lo que pide AI Digest; el piloto ya da una pista contraintuitiva (corregir no acelera el olvido) y el código existe | Puede volver a salir nulo; muchas correcciones no tienen redacción buscable |
| B. Cambiar a diferencias entre agentes por fecha de lanzamiento | Los agentes que entraron en 2025 anotan términos nuevos más que los que entraron en 2026 (36,2 % frente a 22,8 % en los mismos 28 términos) | 2 a 3 horas | Toca "qué tan rápido avanza la IA"; la muestra al azar ya existe | Antigüedad, modelo y reglas de la época están mezclados; el efecto es moderado |
| C. Cambiar al plan alterno ya definido | Tiempo que los agentes tardan en recuperarse tras un aviso de inactividad, por fecha de lanzamiento del modelo | 2 a 3 horas | Definición ya fijada de antemano; datos listos del caso anterior (1.997 pares) | No se ha mirado nada: puede no haber gradiente |
| D. Postular con lo que hay | Abrir con "16 minutos y la mitad se borra en un día" como la tasa base que nadie había medido | 0 horas | Defendible fila por fila | Poco llamativo frente a otros pitches |

Mi recomendación es **A con tope de tiempo, y C como siguiente paso si A sale nulo**. Si A muestra que las
correcciones no cambian la memoria en varios episodios, ese sería un número de apertura con consecuencias prácticas.
Si muestra que sí la cambian, el piloto de diciembre de 2025 queda como excepción y conviene pasar a C.

## Preguntas para el analista

1. ¿Un nulo bien medido ("corregir no acelera el olvido") sirve como apertura, o el grant premia solo contrastes
   positivos?
2. ¿Vale más un número general y modesto (tasa base, 1.895 pares) o un episodio vívido con muestra pequeña (la lista
   fantasma de 93 contactos)?
3. ¿Conviene mantener "propagación memética" como tema, o el rechazo anterior sugiere cambiar a algo más cercano a
   desalineación entre familias de modelos?
