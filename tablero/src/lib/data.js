import gold from '../data/gold.json';

const [CICLO, CARRERA, AREA, POST, ING, TASA, FIABLE, CORTE, ESCALA, PMIN, PMAX, PMED] = [...Array(12).keys()];

export const CICLOS = gold.ciclos;
export const AREAS = gold.areas;
export const MODALIDADES = gold.modalidades;

export const ETIQUETA_MODALIDAD = {
  ordinario: 'Ordinario',
  precatolica: 'Precatolica',
  distancia: 'A distancia',
  rendimiento_superior: 'Alto rendimiento',
  beca: 'Beca 18',
  otras: 'Otras'
};

const filas = gold.porCarrera.map(f => ({
  ciclo: f[CICLO],
  carrera: f[CARRERA],
  area: f[AREA],
  postulaciones: f[POST],
  ingresantes: f[ING],
  tasa: f[TASA],
  fiable: f[FIABLE] === 1,
  corte: f[CORTE],
  escala: f[ESCALA],
  min: f[PMIN],
  max: f[PMAX],
  mediana: f[PMED],
  delta: gold.delta[`${f[CICLO]}|${f[CARRERA]}`] ?? null,
  clave: `${f[CICLO]}|${f[CARRERA]}`
}));

export const nombreArea = cod => AREAS.find(a => a.cod === cod)?.nombre ?? 'Sin clasificar';

/** Area a la que pertenece una carrera, para no romper un filtro contra otro. */
export const areaDe = carrera => filas.find(f => f.carrera === carrera)?.area ?? null;

/** Si la carrera se convoco en ese ciclo. Cambiar de ano no debe borrar el filtro. */
export const hayCarreraEn = (ciclo, carrera) =>
  filas.some(f => f.ciclo === ciclo && f.carrera === carrera);

/** Filas de un ciclo, opcionalmente acotadas a un area. */
export function filasDe(ciclo, area = null) {
  return filas.filter(f => f.ciclo === ciclo && (!area || f.area === area));
}

export function serieCiclos(area = null) {
  return CICLOS.map(c => {
    const fs = filasDe(c, area);
    const conf = fs.filter(f => f.fiable);
    const postF = conf.reduce((s, f) => s + f.postulaciones, 0);
    const ingF = conf.reduce((s, f) => s + f.ingresantes, 0);
    return {
      ciclo: c,
      postulaciones: fs.reduce((s, f) => s + f.postulaciones, 0),
      ingresantes: fs.reduce((s, f) => s + f.ingresantes, 0),
      tasa: postF ? +((ingF / postF) * 100).toFixed(2) : null
    };
  });
}

/** KPI del ciclo. La tasa solo se promedia sobre carreras con denominador fiable. */
export function kpis(ciclo, area = null) {
  const fs = filasDe(ciclo, area);
  const conf = fs.filter(f => f.fiable);
  const post = fs.reduce((s, f) => s + f.postulaciones, 0);
  const ing = fs.reduce((s, f) => s + f.ingresantes, 0);
  const postF = conf.reduce((s, f) => s + f.postulaciones, 0);
  const ingF = conf.reduce((s, f) => s + f.ingresantes, 0);
  const tasa = postF ? +((ingF / postF) * 100).toFixed(2) : null;
  const prev = CICLOS[CICLOS.indexOf(ciclo) - 1];
  const anterior = prev ? kpisCrudos(prev, area) : null;
  const varia = (hoy, ayer) => (ayer ? +(((hoy - ayer) / ayer) * 100).toFixed(2) : null);
  return {
    postulaciones: post,
    ingresantes: ing,
    carreras: fs.length,
    tasa,
    carrerasFiables: conf.length,
    deltaPost: varia(post, anterior?.post),
    deltaIng: varia(ing, anterior?.ing),
    deltaTasa: anterior?.tasa && tasa ? varia(tasa, anterior.tasa) : null
  };
}

/* Totales crudos de un ciclo, para calcular variaciones sin recursion. */
function kpisCrudos(ciclo, area) {
  const fs = filasDe(ciclo, area);
  const conf = fs.filter(f => f.fiable);
  const postF = conf.reduce((s, f) => s + f.postulaciones, 0);
  const ingF = conf.reduce((s, f) => s + f.ingresantes, 0);
  return {
    post: fs.reduce((s, f) => s + f.postulaciones, 0),
    ing: fs.reduce((s, f) => s + f.ingresantes, 0),
    tasa: postF ? (ingF / postF) * 100 : null
  };
}

export function porArea(ciclo) {
  return AREAS.map(a => {
    const fs = filasDe(ciclo, a.cod);
    return {
      ...a,
      postulaciones: fs.reduce((s, f) => s + f.postulaciones, 0),
      ingresantes: fs.reduce((s, f) => s + f.ingresantes, 0),
      carreras: fs.length
    };
  }).filter(a => a.carreras > 0);
}

export function modalidadesDe(ciclo, area = null) {
  const total = Object.fromEntries(MODALIDADES.map(m => [m, 0]));
  for (const f of filasDe(ciclo, area)) {
    const v = gold.porModalidad[f.clave];
    if (v) MODALIDADES.forEach((m, i) => { total[m] += v[i]; });
  }
  return MODALIDADES.map(m => ({ modalidad: m, etiqueta: ETIQUETA_MODALIDAD[m], ingresantes: total[m] }))
    .filter(d => d.ingresantes > 0);
}

/** Histograma agregado por tramo de 10 puntos. */
export function distribucion(ciclo, area = null) {
  const acc = new Map();
  for (const f of filasDe(ciclo, area)) {
    for (const [tramo, ing, no] of gold.distrib[f.clave] ?? []) {
      const a = acc.get(tramo) ?? [0, 0];
      acc.set(tramo, [a[0] + ing, a[1] + no]);
    }
  }
  return [...acc.entries()].sort((a, b) => a[0] - b[0])
    .map(([tramo, [ing, no]]) => ({ tramo, ingresantes: ing, noIngresantes: no }));
}

export function cercanos(ciclo, area = null) {
  let no = 0, cerca = 0;
  for (const f of filasDe(ciclo, area)) {
    const c = gold.cercanos[f.clave];
    if (c) { no += c[0]; cerca += c[1]; }
  }
  return { noIngresantes: no, aMenosDeUnPunto: cerca, porcentaje: no ? +(cerca / no * 100).toFixed(1) : null };
}

export const escalaDe = ciclo => (Number(ciclo) >= 2024 ? 'vigente' : 'anterior');

/** Caja de puntajes de ingresantes, calculada sobre las 69 652 filas de la capa silver. */
export const cajaDe = clave => gold.caja[clave] ?? null;

/** Ocupacion de vacantes. El estado marca los casos que la fuente deja provisionales. */
export const vacantesDe = clave => gold.vacantes[clave] ?? null;

/** Pendiente de postulaciones entre dos ciclos consecutivos, por carrera. */
export function pendiente(ciclo, area = null, limite = 10) {
  const prev = CICLOS[CICLOS.indexOf(ciclo) - 1];
  if (!prev) return { prev: null, ciclo, datos: [] };
  const antes = Object.fromEntries(filasDe(prev, area).map(f => [f.carrera, f.postulaciones]));
  const datos = filasDe(ciclo, area)
    .filter(f => antes[f.carrera] != null)
    .map(f => ({ carrera: f.carrera, antes: antes[f.carrera], despues: f.postulaciones }))
    .sort((a, b) => b.despues - a.despues)
    .slice(0, limite);
  return { prev, ciclo, datos };
}

/** Carreras del ciclo con caja de puntajes, ordenadas por demanda. */
export function cajasDe(ciclo, area = null, limite = 10) {
  return filasDe(ciclo, area)
    .slice()
    .sort((a, b) => b.postulaciones - a.postulaciones)
    .map(f => ({ carrera: f.carrera, caja: cajaDe(f.clave) }))
    .filter(f => f.caja)
    .slice(0, limite);
}

/** Toda la capa procesada en filas planas, para la descarga completa. */
export function baseCompleta() {
  return filas.map(f => ({
    ciclo: f.ciclo,
    area: f.area,
    area_nombre: nombreArea(f.area),
    carrera: f.carrera,
    postulaciones: f.postulaciones,
    ingresantes: f.ingresantes,
    tasa_ingreso_pct: f.fiable ? f.tasa : '',
    denominador_fiable: f.fiable ? 'si' : 'no',
    escala: f.escala,
    variacion_postulaciones_pct: f.delta ?? '',
    ingreso_mas_bajo: gold.caja[f.clave]?.min ?? '',
    ingreso_q1: gold.caja[f.clave]?.q1 ?? '',
    ingreso_mediana: gold.caja[f.clave]?.med ?? '',
    ingreso_q3: gold.caja[f.clave]?.q3 ?? '',
    ingreso_mas_alto: gold.caja[f.clave]?.max ?? '',
    ingresantes_con_puntaje: gold.caja[f.clave]?.n ?? '',
    ocupacion_vacantes_pct: gold.vacantes[f.clave]?.[0] ?? '',
    ocupacion_estado: gold.vacantes[f.clave]?.[1] ?? '',
    ...Object.fromEntries(
      MODALIDADES.map((m, i) => [`ingresantes_${m}`, gold.porModalidad[f.clave]?.[i] ?? 0])
    )
  }));
}
