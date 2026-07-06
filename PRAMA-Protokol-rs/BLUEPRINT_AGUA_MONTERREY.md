# Blueprint — Dominio Agua y Drenaje (Monterrey)
## Diseño anticipado de la interfaz de observación, para activar al obtener insumos

**Documento de planeación interno — AptadynamiK**
**Estado:** blueprint (sin datos aún). Al conseguir acceso a insumos reales, este
documento se convierte en el borrador del pre-registro P1 del dominio.
**Norma:** AS-1 §5 (contrato C1–C5) y §8 (disciplina de estudio).
**Motor:** `prama-protokol` (estudios, Python) / `prama-protokol-rs` (producción,
streaming). El kernel no se toca; todo lo de este documento vive en O_D.

---

## 1. Por qué el dominio es estructuralmente ideal

Una red de agua/drenaje es el pariente hidráulico del dominio eléctrico validado:
eventos discretos y fechables (fugas, roturas, bloqueos, derrames, fallas de bombeo),
flujo raro-y-en-ráfagas, cascadas físicas reales (una rotura sube presión aguas
abajo; un bloqueo desborda al colector vecino; el envejecimiento es literalmente
Ξ acumulándose en tubería), historia larga en registros de la utility, y fuerte
estructura estacional. La pregunta del Protokol es exactamente la de la
infraestructura envejecida: *¿la red se sostiene, o solo lo aparenta?* — el sector
que "opera con normalidad" mientras consume su margen estructural es el colapso
latente en su forma más literal.

## 2. Insumos a solicitar (en orden de valor)

1. **Órdenes de trabajo correctivas históricas** (5–20 años): fecha/hora del
   reporte, tipo de falla (fuga, rotura, bloqueo, hundimiento, falla de bomba),
   ubicación (sector/distrito hidrométrico), y si es posible severidad
   (duración de reparación, usuarios afectados). Este es el análogo directo del
   registro de outages de BPA y basta por sí solo para el primer estudio.
2. **Reportes ciudadanos** (líneas de atención/073/app): timestamp + tipo + zona.
   Ruidosos pero abundantes; útiles como canal secundario declarado.
3. **SCADA de bombeo/presión** (si existe): eventos de arranque/paro no
   programado, alarmas de presión. Canal de eventos de alta calidad.
4. **Precipitación horaria** (pública: CONAGUA/SMN): NO como evento — como
   **contexto** de la expectativa (ver §4).

Nota práctica: el primer estudio NO requiere datos de toda la red; un subconjunto
de sectores con historia larga y consistente vale más que cobertura total.

## 3. Definiciones O_D (borrador de decisiones P1)

- **Bin:** día (primera opción) u hora si la densidad de eventos lo permite.
  Regla de la meseta (hallazgo AS-1 v1.1 pendiente): tau_memory ≪ longitud del
  registro; con años de historia diaria, la configuración validada en bins es
  aplicable directamente — verificar meseta igual que en el dominio LLM.
- **Unidad de flujo:** por sector/distrito hidrométrico (cada sector es un
  stream Ω; la ciudad es una flota de streams — el modo streaming de
  `prama-protokol-rs` está hecho para esto).
- **ω̃ (medición cruda):** conteo de eventos correctivos del sector en el bin
  (tipos incluidos: declarar lista cerrada ex-ante; excluir mantenimiento
  programado — el análogo de la distinción automatic/planned del grid).
- **Normalización N_D (C4):** división por media móvil causal del sector
  (idéntica a la del ejemplo del Engine), de modo que sectores grandes y chicos
  sean comparables sin parámetros por sector.
- **Expectativa causal ω̂ (C2/C3):** `CausalConditionalMean` con contexto
  declarado ex-ante. Candidatos, elegir UNO en P1:
  (a) (mes) — estacionalidad simple;
  (b) (mes, día-de-semana);
  (c) (mes, banda de precipitación del bin) — **la decisión delicada**: si la
  lluvia entra al contexto, Δ mide desacoplamiento *más allá de lo que la lluvia
  explica* (la red que falla más de lo que su propia historia de lluvia
  predeciría); si no entra, las temporadas de lluvia saturarán Δ trivialmente.
  Recomendación del blueprint: (c), con bandas de precipitación declaradas
  (p. ej. 0 / 0–10mm / 10–30mm / >30mm) — es la lección NYISO aplicada
  preventivamente: que Δ no degenere en pluviómetro.
- **σ_op:** el sector presta servicio en el bin (sin corte general declarado).
- **Esquema de outcomes (Y_o, Y_s):** Y_o = incidente compuesto del sector
  (≥ k eventos encadenados con gap ≤ g días — análogo de las cascadas ≥ 4 del
  grid; k y g se declaran en P1); Y_s = severidad (usuarios-hora afectados o
  duración total de reparación).
- **Líneas base obligatorias:** intensidad markoviana móvil (la que el grid
  venció), conteo del bin anterior, media estacional simple, y —si la lluvia no
  entró al contexto— precipitación misma como línea base (¡debe ser batida!).

## 4. Riesgos de diseño declarados

1. **Degeneración pluvial** (el NYISO de este dominio): sin precipitación en el
   contexto, Δ correlaciona con lluvia y el estudio mide meteorología. El
   chequeo C3 del Engine lo detectará mecánicamente; el diseño (c) lo previene.
2. **Cambios de régimen administrativo:** campañas de reparación masiva o
   cambios en el sistema de captura de órdenes rompen la estacionariedad del
   *proceso de observación* (no del sistema). Declarar en P1 cómo se marcan
   esos periodos (análogo al criterio de completitud del grid).
3. **Sesgo de reporte ciudadano:** el canal 2 refleja atención mediática además
   de fallas. Mantenerlo secundario, nunca mezclarlo con el canal 1 en un mismo ω̃.
4. **Sensibilidad institucional:** los resultados señalan sectores en consumo de
   margen — información operativamente valiosa y políticamente delicada. Política
   del programa: entregar a la utility como diagnóstico estructural, no publicar
   sectores identificables sin acuerdo; el estudio metodológico se publica con
   sectores anonimizados.

## 5. Ruta de activación (cuando lleguen los insumos)

1. Convertir §3 en `PREREGISTRATION_P1.md` del repo `Aptadynamic-Water-<utility>`,
   decisiones cerradas, commit ANTES de mirar outcomes.
2. Pipeline calcado del dominio LLM: ingest → omega → kernel del paquete →
   cumplimiento C2/C3/C4 bloqueante → métricas con líneas base y permutación.
3. Criterios de éxito idénticos en forma a los del estudio LLM (D6): confirmatorio /
   nulo honesto / fracaso de interfaz.
4. Si valida: despliegue streaming con `prama-protokol-rs` (un `Kernel` por
   sector; alerta = colapso latente sostenido) — el sentinel de la red.

---
*Este blueprint no contiene ningún resultado; contiene decisiones listas para
congelar. Su valor es que el día que exista acceso a datos, el estudio empieza
en P1, no en cero.*
