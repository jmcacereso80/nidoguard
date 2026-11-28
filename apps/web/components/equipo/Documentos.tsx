"use client";
import { useRef, useState } from "react";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import { Icon } from "@/components/Icon";
import { ApiError, useApi } from "@/lib/api";
import { DocumentsData, WarrantyInfo, WarrantyPending, warrantyView } from "@/lib/care";

export function useDocumentos(id: string) {
  const api = useApi();
  return useQuery({
    queryKey: ["documents", id],
    // Si la API todavía no tiene documentos de este equipo, se muestra el estado vacío.
    queryFn: async () => {
      try { return await api<DocumentsData>(`/assets/${id}/documents`); }
      catch (x) { if (x instanceof ApiError && (x.status === 404 || x.status === 501)) return null; throw x; }
    },
  });
}

const TONE = { ok: "text-[var(--ng-ok)]", warn: "text-[var(--ng-warn)]", off: "text-muted" } as const;

function Titulo({ children }: { children: React.ReactNode }) {
  return <h2 className="mb-2 px-1 text-[15px] font-extrabold text-navy">{children}</h2>;
}

export function Documentos({ id }: { id: string }) {
  const { data } = useDocumentos(id);
  const manuals = data?.manuals ?? [];
  const w = data?.warranty ? warrantyView(data.warranty) : null;
  return (
    <div className="flex flex-col gap-5">
      <section>
        <Titulo>Manual de uso</Titulo>
        <div className="flex flex-col gap-2.5">
          {manuals.length === 0 && (
            <div className="g flex items-center gap-3 rounded-[22px] p-3.5">
              <span className="icon-tile"><Icon name="file" size={20} /></span>
              <div className="min-w-0 flex-1">
                <p className="text-[15px] font-extrabold">{data?.model_confirmed === false ? "Manual de uso" : "Buscando el manual de tu modelo"}</p>
                <p className="text-[13px] text-muted">{data?.model_confirmed === false ? "Lo buscamos cuando confirmes marca y modelo." : "NidoGuard lo busca por tu marca y modelo. No tienes que subirlo."}</p>
              </div>
              {data?.model_confirmed !== false && <span className="chip"><Icon name="clock" size={13} stroke={2.4} />Buscando</span>}
            </div>
          )}
          {manuals.map((m) => (
            <div key={m.id} className="g flex items-center gap-3 rounded-[22px] p-3.5">
              <span className="icon-tile"><Icon name="file" size={20} /></span>
              <div className="min-w-0 flex-1">
                <p className="truncate text-[15px] font-extrabold">{m.title}</p>
                <p className="text-[13px] text-muted">{m.status === "buscando" ? "Buscando el documento de tu modelo" : m.status === "no_encontrado" ? "No lo encontramos todavía. Lo seguiremos intentando." : m.note}</p>
              </div>
              {m.status === "buscando" && <span className="chip"><Icon name="clock" size={13} stroke={2.4} />Buscando</span>}
              {m.status === "listo" && m.url && <a href={m.url} target="_blank" rel="noreferrer" className="btn btn-ghost !min-h-10 !px-4 !text-[14px]">Ver</a>}
            </div>
          ))}
        </div>
      </section>

      <section>
        <Titulo>Garantía</Titulo>
        {data?.warranty && (<>
          <FormaGarantia id={id} pendiente={{ document_id: data.warranty.document_id ?? "", filename: "" }} actual={data.warranty} />
          <div className="g -mt-1 flex items-center gap-2 rounded-[22px] px-3.5 py-2">
            <span className="flex-1 text-[12.5px] text-muted">¿Cambió? Sube la nueva garantía</span>
            <Subir id={id} kind="garantia" compact />
          </div>
        </>)}
        {!data?.warranty && data?.warranty_pending && <FormaGarantia id={id} pendiente={data.warranty_pending} />}
        {!data?.warranty && !data?.warranty_pending && (
          <div className="g rounded-[22px] p-4">
            <p className="text-[15px] font-extrabold">Aún no hay garantía</p>
            <p className="mt-0.5 text-[13px] text-muted">Sube una foto o el PDF de tu garantía y escribe la fecha en que vence.</p>
            <Subir id={id} kind="garantia" />
          </div>
        )}
      </section>

      <section>
        <Titulo>Factura</Titulo>
        <div className="g rounded-[22px] p-4">
          {data?.invoice ? (
            <div className="flex items-center gap-3">
              <span className="icon-tile"><Icon name="file" size={20} /></span>
              <div className="min-w-0 flex-1"><p className="truncate text-[15px] font-extrabold">{data.invoice.name}</p>
                <p className="text-[13px] text-muted">Guardada el {new Date(data.invoice.uploaded_at).toLocaleDateString("es-MX", { day: "numeric", month: "short", year: "numeric" })}</p></div>
            </div>
          ) : (
            <>
              <p className="text-[15px] font-extrabold">Aún no hay factura</p>
              <p className="mt-0.5 text-[13px] text-muted">Si la tienes, guárdala para respaldar tu garantía.</p>
              <Subir id={id} kind="factura" />
            </>
          )}
        </div>
        <p className="mt-3 flex items-center gap-1.5 px-1 text-[12.5px] text-muted"><Icon name="shield" size={14} />Solo tú ves tu garantía y tu factura.</p>
      </section>
    </div>
  );
}

// Subir foto o PDF: la API da una URL firmada de R2, se sube el archivo y luego se pide leerlo.
function Subir({ id, kind, compact = false }: { id: string; kind: "garantia" | "factura"; compact?: boolean }) {
  const api = useApi(); const qc = useQueryClient();
  const foto = useRef<HTMLInputElement>(null); const pdf = useRef<HTMLInputElement>(null);
  const [msg, setMsg] = useState<string | null>(null); const [busy, setBusy] = useState(false);
  async function enviar(f: File | undefined) {
    if (!f) return;
    setBusy(true); setMsg(null);
    try {
      const { upload_url, document_id } = await api<{ upload_url: string; document_id: string }>(`/assets/${id}/documents/upload-url`, {
        method: "POST", body: JSON.stringify({ kind, filename: f.name, content_type: f.type || "application/octet-stream", size: f.size }) });
      const put = await fetch(upload_url, { method: "PUT", body: f, headers: { "Content-Type": f.type || "application/octet-stream" } });
      if (!put.ok) throw new Error("No pudimos subir el archivo. Inténtalo de nuevo.");
      await api(`/assets/${id}/documents/${document_id}/process`, { method: "POST" });
      qc.invalidateQueries({ queryKey: ["documents", id] });
      setMsg(kind === "garantia" ? "Listo. Ahora escribe la fecha en que vence tu garantía." : "Factura guardada.");
    } catch (x) {
      setMsg(x instanceof ApiError && (x.status === 404 || x.status === 501) ? "Muy pronto podrás guardarla aquí." : (x as Error).message);
    } finally { setBusy(false); }
  }
  return (
    <div className={compact ? "" : "mt-3"}>
      {compact ? (
        <div className="flex gap-2">
          <button type="button" disabled={busy} aria-label="Tomar foto de la garantía" onClick={() => foto.current?.click()} className="btn btn-ghost !min-h-10 !w-11 !px-0"><Icon name="camera" size={18} /></button>
          <button type="button" disabled={busy} aria-label="Subir PDF de la garantía" onClick={() => pdf.current?.click()} className="btn btn-ghost !min-h-10 !w-11 !px-0"><Icon name="file" size={18} /></button>
        </div>
      ) : (
      <div className="flex gap-2.5">
        <button type="button" disabled={busy} onClick={() => foto.current?.click()} className="btn !min-h-11 flex-1 !px-3 !text-[14px]"><Icon name="camera" size={17} />Tomar foto</button>
        <button type="button" disabled={busy} onClick={() => pdf.current?.click()} className="btn btn-ghost !min-h-11 flex-1 !px-3 !text-[14px]"><Icon name="file" size={17} />Subir PDF</button>
      </div>)}
      <input ref={foto} type="file" accept="image/*" capture="environment" hidden onChange={(e) => { enviar(e.target.files?.[0]); e.target.value = ""; }} />
      <input ref={pdf} type="file" accept="application/pdf" hidden onChange={(e) => { enviar(e.target.files?.[0]); e.target.value = ""; }} />
      {busy && <p className="mt-2 text-[12.5px] text-muted">Subiendo…</p>}
      {msg && <p role="status" className="mt-2 text-[12.5px] text-muted">{msg}</p>}
    </div>
  );
}

// Garantia: la persona escribe la fecha de vencimiento (y proveedor y precio si los tiene). El documento queda de respaldo.
function FormaGarantia({ id, pendiente, actual }: { id: string; pendiente: WarrantyPending; actual?: WarrantyInfo }) {
  const api = useApi(); const qc = useQueryClient();
  const [editando, setEditando] = useState(!actual);
  const [fecha, setFecha] = useState(actual?.ends_on ?? "");
  const [proveedor, setProveedor] = useState(actual?.provider ?? "");
  const [precio, setPrecio] = useState(actual?.price != null ? String(actual.price) : "");
  const [msg, setMsg] = useState<string | null>(null); const [busy, setBusy] = useState(false);
  const docId = actual?.document_id ?? pendiente.document_id;

  async function guardar(e: React.FormEvent) {
    e.preventDefault(); setBusy(true); setMsg(null);
    try {
      await api(`/assets/${id}/warranty`, { method: "POST", body: JSON.stringify({
        document_id: docId, ends_on: fecha, provider: proveedor.trim() || null,
        price: precio.trim() ? Number(precio) : null }) });
      setEditando(false);
      qc.invalidateQueries({ queryKey: ["documents", id] });
    } catch (x) { setMsg((x as Error).message); } finally { setBusy(false); }
  }

  if (!editando && actual) {
    const v = warrantyView(actual);
    return (
      <div className="g mb-2 flex items-center gap-3 rounded-[22px] p-3.5">
        <span className="icon-tile"><Icon name="shield" size={20} /></span>
        <div className="min-w-0 flex-1">
          <p className="text-[15px] font-extrabold">Garantía del fabricante</p>
          <p className="text-[13px] text-muted">{actual.provider ? `${actual.provider} · ` : ""}{v.text}</p>
          {actual.price != null && <p className="text-[13px] text-muted">Precio de compra: ${actual.price.toLocaleString("es-MX")} MXN</p>}
        </div>
        <span className={`chip ${TONE[v.tone]}`}><Icon name="clock" size={13} stroke={2.4} />{v.badge}</span>
        <button type="button" className="btn btn-ghost !min-h-10 !px-3 !text-[14px]" onClick={() => setEditando(true)}>Editar</button>
      </div>
    );
  }

  return (
    <form onSubmit={guardar} className="g mb-2 flex flex-col gap-3 rounded-[22px] p-4">
      <p className="text-[15px] font-extrabold">{actual ? "Corrige los datos de tu garantía" : "Escribe la fecha de vencimiento"}</p>
      <p className="text-[13px] text-muted">Tu documento queda guardado como respaldo.</p>
      <label className="flex flex-col gap-1 text-[13px] font-bold text-navy">Vence el
        <input type="date" className="field" value={fecha} onChange={(e) => setFecha(e.target.value)} required />
      </label>
      <label className="flex flex-col gap-1 text-[13px] font-bold text-navy">Proveedor o tienda (opcional)
        <input className="field" value={proveedor} onChange={(e) => setProveedor(e.target.value)} placeholder="Ej. Liverpool" maxLength={200} />
      </label>
      <label className="flex flex-col gap-1 text-[13px] font-bold text-navy">Precio de compra en pesos (opcional)
        <input type="number" min={0} step="0.01" className="field" value={precio} onChange={(e) => setPrecio(e.target.value)} placeholder="Ej. 8500" />
      </label>
      <div className="flex gap-2.5">
        <button className="btn !min-h-11 flex-1 !px-3 !text-[14px]" disabled={busy || !fecha}>{busy ? "Guardando…" : "Guardar garantía"}</button>
        {actual && <button type="button" className="btn btn-ghost !min-h-11 !px-4 !text-[14px]" onClick={() => setEditando(false)}>Cancelar</button>}
      </div>
      {msg && <p role="alert" className="text-[12.5px] font-semibold text-[var(--ng-danger)]">{msg}</p>}
    </form>
  );
}
