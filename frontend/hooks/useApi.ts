"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import { apiGet } from "@/lib/api";

export function useApiData<T>(path: string | null, deps: unknown[] = []) {
  const [data, setData] = useState<T | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const seq = useRef(0);

  const load = useCallback(async () => {
    if (!path) return;
    const id = ++seq.current;
    setLoading(true);
    setError(null);
    try {
      const result = await apiGet<T>(path);
      if (seq.current === id) setData(result);
    } catch (e) {
      if (seq.current === id) setError(e instanceof Error ? e.message : "Request failed");
    } finally {
      if (seq.current === id) setLoading(false);
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [path, ...deps]);

  useEffect(() => { load(); }, [load]);
  return { data, error, loading, refresh: load, setData };
}

export function usePoll<T>(path: string | null, intervalMs: number, enabled: boolean) {
  const { data, error, loading, refresh, setData } = useApiData<T>(path);
  useEffect(() => {
    if (!enabled || !path) return;
    const t = setInterval(refresh, intervalMs);
    return () => clearInterval(t);
  }, [enabled, intervalMs, path, refresh]);
  return { data, error, loading, refresh, setData };
}
