"use client";
import { use, useEffect, useRef, useState } from "react";
import Link from "next/link";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import { Shell, Card, ErrorNote } from "@/components/Shell";
import { Space, useApi } from "@/lib/api";
import { STILL_READING, statusInfo } from "@/lib/assetStatus";

type Upload = { image_id: string; url: string; headers: Record<string, string> };
type Created = { id: string; upload?: Upload };
type Stage = "form" | "subiendo" | "leyendo" | "listo" | "error_foto";

const LAST_SPACE = "ng:last-space";

/** Sube el archivo directo a R2 y avisa el progreso (0 a 100). */
function putWithProgress(upload: Upload, file: File, onProgress: (pct: number) => void) {
  return new Promise<void>((resolve, reject) => {
    const xhr = new XMLHttpRequest();
    xhr.open("PUT", upload.url);
    Object.entries(upload.headers).forEach(([k, v]) => xhr.setRequestHeader(k, v));
    xhr.upload.onprogress = (e) => { if (e.lengthComputable) onProgress(Math.round((e.loaded / e.total) * 100)); };
    xhr.onload = () => (xhr.status >= 200 && xhr.status < 300 ? resolve() : reject(new Error(`R2 respondió ${xhr.status}`)));
    xhr.onerror = () => reject(new Error("Sin conexión con el servidor de fotos"));
    xhr.send(file);
  });
}

const sleep = (ms: number) => new Promise((r) => setTimeout(r, ms));

export default function Alta({ params }: { params: Promise<{ token: string }> }) {
  const { token } = use(params);
  const api = useApi(); const qc = useQueryClient();
  const spaces = useQuery({ queryKey: ["spaces"], queryFn: () => api<Space[]>("/spaces") });

  const [name, setName] = useState("");
  const [spaceId, setSpaceId] = useState("");
  const [newSpace, setNewSpace] = useState("");
  const [file, setFile] = useState<File | null>(null);
  const [busy, setBusy] = useState(false);
  const [err, setErr] = useState<string | null>(null);

  // Estado del proceso despues de guardar.
  const [stage, setStage] = useState<Stage>("form");
  const [assetId, setAssetId] = useState<string | null>(null);
  const [upload, setUpload] = useState<Upload | null>(null);
  const [pct, setPct] = useState(0);
  const [upErr, setUpErr] = useState<string | null>(null);
  const [finalStatus, setFinalStatus] = useState<string>("");
  const [sinFoto, setSinFoto] = useState(false);

  const camRef = useRef<HTMLInputElement>(null);   // abre la camara directamente
  const pickRef = useRef<HTMLInputElement>(null);  // abre galeria o archivos

  useEffect(() => { const s = sessionStorage.getItem(LAST_SPACE); if (s) setSpaceId(s); }, []);
  const adding = spaceId === "__nueva";
  const ready = name.trim() && (adding ? newSpace.trim() : spaceId);

  async function subirFoto(id: string, up: Upload, f: File) {
    setStage("subiendo"); setPct(0); setUpErr(null);
    try {
      await putWithProgress(up, f, setPct);
      await api(`/assets/${id}/images/${up.image_id}/uploaded`, { method: "POST" });
      setStage("leyendo");
      await esperarLectura(id);
    } catch (x) {
      setUpErr((x as Error).message);
      setStage("error_foto");
    }
  }

  // Revisa el estado cada 2.5 s hasta que la lectura termine (maximo ~2 minutos).
  async function esperarLectura(id: string) {
    for (let i = 0; i < 48; i++) {
      await sleep(2500);
      const a = await api<{ status: string }>(`/assets/${id}`);
      if (!STILL_READING.includes(a.status)) {
        setFinalStatus(a.status); setStage("listo");
        qc.invalidateQueries({ queryKey: ["pending"] });
        return;
      }
    }
    setFinalStatus("leyendo"); setStage("listo");
  }

  async function save(e: React.FormEvent) {
    e.preventDefault(); setBusy(true); setErr(null);
    try {
      const body = { tag_token: token, name, plate_content_type: file?.type || undefined,
                     ...(adding ? { new_space_name: newSpace } : { space_id: spaceId }) };
      const a = await api<Created>("/assets", { method: "POST", body: JSON.stringify(body) });
      await qc.invalidateQueries({ queryKey: ["spaces"] });
      const sid = adding ? (await api<Space[]>("/spaces")).find((s) => s.name === newSpace.trim())?.id : spaceId;
      if (sid) sessionStorage.setItem(LAST_SPACE, sid);       // modo rafaga: se conserva la ubicacion
      qc.invalidateQueries({ queryKey: ["kits"] });
      setAssetId(a.id);
      if (a.upload && file) {
        setUpload(a.upload);
        setBusy(false);
        await subirFoto(a.id, a.upload, file);
      } else {
        setSinFoto(true); setFinalStatus("registrado"); setStage("listo"); setBusy(false);
      }
    } catch (x) { setErr((x as Error).message); setBusy(false); }
  }

  function reintentar() {
    if (assetId && upload && file) subirFoto(assetId, upload, file);
  }

  // ---------- Pantallas despues de guardar ----------
  if (stage === "subiendo") return (
    <Shell title="Subiendo la foto" back="/inicio">
      <Card className="flex flex-col gap-3">
        <p className="text-lg font-extrabold text-ink">{pct}%</p>
        <div className="h-3 w-full overflow-hidden rounded-full bg-white/70" role="progressbar" aria-valuemin={0} aria-valuemax={100} aria-valuenow={pct}>
          <div className="h-3 rounded-full bg-[#C18B58] transition-[width] duration-200" style={{ width: `${pct}%` }} />
        </div>
        <p className="text-sm text-muted">No cierres esta pantalla mientras se sube la foto.</p>
      </Card>
    </Shell>
  );

  if (stage === "leyendo") return (
    <Shell title="Leyendo la placa" back="/inicio">
      <Card className="flex flex-col gap-3">
        <p className="font-extrabold text-ink">Foto recibida</p>
        <p className="text-sm text-muted">Estamos leyendo la marca, el modelo y la serie. Suele tardar menos de un minuto.</p>
        <p className="text-sm text-muted">Puedes esperar aquí o ir al inicio. Te aparecerá en <b>Por confirmar</b> cuando termine.</p>
      </Card>
      <Link href="/inicio" className="btn btn-ghost mt-4 w-full">Ir al inicio</Link>
    </Shell>
  );

  if (stage === "error_foto") return (
    <Shell title="No se subió la foto" back="/inicio">
      <Card className="flex flex-col gap-3">
        <p className="font-extrabold text-ink">Tu equipo ya quedó guardado, pero falta la foto.</p>
        <p className="text-sm text-muted">{upErr} Revisa tu conexión e inténtalo de nuevo.</p>
      </Card>
      <div className="mt-4 flex flex-col gap-3">
        <button className="btn btn-copper w-full" onClick={reintentar}>Reintentar la foto</button>
        <button className="btn btn-ghost w-full" onClick={() => { setSinFoto(true); setFinalStatus("registrado"); setStage("listo"); }}>Continuar sin foto</button>
      </div>
    </Shell>
  );

  if (stage === "listo") {
    const info = finalStatus === "leyendo" ? { label: "Sigue leyendo", detail: "La lectura tarda más de lo normal. Lo verás en Por confirmar cuando termine.", tone: "wait" as const }
      : sinFoto ? { label: "Guardado sin foto", detail: "Puedes escribir sus datos a mano desde el equipo.", tone: "action" as const }
      : statusInfo(finalStatus);
    const toneClass = info.tone === "ok" ? "text-[var(--ng-ok)]" : info.tone === "action" ? "text-[var(--ng-warn)]" : "text-navy";
    return (
      <Shell title="Equipo guardado" back="/inicio">
        <Card className="flex flex-col gap-2">
          <p className={`text-lg font-extrabold ${toneClass}`}>{info.label}</p>
          <p className="text-sm text-muted">{info.detail}</p>
        </Card>
        <Card className="mt-4 flex flex-col gap-2">
          <p className="font-extrabold text-ink">¿Qué sigue?</p>
          <p className="text-sm text-muted">Puedes registrar otro equipo con otra etiqueta de tu kit, o volver al inicio.</p>
        </Card>
        <div className="mt-4 flex flex-col gap-3">
          <Link href="/escanear" className="btn btn-copper w-full">Agregar otro equipo</Link>
          <Link href="/inicio" className="btn btn-ghost w-full">Ir al inicio</Link>
          {assetId && <Link href={`/equipos/${assetId}`} className="text-center text-sm font-bold text-navy underline">Ver este equipo</Link>}
        </div>
      </Shell>
    );
  }

  // ---------- Formulario ----------
  return (
    <Shell title="Nuevo equipo" back="/inicio">
      <form onSubmit={save} className="flex flex-col gap-4">
        <Card>
          <p className="font-extrabold text-ink">1. Foto de la placa</p>
          <p className="text-sm text-muted">Es la etiqueta con marca, modelo y serie, casi siempre en la parte de atrás o dentro de la puerta.</p>
          <input ref={camRef} type="file" accept="image/*" capture="environment" hidden onChange={(e) => setFile(e.target.files?.[0] ?? null)} />
          <input ref={pickRef} type="file" accept="image/*" hidden onChange={(e) => setFile(e.target.files?.[0] ?? null)} />
          <div className="mt-3 grid grid-cols-2 gap-2">
            <button type="button" className="btn btn-copper w-full" onClick={() => camRef.current?.click()}>Tomar foto</button>
            <button type="button" className="btn btn-ghost w-full" onClick={() => pickRef.current?.click()}>Subir foto</button>
          </div>
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
        <p className="text-center text-xs text-muted">
          {file ? "Al guardar, subimos la foto y leemos la placa. Verás el avance aquí." : "Sin foto, el equipo se guarda y puedes escribir sus datos a mano."}
        </p>
        <button className="btn w-full" disabled={busy || !ready}>{busy ? "Guardando…" : file ? "Guardar y leer la placa" : "Guardar equipo"}</button>
        <ErrorNote text={err} />
      </form>
    </Shell>
  );
}
