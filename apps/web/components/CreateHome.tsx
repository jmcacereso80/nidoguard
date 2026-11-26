"use client";
import { useState } from "react";
import { useQueryClient } from "@tanstack/react-query";
import { Card, ErrorNote } from "./Shell";
import { Home, useApi } from "@/lib/api";

export function CreateHome({ onDone }: { onDone?: () => void }) {
  const api = useApi();
  const qc = useQueryClient();
  const [name, setName] = useState("Mi casa");
  const [busy, setBusy] = useState(false);
  const [err, setErr] = useState<string | null>(null);
  async function submit(e: React.FormEvent) {
    e.preventDefault(); setBusy(true); setErr(null);
    try {
      await api<Home>("/home", { method: "POST", body: JSON.stringify({ name }) });
      await qc.invalidateQueries({ queryKey: ["me"] });
      onDone?.();
    } catch (x) { setErr((x as Error).message); } finally { setBusy(false); }
  }
  return (
    <Card>
      <form onSubmit={submit} className="flex flex-col gap-3">
        <label htmlFor="home" className="font-bold text-navy">¿Cómo se llama tu hogar?</label>
        <input id="home" className="field" value={name} onChange={(e) => setName(e.target.value)} maxLength={200} required />
        <button className="btn" disabled={busy || !name.trim()}>{busy ? "Creando…" : "Crear mi hogar"}</button>
        <ErrorNote text={err} />
      </form>
    </Card>
  );
}
