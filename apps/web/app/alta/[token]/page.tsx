"use client";
import { use, useEffect, useRef, useState } from "react";
import { useRouter } from "next/navigation";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import { Shell, Card, ErrorNote } from "@/components/Shell";
import { Space, useApi } from "@/lib/api";

type Created = { id: string; upload?: { image_id: string; url: string; headers: Record<string, string> } };
const LAST_SPACE = "ng:last-space";

async function uploadWithRetry(url: string, file: File, headers: Record<string, string>) {
  for (let i = 0; i < 4; i++) {
    try { const r = await fetch(url, { method: "PUT", body: file, headers }); if (r.ok) return; } catch {}
    await new Promise((res) => setTimeout(res, 1000 * 2 ** i));
  }
  throw new Error("No se pudo subir la foto");
}

export default function Alta({ params }: { params: Promise<{ token: string }> }) {
  const { token } = use(params);
  const api = useApi(); const router = useRouter(); const qc = useQueryClient();
  const spaces = useQuery({ queryKey: ["spaces"], queryFn: () => api<Space[]>("/spaces") });
  const [name, setName] = useState("");
  const [spaceId, setSpaceId] = useState("");
  const [newSpace, setNewSpace] = useState("");
  const [file, setFile] = useState<File | null>(null);
  const [busy, setBusy] = useState(false);
  const [err, setErr] = useState<string | null>(null);
  const fileRef = useRef<HTMLInputElement>(null);

  useEffect(() => { const s = sessionStorage.getItem(LAST_SPACE); if (s) setSpaceId(s); }, []);
  const adding = spaceId === "__nueva";
  const ready = name.trim() && (adding ? newSpace.trim() : spaceId);

  async function save(e: React.FormEvent) {
    e.preventDefault(); setBusy(true); setErr(null);
    try {
      const body = { tag_token: token, name, plate_content_type: file?.type || undefined,
                     ...(adding ? { new_space_name: newSpace } : { space_id: spaceId }) };
      const a = await api<Created>("/assets", { method: "POST", body: JSON.stringify(body) });
      await qc.invalidateQueries({ queryKey: ["spaces"] });
      const sid = adding ? (await api<Space[]>("/spaces")).find((s) => s.name === newSpace.trim())?.id : spaceId;
      if (sid) sessionStorage.setItem(LAST_SPACE, sid);       // modo ráfaga: se conserva la ubicación
      if (a.upload && file) {
        const { image_id, url, headers } = a.upload;
        uploadWithRetry(url, file, headers)                    // en segundo plano, no bloquea al usuario
          .then(() => api(`/assets/${a.id}/images/${image_id}/uploaded`, { method: "POST" }))
          .catch(() => {});
      }
      qc.invalidateQueries({ queryKey: ["kits"] }); qc.invalidateQueries({ queryKey: ["pending"] });
      router.replace("/escanear");                              // siguiente equipo
    } catch (x) { setErr((x as Error).message); setBusy(false); }
  }

  return (
    <Shell title="Nuevo equipo" back="/inicio">
      <form onSubmit={save} className="flex flex-col gap-4">
        <Card>
          <p className="font-extrabold text-ink">1. Foto de la placa</p>
          <p className="text-sm text-muted">Es la etiqueta con marca, modelo y serie, casi siempre en la parte de atrás o dentro de la puerta.</p>
          <input ref={fileRef} type="file" accept="image/*" capture="environment" hidden onChange={(e) => setFile(e.target.files?.[0] ?? null)} />
          <button type="button" className="btn btn-copper mt-3 w-full" onClick={() => fileRef.current?.click()}>
            {file ? "Cambiar foto" : "Tomar foto"}
          </button>
          {file && <p className="mt-2 text-sm font-semibold text-[var(--ng-ok)]">Foto lista</p>}
        </Card>
        <Card className="flex flex-col gap-3">
          <label htmlFor="n" className="font-extrabold text-ink">2. ¿Qué equipo es?</label>
          <input id="n" className="field" value={name} onChange={(e) => setName(e.target.value)} placeholder="Lavadora" maxLength={200} required />
          <label htmlFor="s" className="font-extrabold text-ink">3. ¿Dónde está?</label>
          <select id="s" className="field" value={spaceId} onChange={(e) => setSpaceId(e.target.value)} required>
            <option value="" disabled>Elige un lugar</option>
            {spaces.data?.map((s) => <option key={s.id} value={s.id}>{s.name}</option>)}
            <option value="__nueva">+ Nueva ubicación</option>
          </select>
          {adding && <input className="field" placeholder="Ej. Taller" value={newSpace} onChange={(e) => setNewSpace(e.target.value)} maxLength={120} />}
        </Card>
        <button className="btn w-full" disabled={busy || !ready}>{busy ? "Guardando…" : "Guardar y seguir"}</button>
        <ErrorNote text={err} />
      </form>
    </Shell>
  );
}
