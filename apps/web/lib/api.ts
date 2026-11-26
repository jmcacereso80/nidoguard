"use client";
import { useAuth } from "@clerk/nextjs";
import { useCallback } from "react";

// Por defecto la API va por el mismo host, bajo /api (ver rewrites en next.config.ts).
export const API_URL = process.env.NEXT_PUBLIC_API_URL ?? "/api";

export class ApiError extends Error {
  constructor(public status: number, message: string) { super(message); }
}

export function useApi() {
  const { getToken } = useAuth();
  return useCallback(async <T,>(path: string, init: RequestInit = {}): Promise<T> => {
    const token = await getToken();
    const res = await fetch(`${API_URL}${path}`, {
      ...init,
      headers: { "Content-Type": "application/json", ...(token ? { Authorization: `Bearer ${token}` } : {}), ...init.headers },
    });
    if (!res.ok) {
      let msg = "Algo salió mal. Inténtalo de nuevo.";
      try { msg = (await res.json()).detail ?? msg; } catch {}
      throw new ApiError(res.status, typeof msg === "string" ? msg : "Revisa los datos e inténtalo de nuevo.");
    }
    // 204 (sin contenido, p. ej. al eliminar) no tiene JSON que leer.
    if (res.status === 204) return undefined as T;
    return res.json() as Promise<T>;
  }, [getToken]);
}

export type Home = { id: string; name: string; properties: { id: string; name: string }[] };
export type Me = { user: { id: string; email: string | null; name: string | null }; home: Home | null; suggested_spaces: string[] };
export type Space = { id: string; name: string; icon: string | null; property_id: string };
export type Asset = { id: string; name: string; status: string; brand: string | null; model: string | null; serial: string | null; category: string | null; space_id: string | null };
export type Kit = { id: string; status: string; tags_total: number; tags_used: number };
