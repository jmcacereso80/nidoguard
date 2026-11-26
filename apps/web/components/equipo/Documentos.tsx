"use client";
import { useQuery } from "@tanstack/react-query";
import { Icon } from "@/components/Icon";
import { ApiError, useApi } from "@/lib/api";
import { DocumentsData, warrantyView } from "@/lib/care";

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
        <Titulo>Manuales</Titulo>
        <div className="flex flex-col gap-2.5">
          {manuals.length === 0 && (
            <div className="g flex items-center gap-3 rounded-[22px] p-3.5">
              <span className="icon-tile"><Icon name="file" size={20} /></span>
              <div className="min-w-0 flex-1">
                <p className="text-[15px] font-extrabold">Manual de uso</p>
                <p className="text-[13px] text-muted">Buscaremos el documento de tu modelo cuando confirmes marca y modelo.</p>
              </div>
            </div>
          )}
          {manuals.map((m) => (
            <div key={m.id} className="g flex items-center gap-3 rounded-[22px] p-3.5">
              <span className="icon-tile"><Icon name="file" size={20} /></span>
              <div className="min-w-0 flex-1">
                <p className="truncate text-[15px] font-extrabold">{m.title}</p>
                <p className="text-[13px] text-muted">{m.status === "buscando" ? "Buscando el documento de tu modelo" : m.note}</p>
              </div>
              {m.status === "buscando"
                ? <span className="chip"><Icon name="clock" size={13} stroke={2.4} />Buscando</span>
                : m.url && <a href={m.url} target="_blank" rel="noreferrer" className="btn-ghost h-10 px-4 text-[14px] font-bold">Ver</a>}
            </div>
          ))}
        </div>
      </section>

      <section>
        <Titulo>Garantía</Titulo>
        {w ? (
          <div className="g flex items-center gap-3 rounded-[22px] p-3.5">
            <span className="icon-tile"><Icon name="shield" size={20} /></span>
            <div className="min-w-0 flex-1">
              <p className="text-[15px] font-extrabold">Garantía del fabricante</p>
              <p className="text-[13px] text-muted">{w.text}</p>
            </div>
            <span className={`chip ${TONE[w.tone]}`}><Icon name="clock" size={13} stroke={2.4} />{w.badge}</span>
          </div>
        ) : (
          <div className="g rounded-[22px] p-4">
            <p className="text-[15px] font-extrabold">Aún no hay garantía</p>
            <p className="mt-0.5 text-[13px] text-muted">Súbela junto con tu factura y te avisamos antes de que venza.</p>
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
              <div className="mt-3 flex gap-2.5">
                <button type="button" disabled className="btn h-11 flex-1 text-[14px] font-bold opacity-60"><Icon name="camera" size={17} />Tomar foto</button>
                <button type="button" disabled className="btn-ghost h-11 flex-1 text-[14px] font-bold opacity-60"><Icon name="file" size={17} />Subir PDF</button>
              </div>
              <p className="mt-2 text-[12px] text-muted">Muy pronto podrás guardarla aquí.</p>
            </>
          )}
        </div>
        <p className="mt-3 flex items-center gap-1.5 px-1 text-[12.5px] text-muted"><Icon name="shield" size={14} />Solo tú ves tu garantía y tu factura.</p>
      </section>
    </div>
  );
}
