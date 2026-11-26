"use client";
import Link from "next/link";
import { useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Shell, ErrorNote } from "@/components/Shell";
import { Icon, equipmentIcon } from "@/components/Icon";
import { useApi } from "@/lib/api";
import {
  HouseholdTask, PRIORITY_LABEL, SOURCE_LABEL, dueLabel, firstStep, longDate, monthLabel, shortDate, splitByDue, warrantyView, weekDays,
} from "@/lib/care";

const TABS = ["Próximas", "Vencidas", "Garantías", "Historial"] as const;
type Tab = (typeof TABS)[number];
type Todo = { today: string; tasks: HouseholdTask[] };
type Garantias = { today: string; warranties: { asset_id: string; asset_name: string; space_name: string | null; ends_on: string; provider: string | null }[] };
type Historia = { records: { id: string; title: string; done_on: string; asset_id: string; asset_name: string }[] };

const PRIO_STYLE = { alta: "!bg-[rgba(193,139,88,.24)] !text-[#8F5A1F]", media: "", baja: "" } as const;

export default function Cuidado() {
  const api = useApi(); const qc = useQueryClient();
  const [tab, setTab] = useState<Tab>("Próximas");
  const [semana, setSemana] = useState(0);
  const [dia, setDia] = useState<string | null>(null);
  const [resched, setResched] = useState<string | null>(null);
  const [fecha, setFecha] = useState("");
  const [aviso, setAviso] = useState<string | null>(null);
  const [err, setErr] = useState<string | null>(null);

  const todo = useQuery({ queryKey: ["care-all"], queryFn: () => api<Todo>("/care") });
  const gar = useQuery({ queryKey: ["care-warranties"], queryFn: () => api<Garantias>("/care/warranties"), enabled: tab === "Garantías" });
  const his = useQuery({ queryKey: ["care-history"], queryFn: () => api<Historia>("/care/history"), enabled: tab === "Historial" });

  const refresh = () => { for (const k of ["care-all", "care-history", "care"]) qc.invalidateQueries({ queryKey: [k] }); qc.invalidateQueries({ queryKey: ["asset"] }); };
  const accion = useMutation({
    mutationFn: (a: { path: string; body?: unknown; ok: string }) =>
      api(a.path, { method: "POST", body: a.body ? JSON.stringify(a.body) : undefined }).then(() => a.ok),
    onSuccess: (ok) => { setErr(null); setResched(null); setAviso(ok); refresh(); },
    onError: (x) => { setAviso(null); setErr((x as Error).message); },
  });

  const today = todo.data?.today ?? new Date().toISOString().slice(0, 10);
  const { overdue, upcoming } = splitByDue(todo.data?.tasks ?? [], today);
  const dias = weekDays(today, semana);
  const conTareas = new Set((todo.data?.tasks ?? []).map((t) => t.next_due));
  const lista = tab === "Vencidas" ? overdue : dia ? (todo.data?.tasks ?? []).filter((t) => t.next_due === dia) : upcoming;

  return (
    <Shell title="Cuidado" subtitle="Lo que conviene hacer para que tus equipos duren más." big nav="cuidado">
      <div role="tablist" className="g mt-3 flex gap-1 rounded-full p-1" style={{ borderRadius: 999 }}>
        {TABS.map((t) => (
          <button key={t} role="tab" aria-selected={tab === t} onClick={() => { setTab(t); setAviso(null); setErr(null); }}
            className={`h-10 flex-1 rounded-full text-[13px] font-bold ${tab === t ? "gd" : "text-[var(--ng-body)]"}`} style={{ borderRadius: 999 }}>{t}</button>
        ))}
      </div>

      {tab === "Próximas" && (
        <>
          <div className="mt-4 flex items-center justify-between text-[14px] font-extrabold">
            <span>{monthLabel(dias[3].iso)}</span>
            <span className="flex gap-1.5 text-navy">
              <button type="button" aria-label="Semana anterior" onClick={() => setSemana(semana - 1)} className="grid h-9 w-9 place-items-center rounded-full"><Icon name="back" size={20} /></button>
              <button type="button" aria-label="Semana siguiente" onClick={() => setSemana(semana + 1)} className="grid h-9 w-9 place-items-center rounded-full"><span style={{ display: "inline-flex", transform: "rotate(180deg)" }}><Icon name="back" size={20} /></span></button>
            </span>
          </div>
          <div className="g mt-2 flex justify-between rounded-[30px] px-1.5 py-1">
            {dias.map((d) => {
              const sel = dia === d.iso;
              return (
                <button key={d.iso} type="button" aria-pressed={sel} aria-label={`${longDate(d.iso)}${conTareas.has(d.iso) ? ", con cuidados" : ""}`}
                  onClick={() => setDia(sel ? null : d.iso)}
                  className={`flex h-[66px] w-[42px] flex-col items-center justify-center gap-[3px] rounded-[21px] ${sel ? "gd" : "text-ink"} ${d.iso === today && !sel ? "ring-1 ring-navy/40" : ""}`}>
                  <span className={`text-[12px] font-semibold ${sel ? "text-white/90" : "text-muted"}`}>{d.dow}</span>
                  <span className="text-[17px] font-extrabold">{d.num}</span>
                  <span aria-hidden="true" className="h-[5px] w-[5px] rounded-full" style={{ background: conTareas.has(d.iso) ? "#C18B58" : "transparent" }} />
                </button>
              );
            })}
          </div>
          {dia && <button type="button" onClick={() => setDia(null)} className="mt-2 px-1 text-[13px] font-bold text-navy">Ver todas las próximas</button>}
        </>
      )}

      {aviso && <p role="status" className="mt-3 px-1 text-[13px] font-bold text-[var(--ng-ok)]">{aviso}</p>}
      <ErrorNote text={err} />

      {(tab === "Próximas" || tab === "Vencidas") && (
        <div className="mt-4 flex flex-col gap-3">
          {lista.map((t) => {
            const due = dueLabel(t.next_due ?? today, new Date(`${today}T12:00:00`));
            const paso = firstStep(t.instructions);
            const ocupado = accion.isPending;
            return (
              <article key={t.id} className="g rounded-[28px] p-4">
                <div className="flex items-start gap-3">
                  <Link href={`/equipos/${t.asset_id}`} aria-label={`Abrir ${t.asset_name}`} className="icon-tile !h-[42px] !w-[42px]"><Icon name={equipmentIcon({ name: t.asset_name })} size={20} /></Link>
                  <div className="min-w-0 flex-1">
                    <p className="text-[15.5px] font-extrabold leading-snug">{t.title}</p>
                    <p className="mt-0.5 text-[12.5px] text-muted">{t.asset_name}{t.space_name ? ` · ${t.space_name}` : ""}, {longDate(t.next_due ?? today)}</p>
                  </div>
                  {t.priority && <span className={`chip whitespace-nowrap ${PRIO_STYLE[t.priority]}`}>{PRIORITY_LABEL[t.priority]}</span>}
                </div>
                {due.tone === "vencido" && <p className="mt-2 text-[12.5px] font-bold text-[var(--ng-warn)]">{due.text}</p>}
                <p className="mt-2.5 flex items-center gap-1.5 text-[12.5px] font-semibold text-muted">
                  <Icon name={t.source === "manual" || t.confirmed ? "check" : "sparkle"} size={14} stroke={2.2} />
                  {t.confirmed && t.source === "sugerencia" ? "Confirmado por ti" : SOURCE_LABEL[t.source]}</p>
                {paso && <p className="mt-1 text-[12.5px] leading-snug text-muted">{paso}</p>}
                <div className="mt-3 flex gap-2">
                  <button type="button" disabled={ocupado} className="btn !min-h-10 flex-1 !px-3 !text-[13.5px]"
                    onClick={() => accion.mutate({ path: `/care/${t.id}/done`, ok: "Listo, lo anotamos en el historial." })}><Icon name="check" size={16} stroke={2.4} />Marcar como realizado</button>
                  <button type="button" disabled={ocupado} className="btn btn-ghost !min-h-10 !px-4 !text-[13.5px]"
                    onClick={() => { setResched(resched === t.id ? null : t.id); setFecha(t.next_due ?? today); }}>Reprogramar</button>
                </div>
                {resched === t.id && (
                  <div className="mt-2 flex items-center gap-2">
                    <label className="sr-only" htmlFor={`g-${t.id}`}>Nueva fecha</label>
                    <input id={`g-${t.id}`} type="date" className="field !min-h-11 flex-1" min={today} value={fecha} onChange={(e) => setFecha(e.target.value)} />
                    <button type="button" disabled={ocupado || !fecha} className="btn !min-h-11 !px-4 !text-[14px]"
                      onClick={() => accion.mutate({ path: `/care/${t.id}/reschedule`, body: { next_due: fecha }, ok: "Listo, cambiamos la fecha." })}>Guardar</button>
                  </div>
                )}
              </article>
            );
          })}
          {todo.isSuccess && lista.length === 0 && (
            <Vacio icon="heart" titulo={tab === "Vencidas" ? "Estás al día" : dia ? "Nada para este día" : (todo.data?.tasks.length ? "No hay cuidados próximos" : "Aún no hay cuidados")}
              texto={tab === "Vencidas" ? "No tienes cuidados vencidos." : dia ? "Elige otro día o toca el mismo para ver todas las próximas."
                : todo.data?.tasks.length ? "Cuando se acerque la fecha de un cuidado, lo verás aquí." : "Se preparan solos cuando confirmas un equipo. Confirma tus equipos en Por revisar y vuelve aquí."} />
          )}
          {todo.isLoading && <p className="px-1 text-[14px] text-muted">Cargando…</p>}
          {todo.isError && <ErrorNote text={(todo.error as Error).message} />}
        </div>
      )}

      {tab === "Garantías" && (
        <div className="mt-4 flex flex-col gap-3">
          {gar.data?.warranties.map((w) => {
            const v = warrantyView({ ends_on: w.ends_on, provider: w.provider, confirmed: true }, new Date(`${gar.data!.today}T12:00:00`));
            return (
              <Link key={w.asset_id} href={`/equipos/${w.asset_id}`} className="g flex items-center gap-3 rounded-[22px] p-3.5">
                <span className="icon-tile"><Icon name="shield" size={20} /></span>
                <div className="min-w-0 flex-1">
                  <p className="truncate text-[15px] font-extrabold">{w.asset_name}</p>
                  <p className="text-[13px] text-muted">{v.text}{w.provider ? ` · ${w.provider}` : ""}</p>
                </div>
                <span className={`chip ${v.tone === "warn" ? "text-[var(--ng-warn)]" : v.tone === "off" ? "text-muted" : ""}`}><Icon name="clock" size={13} stroke={2.4} />{v.badge}</span>
              </Link>
            );
          })}
          {gar.isSuccess && gar.data.warranties.length === 0 && <Vacio icon="shield" titulo="Aún no hay garantías" texto="Sube la garantía de un equipo en su pestaña Documentos y la verás aquí, con los días que faltan." />}
          {gar.isError && <ErrorNote text={(gar.error as Error).message} />}
        </div>
      )}

      {tab === "Historial" && (
        <div className="mt-4 flex flex-col gap-3">
          {his.data?.records.map((r) => (
            <Link key={r.id} href={`/equipos/${r.asset_id}`} className="g flex items-center gap-3 rounded-[22px] p-3.5">
              <span className="icon-tile"><Icon name="check" size={20} stroke={2.4} /></span>
              <div className="min-w-0 flex-1">
                <p className="text-[15px] font-extrabold leading-snug">{r.title}</p>
                <p className="text-[13px] text-muted">{r.asset_name} · {shortDate(r.done_on)}</p>
              </div>
            </Link>
          ))}
          {his.isSuccess && his.data.records.length === 0 && <Vacio icon="clock" titulo="Aún no hay historial" texto="Cuando marques un cuidado como realizado, quedará anotado aquí." />}
          {his.isError && <ErrorNote text={(his.error as Error).message} />}
        </div>
      )}
    </Shell>
  );
}

function Vacio({ icon, titulo, texto }: { icon: string; titulo: string; texto: string }) {
  return (
    <div className="g rounded-[26px] p-6 text-center">
      <span className="icon-tile mx-auto"><Icon name={icon} size={22} /></span>
      <p className="mt-3 text-[16px] font-extrabold">{titulo}</p>
      <p className="mt-1 text-[13.5px] text-muted">{texto}</p>
    </div>
  );
}
