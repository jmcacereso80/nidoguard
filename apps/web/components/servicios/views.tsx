"use client";
import Link from "next/link";
import type { ServiceContacts } from "@/lib/api";
import { AgregarCalendario } from "@/components/servicios/AgregarCalendario";
import { ConfirmLink } from "@/components/servicios/ConfirmLink";
import { Stars } from "@/components/servicios/Stars";
import { useEffect, useState } from "react";
import { Icon } from "@/components/Icon";
import { ErrorNote } from "@/components/Shell";
import { useMe } from "@/components/useHome";
import {
  Actions, Callout, Chip, ConsentCheck, Hero, Hr, KV, Label, NoCobro, Note, Steps, Summary, TextLink, Timeline,
} from "./ui";
import {
  NO_COBRO_FABRICANTE, Quote, ServiceRequest, Sort, TAG_LABEL, URGENCY_LABEL, calendarEvent, callText, distanceLabel, hourRange, invoiceLabel, longDay,
  mapsLink, money, priceLabel, priceNote, progressOf, slotChip, sortQuotes, warrantyLabel, shortDay,
} from "@/lib/servicios";

export type Act = (path: string, body?: unknown) => Promise<unknown>;
type P = { r: ServiceRequest; act: Act; busy: boolean; err: string | null };
const Btn = ({ onClick, disabled, children, ghost, danger }: { onClick?: () => void; disabled?: boolean; children: React.ReactNode; ghost?: boolean; danger?: boolean }) => (
  <button type="button" onClick={onClick} disabled={disabled} className={`btn ${ghost ? "btn-ghost" : ""} ${danger ? "!text-[var(--ng-danger)]" : ""}`}>{children}</button>
);

// ---------------------------------------------------------------- Antes de empezar
export function Alerta({ r, act, busy, err }: P) {
  const s = r.safety!;
  return (
    <div>
      <div className="mt-4 flex flex-col items-center gap-2.5 rounded-[30px] px-5 py-6 text-center" role="alert" style={{ background: "rgba(143,47,47,.10)", border: "1px solid rgba(143,47,47,.25)" }}>
        <span aria-hidden="true" className="grid h-16 w-16 place-items-center rounded-full bg-[#8F2F2F] text-white"><Icon name="alert" size={30} stroke={2.2} /></span>
        <p className="text-[20px] font-extrabold text-[#5E1F1F]">{s.title}</p>
        <p className="text-[14.5px] leading-relaxed text-[#5E1F1F]">{s.advice}</p>
      </div>
      <Actions>
        <a href="tel:911" className="btn !bg-[#8F2F2F] !bg-none text-white"><Icon name="phone" size={20} stroke={2.2} />Llamar al 911</a>
        <Btn ghost disabled={busy} onClick={() => act("/service-requests/{id}/ack-safety")}>Ya estoy a salvo, continuar</Btn>
      </Actions>
      <ErrorNote text={err} />
      <Note>NidoGuard no sustituye a los servicios de emergencia. Cuando estés a salvo, buscamos un técnico.</Note>
    </div>
  );
}

export function Confirmar({ r, act, busy, err }: P) {
  const [scope, setScope] = useState(r.scope_text ?? "");
  const [ok, setOk] = useState(true);
  useEffect(() => setScope(r.scope_text ?? ""), [r.scope_text]);
  const guardar = () => { if (scope.trim() && scope.trim() !== r.scope_text) act("/service-requests/{id}/scope", { scope_text: scope.trim() }); };
  const falla = r.origin === "libre";
  const puedeFabricante = !!r.asset_id;
  const sitios = (useMe().data?.home?.properties ?? []).filter((p) => p.address?.complete);
  return (
    <div>
      <div className="g mt-3 rounded-[26px] p-4">
        <p className="flex items-center gap-1.5 text-[12px] font-bold text-[#8F5A1F]"><Icon name="sparkle" size={14} stroke={2.2} />Así lo entendimos</p>
        <label className="sr-only" htmlFor="alcance">Servicio a cotizar</label>
        <textarea id="alcance" value={scope} onChange={(e) => setScope(e.target.value)} onBlur={guardar} rows={4}
          className="mt-2 block w-full resize-none rounded-[18px] border border-navy/15 bg-white/70 px-3.5 py-3 text-[15px] font-bold leading-snug text-ink" />
        <div className="mt-2.5 flex flex-wrap gap-1.5">
          <Chip icon="wrench">{r.equipment_label}</Chip><Chip icon="home">Visita a domicilio</Chip><Chip tone="gray" icon="clock">Urgencia: {URGENCY_LABEL[r.urgency].toLowerCase()}</Chip>
        </div>
      </div>
      {r.warranty && <div className="mt-3"><Callout icon="shieldok"><b>Tu garantía sigue vigente ({r.warranty.days_left} días).</b> Pregunta primero si este trabajo está cubierto.</Callout></div>}
      {falla && <div className="mt-3"><Callout>Para una falla, el técnico no puede dar el precio final por teléfono. Te diremos lo que cobra por revisar y un precio aproximado de la reparación.</Callout></div>}
      <Label>Dónde</Label>
      {sitios.length > 1 && (
        <div role="radiogroup" aria-label="Dirección del servicio" className="mb-2 flex flex-col gap-2">
          {sitios.map((p) => (
            <label key={p.id} className="g flex min-h-14 items-center gap-3 rounded-[22px] px-3.5 py-2.5">
              <input type="radio" name="direccion" checked={r.property_id === p.id} onChange={() => act("/service-requests/{id}/scope", { property_id: p.id })} className="h-[22px] w-[22px] flex-none accent-[#183B56]" />
              <span className="min-w-0 flex-1 text-[14px] font-extrabold leading-tight">{p.name}<span className="block text-[12.5px] font-semibold text-muted">{[p.address?.colony ?? p.address?.street, p.address?.city].filter(Boolean).join(", ")}</span></span>
            </label>
          ))}
        </div>
      )}
      {r.address_complete ? (
        <div className="g flex items-center gap-3 rounded-[22px] px-3.5 py-2.5">
          <span className="text-navy"><Icon name="pin" size={20} /></span>
          <div className="min-w-0 flex-1"><p className="text-[14px] font-extrabold">{r.zone}</p><p className="text-[12.5px] text-muted">Técnicos a menos de {r.radius_km} km</p></div>
          <Link href={`/hogar/direccion?p=${r.property_id ?? ""}&volver=/servicios/${r.id}`} className="flex min-h-11 items-center pl-2 text-[13px] font-extrabold text-navy">{sitios.length > 1 ? "Editar" : "Cambiar"}</Link>
        </div>
      ) : (
        <Callout icon="pin">Para buscar técnicos cercanos necesitamos la dirección de tu hogar. <Link href={`/hogar/direccion?volver=/servicios/${r.id}`} className="font-extrabold underline">Agregar mi dirección</Link></Callout>
      )}
      <Steps items={[["phone", "Un asistente virtual llama a técnicos cercanos por ti."], ["list", "Te mostramos hasta 5 cotizaciones con precio y fecha."], ["lock", "Los técnicos no ven tu dirección ni tu teléfono hasta que tú elijas."]]} />
      <div className="mt-4"><NoCobro /></div>
      <ConsentCheck checked={ok} onChange={setOk}>Autorizo que NidoGuard llame de mi parte. Tú verás solo un extracto de lo que dijo el técnico, sin su nombre ni sus datos; no compartimos la grabación.</ConsentCheck>
      <ErrorNote text={err} />
      <Actions>
        <Btn disabled={busy || !ok || !r.address_complete} onClick={() => act("/service-requests/{id}/start", { consent: ok })}><Icon name="phone" size={19} stroke={2.2} />Buscar cotizaciones</Btn>
        {puedeFabricante && <TextLink onClick={() => act("/service-requests/{id}/scope", { route: "fabricante" })}>Prefiero llevarlo al fabricante</TextLink>}
        <ConfirmLink kind="solicitud" onConfirm={() => act("/service-requests/{id}/cancel")}>Cancelar solicitud</ConfirmLink>
      </Actions>
    </div>
  );
}

export function FabricanteDatos({ r, act, busy, err }: P) {
  const m = r.manufacturer!;
  const [ok, setOk] = useState(true);
  const guardado = useMe().data?.user.phone ?? "";
  const [phone, setPhone] = useState("");
  const tecleado = phone.replace(/\D/g, "").length >= 10;
  const tengoTel = tecleado || !!guardado;  // si ya guardó su teléfono en Mi casa, no hace falta escribirlo otra vez
  const dato = (icon: string, k: string, v: string | null) => v ? <><KV icon={icon} k={k} v={v} /><Hr /></> : null;
  return (
    <div>
      <div className="g mt-3 flex items-start gap-3 rounded-[26px] p-3.5">
        <span className="icon-tile" style={{ background: "#F1E2D3" }}><Icon name="building" size={20} /></span>
        <p className="flex-1 text-[13.5px] leading-snug"><b>Este equipo se lleva a un centro de servicio.</b> Llamamos al fabricante, agendamos tu cita y te decimos para cuándo quedó.</p>
      </div>
      {r.warranty && <div className="mt-2.5"><Chip tone="cobre" icon="shieldok">Garantía vigente · {r.warranty.days_left} días</Chip></div>}
      <Label>Qué pasa</Label>
      <div className="g rounded-[22px] px-4 py-3 text-[14px] font-semibold leading-snug">{r.symptom ?? r.scope_text}</div>
      <Label>Qué le diremos al fabricante</Label>
      <div className="g rounded-[26px] px-4 py-1">
        {dato("user", "Tu nombre", m.holder_name)}
        {dato("pin", "Tu dirección", m.address)}
        {dato("doc", "Marca y modelo", [m.brand, m.model].filter(Boolean).join(" ") || null)}
        {dato("tag", "Número de serie", m.serial)}
        {dato("shieldok", "Garantía hasta", m.warranty_ends_on ? shortDay(m.warranty_ends_on) : null)}
        <div className="py-3"><label htmlFor="tel" className="text-[12.5px] text-muted">Tu teléfono (el fabricante lo pide para agendar)</label>
          <input id="tel" inputMode="tel" autoComplete="tel" placeholder={guardado ? "Usaremos el que guardaste" : "55 1234 5678"} value={phone} onChange={(e) => setPhone(e.target.value)} className="field mt-1" />
          {guardado && <p className="mx-1.5 mt-1.5 text-[12.5px] text-muted">Ya lo tenemos guardado en <Link href="/hogar/datos" className="font-extrabold underline">Mi casa</Link>. Escribe otro solo si quieres cambiarlo.</p>}</div>
      </div>
      <ConsentCheck checked={ok} onChange={setOk}>Autorizo que NidoGuard llame al fabricante y le dé estos datos para agendar mi servicio. La llamada se graba.</ConsentCheck>
      <div className="mt-2.5"><NoCobro text={NO_COBRO_FABRICANTE} /></div>
      <ErrorNote text={err} />
      <Actions>
        <Btn disabled={busy || !ok || !tengoTel} onClick={() => act("/service-requests/{id}/start", { consent: ok, phone: tecleado ? phone : null })}><Icon name="phone" size={19} stroke={2.2} />Agendar con el fabricante</Btn>
        <button type="button" disabled={busy} onClick={() => act("/service-requests/{id}/scope", { route: "tecnico" })} className="btn btn-copper w-full"><Icon name="wrench" size={19} stroke={2.2} />Cotizar con técnicos a domicilio</button>
        <ConfirmLink kind="solicitud" onConfirm={() => act("/service-requests/{id}/cancel")}>Cancelar solicitud</ConfirmLink>
      </Actions>
    </div>
  );
}

// ---------------------------------------------------------------- Mientras se busca
export function Progreso({ r, act, busy, onSee }: P & { onSee: () => void }) {
  const p = progressOf(r);
  const shown = (r.calls ?? []).filter((c) => c.status !== "cancelada");
  return (
    <div>
      <Summary title={r.scope_text ?? ""} sub={r.equipment_label} />
      <div className="g mt-3 rounded-[26px] p-4" role="status">
        <p className="text-[13px] font-bold text-muted">Llamando a técnicos cercanos</p>
        <p className="mt-1 text-[26px] font-extrabold leading-tight">{p.got} de {p.target} <span className="text-[15px] font-bold text-muted">cotizaciones</span></p>
        <div role="progressbar" aria-valuemin={0} aria-valuemax={p.target} aria-valuenow={p.got} aria-label="Cotizaciones recibidas" className="mt-3 h-2.5 overflow-hidden rounded-full bg-navy/10">
          <div className="h-full rounded-full" style={{ width: `${p.pct}%`, background: "linear-gradient(90deg,#7399B5,#183B56)" }} /></div>
        <p className="mt-2 text-[12.5px] text-muted">Llevamos {p.done} de {p.total} llamadas. Solo llamamos de lunes a sábado, de 9:00 a 19:00.</p>
      </div>
      {r.resumes_at && <div className="mt-3"><Callout icon="clock"><b>Seguimos {new Date(r.resumes_at).toLocaleString("es-MX", { weekday: "long", hour: "numeric", minute: "2-digit", timeZone: "America/Mexico_City" })}.</b> Ya es fuera de horario de llamadas; te avisamos aquí en cuanto haya cotizaciones.</Callout></div>}
      <Label>Llamadas</Label>
      <div className="g rounded-[26px] px-4 py-1">
        {shown.map((c, i) => {
          const done = c.status === "completada";
          const tone = done ? "#235A3B" : c.status === "sin_respuesta" || c.status === "rechazo" ? "#8F5A1F" : "#183B56";
          return (
            <div key={c.label}>{i > 0 && <Hr />}
              <div className="flex items-center gap-3 py-3">
                <span aria-hidden="true" className="grid h-[34px] w-[34px] flex-none place-items-center rounded-full" style={{ background: done ? "rgba(47,107,74,.16)" : "rgba(115,153,181,.28)", color: tone }}>
                  <Icon name={done ? "check" : c.status === "en_cola" ? "clock" : "phone"} size={17} stroke={2.4} /></span>
                <div className="min-w-0 flex-1"><p className="text-[14px] font-extrabold">{c.label}<span className="ml-1.5 text-[12.5px] font-semibold text-muted">{distanceLabel(c.distance_km)}</span></p>
                  <p className="text-[12.5px] font-semibold" style={{ color: tone }}>{callText(c)}</p></div>
              </div>
            </div>
          );
        })}
      </div>
      <Note>Puedes cerrar la app. Te avisamos cuando haya cotizaciones.</Note>
      <Actions>
        {r.quote_count > 0 && <Btn ghost onClick={onSee}><Icon name="list" size={19} />Ver las que ya llegaron</Btn>}
        <ConfirmLink kind="solicitud" onConfirm={() => act("/service-requests/{id}/cancel")}>Cancelar búsqueda</ConfirmLink>
      </Actions>
    </div>
  );
}

export function FabricanteLlamando({ r, act }: P) {
  return (
    <div>
      <Summary icon="building" title={r.scope_text ?? ""} sub={r.equipment_label} />
      <Timeline rows={[{ state: "ok", text: "Tenemos tus datos y tu permiso" }, { state: "now", text: "Llamando al fabricante", sub: "Puede haber espera en la línea" }, { state: "wait", text: "Agendando tu cita" }, { state: "wait", text: "Confirmación y folio" }]} />
      <Note>Puedes cerrar la app. Te avisamos con la fecha de tu cita en cuanto quede.</Note>
      <Actions><ConfirmLink kind="solicitud" onConfirm={() => act("/service-requests/{id}/cancel")}>Cancelar</ConfirmLink></Actions>
    </div>
  );
}

export function SinRespuesta({ r, act, busy, err }: P) {
  const calls = r.calls ?? [];
  const no = calls.filter((c) => c.status === "sin_respuesta").length, rech = calls.filter((c) => c.status === "rechazo").length;
  return (
    <div>
      <Summary title={r.scope_text ?? ""} sub={r.equipment_label} />
      <div className="g mt-3 rounded-[26px] p-5 text-center">
        <span className="icon-tile mx-auto"><Icon name="clock" size={22} /></span>
        <p className="mt-3 text-[20px] font-extrabold">Hoy nadie cotizó</p>
        <p className="mt-1.5 text-[14px] leading-relaxed text-muted">{calls.length === 0 ? "No encontramos técnicos para este equipo en tu zona." : `Llamamos a ${calls.length} técnicos. ${no} no contestaron${rech ? ` y ${rech} no dan servicio a este equipo` : ""}.`}</p>
      </div>
      <ErrorNote text={err} />
      <Actions>
        {r.radius_km < 25 && <Btn disabled={busy} onClick={() => act("/service-requests/{id}/expand")}><Icon name="pin" size={19} />Buscar hasta 25 km</Btn>}
        <ConfirmLink kind="solicitud" onConfirm={() => act("/service-requests/{id}/cancel")}>Cancelar búsqueda</ConfirmLink>
      </Actions>
    </div>
  );
}

// ---------------------------------------------------------------- Comparar
export function QuoteCard({ q, rid }: { q: Quote; rid: string }) {
  const otro = q.matches === "distinto";
  return (
    <Link href={`/servicios/${rid}/cotizacion/${q.id}`} className="g block rounded-[26px] p-4">
      <div className="flex items-start justify-between gap-2.5">
        <div className="min-w-0"><p className="text-[15px] font-extrabold">{q.label}</p><p className="mt-0.5 text-[12.5px] text-muted">{distanceLabel(q.distance_km)}</p></div>
        {q.rating != null && <span className="flex items-center gap-1 whitespace-nowrap text-[12.5px] font-extrabold text-[#8F5A1F]"><Icon name="star" size={14} fill />{q.rating.toFixed(1)}{q.reviews != null && <span className="font-semibold text-muted">({q.reviews})</span>}</span>}
      </div>
      <div className="mt-2.5 rounded-2xl bg-navy/[.06] px-3 py-2.5">
        <p className="text-[12px] font-bold text-muted">Qué cotizó</p>
        <p className={`mt-0.5 text-[13.5px] font-bold leading-snug ${otro ? "text-[#8F5A1F]" : ""}`}>{q.scope_quoted}</p>
        {otro && <div className="mt-1.5"><Chip tone="cobre" icon="info">Cotizó otra cosa</Chip></div>}
      </div>
      <div className="mt-2.5 flex items-end justify-between gap-2.5">
        <div><p className="text-[24px] font-extrabold leading-tight">{priceLabel(q)}</p><p className="text-[12.5px] text-muted">{priceNote(q.price_type)}</p></div>
        <div className="text-right">{q.availability[0] && <p className="text-[13px] font-extrabold">{shortDay(q.availability[0].date)}</p>}
          <div className="mt-1 flex flex-wrap justify-end gap-1">{q.tags.map((t) => <Chip key={t} tone={t === "mas_barata" ? "green" : "blue"}>{TAG_LABEL[t]}</Chip>)}</div></div>
      </div>
      <div className="mt-2.5 flex flex-wrap gap-1.5"><Chip tone="gray">{warrantyLabel(q.warranty_days)}</Chip><Chip tone="gray">{invoiceLabel(q.invoice)}</Chip></div>
    </Link>
  );
}

export function Comparar({ r, act }: { r: ServiceRequest; act?: Act }) {
  const [sort, setSort] = useState<Sort>("precio");
  const quotes = sortQuotes(r.quotes ?? [], sort);
  return (
    <div>
      <Summary title={r.scope_text ?? ""} sub={r.equipment_label} />
      <div role="tablist" aria-label="Ordenar" className="g mt-3 flex rounded-[22px] p-1">
        {([["precio", "Mejor precio"], ["pronto", "Más pronto"], ["cerca", "Más cerca"]] as [Sort, string][]).map(([k, l]) => (
          <button key={k} role="tab" aria-selected={sort === k} onClick={() => setSort(k)} className={`h-9 flex-1 rounded-full text-[13px] font-bold ${sort === k ? "gd !rounded-full font-extrabold" : "text-navy"}`}>{l}</button>
        ))}
      </div>
      <Note>Son cotizaciones dadas por teléfono. El precio puede cambiar cuando el técnico revise tu equipo.</Note>
      <div className="mt-3 flex flex-col gap-2.5">{quotes.map((q) => <QuoteCard key={q.id} q={q} rid={r.id} />)}</div>
      <div className="mt-4"><NoCobro /></div>
      <p className="mx-1.5 mt-3 text-center text-[12.5px] leading-snug text-muted">No pasa nada si no eliges ninguna: puedes cancelar cuando quieras.</p>
      {act && <Actions><ConfirmLink kind="solicitud" onConfirm={() => act("/service-requests/{id}/cancel")}>Cancelar solicitud</ConfirmLink></Actions>}
    </div>
  );
}

// ---------------------------------------------------------------- Detalle de una cotización
export function QuoteDetail({ q, scope, rid }: { q: Quote; scope: string | null; rid: string }) {
  return (
    <div>
      <div className="g mt-3 rounded-[26px] p-4">
        <p className="text-[12px] font-bold text-muted">Qué cotizó</p>
        <p className="mt-0.5 text-[15px] font-extrabold leading-snug">{q.scope_quoted}</p>
        <p className="mt-3 text-[34px] font-extrabold leading-none">{priceLabel(q)}</p>
        <p className="mt-1 text-[13px] text-muted">{priceNote(q.price_type)}</p>
        <div className="mt-2">
          <KV icon="wallet" k="Cargo por visita" v={q.visit_fee ? `${money(q.visit_fee)}` : "No lo cobra"} /><Hr />
          <KV icon="shieldok" k="Garantía del trabajo" v={q.warranty_days ? `${q.warranty_days} días` : "No dijo"} /><Hr />
          <KV icon="receipt" k="Factura" v={q.invoice == null ? "No dijo" : q.invoice ? "Sí la da" : "No la da"} />
          {q.payment_methods.length > 0 && <><Hr /><KV icon="wallet" k="Formas de pago" v={q.payment_methods.join(" o ")} /></>}
        </div>
      </div>
      {q.matches === "distinto" && <div className="mt-3"><Callout>Esta cotización no es de lo mismo que pediste (“{scope}”). Compárala con cuidado.</Callout></div>}
      <Label>Qué incluye</Label>
      <div className="g rounded-[26px] px-4 py-3">
        {q.includes.map((t) => <p key={t} className="flex items-start gap-2.5 py-1 text-[13.5px] leading-snug"><span className="mt-px text-[#235A3B]"><Icon name="check" size={16} stroke={2.6} /></span>{t}</p>)}
        {q.excludes.map((t) => <p key={t} className="flex items-start gap-2.5 py-1 text-[13.5px] leading-snug"><span className="mt-px text-[#8F5A1F]"><Icon name="x" size={16} stroke={2.6} /></span>{t}</p>)}
      </div>
      <Label>Cuándo puede ir</Label>
      <div className="g flex flex-wrap gap-2 rounded-[26px] p-3.5">{q.availability.map((s) => <Chip key={`${s.date}${s.window}`} icon="calendar">{slotChip(s)}</Chip>)}</div>
      {(q.excerpt || q.summary) && (<>
        <Label>Lo que dijo por teléfono</Label>
        <div className="g rounded-[26px] p-4">
          {q.excerpt && (<><p className="flex items-center gap-1.5 text-[12px] font-bold text-[#8F5A1F]"><Icon name="phone" size={14} stroke={2.2} />Lo que dijo el técnico</p>
            <blockquote className="mt-2 border-l-2 border-copper/60 pl-3 text-[14px] italic leading-relaxed">{q.excerpt}</blockquote>
            <p className="mt-2 text-[12px] leading-snug text-muted">Extracto solo del trabajo y el precio. Quitamos nombres y datos de contacto; no compartimos la grabación.</p></>)}
          {q.summary && (<><p className={`flex items-center gap-1.5 text-[12px] font-bold text-[#8F5A1F] ${q.excerpt ? "mt-3.5" : ""}`}><Icon name="sparkle" size={14} stroke={2.2} />Resumen de NidoGuard</p>
            <p className="mt-2 text-[14px] leading-relaxed">{q.summary}</p></>)}
        </div>
      </>)}
      <div className="mt-3"><NoCobro /></div>
      <Note>Cotización por teléfono. El precio puede cambiar cuando el técnico revise tu equipo.</Note>
      <Actions><Link href={`/servicios/${rid}/agendar?q=${q.id}`} className="btn"><Icon name="calendar" size={19} stroke={2.2} />Elegir y agendar</Link>
        <Link href={`/servicios/${rid}`} className="btn btn-ghost">Volver a las cotizaciones</Link></Actions>
    </div>
  );
}

// ---------------------------------------------------------------- Después de elegir
function DoneBox({ r, act, busy }: P) {
  const [open, setOpen] = useState(false); const [cost, setCost] = useState(""); const [stars, setStars] = useState(0);
  const ap = r.appointment!;
  if (ap.status !== "confirmada") return null;
  return open ? (
    <div className="g mt-1 rounded-[22px] p-3.5">
      <p className="text-center text-[14px] font-extrabold">¿Cómo te atendió {ap.technician_name ?? "el servicio"}?</p>
      <div className="mt-1"><Stars value={stars} onChange={setStars} /></div>
      <label htmlFor="costo" className="mt-3 block text-[13px] font-bold">¿Cuánto pagaste? (opcional)</label>
      <div className="mt-1.5 flex gap-2"><input id="costo" inputMode="decimal" placeholder="$0" value={cost} onChange={(e) => setCost(e.target.value)} className="field flex-1" />
        <button type="button" disabled={busy} className="btn !px-4" onClick={() => act(`/appointments/${ap.id}/done`, { final_cost: cost ? Number(cost.replace(/[^0-9.]/g, "")) : null, rating: stars || null })}>Guardar</button></div>
      <p className="mt-1.5 text-[12px] text-muted">Se guarda en el Historial de tu equipo. La calificación es opcional. NidoGuard no procesa pagos.</p>
    </div>
  ) : <Btn ghost onClick={() => setOpen(true)}><Icon name="check" size={19} stroke={2.4} />Ya me atendieron</Btn>;
}

export function Visita(p: P) {
  const { r, act } = p; const ap = r.appointment!;
  const confirmada = ap.status === "confirmada" && ap.starts_at;
  const a = ap.agreed;
  const slot = ap.requested_slot;
  return (
    <div>
      {confirmada
        ? <Hero kicker="Tu visita quedó para el" title={longDay(ap.starts_at!)} sub={hourRange(ap.starts_at!, ap.ends_at)} />
        : <Hero icon="clock" kicker="Pedimos tu visita para el" title={slot ? longDay(`${slot.date}T12:00:00-06:00`) : "la fecha que elegiste"} sub="Esperando que el técnico confirme" />}
      {a && (
        <div className="g mt-4 rounded-[26px] p-4">
          <div className="flex items-center gap-3"><span className="icon-tile"><Icon name="user" size={20} /></span>
            <div className="min-w-0 flex-1"><p className="text-[15px] font-extrabold">{ap.technician_name ?? a.label}</p>
              <p className="text-[12.5px] text-muted">{a.rating != null ? `${a.rating.toFixed(1)} de 5 (${a.reviews} reseñas) · ` : ""}Va a tu casa</p></div></div>
          <p className="mt-3 border-t border-navy/10 pt-3 text-[13.5px] leading-relaxed"><b>Qué acordamos:</b> {a.scope} <b>{priceLabel({ price_min: a.price_min, price_max: a.price_max, price_type: a.price_type })}</b>
            {a.visit_fee ? `, más ${money(a.visit_fee)} de visita` : ", sin cargo por visita"}.{a.warranty_days ? ` Garantía de ${a.warranty_days} días` : ""}{a.invoice ? " y factura." : "."}</p>
        </div>
      )}
      {confirmada && (ap.technician_phone || ap.access_notes) && (
        <div className="g mt-4 rounded-[26px] p-4">
          {ap.technician_phone && <a href={`tel:${ap.technician_phone}`} className="btn btn-ghost w-full"><Icon name="phone" size={19} />Llamar a {ap.technician_name ?? "tu técnico"}</a>}
          {ap.technician_phone && <p className="mt-2 text-[12.5px] leading-snug text-muted">Para coordinar el acceso o si necesita algún documento. Se lo mandas tú directo.</p>}
          {ap.access_notes && <p className="mt-3 border-t border-navy/10 pt-3 text-[13.5px] leading-relaxed"><b>Acceso que le dimos:</b> {ap.access_notes}</p>}
        </div>
      )}
      {!confirmada && ap.status === "por_confirmar" && r.resumes_at && (
        <div className="mt-4"><Callout icon="clock">Ahora no es horario de llamadas. Llamamos al técnico a confirmar el <b>{new Date(r.resumes_at).toLocaleString("es-MX", { weekday: "long", hour: "numeric", minute: "2-digit" })}</b>.</Callout></div>
      )}
      {ap.status === "por_reprogramar" && ap.proposed_slot && (
        <div className="mt-4">
          <Callout icon="clock"><b>El técnico propone otro horario:</b> {longDay(`${ap.proposed_slot.date}T12:00:00-06:00`)}{ap.proposed_slot.start_hour != null ? `, desde las ${ap.proposed_slot.start_hour}:00` : ""}.</Callout>
          <Actions>
            <Btn disabled={p.busy} onClick={() => act(`/appointments/${ap.id}/respond`, { accept: true })}><Icon name="check" size={19} stroke={2.4} />Aceptar este horario</Btn>
          </Actions>
          {ap.proposal_round < 2 && (ap.agreed?.slots?.length ?? 0) > 0 && (<><Label>O elige otra de las que dio</Label>
            <div className="g flex flex-wrap gap-2 rounded-[26px] p-3.5">{ap.agreed!.slots.map((s, i) => (
              <button key={`${s.date}${s.window}`} type="button" disabled={p.busy} onClick={() => act(`/appointments/${ap.id}/respond`, { accept: false, slot_index: i })} className="chip">{slotChip(s)}</button>))}</div></>)}
          <TextLink onClick={() => act(`/appointments/${ap.id}/respond`, { accept: false })} danger>No me sirve, ver otras cotizaciones</TextLink>
        </div>
      )}
      <Label>Seguimiento</Label>
      <Timeline rows={[{ state: "ok", text: "Visita pedida" }, { state: confirmada ? "ok" : "now", text: confirmada ? "Confirmada con el técnico" : "Esperando confirmación del técnico" }, { state: "wait", text: "Recordatorio el día anterior" }]} />
      {confirmada && calendarEvent(r) && <div className="mt-4"><AgregarCalendario evento={calendarEvent(r)!} archivo="visita-nidoguard.ics" /></div>}
      <div className="mt-3"><NoCobro /></div>
      <Note>Tu dirección exacta se le dio al técnico cuando confirmó. Cuando termine el servicio, lo guardamos en el Historial de tu equipo.</Note>
      <Actions>
        <DoneBox {...p} />
        <Link href="/servicios" className="btn btn-ghost"><Icon name="list" size={19} />Ver mis solicitudes</Link>
        <ConfirmLink kind="cambiar" onConfirm={() => act(`/appointments/${ap.id}/cancel`)} danger={false}>Elegir otra cotización u horario</ConfirmLink>
        <ConfirmLink kind="solicitud" onConfirm={() => act("/service-requests/{id}/cancel")}>Cancelar la solicitud</ConfirmLink>
      </Actions>
      <p className="mx-1.5 mt-2 text-center text-[12.5px] leading-snug text-muted">Puedes cancelar en cualquier momento. {confirmada ? "Como el técnico ya la había confirmado, le llamamos para avisarle." : "Si el técnico aún no confirma, ya no lo llamamos."}</p>
    </div>
  );
}

export function CitaFabricante(p: P) {
  const { r, act } = p; const ap = r.appointment!;
  const lugar = [ap.center_name, ap.center_address].filter(Boolean).join(", ");
  return (
    <div>
      <Hero kicker={ap.registered_by_user ? "Registraste tu cita para el" : "Tu cita quedó para el"} title={ap.starts_at ? longDay(ap.starts_at) : "la fecha acordada"} sub={ap.starts_at ? hourRange(ap.starts_at, ap.ends_at) : ""} />
      <div className="g mt-4 rounded-[26px] p-4">
        <div className="flex items-start gap-3"><span className="icon-tile" style={{ background: "#F1E2D3" }}><Icon name="building" size={20} /></span>
          <div className="min-w-0 flex-1"><p className="text-[15px] font-extrabold">{ap.center_name ?? "Centro de servicio"}</p>{ap.center_address && <p className="mt-0.5 text-[13px] leading-snug text-muted">{ap.center_address}</p>}</div></div>
        {ap.folio && <p className="mt-3 flex justify-between border-t border-navy/10 pt-3 text-[13.5px]"><span className="text-muted">Folio</span><b>{ap.folio}</b></p>}
      </div>
      {ap.bring.length > 0 && (<><Label>Lleva</Label><div className="g rounded-[26px] px-4 py-2.5">{ap.bring.map((t) => <p key={t} className="flex items-center gap-2.5 py-1.5 text-[14px]"><span className="text-[#235A3B]"><Icon name="check" size={16} stroke={2.6} /></span>{t}</p>)}</div></>)}
      {calendarEvent(r) && <div className="mt-4"><AgregarCalendario evento={calendarEvent(r)!} archivo="cita-nidoguard.ics" /></div>}
      <div className="mt-3"><NoCobro text={NO_COBRO_FABRICANTE} /></div>
      <Note>Cuando termine el servicio, lo guardamos en el Historial de tu equipo.</Note>
      <Actions>
        {ap.center_address && <a className="btn btn-ghost" href={mapsLink(lugar)} target="_blank" rel="noreferrer"><Icon name="nav" size={19} />Cómo llegar</a>}
        <DoneBox {...p} />
        <ConfirmLink kind="cita" onConfirm={() => act(`/appointments/${ap.id}/cancel`)}>Cambiar o cancelar la cita</ConfirmLink>
      </Actions>
    </div>
  );
}

/** Dice la razón real por la que no se agendó con el fabricante, sin suponer que pidió al titular. */
function motivoManual(reason: string | null, brand: string | null, c: ServiceContacts | null): string {
  const marca = brand ?? "esta marca";
  const tienda = c?.store?.name ?? "la tienda";
  switch (reason) {
    case "garantia_tienda": return `Tu garantía todavía es con ${tienda}${c?.store?.until ? ` (hasta el ${longDay(`${c.store.until}T12:00:00-06:00`)})` : ""}, así que ahí toca agendar primero.`;
    case "sin_linea": return `Todavía no tenemos la línea de servicio de ${marca}, así que no pudimos llamar por ti.`;
    case "linea_por_verificar": return `Encontramos la línea de servicio de ${marca}, pero todavía no llamamos por ti a números que una persona no ha verificado.`;
    case "no_se_llamo": return "En esta ocasión no llamamos al fabricante por ti.";
    case "no_contestaron": return "El fabricante no contestó la llamada.";
    case "no_se_pudo": return "Llamamos, pero no se pudo agendar: es común que pidan que el titular hable directamente.";
    default: return "No pudimos agendar con el fabricante.";
  }
}

export function FabricanteManual({ r, act, busy, err }: P) {
  const m = r.manufacturer;
  const [copied, setCopied] = useState<string | null>(null);
  const [date, setDate] = useState(""); const [win, setWin] = useState<"manana" | "tarde">("manana"); const [folio, setFolio] = useState("");
  const filas: [string, string | null][] = [["Marca y modelo", [m?.brand, m?.model].filter(Boolean).join(" ") || null], ["Número de serie", m?.serial ?? null],
    ["Qué pasa", r.symptom ?? r.scope_text], ["Tu dirección", m?.address ?? null], ["Tu teléfono", m?.phone ?? null]];
  return (
    <div>
      <div className="mt-3"><Callout>{motivoManual(m?.reason ?? null, m?.brand ?? null, m?.contacts ?? null)} Te dejamos todo listo para que agendes en un minuto.</Callout></div>
      {m?.contacts?.store?.phone && (
        <><Label>{m.contacts.store.active ? `Tu garantía es con ${m.contacts.store.name ?? "la tienda"}` : `Tienda: ${m.contacts.store.name ?? ""}`}</Label>
        <div className="g rounded-[26px] p-4"><a href={`tel:${m.contacts.store.phone}`} className="text-[18px] font-extrabold text-navy underline">{m.contacts.store.phone.replace(/^\+52/, "")}</a>
          {m.contacts.store.active && m.contacts.store.until && <p className="mt-1 text-[13px] text-muted">La tienda cubre la garantía hasta el {longDay(`${m.contacts.store.until}T12:00:00-06:00`)}.</p>}</div></>)}
      {m?.contacts?.maker?.phone && !m.line && (
        <><Label>{m.contacts.maker.name ? `Tu teléfono guardado de ${m.contacts.maker.name}` : "Tu teléfono guardado del fabricante"}</Label>
        <div className="g rounded-[26px] p-4"><a href={`tel:${m.contacts.maker.phone}`} className="text-[18px] font-extrabold text-navy underline">{m.contacts.maker.phone.replace(/^\+52/, "")}</a>
          <p className="mt-1 text-[12.5px] text-muted">Lo guardaste en el perfil del equipo. Llama tú: nuestro asistente solo llama a líneas que verificamos.</p></div></>)}
      {(m?.line || m?.candidate) && (() => { const l = (m.line ?? m.candidate)!; return (<>
        <Label>Línea de servicio de {m.brand}</Label>
        <div className="g rounded-[26px] p-4">
          <a href={`tel:${l.phone}`} className="text-[18px] font-extrabold text-navy underline">{l.phone.replace(/^\+52/, "")}</a>
          {l.hours && <p className="mt-1 text-[13px] text-muted">Horario: {l.hours}</p>}
          {l.requires_holder && <p className="mt-1 text-[13px] text-[#8F5A1F]">Suelen pedir que hable el titular de la compra.</p>}
          {!m.line && m.candidate && <p className="mt-2 text-[12.5px] leading-snug text-muted">La encontramos{m.candidate.source_domain ? ` en ${m.candidate.source_domain}` : ""}. Confirma que sea la correcta cuando te contesten.</p>}
          {m.feedback == null
            ? <div className="mt-3 flex gap-2 border-t border-navy/10 pt-3"><button type="button" disabled={busy} className="btn btn-ghost !min-h-11 flex-1 !px-2 text-[13.5px]" onClick={() => act("/service-requests/{id}/line-feedback", { worked: true })}>Me contestaron aquí</button>
              <button type="button" disabled={busy} className="btn btn-ghost !min-h-11 flex-1 !px-2 text-[13.5px]" onClick={() => act("/service-requests/{id}/line-feedback", { worked: false })}>No era esa línea</button></div>
            : <p className="mt-3 border-t border-navy/10 pt-3 text-[12.5px] text-muted">Gracias, nos ayuda a que la próxima persona llegue más rápido.</p>}
        </div></>); })()}
      <Label>Esto te van a pedir</Label>
      <div className="g rounded-[26px] px-4 py-1.5">
        {filas.filter(([, v]) => v).map(([k, v], i) => (
          <div key={k}>{i > 0 && <Hr />}<div className="flex items-center gap-2.5 py-2.5">
            <div className="min-w-0 flex-1"><p className="text-[12.5px] text-muted">{k}</p><p className="text-[14px] font-extrabold leading-snug">{v}</p></div>
            <button type="button" aria-label={`Copiar ${k}`} className="g grid h-11 w-11 flex-none place-items-center !rounded-full text-navy"
              onClick={() => { navigator.clipboard?.writeText(v!); setCopied(k); }}><Icon name={copied === k ? "check" : "copy"} size={18} /></button></div></div>
        ))}
      </div>
      {!m?.line && !m?.candidate && !m?.contacts?.maker?.phone && !m?.contacts?.store?.phone && <Note icon="search">Busca la línea de servicio en la garantía, el manual o la página del fabricante.</Note>}
      <Label>Cuando tengas tu cita, dinos para cuándo quedó</Label>
      <div className="g flex flex-col gap-2.5 rounded-[26px] p-3.5">
        <label className="sr-only" htmlFor="fecha">Fecha de la cita</label><input id="fecha" type="date" value={date} onChange={(e) => setDate(e.target.value)} className="field" />
        <div className="flex gap-2">{(["manana", "tarde"] as const).map((w) => (
          <button key={w} type="button" aria-pressed={win === w} onClick={() => setWin(w)} className={`h-11 flex-1 rounded-full text-[14px] font-bold ${win === w ? "gd !rounded-full" : "g !rounded-full text-navy"}`}>{w === "manana" ? "Mañana" : "Tarde"}</button>))}</div>
        <label className="sr-only" htmlFor="folio">Folio (opcional)</label><input id="folio" placeholder="Folio (opcional)" value={folio} onChange={(e) => setFolio(e.target.value)} className="field" />
      </div>
      <ErrorNote text={err} />
      <Actions>
        <Btn disabled={busy || !date} onClick={() => act("/service-requests/{id}/register", { date, window: win, folio: folio || null })}><Icon name="calendar" size={19} stroke={2.2} />Registrar mi cita</Btn>
        <ConfirmLink kind="solicitud" onConfirm={() => act("/service-requests/{id}/cancel")}>Cancelar solicitud</ConfirmLink>
      </Actions>
    </div>
  );
}

function Calificar({ r, act, busy }: { r: ServiceRequest; act: Act; busy: boolean }) {
  const ap = r.appointment!;
  const [stars, setStars] = useState(ap.my_rating ?? 0); const [txt, setTxt] = useState(ap.my_rating_comment ?? ""); const [edit, setEdit] = useState(false);
  const quien = ap.technician_name ?? "la atención";
  if (ap.my_rating && !edit) return (
    <div className="g mt-3 rounded-[26px] p-4 text-center">
      <p className="text-[14px] font-extrabold">Tu calificación</p>
      <div className="mt-1.5"><Stars value={ap.my_rating} size={30} /></div>
      {ap.my_rating_comment && <p className="mt-2 text-[13.5px] leading-relaxed text-muted">“{ap.my_rating_comment}”</p>}
      <button type="button" onClick={() => setEdit(true)} className="mx-auto mt-1 min-h-11 px-3 text-[13.5px] font-extrabold text-navy">Cambiar mi calificación</button>
    </div>
  );
  return (
    <div className="g mt-3 rounded-[26px] p-4">
      <p className="text-center text-[15px] font-extrabold">¿Cómo te atendió {quien}?</p>
      <div className="mt-2"><Stars value={stars} onChange={setStars} /></div>
      <label htmlFor="coment" className="mt-3 block text-[13px] font-bold">Cuéntanos más (opcional)</label>
      <textarea id="coment" value={txt} maxLength={300} rows={2} onChange={(e) => setTxt(e.target.value)} placeholder="Ej. Llegó puntual y explicó todo." className="field mt-1.5 w-full resize-none" />
      <button type="button" className="btn mt-3 w-full" disabled={busy || stars < 1} onClick={async () => { await act(`/appointments/${ap.id}/rate`, { stars, comment: txt.trim() || null }); setEdit(false); }}>
        <Icon name="check" size={19} stroke={2.4} />Enviar calificación</button>
      <p className="mt-2 text-center text-[12px] text-muted">Solo la ves tú. Nos ayuda a recomendar mejor.</p>
    </div>
  );
}

export function Cerrada({ r, act, busy }: { r: ServiceRequest; act?: Act; busy?: boolean }) {
  return (
    <div>
      <Summary title={r.scope_text ?? ""} sub={r.equipment_label} />
      <div className="g mt-3 rounded-[26px] p-5 text-center"><span className="icon-tile mx-auto"><Icon name={r.status === "terminada" ? "check" : "x"} size={22} /></span>
        <p className="mt-3 text-[18px] font-extrabold">{r.status === "terminada" ? "Servicio terminado" : "Solicitud cancelada"}</p>
        <p className="mt-1 text-[13.5px] text-muted">{r.status === "terminada" ? "Quedó guardado en el Historial de tu equipo." : "No se llamó a nadie más."}</p>
        {r.appointment?.final_cost != null && <p className="mt-2 text-[14px] font-bold">Pagaste {money(r.appointment.final_cost)}</p>}</div>
      {r.status === "terminada" && r.appointment && act && <Calificar r={r} act={act} busy={!!busy} />}
      <Actions><Link href="/servicios" className="btn btn-ghost">Ver mis solicitudes</Link></Actions>
    </div>
  );
}
