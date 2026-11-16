# Informe para decidir: ¿con cuál de los tres temas se escribe el pitch?

Fecha: 2026-11-15. Cubre los casos `data-scouts/conformity` y `data-scouts/stuck-time`, y los compara con
`data-scouts/memetic-spread` (correcciones), que ya tiene su propio [informe](memetic-spread/INFORME.md). El detalle
técnico está en el `FINDINGS.md` de cada caso, las definiciones en su `HYPOTHESIS.md`, las lecturas a mano en su
`VERIFICATION.md` y la tabla comparativa en [COMPARISON.md](COMPARISON.md).

## Para qué es este informe

David vuelve a postular al AI Village Data Exploration Grant (AI Digest). El pitch tiene 200 palabras, lo escribe
él y debe abrir con un número sorprendente y defendible. Ya había un candidato (correcciones, del caso de
propagación memética). En esta sesión se exploraron dos más para poder elegir entre tres.

**Resultado en una línea:** conformidad da un número llamativo y contable, aunque con muestra pequeña; tiempo
atascado salió nulo. Recomiendo conformidad.

## Contexto mínimo

El AI Village es un experimento donde entre 4 y más de 20 agentes de IA (Claude, GPT, Gemini y otros) conversan en
un chat común y usan cada uno una computadora. El dataset guarda los 205.625 mensajes del chat y 3,3 millones de
"turnos" de uso de computadora (cada turno es una acción: un clic, una tecla, un comando), de abril de 2025 a
octubre de 2026.

Dos datos del entorno importan para leer los resultados:

- Los organizadores cambiaron muchas veces el andamiaje (las herramientas y reglas que rodean a los agentes). El
  dataset trae un registro fechado de esos cambios. El mayor es de marzo de 2026.
- Los agentes de 2025 trabajaban casi solo con clics en pantalla. Los de mediados de 2026 hacen la mayor parte
  de su trabajo con comandos de terminal (bash).

## Candidato 1: conformidad

### Qué se preguntó

Cuando los agentes toman una decisión de grupo explícita, ¿con qué frecuencia alguno disiente, y qué pasa después
con la posición del que disintió? El post de AI Digest sobre el juego de saboteadores cuenta una votación unánime
contra un agente inocente, y sus lectores notaron que los agentes casi nunca votan contra el grupo. Nadie lo
había contado.

Antes de codificar nada se fijó por escrito qué contaría como nulo:

| | Hipótesis | Criterio fijado de antemano |
|---|---|---|
| H0 | Las decisiones se pueden contar de forma fiable | al menos 30 decisiones y 80 % de acuerdo al releer 10 |
| H1 | La mayoría de las decisiones son unánimes | 70 % o más |
| H2 | Hay más unanimidad de la que producirían agentes independientes | 15 puntos sobre la línea base y fuera de su intervalo |
| H3 | Gana la primera posición que se enuncia | 15 puntos sobre el azar |
| H4 | El disenso no dura | 50 % o más abandonado el mismo día |
| H5 | Hay diferencias por familia de modelo o por año | 20 puntos |

La línea base de H2 responde a esta pregunta: si cada agente disintiera por su cuenta, con la frecuencia con que
de hecho disiente, ¿cuántas decisiones saldrían sin ningún disenso?

### Qué se hizo

1. Se buscaron los mensajes de agentes con lenguaje de voto en primera persona ("I vote", "my vote", "+1",
   "I second"): 1.402 mensajes. Agrupados por sala y hora dan 89 ventanas con al menos tres agentes.
2. Doce sub-agentes (Claude Sonnet) leyeron cada ventana y registraron las decisiones y la posición de cada
   agente, con el número de mensaje y una cita literal.
3. Un script comprobó que cada cita existe tal cual en el mensaje citado y que el autor coincide.
4. Leí a mano los 96 disensos registrados, las nueve votaciones del juego de saboteadores y una muestra de diez
   decisiones al azar.

Una "decisión" es una pregunta puesta al grupo en la que al menos tres agentes enuncian una posición explícita.
Una "posición" es la opción que un agente enuncia en su propio mensaje. El silencio no cuenta.

### Qué salió

En el juego de saboteadores (marzo de 2026) cada día algunos agentes eran saboteadores en secreto y el grupo podía
votar para expulsar a un sospechoso. Hubo nueve votaciones.

| | Resultado | Lectura |
|---|---|---|
| Posiciones de agentes no acusados que fueron con la mayoría | 69 de 70 | Es el número candidato |
| Votaciones unánimes | 7 de 9 | Se esperaban 4,4 (intervalo 2 a 7) con agentes independientes: dentro del intervalo |
| Agentes expulsados | 8 | 5 confesaron ser saboteadores; 1 no se pudo confirmar; 2 no lo eran según el registro |
| Las dos expulsiones equivocadas | ambas unánimes | Una es el caso GPT-5 que AI Digest ya publicó. La otra no está publicada |
| El único disenso entre los 70 | GPT-5.1 | Defendió a un agente que resultó ser saboteador |

La expulsión no publicada: el grupo expulsó por unanimidad a Opus 4.5 (Claude Code) por no haber revelado su rol
el día anterior. Cuatro minutos después un organizador escribió que ese agente no había estado funcionando por un
problema técnico de ellos.

En el conteo amplio (160 decisiones, 748 posiciones, 32 agentes, de mayo de 2025 a octubre de 2026):

| | Resultado | Lectura |
|---|---|---|
| H0 | 160 decisiones; 9 de 10 releídas coinciden | Se pueden contar, con la reserva de abajo sobre errores de etiqueta |
| H1 | 139 de 160 terminan unánimes (86,9 %) | Se cumple |
| H2 | 124 de 160 nunca tuvieron disenso (77,5 %); la línea base da 69,7 % | Nulo: 8 puntos, bajo el umbral de 15 |
| Tasa de disenso | 57 de 748 posiciones (7,6 %); 43 de 709 (6,1 %) sin contar a quien defiende su propio interés | La tasa base que nadie había medido |
| H3 | La primera posición gana en 141 de 160 (88,1 %); por azar sería 96,3 % | Nulo, y por debajo del azar |
| H4 | 29 de 57 disensos abandonados el mismo día (50,9 %) | En el límite: 19 de 26 en propuestas, 8 de 28 en votaciones |
| H5 | Disenso entre 4,8 % y 9,5 % según familia; 8,4 % en 2025 y 7,5 % en 2026 | Nulo |

En palabras: los agentes disienten poco, pero ese poco disenso basta casi por sí solo para explicar tanta
unanimidad. No se pudo mostrar que se pongan de acuerdo más de lo que lo harían agentes independientes con las
mismas tasas. Lo llamativo está en el juego de saboteadores, donde equivocarse tenía un costo.

### Qué tan confiable es

- Las citas pasan la comprobación automática en 788 de 789 posiciones. Eso prueba que el mensaje existe, no que
  la etiqueta sea correcta: al leer los disensos, 11 de las 44 decisiones con disenso tenían errores. Todos
  inflaban el disenso (de 96 a 57) y están corregidos en un archivo con el motivo de cada cambio.
- En las decisiones unánimes solo se buscaron disensos omitidos en la muestra de diez. El 7,6 % es un piso.
- El 69 de 70 es un subconjunto que se eligió después de ver los resultados. Es el que el encargo pedía mirar
  primero, pero son solo nueve votaciones.
- En dos de las nueve votaciones el acusado ya había admitido su rol antes de que se votara. Ahí el acuerdo no
  dice nada sobre conformidad.
- Que GPT-5 no era saboteador viene del post de AI Digest; no aparece en el chat. Que Opus 4.5 (Claude Code) no
  lo era ese día es una inferencia: no está entre los tres que se revelaron al final del día.
- La búsqueda por texto es mala por sí sola: de 100 coincidencias leídas, 41 eran una posición propia, 18 hablaban
  de una votación y 41 eran otro sentido ("+1.232 de daño"). Por eso las ventanas se leyeron.
- Las votaciones son públicas y en secuencia, y las metas que pedían votar las pusieron los organizadores. Nada
  de esto es causal.

## Candidato 2: tiempo atascado

### Qué se preguntó

¿El tiempo que los agentes pasan atascados ha bajado con los modelos más nuevos? Un análisis anterior sobre un
tema cercano cambió de 34 % a 85 % según la definición, así que aquí se fijó una sola definición antes de
calcular, más una única alternativa como control.

- **Definición fija:** un episodio es una racha de cinco o más acciones idénticas seguidas (misma acción, mismo
  objetivo) dentro de una sesión.
- **Alternativa:** tramos de ocho acciones con dos objetivos distintos como máximo, para captar el ir y venir
  entre dos acciones.
- **Medida:** episodios por hora activa de cada agente, contra la fecha de lanzamiento de su modelo.

| | Hipótesis | Criterio fijado de antemano |
|---|---|---|
| H1 | Los modelos más nuevos tienen menos episodios por hora | correlación de rangos de −0,4 o más fuerte, p ≤ 0,05 |
| H2 | La tendencia es del modelo y no del andamiaje, la meta o la sala | −0,3 o más fuerte dentro de cada periodo de andamiaje y entre agentes con la misma meta y sala |
| H3 | Los modelos más nuevos se recuperan más rápido | igual que H1 |
| H4 | El resultado no depende de la definición | mismo signo con la alternativa |

### Qué se hizo

1. Se leyó una vez el archivo completo de turnos (3.295.475 turnos de 55 agentes) y se detectaron los episodios.
2. Se calculó la tendencia en conjunto, dentro de cada periodo de andamiaje, entre agentes con la misma meta y sala, y por
   separado para clics y para comandos de terminal.
3. Se tomaron 30 episodios al azar y se leyeron contra las filas crudas (acción, salida, error y lo que el
   agente decía que estaba haciendo).

### Qué salió

| | Resultado | Lectura |
|---|---|---|
| Tamaño | 3.118 episodios en 20.126 horas activas; 1,3 % del tiempo activo | Es poco tiempo en cualquier caso |
| H1 | ρ = −0,50, p = 0,0006, 43 agentes | Se cumple: los modelos nuevos repiten menos |
| H4 | ρ = −0,63 con la definición alternativa | Mismo signo |
| H3 | ρ = +0,11, 22 agentes | Nulo |
| H2, por periodo de andamiaje | −0,40 hasta marzo de 2026 (p = 0,12); −0,76 de marzo a septiembre; **−0,22 desde octubre** (p = 0,22) | Falla: la tendencia desaparece en el periodo más reciente |
| H2, misma meta y sala | −0,27 en 73 grupos, 60 de ellos con signo negativo | El signo se mantiene; el tamaño queda bajo el umbral |
| Solo clics y teclas | ρ = −0,58, 34 agentes | Aquí está la caída |
| Solo comandos de terminal | **ρ = −0,13**, p = 0,45, 38 agentes | Sin tendencia |
| Lectura de 30 episodios | 7 atascados, 2 dudosos, 21 no | Entre 70 % y 77 % de falsos positivos |

Los 21 episodios que no eran atasco eran otra cosa: pasar página con una tecla, refrescar una bandeja mientras se
espera a alguien, escribir `sleep 90` para esperar, o mandar teclas a un juego.

En palabras: la medida capta repetición, y la repetición casi nunca es estar atascado. La caída con los modelos
nuevos coincide con el paso de clics a terminal y no aparece dentro de la terminal. Los datos no muestran que el
tiempo atascado haya bajado.

### Qué tan confiable es

- El nulo es sólido: se sostiene con dos definiciones, con los controles fijados de antemano y con la lectura a
  mano. Lo que no es sólido es la tendencia.
- El modelo más antiguo de la serie (Claude 3.5 Sonnet) tiene la tasa más alta por un defecto de mi definición:
  68 de sus 72 episodios son clics sobre objetivos distintos que la definición ve como iguales.
- Un cambio de andamiaje se ve como si fuera conducta: 123 de los 165 bucles de `sleep` empiezan el día en que
  los organizadores quitaron la herramienta de pausa (20 de octubre de 2026) o después.
- No se usaron capturas de pantalla, así que nunca se comprobó si la pantalla cambiaba.
- Para los modelos de 2026 se usó la fecha de ingreso al Village como fecha de lanzamiento.

## Comparación de los tres

| | Correcciones | Conformidad | Tiempo atascado |
|---|---|---|---|
| Número candidato | Tras una corrección del organizador, 36 % de los pares conserva el término al día siguiente (48 de 132) frente a 34 % en los términos de control (11 de 32) | 69 de 70 posiciones con la mayoría; 2 de 8 expulsiones equivocadas, ambas unánimes | Solo 7 de 30 episodios de repetición eran un atasco |
| Sorpresa | Media | Media a alta en saboteadores; baja en el conteo amplio | Baja |
| Solidez | Baja a media: un solo episodio | Media: nueve votaciones | El nulo es sólido |
| Ya publicado por AI Digest | Anécdotas, sin tasas | El caso GPT-5 y los conteos de la elección; nadie contó el disenso | Solo afirmaciones cualitativas |
| Encaje con la convocatoria | "cómo se propaga la información entre agentes" | "dinámicas sociales entre IAs" | "qué tan rápido avanza la IA", pero con resultado nulo |

Correcciones no se volvió a ejecutar en esta sesión. Lo publicado por AI Digest lo recogió un sub-agente por
búsqueda web y las citas no se releyeron.

## Recomendación

**Postular con conformidad, abriendo con el conteo del juego de saboteadores**, y decir en el propio pitch que el
conteo amplio queda cerca de su línea base. Es el único candidato con un número a la vez llamativo y contable
fila por fila, y sus puntos débiles son los que un proyecto de 10 a 20 horas arregla.

| Opción | Qué es | Costo | Por qué sí | Riesgo |
|---|---|---|---|---|
| A. Conformidad | Abrir con 69 de 70 y las dos expulsiones equivocadas | 0 horas para postular; 2 a 3 para una segunda codificación de las nueve votaciones | Extiende algo que los lectores de AI Digest ya preguntaron; la expulsión por la falla técnica es nueva | Muestra pequeña; un revisor puede decir que el acusado casi siempre se había delatado |
| B. Correcciones | Repetir el estudio sobre las 144 correcciones de organizadores | 2 a 3 horas | Lo más cercano a "cómo dirigir a los agentes" | Puede volver a salir nulo |
| C. Tiempo atascado como nota de método | "La métrica obvia de progreso mide sobre todo esperas y paginación" | 0 horas | Nulo bien respaldado; la convocatoria acepta nulos | Poco llamativo como apertura |

No recomiendo presentar tiempo atascado como resultado de progreso: los datos no lo sostienen.

## Preguntas para el analista

1. ¿Nueve votaciones bastan para abrir un pitch si cada una está verificada a mano, o conviene abrir con la tasa
   general (6 % a 8 % de disenso en 160 decisiones) y dejar los saboteadores como ejemplo?
2. La línea base dice que la unanimidad es casi la esperable con tan poco disenso. ¿Eso debilita el tema, o lo
   vuelve más interesante (el fenómeno es que disienten poco, no que se contagien)?
3. ¿Vale la pena gastar 2 a 3 horas en una segunda codificación independiente antes de postular?
4. ¿El hallazgo de la herramienta de pausa (un cambio de andamiaje que parece conducta) merece una línea en el
   pitch como muestra de cuidado metodológico?
