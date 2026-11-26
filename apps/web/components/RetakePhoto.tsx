"use client";
import { useRef, useState } from "react";
import { useQueryClient } from "@tanstack/react-query";
import { Card } from "./Shell";
import { useApi } from "@/lib/api";
import { putWithProgress, sleep, Upload } from "@/lib/upload";
import { STILL_READING } from "@/lib/assetStatus";

/**
 * Toma otra foto de la placa de un equipo que ya existe, la sube y espera la nueva lectura.
 * onDone recibe el nuevo estado del equipo (o "leyendo" si tarda demasiado).
 */
export type PhotoKind = "placa" | "equipo";
const TEXT: Record<PhotoKind, { title: string; help: string }> = {
  placa: { title: "Tomar otra foto de la placa", help: "Acércate a la placa, con buena luz y sin reflejos. Que se vean bien la marca, el modelo y la serie." },
  equipo: { title: "Agregar foto del equipo", help: "Toma el equipo completo, de frente y con buena luz. Así podemos saber qué es aunque la placa no se lea." },
};

export function RetakePhoto({ assetId, onDone, kind = "placa" }: { assetId: string; onDone: (status: string) => void; kind?: PhotoKind }) {
  const api = useApi(); const qc = useQueryClient();
  const camRef = useRef<HTMLInputElement>(null);
  const pickRef = useRef<HTMLInputElement>(null);
  const [phase, setPhase] = useState<"idle" | "subiendo" | "leyendo" | "error">("idle");
  const [pct, setPct] = useState(0);
  const [msg, setMsg] = useState<string | null>(null);

  async function subir(file: File) {
    setMsg(null); setPct(0); setPhase("subiendo");
    try {
      const up = await api<Upload>(`/assets/${assetId}/fotos`, { method: "POST", body: JSON.stringify({ content_type: file.type || "image/jpeg", kind }) });
      await putWithProgress(up, file, setPct);
      await api(`/assets/${assetId}/images/${up.image_id}/uploaded`, { method: "POST" });
      setPhase("leyendo");
      for (let i = 0; i < 48; i++) {
        await sleep(2500);
        const a = await api<{ status: string }>(`/assets/${assetId}`);
        if (!STILL_READING.includes(a.status)) { setPhase("idle"); onDone(a.status); qc.invalidateQueries({ queryKey: ["assets"] }); return; }
      }
      setPhase("idle"); onDone("leyendo");
    } catch (x) {
      setMsg((x as Error).message + ". Tu foto anterior sigue guardada; inténtalo de nuevo.");
      setPhase("error");
    }
  }

  const busy = phase === "subiendo" || phase === "leyendo";
  return (
    <Card className="flex flex-col gap-3">
      <p className="font-extrabold text-ink">{TEXT[kind].title}</p>
      <p className="text-sm text-muted">{TEXT[kind].help}</p>
      <input ref={camRef} type="file" accept="image/*" capture="environment" hidden onChange={(e) => { const f = e.target.files?.[0]; if (f) subir(f); e.target.value = ""; }} />
      <input ref={pickRef} type="file" accept="image/*" hidden onChange={(e) => { const f = e.target.files?.[0]; if (f) subir(f); e.target.value = ""; }} />
      {phase === "idle" || phase === "error" ? (
        <div className="grid grid-cols-2 gap-2">
          <button type="button" className="btn btn-copper w-full" disabled={busy} onClick={() => camRef.current?.click()}>{kind === "equipo" ? "Tomar foto del equipo" : "Tomar foto"}</button>
          <button type="button" className="btn btn-ghost w-full" disabled={busy} onClick={() => pickRef.current?.click()}>{kind === "equipo" ? "Subir foto del equipo" : "Subir foto"}</button>
        </div>
      ) : null}
      {phase === "subiendo" && (
        <div className="flex flex-col gap-2">
          <p className="text-sm font-semibold text-navy">{kind === "equipo" ? "Subiendo la foto del equipo" : "Subiendo la foto de la placa"}… {pct}%</p>
          <div className="h-3 w-full overflow-hidden rounded-full bg-white/70" role="progressbar" aria-valuemin={0} aria-valuemax={100} aria-valuenow={pct}>
            <div className="h-3 rounded-full bg-[#C18B58] transition-[width] duration-200" style={{ width: `${pct}%` }} />
          </div>
        </div>
      )}
      {phase === "leyendo" && (
        <p className="text-sm font-semibold text-navy">
          {kind === "equipo" ? "Foto recibida. Estamos reconociendo el equipo con esta foto…" : "Foto recibida. Estamos leyendo la placa otra vez…"}
        </p>
      )}
      {msg && <p role="alert" className="text-sm font-semibold text-[var(--ng-danger)]">{msg}</p>}
    </Card>
  );
}
