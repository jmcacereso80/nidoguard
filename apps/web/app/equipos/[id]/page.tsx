"use client";
import { use, useState } from "react";
import { useRouter } from "next/navigation";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import { Shell, Card, ErrorNote } from "@/components/Shell";
import { Asset, Space, useApi } from "@/lib/api";
import { statusInfo } from "@/lib/assetStatus";

type Detail = Asset & {
  extra?: { nombre_pendiente?: boolean } | null;
  reading: { status: string; source: string; fields: Record<string, string>; confidence: Record<string, number>; confirmed: boolean } | null;
  events: { type: string; at: string; payload: Record<string, unknown> }[];
};
const EVENT: Record<string, string> = {
  registro: "Registrado", lectura_ia: "Placa leída", confirmado: "Datos confirmados",
  datos_manuales: "Datos escritos a mano", edicion: "Datos corregidos",
};
// Nombres en español de los datos que lee la IA de la placa.
const READ_LABEL: Record<string, string> = {
  brand: "Marca", model: "Modelo", serial: "Número de serie", product_number: "Número de producto",
  category: "Tipo", voltage: "Voltaje", frequency: "Frecuencia", capacity: "Capacidad", power: "Potencia",
  refrigerant: "Refrigerante", country: "Origen", certifications: "Certificaciones", manufacture_date: "Fecha de fabricación",
};
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

  const a = q.data;
  if (!a) return <Shell title="Equipo" back="/inicio"><p>Cargando…</p></Shell>;
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

  return (
    <Shell title={a.name} back="/inicio">
      <div className="flex flex-col gap-4">
        <Card className="flex flex-col gap-2">
          <p className={`text-lg font-extrabold ${toneClass}`}>{info.label}</p>
          <p className="text-sm text-muted">{info.detail}</p>
          {asset.extra?.nombre_pendiente && (
            <p className="text-sm font-semibold text-[var(--ng-warn)]">
              No pudimos saber qué equipo es. Escríbelo en “Corregir datos” para poder confirmarlo.
            </p>
          )}
        </Card>

        {a.status === "por_confirmar" && a.reading && (
          <Card className="flex flex-col gap-3">
            <p className="font-extrabold text-ink">Datos leídos de la placa</p>
            <p className="text-sm text-muted">Los leyó la IA. Revísalos: si algo está mal, corrígelo abajo antes de confirmar.</p>
            <dl className="grid grid-cols-2 gap-y-2 text-sm">
              {Object.entries(a.reading.fields)
                .filter(([k, v]) => v && k !== "suggested_name" && READ_LABEL[k])
                .map(([k, v]) => (
                  <div key={k} className="contents"><dt className="text-muted">{READ_LABEL[k]}</dt><dd className="font-semibold">{String(v)}</dd></div>
                ))}
            </dl>
            <button className="btn w-full" disabled={busy} onClick={confirmData}>Confirmar estos datos</button>
          </Card>
        )}

        <Card>
          <dl className="grid grid-cols-2 gap-y-2 text-sm">
            {([["Marca", a.brand], ["Modelo", a.model], ["Serie", a.serial], ["Tipo", a.category]] as const).map(([k, v]) => (
              <div key={k} className="contents"><dt className="text-muted">{k}</dt><dd className="font-semibold">{v ?? "—"}</dd></div>
            ))}
          </dl>
        </Card>

        <Card className="flex flex-col gap-3">
          <p className="font-extrabold text-ink">Corregir datos</p>
          <p className="text-sm text-muted">Cambia lo que esté mal. Solo se guarda lo que modifiques.</p>
          {FIELDS.map((k) => (
            <label key={k} className="flex flex-col gap-1 text-sm">
              <span className="font-semibold text-navy">{LABEL[k]}</span>
              <input className="field" value={cur[k] ?? ""} maxLength={k === "name" ? 200 : 120}
                     onChange={(e) => setEdit({ ...cur, [k]: e.target.value })} />
            </label>
          ))}
          <label className="flex flex-col gap-1 text-sm">
            <span className="font-semibold text-navy">Ubicación</span>
            <select className="field" value={cur.space_id} onChange={(e) => setEdit({ ...cur, space_id: e.target.value })}>
              {spaces.data?.map((s) => <option key={s.id} value={s.id}>{s.name}</option>)}
            </select>
          </label>
          <button className="btn w-full" disabled={busy} onClick={saveEdit}>Guardar cambios</button>
          {okMsg && <p className="text-sm font-semibold text-[var(--ng-ok)]">{okMsg}</p>}
        </Card>

        {needs && (
          <Card className="flex flex-col gap-3">
            <p className="font-extrabold text-ink">Escribir los datos que faltan</p>
            {(["brand", "model", "serial"] as const).map((k) => (
              <input key={k} className="field" placeholder={{ brand: "Marca", model: "Modelo", serial: "Número de serie" }[k]}
                     value={manual[k]} onChange={(e) => setManual({ ...manual, [k]: e.target.value })} />
            ))}
            <button className="btn btn-ghost" disabled={busy} onClick={saveManual}>Guardar datos</button>
          </Card>
        )}

        <Card>
          <p className="mb-2 font-extrabold text-ink">Historial</p>
          <ol className="flex flex-col gap-2 text-sm">
            {a.events.map((e, i) => <li key={i}><span className="font-semibold">{EVENT[e.type] ?? e.type}</span> · {new Date(e.at).toLocaleDateString("es-MX")}</li>)}
          </ol>
        </Card>

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
    </Shell>
  );
}
