export interface Point {
  day: number
  survival: number
}

export interface Frame {
  width: number
  height: number
  left: number
  right: number
  top: number
  bottom: number
  maxDay: number
}

export const xOf = (f: Frame, day: number): number =>
  f.left + ((f.width - f.left - f.right) * day) / f.maxDay
export const yOf = (f: Frame, survival: number): number =>
  f.top + (f.height - f.top - f.bottom) * (1 - survival)

/** Step path: the value of day d holds until day d + 1, then drops. Survival is a
 *  step function, so points are never joined by sloping lines. */
export function stepPath(f: Frame, points: Point[]): string {
  if (points.length === 0) return ''
  const r = (n: number) => Math.round(n * 100) / 100
  let d = `M${r(xOf(f, points[0].day))},${r(yOf(f, points[0].survival))}`
  for (const p of points.slice(1)) d += `H${r(xOf(f, p.day))}V${r(yOf(f, p.survival))}`
  return d
}

/** Day under a horizontal position in viewBox units, clamped to the curve. */
export function dayAt(f: Frame, x: number): number {
  const day = Math.round(((x - f.left) / (f.width - f.left - f.right)) * f.maxDay)
  return Math.min(f.maxDay, Math.max(0, day))
}
