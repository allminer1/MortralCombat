import { useEffect, useRef, useState, type PointerEvent } from 'react'
import { useTranslation } from 'react-i18next'
import { dayAt, stepPath, xOf, yOf, type Frame, type Point } from '../lib/curve'
import { percent0, percent1 } from '../lib/format'

/** From this day the baseline table is sparse (spec 7.3; owner may change it). */
export const LATE_FROM_DAY = 56
const MARGINS = { left: 52, right: 16, top: 16, bottom: 44, maxDay: 100 }

/** The drawing is sized in real pixels of its container, so axis labels keep their
 *  size on a phone instead of shrinking with the picture. */
function useFrame(): [React.RefObject<HTMLDivElement | null>, Frame] {
  const ref = useRef<HTMLDivElement>(null)
  const [width, setWidth] = useState(640)
  useEffect(() => {
    const node = ref.current
    if (!node) return
    const observer = new ResizeObserver(([entry]) => setWidth(Math.max(240, Math.round(entry.contentRect.width))))
    observer.observe(node)
    return () => observer.disconnect()
  }, [])
  const height = Math.round(Math.min(340, Math.max(230, width * 0.56)))
  return [ref, { ...MARGINS, width, height }]
}
const X_TICKS = [0, 7, 28, LATE_FROM_DAY, 100]
const Y_TICKS = [0, 0.25, 0.5, 0.75, 1]

export function SurvivalCurve({ points, marked }: { points: Point[] | null; marked: number[] }) {
  const { t, i18n } = useTranslation()
  const lang = i18n.resolvedLanguage ?? 'en'
  const [day, setDay] = useState(28)
  const [frameRef, f] = useFrame()
  const bottom = yOf(f, 0)
  const lateX = xOf(f, LATE_FROM_DAY)
  const early = points?.filter((p) => p.day <= LATE_FROM_DAY) ?? []
  const late = points?.filter((p) => p.day >= LATE_FROM_DAY) ?? []
  const selected = points?.find((p) => p.day === day) ?? null

  const onPointer = (event: PointerEvent<SVGSVGElement>) => {
    // A resting mouse gets synthetic move events when the page layout shifts under it;
    // those must not override a day chosen with the keyboard.
    if (event.pointerType === 'mouse' && event.type === 'pointermove' && event.movementX === 0 && event.movementY === 0) return
    const box = event.currentTarget.getBoundingClientRect()
    setDay(dayAt(f, event.clientX - box.left))
  }
  return (
    <figure className="m-0">
      <figcaption className="font-semibold">{t('result.curveTitle')}</figcaption>
      {/* The drawing is taken out of the flow so that it can never widen the page. */}
      <div ref={frameRef} className="relative mt-2 w-full overflow-hidden" style={{ height: f.height }}>
      <svg
        width={f.width}
        height={f.height}
        viewBox={`0 0 ${f.width} ${f.height}`}
        className="absolute top-0 left-0 block touch-pan-y select-none"
        role="img"
        aria-label={t('result.curveTitle')}
        onPointerMove={points ? onPointer : undefined}
        onPointerDown={points ? onPointer : undefined}
      >
        <defs>
          <pattern id="late-hatch" width="6" height="6" patternUnits="userSpaceOnUse" patternTransform="rotate(45)">
            <line x1="0" y1="0" x2="0" y2="6" stroke="var(--color-rule)" strokeWidth="1.5" />
          </pattern>
        </defs>
        <rect x={lateX} y={f.top} width={xOf(f, f.maxDay) - lateX} height={bottom - f.top} fill="url(#late-hatch)" opacity="0.55" />

        {Y_TICKS.map((v) => (
          <g key={v}>
            <line x1={f.left} x2={xOf(f, f.maxDay)} y1={yOf(f, v)} y2={yOf(f, v)} stroke="var(--color-rule)" strokeWidth={v === 0 ? 1.5 : 1} />
            <text x={f.left - 8} y={yOf(f, v) + 4} textAnchor="end" fontSize="13" fill="var(--color-muted)">
              {percent0(v, lang)}
            </text>
          </g>
        ))}
        {X_TICKS.map((d) => (
          <g key={d}>
            <line x1={xOf(f, d)} x2={xOf(f, d)} y1={bottom} y2={bottom + 5} stroke="var(--color-muted)" />
            <text x={xOf(f, d)} y={bottom + 20} textAnchor="middle" fontSize="13" fill="var(--color-muted)">
              {d}
            </text>
          </g>
        ))}
        <text x={xOf(f, f.maxDay)} y={f.height - 4} textAnchor="end" fontSize="13" fill="var(--color-muted)">
          {t('result.axisDay')}
        </text>
        <line x1={lateX} x2={lateX} y1={f.top} y2={bottom} stroke="var(--color-muted)" strokeDasharray="2 4" />

        {points && (
          <>
            <path d={stepPath(f, early)} fill="none" stroke="var(--color-accent)" strokeWidth="2.75" strokeLinejoin="round" />
            <path d={stepPath(f, late)} fill="none" stroke="var(--color-accent)" strokeWidth="1.75" strokeDasharray="5 4" opacity="0.75" />
            {marked.map((d) => {
              const p = points.find((q) => q.day === d)
              return p ? <circle key={d} cx={xOf(f, d)} cy={yOf(f, p.survival)} r="4.5" fill="var(--color-surface)" stroke="var(--color-accent)" strokeWidth="2.5" /> : null
            })}
            {selected && (
              <g>
                <line x1={xOf(f, day)} x2={xOf(f, day)} y1={f.top} y2={bottom} stroke="var(--color-ink)" strokeWidth="1" />
                <circle cx={xOf(f, day)} cy={yOf(f, selected.survival)} r="5.5" fill="var(--color-ink)" />
              </g>
            )}
          </>
        )}
      </svg>
      </div>

      {points && selected && (
        <div className="mt-2 flex flex-wrap items-center gap-x-4 gap-y-2">
          <input
            type="range"
            min={0}
            max={f.maxDay}
            step={1}
            value={day}
            onChange={(e) => setDay(Number(e.target.value))}
            aria-label={t('result.curveSlider')}
            aria-valuetext={t('result.readout', { day, value: percent1(selected.survival, lang) })}
            className="h-11 min-w-40 flex-1 accent-(--color-accent)"
          />
          <output className="min-w-36 text-lg font-medium tabular-nums" data-testid="curve-readout">
            {t('result.readout', { day, value: percent1(selected.survival, lang) })}
          </output>
        </div>
      )}
      <p className="mt-2 max-w-[68ch] text-[0.9rem] text-muted">
        {points && <>{t('result.curveHelp')} </>}
        {t('result.lateNote', { day: LATE_FROM_DAY })}
      </p>

      {points && (
        <details className="mt-3">
          <summary className="cursor-pointer text-accent underline underline-offset-2">{t('result.tableToggle')}</summary>
          <div className="sr-only-table-scroll mt-2 rounded-md border border-rule" tabIndex={0} role="region" aria-label={t('result.tableCaption')}>
            <table className="w-full border-collapse text-left tabular-nums">
              <caption className="sr-only">{t('result.tableCaption')}</caption>
              <thead className="sticky top-0 bg-page">
                <tr>
                  <th scope="col" className="px-3 py-1.5 font-semibold">{t('result.axisDay')}</th>
                  <th scope="col" className="px-3 py-1.5 font-semibold">{t('result.axisSurvival')}</th>
                </tr>
              </thead>
              <tbody>
                {points.map((p) => (
                  <tr key={p.day} className="border-t border-rule">
                    <td className="px-3 py-1">{p.day}</td>
                    <td className="px-3 py-1">{percent1(p.survival, lang)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </details>
      )}
    </figure>
  )
}
