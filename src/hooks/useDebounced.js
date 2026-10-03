import { useEffect, useState } from 'react'

/** Returns `value` after it has stopped changing for `ms` milliseconds (for search boxes). */
export function useDebounced(value, ms = 300) {
  const [v, setV] = useState(value)
  useEffect(() => {
    const t = setTimeout(() => setV(value), ms)
    return () => clearTimeout(t)
  }, [value, ms])
  return v
}
