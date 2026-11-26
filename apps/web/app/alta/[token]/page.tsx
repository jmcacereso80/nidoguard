"use client";
import { use, useEffect, useRef, useState } from "react";
import Link from "next/link";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import { Shell, Card, ErrorNote } from "@/components/Shell";
import { Icon, SPACE_ICONS } from "@/components/Icon";
import { Kit, Space, useApi } from "@/lib/api";
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
  const kits = useQuery({ queryKey: ["kits"], queryFn: () => api<Kit[]>("/kits") });
  const me = useQuery({ queryKey: ["me"], queryFn: () => api<{ suggested_spaces: string[] }>("/me") });
  const [sheet, setSheet] = useState(false);
  const [sheetName, setSheetName] = useState("");
  const [sheetIcon, setSheetIcon] = useState<string>("home");

  const [name, setName] = useState("");
  const [spaceId, setSpaceId] = useState("");
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
  // Las ubicaciones sugeridas (Cocina, Sala...) se crean al elegirlas: su id empieza con "sug:".
  const adding = spaceId.startsWith("sug:");
  // Con foto no hace falta el nombre: lo lee la IA. Sin foto, el nombre es obligatorio.
  const ready = (file || name.trim()) && spaceId;
  const used = kits.data?.reduce((n, k) => n + k.tags_used, 0) ?? 0;
  const total = kits.data?.reduce((n, k) => n + k.tags_total, 0) ?? 0;
  const existing = new Set((spaces.data ?? []).map((x) => x.name.toLowerCase()));
  const chips = [...(spaces.data ?? []).map((x) => ({ id: x.id, name: x.name })),
    ...(me.data?.suggested_spaces ?? []).filter((n) => !existing.has(n.toLowerCase())).map((n) => ({ id: `sug:${n}`, name: n }))];

  async function createSpace() {
    if (!sheetName.trim()) return;
    try {
      const sp = await api<Space>("/spaces", { method: "POST", body: JSON.stringify({ name: sheetName.trim(), icon: sheetIcon }) });
      await qc.invalidateQueries({ queryKey: ["spaces"] });
      setSpaceId(sp.id); setSheet(false); setSheetName("");
    } catch (x) { setErr((x as Error).message); }
  }

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
      // Con foto, el tipo de equipo lo toma la IA de la placa; sin foto, lo escribe la persona.
      const body = { tag_token: token, name: file ? undefined : name, plate_content_type: file?.type || undefined,
                     ...(adding ? { new_space_name: spaceId.slice(4) } : { space_id: spaceId }) };
      const a = await api<Created>("/assets", { method: "POST", body: JSON.stringify(body) });
      await qc.invalidateQueries({ queryKey: ["spaces"] });
      const sid = adding ? (await api<Space[]>("/spaces")).find((x) => x.name === spaceId.slice(4))?.id : spaceId;
      if (sid) sessionStorage.setItem(LAST_SPACE, sid);       // modo rafaga: se conserva la ubicacion
      qc.invalidateQueries({ queryKey: ["kits"] }); qc.invalidateQueries({ queryKey: ["assets"] });
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
    <Shell title="Nuevo equipo" back="/inicio" right={total > 0 ? <span className="chip whitespace-nowrap"><Icon name="tag" size={13} stroke={2.4} />{used} de {total}</span> : undefined}>
      <form onSubmit={save} className="flex flex-col gap-4">
        <input ref={camRef} type="file" accept="image/*" capture="environment" hidden onChange={(e) => setFile(e.target.files?.[0] ?? null)} />
        <input ref={pickRef} type="file" accept="image/*" hidden onChange={(e) => setFile(e.target.files?.[0] ?? null)} />
        <div className="g rounded-[26px] p-3.5">
          <div className="flex items-center gap-3">
            <span className="icon-tile !h-12 !w-12 !rounded-2xl"><Icon name="camera" size={24} /></span>
            <span className="min-w-0 flex-1"><span className="block text-[15px] font-extrabold">Foto de la placa</span><span className="block text-[12.5px] leading-tight text-muted">{file ? "Foto lista. El tipo de equipo lo leeremos de la placa." : "Es la etiqueta con marca, modelo y serie, casi siempre atrás o dentro de la puerta."}</span></span>
          </div>
          <div className="mt-3 grid grid-cols-2 gap-2">
            <button type="button" className="btn btn-copper !min-h-11 w-full !text-[15px]" onClick={() => camRef.current?.click()}>{file ? "Cambiar foto" : "Tomar foto"}</button>
            <button type="button" className="btn btn-ghost !min-h-11 w-full !text-[15px]" onClick={() => pickRef.current?.click()}>Subir foto</button>
          </div>
        </div>
        {!file && (
          <div>
            <label htmlFor="n" className="mb-1.5 block text-[13px] font-bold text-muted">Nombre</label>
            <input id="n" className="field" value={name} onChange={(e) => setName(e.target.value)} placeholder="Lavadora" maxLength={200} required />
          </div>
        )}
        <div>
          <p className="mb-2 text-[13px] font-bold text-muted">¿Dónde está?</p>
          <div className="flex flex-wrap gap-2">
            {chips.map((c) => (
              <button type="button" key={c.id} aria-pressed={spaceId === c.id} onClick={() => setSpaceId(c.id)}
                className={`inline-flex h-11 items-center gap-1.5 rounded-full px-4 text-[15px] font-bold ${spaceId === c.id ? "gd" : "g text-navy"}`} style={{ borderRadius: 999 }}>
                {spaceId === c.id && <Icon name="check" size={16} stroke={2.6} />}{c.name}
              </button>
            ))}
            <button type="button" onClick={() => setSheet(true)} className="inline-flex h-11 items-center gap-1.5 rounded-full border-[1.5px] border-dashed border-navy/40 bg-white/40 px-4 text-[15px] font-bold text-navy"><Icon name="plus" size={16} stroke={2.4} />Nueva</button>
          </div>
        </div>
        <p className="text-center text-xs text-muted">
          {file ? "Al guardar, subimos la foto y leemos la placa. Verás el avance aquí." : "Sin foto, el equipo se guarda y puedes escribir sus datos a mano."}
        </p>
        <button className="btn w-full" disabled={busy || !ready}>{busy ? "Guardando…" : file ? "Guardar y leer la placa" : "Guardar equipo"}</button>
        <ErrorNote text={err} />
      </form>
      {sheet && (
        <div className="fixed inset-0 z-20 flex items-end bg-[rgba(2,38,77,.35)]" role="dialog" aria-modal="true" aria-label="Nueva ubicación" onClick={() => setSheet(false)}>
          <div className="gs mx-auto w-full max-w-md rounded-b-none rounded-t-[34px] px-5 pb-8 pt-3" onClick={(e) => e.stopPropagation()}>
            <span className="mx-auto mb-3 block h-1 w-10 rounded-full bg-navy/20" />
            <h2 className="text-[22px] font-extrabold">Nueva ubicación</h2>
            <p className="text-[13px] text-muted">La podrás usar para todos tus equipos.</p>
            <label htmlFor="sn" className="mb-1.5 mt-4 block text-[13px] font-bold text-muted">Nombre</label>
            <input id="sn" className="field" value={sheetName} onChange={(e) => setSheetName(e.target.value)} placeholder="Patio" maxLength={120} autoFocus />
            <p className="mb-2 mt-4 text-[13px] font-bold text-muted">Ícono</p>
            <div className="flex justify-between">
              {SPACE_ICONS.map((i) => (
                <button type="button" key={i} aria-label={i} aria-pressed={sheetIcon === i} onClick={() => setSheetIcon(i)}
                  className={`grid h-12 w-12 place-items-center rounded-2xl ${sheetIcon === i ? "gd" : "g text-navy"}`}><Icon name={i} size={22} /></button>
              ))}
            </div>
            <button type="button" className="btn mt-5 w-full" disabled={!sheetName.trim()} onClick={createSpace}>Crear y usar</button>
            <button type="button" className="mt-3 block w-full text-center text-[15px] font-bold text-navy" onClick={() => setSheet(false)}>Cancelar</button>
          </div>
        </div>
      )}
    </Shell>
  );
}
