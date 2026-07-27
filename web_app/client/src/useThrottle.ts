import { useCallback, useEffect, useRef } from 'react'

/**
 * A throttled wrapper around `fn`: runs immediately, then at most once per `ms`
 * while called repeatedly, and always runs one final time with the latest args
 * after the calls stop (leading + trailing). Built for sliders / color pickers,
 * which fire a flood of onChange events during a single drag — this collapses
 * them into a steady trickle plus a guaranteed final value on release.
 */
export function useThrottledCallback<A extends unknown[]>(
  fn: (...args: A) => void,
  ms: number,
): (...args: A) => void {
  const fnRef = useRef(fn)
  const last = useRef(0)
  const timer = useRef<ReturnType<typeof setTimeout> | null>(null)
  const latest = useRef<A | null>(null)

  useEffect(() => {
    fnRef.current = fn
  })
  useEffect(
    () => () => {
      if (timer.current) clearTimeout(timer.current)
    },
    [],
  )

  return useCallback(
    (...args: A) => {
      latest.current = args
      const wait = ms - (Date.now() - last.current)
      if (wait <= 0) {
        if (timer.current) {
          clearTimeout(timer.current)
          timer.current = null
        }
        last.current = Date.now()
        fnRef.current(...args)
      } else if (timer.current === null) {
        // schedule the trailing call to land at the end of this window
        timer.current = setTimeout(() => {
          timer.current = null
          last.current = Date.now()
          if (latest.current) fnRef.current(...latest.current)
        }, wait)
      }
    },
    [ms],
  )
}
