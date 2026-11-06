import { useCallback, useEffect, useRef, useState } from 'react'

/**
 * Loads data from a service function and tracks loading / error state.
 *
 *   const { data, loading, error, reload, setData } = useQuery(signal => dashboardService.get({ signal }), [])
 *
 * - `deps` re-run the query when they change (like useEffect deps).
 * - `pollInterval` (ms) re-fetches silently while `shouldPoll(data)` returns true.
 * - `setData` lets pages apply optimistic updates after a mutation.
 */
export function useQuery(fetcher, deps = [], { enabled = true, initialData, pollInterval, shouldPoll } = {}) {
  const [state, setState] = useState({ data: initialData, loading: enabled, error: null })
  const fetchRef = useRef(fetcher)
  fetchRef.current = fetcher
  const ctrlRef = useRef(null)

  const load = useCallback(async ({ silent = false } = {}) => {
    ctrlRef.current?.abort()
    const ctrl = new AbortController()
    ctrlRef.current = ctrl
    if (!silent) setState(s => ({ ...s, loading: true, error: null }))
    try {
      const data = await fetchRef.current(ctrl.signal)
      if (!ctrl.signal.aborted) setState({ data, loading: false, error: null })
      return data
    } catch (error) {
      if (error?.name === 'AbortError' || ctrl.signal.aborted) return undefined
      setState(s => ({ ...s, loading: false, error }))
      return undefined
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, deps)

  useEffect(() => {
    if (!enabled) return undefined
    load()
    return () => ctrlRef.current?.abort()
  }, [load, enabled])

  useEffect(() => {
    if (!pollInterval || !enabled) return undefined
    if (shouldPoll && !shouldPoll(state.data)) return undefined
    const t = setInterval(() => load({ silent: true }), pollInterval)
    return () => clearInterval(t)
  }, [pollInterval, enabled, shouldPoll, state.data, load])

  const setData = useCallback(updater => {
    setState(s => ({ ...s, data: typeof updater === 'function' ? updater(s.data) : updater }))
  }, [])

  return { ...state, reload: load, setData }
}

/**
 * Wraps a write operation (POST/PATCH/DELETE) with loading + error state.
 *
 *   const save = useMutation(settingsService.updateProfile, { onSuccess: () => toast('Saved') })
 *   save.mutate(values)
 */
export function useMutation(fn, { onSuccess, onError } = {}) {
  const [state, setState] = useState({ loading: false, error: null, data: null })
  const fnRef = useRef(fn)
  fnRef.current = fn
  const cbRef = useRef({ onSuccess, onError })
  cbRef.current = { onSuccess, onError }

  const mutate = useCallback(async (...args) => {
    setState({ loading: true, error: null, data: null })
    try {
      const data = await fnRef.current(...args)
      setState({ loading: false, error: null, data })
      await cbRef.current.onSuccess?.(data, ...args)
      return data
    } catch (error) {
      setState({ loading: false, error, data: null })
      cbRef.current.onError?.(error, ...args)
      throw error
    }
  }, [])

  return { ...state, mutate }
}
