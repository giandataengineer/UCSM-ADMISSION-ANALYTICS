import { useState } from 'react';
import { motion } from 'motion/react';

export const VERDE = '#17512f';
export const VERDE_MEDIO = '#2a8756';
export const GRIS = '#c4cbc4';
export const COLOR_AREA = { A: '#b4e2c8', B: '#0d2f1c', C: '#48a973', D: '#17512f', E: '#c2ccc2' };
export const COLOR_MODALIDAD = ['#0d2f1c', '#1f6b42', '#2a8756', '#7cc79c', '#c8a24a', '#aab6ab'];

const mil = n => (n == null ? '—' : n.toLocaleString('es-PE'));
const dec = n => (n == null ? '—' : n.toLocaleString('es-PE', { minimumFractionDigits: 1, maximumFractionDigits: 1 }));
const corta = (s, n) => (s.length > n ? s.slice(0, n - 1) + '…' : s);

/* Globo de datos compartido por los graficos SVG. */
function useGlobo() {
  const [globo, setGlobo] = useState(null);
  const enlazar = contenido => ({
    onMouseMove: ev => {
      const svg = ev.currentTarget.ownerSVGElement ?? ev.currentTarget;
      const r = svg.getBoundingClientRect();
      setGlobo({ x: ev.clientX - r.left, y: ev.clientY - r.top, contenido });
    },
    onMouseLeave: () => setGlobo(null)
  });
  const Globo = () => (globo ? <div className="globo" style={{ left: globo.x, top: globo.y }}>{globo.contenido}</div> : null);
  return [enlazar, Globo];
}

/* ============ Puntajes maximos y minimos (piruletas verticales) ============ */
export function Piruletas({ datos, ciclo, activa, onCarrera }) {
  const [enlazar, Globo] = useGlobo();
  const ancho = 1180, alto = 430;
  const base = alto - 26, techo = 96;
  const max = Math.max(...datos.map(d => d.max), 1);
  const grupo = (ancho - 40) / Math.max(datos.length, 1);
  const y = v => base - (v / max) * (base - techo);
  const r = Math.min(23, grupo / 5.4);

  return (
    <div className="lienzo-relativo">
      <svg viewBox={`0 0 ${ancho} ${alto}`} className="grafico-svg" preserveAspectRatio="xMidYMid meet" role="img" aria-label="Puntajes maximos y minimos por carrera">
        {datos.map((d, i) => {
          const cx = 20 + grupo * i + grupo / 2;
          const xMin = cx - grupo * 0.17;
          const xMax = cx + grupo * 0.17;
            const apagada = activa && activa !== d.carrera;
          return (
            <g
              key={d.carrera}
              className="grupo-clicable"
              opacity={apagada ? 0.3 : 1}
              onClick={() => onCarrera?.(activa === d.carrera ? null : d.carrera)}
              {...enlazar(
                <>
                  <strong>{d.carrera}</strong>
                  <span>Ingreso mas alto {dec(d.max)}</span>
                  <span>Ingreso mas bajo {dec(d.min)}</span>
                  {d.n != null && <span>{mil(d.n)} ingresantes</span>}
                  <span className="globo-pista">Clic para filtrar</span>
                </>
              )}
            >
              <rect x={cx - grupo / 2} y="0" width={grupo} height={alto} fill="transparent" />
              <text x={cx} y="34" textAnchor="middle" className="piru-carrera">{corta(d.carrera, 22)}</text>
              <text x={cx} y="50" textAnchor="middle" className="piru-anio">{ciclo}</text>

              <rect x={xMin - 5} y={y(d.min)} width="10" height={base - y(d.min)} fill={GRIS} />
              <circle cx={xMin} cy={y(d.min)} r={r} fill={GRIS} />
              <text x={xMin} y={y(d.min) - r - 8} textAnchor="middle" className="piru-valor">{dec(d.min)}</text>

              <rect x={xMax - 5} y={y(d.max)} width="10" height={base - y(d.max)} fill={VERDE} />
              <circle cx={xMax} cy={y(d.max)} r={r} fill={VERDE} />
              <text x={xMax} y={y(d.max) - r - 8} textAnchor="middle" className="piru-valor">{dec(d.max)}</text>
            </g>
          );
        })}
        <line x1="12" y1={base} x2={ancho - 12} y2={base} stroke="#e4e9e3" strokeWidth="1" />
      </svg>
      <Globo />
    </div>
  );
}

/* ============ Postulaciones por carrera (barra con cabeza redonda) ============ */
export function BarrasCabeza({ datos, campo = 'postulaciones', activa, onCarrera }) {
  const max = Math.max(...datos.map(d => d[campo]), 1);
  return (
    <div className="cabeza">
      {datos.map((d, i) => (
        <button
          type="button"
          className={`cabeza-fila ${activa && activa !== d.carrera ? 'apagado' : ''} ${activa === d.carrera ? 'cabeza-activa' : ''}`}
          key={d.carrera}
          onClick={() => onCarrera?.(activa === d.carrera ? null : d.carrera)}
          title={`${d.carrera}: ${mil(d[campo])} postulaciones`}
        >
          <span className="cabeza-nombre">{d.carrera}</span>
          <span className="cabeza-pista">
            <motion.span
              className="cabeza-barra"
              initial={{ width: 0 }}
              animate={{ width: `calc(${Math.max((d[campo] / max) * 100, 6)}% )` }}
              transition={{ duration: 0.55, delay: i * 0.04, ease: [0.16, 1, 0.3, 1] }}
            >
              <span className="cabeza-valor tab-num">{mil(d[campo])}</span>
              <span className="cabeza-punto" />
            </motion.span>
          </span>
        </button>
      ))}
    </div>
  );
}

/* ============ Tabla de detalle ============ */
function Flecha({ valor }) {
  if (valor == null) return <span className="sin-dato">sin base</span>;
  const sube = valor >= 0;
  return (
    <span className={`badge-var ${sube ? 'sube' : 'baja'}`}>
      <svg viewBox="0 0 24 24" aria-hidden="true">
        <path d={sube ? 'M7 17 17 7M10 7h7v7' : 'M17 7 7 17M14 17H7v-7'} fill="none" stroke="currentColor" strokeWidth="2.4" strokeLinecap="round" strokeLinejoin="round" />
      </svg>
      {valor.toFixed(1)}%
    </span>
  );
}

export function TablaDetalle({ filas, ciclo, maxPost, activa, onCarrera }) {
  return (
    <div className="tabla-envoltura scroll-fino">
      <table className="tabla">
        <thead>
          <tr>
            <th className="col-anio">Año</th>
            <th className="col-area">Area</th>
            <th>Carrera</th>
            <th className="der">Puntaje maximo</th>
            <th className="der">Puntaje minimo</th>
            <th className="der">% incremento de postulantes</th>
            <th>Postulaciones</th>
            <th>% vacantes cubiertas</th>
          </tr>
        </thead>
        <tbody>
          {filas.map((f, i) => (
            <tr
              key={f.carrera}
              className={`fila-clicable ${activa === f.carrera ? 'fila-activa' : ''}`}
              onClick={() => onCarrera?.(activa === f.carrera ? null : f.carrera)}
            >
              <td className="col-anio tab-num">{i === 0 ? ciclo : ''}</td>
              <td className="col-area">
                <span className="chip-area" style={{ background: COLOR_AREA[f.area], color: f.area === 'A' || f.area === 'E' ? '#0d2f1c' : '#fff' }}>{f.area}</span>
              </td>
              <td className="td-carrera">{f.carrera}</td>
              <td className="der tab-num">{dec(f.entroMax)}</td>
              <td className="der tab-num">{dec(f.entroMin)}</td>
              <td className="der"><Flecha valor={f.delta} /></td>
              <td>
                <span className="celda-barra">
                  <span className="celda-relleno" style={{ width: `${(f.postulaciones / maxPost) * 100}%` }} />
                  <span className="celda-num tab-num">{mil(f.postulaciones)}</span>
                </span>
              </td>
              <td>
                {f.ocupacion == null ? (
                  <span className="sin-dato">no publicado</span>
                ) : (
                  <span className="celda-vac">
                    <span className="celda-vac-num tab-num">{f.ocupacion.toFixed(2)}%</span>
                    <span className="celda-vac-pista">
                      <span className="celda-vac-relleno" style={{ width: `${Math.min(f.ocupacion, 100)}%` }} />
                      <span className="celda-vac-marca" style={{ left: `${Math.min(f.ocupacion, 100)}%` }} />
                    </span>
                  </span>
                )}
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

/* ============ Pendiente entre dos ciclos ============ */
export function Pendiente({ datos, antes, despues }) {
  const filaAlto = 96, izq = 132, ancho = 620;
  const alto = datos.length * filaAlto + 40;
  const xa = izq + 60, xb = ancho - 96;

  return (
    <svg viewBox={`0 0 ${ancho} ${alto}`} className="grafico-svg" preserveAspectRatio="xMidYMid meet" role="img" aria-label={`Postulaciones ${antes} contra ${despues}`}>
      {datos.map((d, i) => {
        const y0 = 34 + i * filaAlto;
        const banda = y0 + 22;
        const max = Math.max(d.antes, d.despues, 1);
        const ya = banda + 40 - (d.antes / max) * 34;
        const yb = banda + 40 - (d.despues / max) * 34;
        return (
          <g key={d.carrera}>
            <text x="8" y={banda + 24} className="pend-carrera">
              {corta(d.carrera, 18).split(' ').slice(0, 2).join(' ')}
            </text>
            <text x="8" y={banda + 38} className="pend-carrera">
              {corta(d.carrera, 18).split(' ').slice(2).join(' ')}
            </text>
            <rect x={xa - 52} y={banda + 6} width="104" height="48" fill="#e8ebe7" />
            <rect x={xb - 52} y={banda + 6} width="104" height="48" fill="#e8ebe7" />
            <text x={xa} y={y0 + 2} textAnchor="middle" className="pend-valor tab-num">{mil(d.antes)}</text>
            <text x={xa} y={y0 + 16} textAnchor="middle" className="pend-anio">{antes}</text>
            <text x={xb} y={y0 + 2} textAnchor="middle" className="pend-valor tab-num">{mil(d.despues)}</text>
            <text x={xb} y={y0 + 16} textAnchor="middle" className="pend-anio">{despues}</text>
            <motion.line
              x1={xa} y1={ya} x2={xb} y2={yb}
              stroke={VERDE} strokeWidth="2.6" strokeLinecap="round"
              initial={{ pathLength: 0 }} animate={{ pathLength: 1 }}
              transition={{ duration: 0.6, delay: i * 0.05 }}
            />
            <circle cx={xa} cy={ya} r="4.5" fill={VERDE} />
            <circle cx={xb} cy={yb} r="4.5" fill={VERDE} />
          </g>
        );
      })}
      <text x={xa} y={alto - 6} textAnchor="middle" className="pend-anio">{antes}</text>
      <text x={xb} y={alto - 6} textAnchor="middle" className="pend-anio">{despues}</text>
    </svg>
  );
}

/* ============ Top de carreras ============ */
export function TopCarreras({ datos, activa, onCarrera }) {
  const max = Math.max(...datos.map(d => d.postulaciones), 1);
  const filaAlto = 38, izq = 240, ancho = 700;
  const alto = datos.length * filaAlto + 34;
  return (
    <svg viewBox={`0 0 ${ancho} ${alto}`} className="grafico-svg" preserveAspectRatio="xMidYMid meet" role="img" aria-label="Carreras mas demandadas">
      <text x={izq - 4} y="14" textAnchor="end" className="top-cabecera">Escuela profesional</text>
      {datos.map((d, i) => {
        const y = 30 + i * filaAlto;
        const w = ((d.postulaciones / max) * (ancho - izq - 24)) || 2;
        return (
          <g
            key={d.carrera}
            className="grupo-clicable"
            opacity={activa && activa !== d.carrera ? 0.32 : 1}
            onClick={() => onCarrera?.(activa === d.carrera ? null : d.carrera)}
          >
            <title>{`${d.carrera}: ${mil(d.postulaciones)} postulaciones`}</title>
            <rect x="0" y={y - 6} width={ancho} height={filaAlto - 4} fill="transparent" />
            <text x={izq - 10} y={y + 15} textAnchor="end" className="top-nombre">{corta(d.carrera, 30)}</text>
            <motion.rect
              x={izq} y={y} height="22" fill={VERDE} rx="2"
              initial={{ width: 0 }} animate={{ width: w }}
              transition={{ duration: 0.55, delay: i * 0.04, ease: [0.16, 1, 0.3, 1] }}
            />
            <text x={izq + 8} y={y + 16} className="top-valor tab-num">{mil(d.postulaciones)}</text>
          </g>
        );
      })}
    </svg>
  );
}

/* ============ Anillo por area ============ */
export function Anillo({ datos, total, campo = 'postulaciones', activa, onArea }) {
  const [hov, setHov] = useState(null);
  const cx = 240, cy = 210, R = 132, r = 88;
  const suma = datos.reduce((s, d) => s + d[campo], 0) || 1;
  let ang = -Math.PI / 2;

  const arcos = datos.map(d => {
    const barrido = (d[campo] / suma) * Math.PI * 2;
    const a0 = ang, a1 = ang + barrido - 0.008, medio = ang + barrido / 2;
    ang += barrido;
    const p = (rad, a) => [cx + rad * Math.cos(a), cy + rad * Math.sin(a)];
    const grande = barrido > Math.PI ? 1 : 0;
    const [x0, y0] = p(R, a0), [x1, y1] = p(R, a1), [x2, y2] = p(r, a1), [x3, y3] = p(r, a0);
    const [lx, ly] = p(R + 44, medio);
    return {
      ...d,
      pct: (d[campo] / suma) * 100,
      lx, ly,
      anclaje: Math.cos(medio) > 0.08 ? 'start' : Math.cos(medio) < -0.08 ? 'end' : 'middle',
      d: `M${x0} ${y0}A${R} ${R} 0 ${grande} 1 ${x1} ${y1}L${x2} ${y2}A${r} ${r} 0 ${grande} 0 ${x3} ${y3}Z`
    };
  });

  return (
    <svg viewBox="0 0 480 420" className="grafico-svg" preserveAspectRatio="xMidYMid meet" role="img" aria-label="Distribucion por area">
      {arcos.map(a => (
        <g
          key={a.cod}
          className="grupo-clicable"
          onMouseEnter={() => setHov(a.cod)}
          onMouseLeave={() => setHov(null)}
          onClick={() => onArea?.(activa === a.cod ? null : a.cod)}
        >
          <title>{`${a.cod}: ${a.nombre} — ${mil(a[campo])} postulaciones`}</title>
          <path
            d={a.d}
            fill={COLOR_AREA[a.cod]}
            stroke={activa === a.cod ? '#0d2f1c' : 'transparent'}
            strokeWidth="2.5"
            opacity={(hov && hov !== a.cod) || (activa && activa !== a.cod) ? 0.38 : 1}
            style={{ transition: 'opacity .18s' }}
          />
          <text x={a.lx} y={a.ly} textAnchor={a.anclaje} className="anillo-rot">Area {a.cod}</text>
          <text x={a.lx} y={a.ly + 17} textAnchor={a.anclaje} className="anillo-pct tab-num">{a.pct.toFixed(2)}%</text>
        </g>
      ))}
      <text x={cx} y={cy + 2} textAnchor="middle" className="anillo-total tab-num">{mil(total)}</text>
      <text x={cx} y={cy + 22} textAnchor="middle" className="anillo-pie">postulaciones</text>
    </svg>
  );
}

/* ============ Cajas de puntaje de ingresantes ============ */
export function Cajas({ datos, activa, onCarrera }) {
  const [enlazar, Globo] = useGlobo();
  const ancho = 1180, alto = 480, base = alto - 58, techo = 24;
  const todos = datos.flatMap(d => [d.caja.min, d.caja.max]);
  const lo = Math.min(...todos), hi = Math.max(...todos);
  const grupo = (ancho - 60) / Math.max(datos.length, 1);
  const y = v => base - ((v - lo) / (hi - lo || 1)) * (base - techo);
  const bw = Math.min(56, grupo * 0.42);

  return (
    <div className="lienzo-relativo">
      <svg viewBox={`0 0 ${ancho} ${alto}`} className="grafico-svg" preserveAspectRatio="xMidYMid meet" role="img" aria-label="Distribucion de puntajes de los ingresantes">
        {datos.map((d, i) => {
          const cx = 40 + grupo * i + grupo / 2;
          const c = d.caja;
          return (
            <g
              key={d.carrera}
              className="grupo-clicable"
              opacity={activa && activa !== d.carrera ? 0.28 : 1}
              onClick={() => onCarrera?.(activa === d.carrera ? null : d.carrera)}
              {...enlazar(
              <>
                <strong>{d.carrera}</strong>
                <span>Maximo {dec(c.max)} · Q3 {dec(c.q3)}</span>
                <span>Mediana {dec(c.med)}</span>
                <span>Q1 {dec(c.q1)} · Minimo {dec(c.min)}</span>
                <span>{mil(c.n)} ingresantes</span>
                <span className="globo-pista">Clic para filtrar</span>
              </>
            )}
            >
              <rect x={cx - grupo / 2} y="0" width={grupo} height={alto} fill="transparent" />
              <line x1={cx} y1={y(c.min)} x2={cx} y2={y(c.max)} stroke="#8f9b90" strokeWidth="1" />
              <line x1={cx - bw / 2} y1={y(c.max)} x2={cx + bw / 2} y2={y(c.max)} stroke="#546156" strokeWidth="1.4" />
              <line x1={cx - bw / 2} y1={y(c.min)} x2={cx + bw / 2} y2={y(c.min)} stroke="#546156" strokeWidth="1.4" />
              <rect x={cx - bw / 2} y={y(c.q3)} width={bw} height={Math.max(y(c.q1) - y(c.q3), 2)} fill="#dfe4de" />
              <rect x={cx - bw / 2} y={y(c.med)} width={bw} height={Math.max(y(c.q1) - y(c.med), 2)} fill="#c3ccc3" />
              <line x1={cx - bw / 2} y1={y(c.med)} x2={cx + bw / 2} y2={y(c.med)} stroke="#7d8a7f" strokeWidth="1.4" />
              {c.puntos.map((p, j) => (
                <circle
                  key={j}
                  cx={cx + (((j * 37) % 17) - 8) * (bw / 26)}
                  cy={y(p)}
                  r="3.4"
                  fill={VERDE}
                  opacity="0.72"
                />
              ))}
              <text x={cx} y={base + 22} textAnchor="middle" className="caja-rot">{corta(d.carrera.split(' ')[0], 14)}</text>
              <text x={cx} y={base + 36} textAnchor="middle" className="caja-rot">
                {corta(d.carrera.split(' ').slice(1).join(' '), 16)}
              </text>
            </g>
          );
        })}
      </svg>
      <Globo />
    </div>
  );
}
