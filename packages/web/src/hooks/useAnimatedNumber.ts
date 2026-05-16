import { useEffect, useRef, useState } from 'react'

type AnimatedNumberOptions = { durationMs?: number }

export function useAnimatedNumber(
  target: number,
  durationMsOrOptions: number | AnimatedNumberOptions = 700,
): number {
  const durationMs =
    typeof durationMsOrOptions === 'number'
      ? durationMsOrOptions
      : (durationMsOrOptions.durationMs ?? 700)

  const [display, setDisplay] = useState(target)
  const displayRef = useRef(target)

  useEffect(() => {
    const from = displayRef.current
    if (from === target) return

    const start = performance.now()

    const tick = (now: number) => {
      const t = Math.min(1, (now - start) / durationMs)
      const eased = 1 - (1 - t) ** 3
      const next = from + (target - from) * eased
      displayRef.current = next
      setDisplay(next)
      if (t < 1) {
        requestAnimationFrame(tick)
      } else {
        displayRef.current = target
        setDisplay(target)
      }
    }

    const frame = requestAnimationFrame(tick)
    return () => cancelAnimationFrame(frame)
  }, [target, durationMs])

  return display
}
