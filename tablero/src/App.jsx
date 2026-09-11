import { useMemo, useState } from 'react';
import { motion } from 'motion/react';
import { toPng } from 'html-to-image';
import Counter from './components/Counter';
import {
  Piruletas, BarrasCabeza, TablaDetalle, Pendiente, TopCarreras, Anillo, Cajas, COLOR_AREA
} from './components/charts';
import {
  CICLOS, AREAS, kpis, filasDe, porArea, serieCiclos, pendiente, cajasDe, cajaDe, vacantesDe, nombreArea, escalaDe, baseCompleta
} from './lib/data';
import './App.css';

const mil = n => (n == null ? '—' : n.toLocaleString('es-PE'));
const LINKEDIN = 'https://www.linkedin.com/in/giandataengineer/';

function bajar(url, nombre) {
  const a = document.createElement('a');
  a.href = url;
  a.download = nombre;
  a.click();
}

/** Comillas dobles y separadores dentro del valor romperian el CSV. */
function aCsv(filas) {
  if (!filas.length) return '';
  const cols = Object.keys(filas[0]);
  const celda = v => {
    const t = String(v ?? '');
    return /[",\n]/.test(t) ? `"${t.replace(/"/g, '""')}"` : t;
  };
  return [cols.join(','), ...filas.map(f => cols.map(c => celda(f[c])).join(','))].join('\n');
}

function descargarCsv(filas, nombre) {
  const url = URL.createObjectURL(new Blob(['\uFEFF' + aCsv(filas)], { type: 'text/csv;charset=utf-8' }));
  bajar(url, nombre);
  URL.revokeObjectURL(url);
}

/** Exporta a PNG lo que se ve, al doble de resolucion. */
async function descargarImagen(nombre) {
  const nodo = document.querySelector('.lienzo-interior');
  if (!nodo) return;
  const url = await toPng(nodo, {
    pixelRatio: 2,
    backgroundColor: '#f2f5f0',
    filter: n => !(n.classList && n.classList.contains('barra-exportar'))
  });
  bajar(url, nombre);
}

/* Los tres controles de exportacion, iguales en las dos hojas. */
function BarraExportar({ nombreBase, filasVisibles }) {
  const [ocupado, setOcupado] = useState(null);

  const conEstado = (clave, fn) => async () => {
    setOcupado(clave);
    try { await fn(); } finally { setOcupado(null); }
  };

  return (
    <span className="barra-exportar">
      <button
        type="button"
        title="Descargar la base procesada completa: 244 filas, los 7 ciclos y las 47 carreras"
        aria-label="Descargar la base procesada completa en CSV"
        onClick={conEstado('csv', () => descargarCsv(baseCompleta(), 'admision_ucsm_2021_2027.csv'))}
      >
        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.7" strokeLinecap="round" strokeLinejoin="round">
          <ellipse cx="12" cy="5.6" rx="7.4" ry="2.8" />
          <path d="M4.6 5.6v6.8c0 1.55 3.31 2.8 7.4 2.8s7.4-1.25 7.4-2.8V5.6" />
          <path d="M4.6 12.4v5.2c0 1.55 3.31 2.8 7.4 2.8" />
          <path d="M17.4 15.6v5.2m0 0 2.4-2.4m-2.4 2.4-2.4-2.4" />
        </svg>
        {ocupado === 'csv' && <span className="punto-ocupado" />}
      </button>

      <button
        type="button"
        title="Guardar esta hoja en PDF con el dialogo de impresion"
        aria-label="Guardar la hoja en PDF"
        onClick={() => window.print()}
      >
        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.7" strokeLinecap="round" strokeLinejoin="round">
          <path d="M7 9V3h7l3 3v3" />
          <path d="M7 19H5.4A2.4 2.4 0 0 1 3 16.6v-3.4A2.4 2.4 0 0 1 5.4 10.8h13.2A2.4 2.4 0 0 1 21 13.2v3.4a2.4 2.4 0 0 1-2.4 2.4H17" />
          <path d="M7 15h10v6H7z" />
        </svg>
      </button>

      <button
        type="button"
        title="Guardar como imagen PNG lo que se ve en pantalla"
        aria-label="Guardar la vista como imagen PNG"
        onClick={conEstado('png', () => descargarImagen(`${nombreBase}.png`))}
      >
        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.7" strokeLinecap="round" strokeLinejoin="round">
          <rect x="3" y="5" width="18" height="14" rx="2.4" />
          <circle cx="8.6" cy="10" r="1.6" />
          <path d="m3.6 17.4 4.6-4.3 3.5 3.1 3.3-3.1 5.4 5" />
        </svg>
        {ocupado === 'png' && <span className="punto-ocupado" />}
      </button>
      <span className="visualmente-oculto" aria-live="polite">
        {ocupado === 'csv' ? 'Preparando el CSV' : ocupado === 'png' ? 'Generando la imagen' : ''}
      </span>
      <span hidden>{filasVisibles?.length}</span>
    </span>
  );
}

const ICONO = {
  postulaciones: <><circle cx="9" cy="8" r="3.2" /><circle cx="16.6" cy="9.2" r="2.4" /><path d="M3.4 19c0-3.2 2.6-5.2 5.6-5.2s5.6 2 5.6 5.2" /><path d="M16.4 14c2.5.2 4.4 2 4.4 5" /></>,
  ingresantes: <><path d="M8 4h8v4a4 4 0 0 1-8 0V4Z" /><path d="M8 5.5H5.4v1.2A3.2 3.2 0 0 0 8.6 10" /><path d="M16 5.5h2.6v1.2A3.2 3.2 0 0 1 15.4 10" /><path d="M12 12v4M9 20h6M10.5 16h3l.6 4h-4.2l.6-4Z" /></>,
  tasa: <><circle cx="12" cy="12" r="8.4" /><path d="M12 3.6V12l6 3.6" /></>
};

function Variacion({ valor, invertir = false }) {
  if (valor == null) return <span className="kpi-sin">sin base comparable</span>;
  const sube = valor >= 0;
  const bueno = invertir ? !sube : sube;
  return <span className={`kpi-var ${bueno ? 'alza' : 'baja'}`}>{sube ? '▲' : '▼'}{Math.abs(valor).toFixed(2)}%</span>;
}

/* Serie de los siete ciclos, compacta, dentro del propio indicador. */
function Chispa({ serie, campo, ciclo }) {
  const datos = serie.filter(d => d[campo] != null);
  if (datos.length < 2) return null;
  const vals = datos.map(d => d[campo]);
  const lo = Math.min(...vals), hi = Math.max(...vals);
  const ancho = 120, alto = 20;
  const x = i => (i / (datos.length - 1)) * (ancho - 6) + 3;
  const y = v => alto - 3 - ((v - lo) / (hi - lo || 1)) * (alto - 7);
  const linea = datos.map((d, i) => `${i ? 'L' : 'M'}${x(i).toFixed(1)} ${y(d[campo]).toFixed(1)}`).join(' ');
  const iAct = datos.findIndex(d => d.ciclo === ciclo);

  return (
    <svg viewBox={`0 0 ${ancho} ${alto}`} className="chispa" aria-hidden="true">
      <defs>
        <linearGradient id={`chispa-${campo}`} x1="0" y1="0" x2="0" y2="1">
          <stop offset="0%" stopColor="#0ed85e" stopOpacity="0.3" />
          <stop offset="100%" stopColor="#0ed85e" stopOpacity="0" />
        </linearGradient>
      </defs>
      <path d={`${linea}L${x(datos.length - 1)} ${alto}L${x(0)} ${alto}Z`} fill={`url(#chispa-${campo})`} />
      <motion.path
        d={linea} fill="none" stroke="var(--color-v400)" strokeWidth="1.7"
        strokeLinecap="round" strokeLinejoin="round"
        initial={{ pathLength: 0 }} animate={{ pathLength: 1 }}
        transition={{ duration: 0.85, ease: 'easeOut' }}
      />
      {iAct >= 0 && (
        <motion.circle
          cx={x(iAct)} cy={y(datos[iAct][campo])} r="2.9"
          fill="var(--color-hondo)" stroke="var(--color-papel)" strokeWidth="1.5"
          initial={{ scale: 0 }} animate={{ scale: 1 }}
          transition={{ type: 'spring', stiffness: 220, damping: 14, delay: 0.55 }}
          style={{ transformOrigin: `${x(iAct)}px ${y(datos[iAct][campo])}px` }}
        />
      )}
    </svg>
  );
}

function TarjetaKpi({ icono, rotulo, ciclo, valor, sufijo = '', variacion, decimales = 0, alcance, chispa, retraso = 0 }) {
  return (
    <motion.article className="kpi" initial={{ opacity: 0, y: 12 }} animate={{ opacity: 1, y: 0 }} transition={{ duration: 0.35, delay: retraso }}>
      <span className="kpi-medalla" aria-hidden="true">
        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.6" strokeLinecap="round" strokeLinejoin="round">{ICONO[icono]}</svg>
      </span>
      <p className="kpi-rotulo">{rotulo} <span className="kpi-barra">|</span> {ciclo}</p>
      <p className="kpi-cifra">
        {valor == null ? <span className="kpi-nulo">no calculable</span> : <Counter value={decimales ? +valor.toFixed(2) : valor} fontSize={40} />}
        {valor != null && sufijo}
      </p>
      <Variacion valor={variacion} />
      {chispa}
      {alcance && <p className="kpi-alcance">{alcance}</p>}
    </motion.article>
  );
}

/* ---------------- Hoja 1: HOME ---------------- */
function Home({ ciclo, setCiclo, area, setArea, carrera, setCarrera, irAnalisis }) {
  const k = useMemo(() => kpis(ciclo, area), [ciclo, area]);
  const todas = useMemo(() => filasDe(ciclo, area).slice().sort((a, b) => b.postulaciones - a.postulaciones), [ciclo, area]);
  // El rango que interesa es el de quienes entraron. El minimo sobre todos los
  // postulantes incluye examenes en blanco y no dice nada del corte real.
  const filas = useMemo(
    () => (carrera ? todas.filter(f => f.carrera === carrera) : todas).map(f => {
      const c = cajaDe(f.clave);
      return { ...f, ocupacion: vacantesDe(f.clave)?.[0] ?? null, entroMin: c?.min ?? null, entroMax: c?.max ?? null, ingCaja: c?.n ?? null };
    }),
    [todas, carrera]
  );
  const areasRes = useMemo(() => porArea(ciclo), [ciclo]);
  const totalPost = areasRes.reduce((s, a) => s + a.postulaciones, 0);

  const serie = useMemo(() => serieCiclos(area), [area]);
  const conPuntaje = filas.filter(f => f.entroMin != null).slice(0, 8)
    .map(f => ({ carrera: f.carrera, min: f.entroMin, max: f.entroMax, n: f.ingCaja }));
  const topPost = filas.slice(0, 7).map(f => ({ carrera: f.carrera, postulaciones: f.postulaciones }));
  const maxPost = Math.max(...filas.map(f => f.postulaciones), 1);

  return (
    <div className="hoja hoja-home">
      <aside className="lateral">
        <p className="lateral-titulo">Resultado</p>
        <p className="lateral-subtitulo">del examen de admision</p>

        <div className="lateral-escudo">
          <img src="/img/ucsm-vivo.png" alt="Escudo de la Universidad Catolica de Santa Maria" width="1200" height="1200" />
          <p className="lateral-sigla">UCSM</p>
        </div>

        <div className="lateral-areas">
          {AREAS.map(a => {
            const total = areasRes.find(x => x.cod === a.cod)?.postulaciones ?? 0;
            const activa = area === a.cod;
            return (
              <button
                key={a.cod}
                type="button"
                className={`area-pastilla ${activa ? 'area-activa' : ''}`}
                onClick={() => { setArea(activa ? null : a.cod); setCarrera(null); }}
                aria-pressed={activa}
              >
                <span className="area-titulo">{a.cod}: {a.nombre}</span>
                <span className="area-medidor">
                  <span className="area-relleno" style={{ width: `${totalPost ? (total / totalPost) * 100 : 0}%` }} />
                  <span className="area-cifra tab-num">{mil(total)} post</span>
                </span>
              </button>
            );
          })}
        </div>

        <button type="button" className="boton-analisis" onClick={irAnalisis}>Analisis por carrera</button>

        <a className="lateral-linkedin" href={LINKEDIN} target="_blank" rel="noreferrer">
          <svg viewBox="0 0 24 24" fill="currentColor" aria-hidden="true">
            <path d="M4.98 3.5a2.5 2.5 0 1 1 0 5 2.5 2.5 0 0 1 0-5ZM3 9h4v12H3V9Zm7 0h3.8v1.7h.05c.53-1 1.83-2.05 3.77-2.05 4.03 0 4.78 2.65 4.78 6.1V21h-4v-5.4c0-1.29-.02-2.95-1.8-2.95-1.8 0-2.07 1.4-2.07 2.85V21h-4V9Z" />
          </svg>
          <span>Gian<br />Cruz</span>
        </a>
      </aside>

      <div className="tablero">
        <div className="kpis">
          <TarjetaKpi icono="postulaciones" rotulo="Postulaciones" ciclo={ciclo} valor={k.postulaciones} variacion={k.deltaPost}
            chispa={<Chispa serie={serie} campo="postulaciones" ciclo={ciclo} />} />
          <TarjetaKpi icono="ingresantes" rotulo="Ingresantes" ciclo={ciclo} valor={k.ingresantes} variacion={k.deltaIng} retraso={0.05}
            chispa={<Chispa serie={serie} campo="ingresantes" ciclo={ciclo} />} />
          <TarjetaKpi icono="tasa" rotulo="% Ingreso" ciclo={ciclo} valor={k.tasa} sufijo="%" decimales={2} variacion={k.deltaTasa} retraso={0.1}
            chispa={<Chispa serie={serie} campo="tasa" ciclo={ciclo} />}
            alcance={k.tasa == null ? 'las actas de este ciclo no publican el total de postulantes' : `sobre las ${k.carrerasFiables} de ${k.carreras} carreras con denominador fiable`} />
        </div>

        <div className="filtros">
          <label className="filtro">
            <span>Carrera:</span>
            <select value={carrera ?? ''} onChange={e => setCarrera(e.target.value || null)}>
              <option value="">Todas</option>
              {todas.map(f => <option key={f.carrera} value={f.carrera}>{f.carrera}</option>)}
            </select>
          </label>
          <label className="filtro">
            <span>Año:</span>
            <select value={ciclo} onChange={e => { setCiclo(e.target.value); setCarrera(null); }}>
              {CICLOS.map(c => <option key={c} value={c}>{c}</option>)}
            </select>
          </label>
          <label className="filtro">
            <span>Area:</span>
            <select value={area ?? ''} onChange={e => { setArea(e.target.value || null); setCarrera(null); }}>
              <option value="">Todo</option>
              {AREAS.map(a => <option key={a.cod} value={a.cod}>{a.cod}: {a.nombre}</option>)}
            </select>
          </label>
          {carrera && (
            <button type="button" className="chip-filtro" onClick={() => setCarrera(null)}>
              {carrera}
              <span aria-hidden="true">×</span>
              <span className="visualmente-oculto">Quitar el filtro de carrera</span>
            </button>
          )}
          <BarraExportar nombreBase={`admision-ucsm-${ciclo}${area ? "-area" + area : ""}`} filasVisibles={filas} />
        </div>

        <div className="fila-media">
          <section className="tarjeta tarjeta-piruletas">
            <header className="tarjeta-cab">
              <h2>Puntaje de ingreso, mas bajo y mas alto</h2>
              <div className="leyenda">
                <span><i style={{ background: '#c4cbc4' }} />Mas bajo</span>
                <span><i style={{ background: '#17512f' }} />Mas alto</span>
              </div>
            </header>
            {conPuntaje.length
              ? <Piruletas datos={conPuntaje} ciclo={ciclo} activa={carrera} onCarrera={setCarrera} />
              : <p className="vacio">Las actas de {ciclo} no publican puntajes para esta seleccion.</p>}
          </section>

          <section className="tarjeta tarjeta-postulantes">
            <header className="tarjeta-cab"><h2>Postulaciones por carrera</h2></header>
            <BarrasCabeza datos={topPost} activa={carrera} onCarrera={setCarrera} />
          </section>
        </div>

        <section className="tarjeta tarjeta-tabla">
          <TablaDetalle filas={filas} ciclo={ciclo} maxPost={maxPost} activa={carrera} onCarrera={setCarrera} />
        </section>

      </div>

        <p className="nota-pie">
          {area ? nombreArea(area) : 'Todas las areas'} · escala {escalaDe(ciclo) === 'vigente' ? 'vigente desde 2024' : 'anterior a 2024'}.
          Los puntajes de antes y despues de 2024 no son comparables entre si. El % de ingreso se calcula solo sobre las{' '}
          {k.carrerasFiables} de {k.carreras} carreras cuyas actas publican el total de postulantes. La ocupacion de vacantes va marcada como provisional
          porque mezcla la seleccion del centro preuniversitario con la admision ordinaria. El rango de puntaje
          describe a los ingresantes: el minimo sobre todos los postulantes llega a cero porque hay examenes en blanco,
          y ese numero no dice nada del corte.
      </p>
    </div>
  );
}

/* ---------------- Hoja 2: ANALISIS POR CARRERA ---------------- */
function Analisis({ ciclo, area, setArea, carrera, setCarrera, volver }) {
  const pend = useMemo(() => pendiente(ciclo, area, 9), [ciclo, area]);
  const top = useMemo(
    () => filasDe(ciclo, area).slice().sort((a, b) => b.postulaciones - a.postulaciones).slice(0, 10)
      .map(f => ({ carrera: f.carrera, postulaciones: f.postulaciones })),
    [ciclo, area]
  );
  const areasRes = useMemo(() => porArea(ciclo), [ciclo]);
  const cajas = useMemo(() => cajasDe(ciclo, area, 10), [ciclo, area]);
  const total = areasRes.reduce((s, a) => s + a.postulaciones, 0);

  return (
    <div className="hoja hoja-analisis">
      <div className="analisis-acciones">
        <BarraExportar nombreBase={`admision-ucsm-analisis-${ciclo}`} />
        <button type="button" className="boton-volver" onClick={volver} aria-label="Volver al tablero principal">
        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.2" strokeLinecap="round" strokeLinejoin="round">
            <path d="M4 9h11a5 5 0 0 1 0 10H9" /><path d="M8 4 3.5 9 8 13.5" />
          </svg>
        </button>
      </div>

      <section className="tarjeta tarjeta-pendiente">
        <header className="tarjeta-cab"><h2>Incremento de postulaciones por año y carrera</h2></header>
        {pend.datos.length
          ? <Pendiente datos={pend.datos} antes={pend.prev} despues={pend.ciclo} activa={carrera} onCarrera={setCarrera} />
          : <p className="vacio">{ciclo} es el primer proceso de la serie: no hay año anterior con que compararlo.</p>}
      </section>

      <section className="tarjeta tarjeta-top">
        <header className="tarjeta-cab"><h2>Diez carreras mas demandadas</h2></header>
        <TopCarreras datos={top} activa={carrera} onCarrera={setCarrera} />
      </section>

      <section className="tarjeta tarjeta-anillo">
        <header className="tarjeta-cab"><h2>Distribucion por areas</h2></header>
        <Anillo datos={areasRes} total={total} activa={area} onArea={a => { setArea(a); setCarrera(null); }} />
      </section>

      <section className="tarjeta tarjeta-cajas">
        <header className="tarjeta-cab">
          <h2>Distribucion del puntaje de los ingresantes</h2>
          <p className="tarjeta-apunte">Caja de cuartiles sobre los puntajes individuales publicados en las actas de {ciclo}</p>
        </header>
        {cajas.length
          ? <Cajas datos={cajas} activa={carrera} onCarrera={setCarrera} />
          : <p className="vacio">Las actas de {ciclo} no publican puntajes individuales para esta seleccion.</p>}
      </section>
    </div>
  );
}

/* ---------------- Marco tipo Tableau ---------------- */
const HOJAS = [
  { id: 'home', nombre: 'HOME' },
  { id: 'analisis', nombre: 'ANALISIS POR CARRERA' }
];

export default function App() {
  // La hoja vive en el hash, asi cada una tiene enlace propio.
  const [hoja, setHojaEstado] = useState(
    () => (HOJAS.some(h => h.id === window.location.hash.slice(1)) ? window.location.hash.slice(1) : 'home')
  );
  const setHoja = id => {
    window.location.hash = id;
    setHojaEstado(id);
  };
  const [ciclo, setCiclo] = useState('2025');
  const [area, setArea] = useState(null);
  const [carrera, setCarrera] = useState(null);

  return (
    <div className="tableau">
      <div className="lienzo">
        <motion.div
          key={hoja}
          initial={{ opacity: 0, y: 8 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.28, ease: [0.16, 1, 0.3, 1] }}
          className="lienzo-interior"
        >
          {hoja === 'home' ? (
              <Home
                ciclo={ciclo} setCiclo={setCiclo}
                area={area} setArea={setArea}
                carrera={carrera} setCarrera={setCarrera}
                irAnalisis={() => setHoja('analisis')}
              />
            ) : (
            <Analisis ciclo={ciclo} area={area} setArea={setArea} carrera={carrera} setCarrera={setCarrera} volver={() => setHoja('home')} />
          )}
        </motion.div>
      </div>

      <div className="pestanas" role="tablist" aria-label="Hojas del tablero">
        <div className="pestanas-nav" aria-hidden="true">
          <span>⏮</span><span>◀</span><span>▶</span><span>⏭</span>
        </div>
        {HOJAS.map(h => (
          <button
            key={h.id}
            role="tab"
            aria-selected={hoja === h.id}
            className={`pestana ${hoja === h.id ? 'pestana-activa' : ''}`}
            onClick={() => setHoja(h.id)}
          >
            {h.nombre}
          </button>
        ))}
        <div className="pestanas-pie">
          <a href={LINKEDIN} target="_blank" rel="noreferrer">linkedin.com/in/giandataengineer</a>
        </div>
      </div>
    </div>
  );
}
