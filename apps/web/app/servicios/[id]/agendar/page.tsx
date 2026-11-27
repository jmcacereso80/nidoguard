"use client";
import { Suspense, use, useState } from "react";
import Link from "next/link";
import { useRouter, useSearchParams } from "next/navigation";
import { useQuery } from "@tanstack/react-query";
import { Shell, ErrorNote } from "@/components/Shell";
import { Icon } from "@/components/Icon";
import { Actions, ConsentCheck, Hr, Label, NoCobro, Summary, TextLink } from "@/components/servicios/ui";
import { useRequestAction } from "@/components/servicios/hooks";
import { useMe } from "@/components/useHome";
import { useApi } from "@/lib/api";
import { Quote, priceLabel, shortDay, slotWindowLong } from "@/lib/servicios";

function Compartido({ icon, text, ok }: { icon: string; text: string; ok: boolean }) {
  return <div className="flex items-center gap-3 py-2.5"><span className={ok ? "text-navy" : "text-muted"}><Icon name={icon} size={20} /></span>
    <span className="flex-1 text-[14px] font-semibold">{text}</span><span className={ok ? "text-[#235A3B]" : "text-[#8F5A1F]"}><Icon name={ok ? "check" : "x"} size={18} stroke={2.6} /></span></div>;
}

function Form({ id }: { id: string }) {
  const api = useApi(); const router = useRouter(); const qid = useSearchParams().get("q") ?? "";
  const m = useRequestAction(id);
  const q = useQuery({ queryKey: ["svc-quote", id, qid], queryFn: () => api<{ quote: Quote; scope_text: string | null; equipment_label: string | null }>(`/service-requests/${id}/quotes/${qid}`), enabled: !!qid });
  const me = useMe().data?.user; const tiene = !!me?.phone;
  const [slot, setSlot] = useState(0); const [ok, setOk] = useState(true); const [tel, setTel] = useState(true);
  const d = q.data;
  const pedir = () => m.mutate({ path: "/service-requests/{id}/schedule", body: { quote_id: qid, slot_index: slot, consent: ok, share_phone: tiene && tel } }, { onSuccess: () => router.push(`/servicios/${id}`) });
  return (
    <Shell title="Agendar visita" subtitle={d ? `${d.quote.label} · ${priceLabel(d.quote)}` : undefined} back={`/servicios/${id}/cotizacion/${qid}`} nav="servicios">
      {d && (<>
        <Summary title={d.quote.scope_quoted ?? ""} sub={d.equipment_label} />
        <Label>Elige cuándo</Label>
        <div role="radiogroup" aria-label="Horario" className="flex flex-col gap-2">
          {d.quote.availability.map((s, i) => (
            <label key={`${s.date}${s.window}`} className="g flex min-h-14 items-center gap-3 rounded-[22px] px-3.5 py-3">
              <input type="radio" name="franja" checked={slot === i} onChange={() => setSlot(i)} className="h-[22px] w-[22px] flex-none accent-[#183B56]" />
              <span className="text-[14px] leading-snug"><b>{shortDay(s.date)}</b><br /><span className="text-muted">{slotWindowLong(s)}</span></span>
            </label>
          ))}
        </div>
        <p className="mx-1.5 mt-2 text-[12.5px] leading-snug text-muted">Son los horarios que dio el técnico. Nosotros llamamos para confirmar la hora exacta y te avisamos.</p>
        <Label>Qué compartimos con el técnico</Label>
        <div className="g rounded-[26px] px-4 py-1.5">
          {me?.name && <><Compartido icon="user" text={`Tu nombre de pila (${me.name.split(" ")[0]})`} ok /><Hr /></>}
          <Compartido icon="pin" text="Tu dirección exacta, cuando confirme la visita" ok /><Hr />
          <Compartido icon="wrench" text="El equipo y el trabajo acordado" ok /><Hr />
          <Compartido icon="phone" text={tiene && tel ? "Tu teléfono, cuando confirme la visita" : "Tu teléfono no se comparte"} ok={tiene && tel} />
        </div>
        <div className="mt-3"><NoCobro /></div>
        <ConsentCheck checked={ok} onChange={setOk}>Autorizo dar mi dirección al técnico cuando confirme la visita.</ConsentCheck>
        {tiene ? <ConsentCheck checked={tel} onChange={setTel}>Comparto mi teléfono con el técnico cuando confirme, para que pueda avisarme si llega o se retrasa.</ConsentCheck>
          : <p className="mx-1.5 mt-2 text-[12.5px] leading-snug text-muted">Sin tu teléfono, el técnico no podrá avisarte si se retrasa. <Link href={`/hogar/datos?volver=${encodeURIComponent(`/servicios/${id}/agendar?q=${qid}`)}`} className="font-extrabold underline">Agregar mi teléfono</Link></p>}
        <ErrorNote text={m.isError ? (m.error as Error).message : null} />
        <Actions><button type="button" className="btn" disabled={m.isPending || !ok} onClick={pedir}><Icon name="check" size={19} stroke={2.4} />Pedir esta visita</button>
          <TextLink href={`/servicios/${id}/cotizacion/${qid}`}>Ahora no</TextLink></Actions>
      </>)}
      {q.isLoading && <p className="text-muted">Cargando…</p>}
    </Shell>
  );
}
export default function Agendar({ params }: { params: Promise<{ id: string }> }) { const { id } = use(params); return <Suspense><Form id={id} /></Suspense>; }
