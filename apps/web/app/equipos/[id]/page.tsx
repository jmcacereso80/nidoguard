"use client";
import Link from "next/link";
import { use, useState } from "react";
import { useRouter } from "next/navigation";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import { Shell, Card, ErrorNote, Pronto } from "@/components/Shell";
import { Icon, equipmentIcon } from "@/components/Icon";
import { Asset, Space, useApi } from "@/lib/api";
import { statusInfo } from "@/lib/assetStatus";
import { RetakePhoto } from "@/components/RetakePhoto";

type Detail = Asset & {
  extra?: { nombre_pendiente?: boolean } | null;
  reading: { status: string; source: string; fields: Record<string, string>; confidence: Record<string, number>; confirmed: boolean } | null;
  events: { type: string; at: string; payload: Record<string, unknown> }[];
};
const EVENT: Record<string, string> = {
  registro: "Registrado", lectura_ia: "Placa leída", confirmado: "Datos confirmados",
  datos_manuales: "Datos escritos a mano", edicion: "Datos corregidos",
};
// Datos que se leen de la placa: solo estos tres, iguales para todos los equipos.
const READ_LABEL: Record<string, string> = { brand: "Marca", model: "Modelo", serial: "Número de serie" };
const TABS = ["Resumen", "Documentos", "Cuidado", "Historial"] as const;
const FIELDS = ["name", "category", "brand", "model", "serial"] as const;
type Field = (typeof FIELDS)[number];
const LABEL: Record<Field, string> = { name: "Nombre", category: "Tipo", brand: "Marca", model: "Modelo", serial: "Número de serie" };

export default function Equipo({ params }: { params: Promise<{ id: string }> }) {
  const { id } = use(params);
  const api = useApi(); const qc = useQueryClient(); const router = useRouter();
  const q = useQuery({ queryKey: ["asset", id], queryFn: () => api<Detail>(`/assets/${id}`) });
  const spaces = useQuery({ queryKey: ["spaces"], queryFn: () => api<Space[]>("/spaces") });
  const [manual, setManual] = useState({ brand: "", model: "", serial: "" });
  const [edit, setEdit] = useState<Record<string, string> | null>(null);
  const [okMsg, setOkMsg] = useState<string | null>(null);
  const [confirmDel, setConfirmDel] = useState(false);
  const [err, setErr] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const [tab, setTab] = useState<(typeof TABS)[number]>("Resumen");

  const a = q.data;
  if (!a) return <Shell title="Equipo" back="/equipos"><p>Cargando…</p></Shell>;
  const asset: Detail = a;  // version no nula para usar dentro de funciones
  const info = statusInfo(a.status);
  const needs = a.status !== "completo";
  const toneClass = info.tone === "ok" ? "text-[var(--ng-ok)]" : info.tone === "action" ? "text-[var(--ng-warn)]" : "text-navy";
  // Valor guardado de cada campo, para mandar solo lo que cambio.
  const saved = (k: Field): string => (asset[k] as string | null) ?? "";
  // Formulario de correccion: si todavia no se edita, muestra los valores guardados.
  const cur: Record<string, string> = edit ?? {
    name: a.name, category: saved("category"), brand: saved("brand"), model: saved("model"), serial: saved("serial"),
    space_id: a.space_id ?? "",
  };

  async function refresh() {
    qc.invalidateQueries({ queryKey: ["asset", id] }); qc.invalidateQueries({ queryKey: ["pending"] });
    qc.invalidateQueries({ queryKey: ["kits"] }); qc.invalidateQueries({ queryKey: ["assets"] });
  }

  async function saveManual() {
    setErr(null); setOkMsg(null); setBusy(true);
    try {
      await api(`/assets/${id}/manual`, { method: "PATCH", body: JSON.stringify(Object.fromEntries(Object.entries(manual).filter(([, v]) => v.trim()))) });
      await refresh();
    } catch (x) { setErr((x as Error).message); } finally { setBusy(false); }
  }

  async function confirmData() {
    setErr(null); setOkMsg(null); setBusy(true);
    try { await api(`/assets/${id}/confirm`, { method: "POST", body: JSON.stringify({}) }); await refresh(); }
    catch (x) { setErr((x as Error).message); } finally { setBusy(false); }
  }

  async function saveEdit() {
    setErr(null); setOkMsg(null);
    const body: Record<string, string | null> = {};
    for (const k of FIELDS) {
      const v = (cur[k] ?? "").trim();
      if (v !== saved(k)) body[k] = v || null;
    }
    if (cur.space_id && cur.space_id !== (asset.space_id ?? "")) body.space_id = cur.space_id;
    if (!Object.keys(body).length) { setOkMsg("No hay cambios que guardar."); return; }
    if (body.name === null) { setErr("El equipo necesita un nombre."); return; }
    setBusy(true);
    try {
      await api(`/assets/${id}`, { method: "PATCH", body: JSON.stringify(body) });
      setEdit(null); setOkMsg("Cambios guardados."); await refresh();
    } catch (x) { setErr((x as Error).message); } finally { setBusy(false); }
  }

  async function eliminar() {
    setErr(null); setBusy(true);
    try {
      await api(`/assets/${id}`, { method: "DELETE" });
      qc.removeQueries({ queryKey: ["asset", id] });
      await refresh();
      router.replace("/inicio");
    } catch (x) { setErr((x as Error).message); setBusy(false); setConfirmDel(false); }
  }

  const place = spaces.data?.find((x) => x.id === a.space_id)?.name;
  const rows: [string, string | null][] = [["Tipo", a.category], ["Marca", a.brand], ["Modelo", a.model], ["Número de serie", a.serial]];
  return (
    <Shell title={a.name} subtitle={place} back="/equipos" nav="equipos">
      <div role="tablist" className="g mb-4 flex gap-1 rounded-full p-1" style={{ borderRadius: 999 }}>
        {TABS.map((t) => (
          <button key={t} role="tab" aria-selected={tab === t} onClick={() => setTab(t)}
            className={`h-10 flex-1 rounded-full text-[13px] font-bold ${tab === t ? "gd" : "text-[var(--ng-body)]"}`} style={{ borderRadius: 999 }}>{t}</button>
        ))}
      </div>

      {tab === "Resumen" && (
        <div className="flex flex-col gap-4">
          <div className="g relative grid h-[150px] place-items-center rounded-[30px] text-navy" style={{ background: "linear-gradient(145deg,rgba(241,226,211,.9),rgba(227,195,163,.75))" }}>
            <span className={`chip absolute left-3.5 top-3.5 !bg-white/70 ${toneClass}`}><Icon name={info.tone === "ok" ? "check" : "clock"} size={13} stroke={2.6} />{info.label}</span>
            <Icon name={equipmentIcon(a)} size={72} stroke={1.3} />
          </div>
          <p className="-mt-1 text-sm text-muted">{info.detail}</p>
          {asset.extra?.nombre_pendiente && (
            <p className="rounded-2xl bg-white/70 px-4 py-3 text-sm font-semibold text-[var(--ng-warn)]">
              No pudimos saber qué equipo es. Escríbelo en “Corregir datos” para poder confirmarlo.
            </p>
          )}

          {a.status === "necesita_foto" && <RetakePhoto assetId={id} onDone={() => refresh()} />}
          {(a.status === "faltan_datos" || asset.extra?.nombre_pendiente) && (
            <RetakePhoto kind="equipo" assetId={id} onDone={() => refresh()} />
          )}

          {a.status === "por_confirmar" && a.reading && (
            <Card className="flex flex-col gap-3">
              <p className="font-extrabold text-ink">Datos leídos de la placa</p>
              <p className="text-sm text-muted">Los leyó la IA. Revísalos: si algo está mal, corrígelo abajo antes de confirmar.</p>
              <dl className="grid grid-cols-2 gap-y-2 text-sm">
                {Object.entries(READ_LABEL).map(([k, label]) => (
                  <div key={k} className="contents"><dt className="text-muted">{label}</dt><dd className="font-semibold">{a.reading?.fields[k] ? String(a.reading.fields[k]) : "No se leyó"}</dd></div>
                ))}
              </dl>
              <button className="btn w-full" disabled={busy} onClick={confirmData}><Icon name="check" size={18} stroke={2.6} />Confirmar estos datos</button>
            </Card>
          )}

          <Card className="!p-0">
            <dl className="divide-y divide-white/70">
              {rows.map(([k, v]) => (
                <div key={k} className="flex min-h-[52px] items-center justify-between gap-3 px-5 py-3">
                  <dt className="text-sm text-[var(--ng-body)]">{k}</dt>
                  <dd className="text-[15px] font-extrabold">{v ?? "—"}</dd>
                </div>
              ))}
              <div className="flex min-h-[52px] items-center justify-between px-5 py-3"><dt className="text-sm text-[var(--ng-body)]">Valor estimado</dt><dd className="chip"><Icon name="clock" size={13} stroke={2.4} />Muy pronto</dd></div>
            </dl>
          </Card>

          <Card className="flex flex-col gap-3">
            <p className="font-extrabold text-ink">Corregir datos</p>
            <p className="text-sm text-muted">Cambia lo que esté mal. Solo se guarda lo que modifiques.</p>
            {FIELDS.map((k) => (
              <label key={k} className="flex flex-col gap-1 text-sm">
                <span className="font-bold text-muted">{LABEL[k]}</span>
                <input className="field" value={cur[k] ?? ""} maxLength={k === "name" ? 200 : 120}
                       onChange={(e) => setEdit({ ...cur, [k]: e.target.value })} />
              </label>
            ))}
            <label className="flex flex-col gap-1 text-sm">
              <span className="font-bold text-muted">Ubicación</span>
              <select className="field" value={cur.space_id} onChange={(e) => setEdit({ ...cur, space_id: e.target.value })}>
                {spaces.data?.map((x) => <option key={x.id} value={x.id}>{x.name}</option>)}
              </select>
            </label>
            <button className="btn w-full" disabled={busy} onClick={saveEdit}>Guardar cambios</button>
            {okMsg && <p className="text-sm font-semibold text-[var(--ng-ok)]">{okMsg}</p>}
          </Card>

          {needs && (
            <Card className="flex flex-col gap-3">
              <p className="font-extrabold text-ink">Escribir los datos que faltan</p>
              {(["brand", "model", "serial"] as const).map((k) => (
                <input key={k} className="field" placeholder={{ brand: "Marca", model: "Modelo", serial: "Número de serie" }[k]} aria-label={{ brand: "Marca", model: "Modelo", serial: "Número de serie" }[k]}
                       value={manual[k]} onChange={(e) => setManual({ ...manual, [k]: e.target.value })} />
              ))}
              <button className="btn btn-ghost" disabled={busy} onClick={saveManual}>Guardar datos</button>
            </Card>
          )}

          <div className="flex gap-2.5">
            <Link href="/servicios" className="btn !min-h-12 flex-1 !px-3 !text-sm"><Icon name="headset" size={18} />Necesito ayuda</Link>
            <Link href="/cuidado" className="btn btn-ghost !min-h-12 flex-1 !px-3 !text-sm"><Icon name="wrench" size={18} />Registrar cuidado</Link>
          </div>

          <Card className="flex flex-col gap-3">
            <p className="font-extrabold text-ink">Eliminar equipo</p>
            {!confirmDel ? (
              <>
                <p className="text-sm text-muted">¿Ya lo vendiste o lo regalaste? Quítalo de tu hogar. La etiqueta queda libre para otro equipo.</p>
                <button className="btn btn-ghost w-full" onClick={() => setConfirmDel(true)}>Eliminar equipo</button>
              </>
            ) : (
              <>
                <p className="text-sm font-semibold text-[var(--ng-warn)]">
                  Se borran {a.name}, su foto y su historial. Esta acción no se puede deshacer.
                </p>
                <div className="grid grid-cols-2 gap-2">
                  <button className="btn w-full" disabled={busy} onClick={eliminar}>Sí, eliminar</button>
                  <button className="btn btn-ghost w-full" disabled={busy} onClick={() => setConfirmDel(false)}>Cancelar</button>
                </div>
              </>
            )}
          </Card>
          <ErrorNote text={err} />
        </div>
      )}
      {tab === "Documentos" && <Pronto icon="file" title="Manuales, garantía y factura" text="Aquí guardarás el manual de uso, la garantía y la factura de este equipo." />}
      {tab === "Cuidado" && <Pronto icon="heart" title="Plan de cuidado" text="Aquí verás qué hacerle a este equipo y cuándo, según su modelo." />}
      {tab === "Historial" && (
        <ol className="flex flex-col gap-3">
          {a.events.map((e, i) => (
            <li key={i} className="g rounded-[22px] p-4">
              <div className="flex items-center justify-between"><span className="chip">{e.type === "registro" ? "Registro" : "Actualización"}</span><span className="text-[12.5px] text-muted">{new Date(e.at).toLocaleDateString("es-MX", { day: "numeric", month: "short", year: "numeric" })}</span></div>
              <p className="mt-2 text-[15px] font-extrabold">{EVENT[e.type] ?? e.type}</p>
            </li>
          ))}
        </ol>
      )}
    </Shell>
  );
}
