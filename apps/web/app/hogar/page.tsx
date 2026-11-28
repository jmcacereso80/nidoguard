"use client";
import Link from "next/link";
import { Shell } from "@/components/Shell";
import { Icon } from "@/components/Icon";
import { Chip } from "@/components/servicios/ui";
import { useMe } from "@/components/useHome";
import { iniciales, lineaDireccion, pendientes } from "@/lib/micasa";

function Paso({ ok, texto, href, accion }: { ok: boolean; texto: string; href: string; accion: string }) {
  return (
    <li className="flex min-h-12 items-center gap-3">
      {ok ? <span aria-hidden className="grid h-7 w-7 flex-none place-items-center rounded-full bg-[rgba(47,107,74,.18)] text-[#235A3B]"><Icon name="check" size={16} stroke={2.8} /></span>
        : <span aria-hidden className="h-7 w-7 flex-none rounded-full border-2 border-dashed border-[#C18B58]" />}
      <span className={`flex-1 text-[14.5px] font-extrabold ${ok ? "" : "text-[#5E3B12]"}`}>{texto}</span>
      {!ok && <Link href={href} className="flex min-h-11 items-center rounded-full bg-[rgba(193,139,88,.24)] px-3.5 text-[13px] font-extrabold text-[#8F5A1F]">{accion}</Link>}
    </li>
  );
}

export default function MiCasa() {
  const me = useMe();
  const m = me.data;
  if (!m) return <Shell title="Mi casa" back="/inicio" nav="inicio"><p className="text-sm text-muted">Cargando…</p></Shell>;
  const p = pendientes(m);
  const props = m.home?.properties ?? [];
  const nombre = [m.user.first_name, m.user.last_name].filter(Boolean).join(" ") || m.user.name || "Agrega tu nombre";
  return (
    <Shell title="Mi casa" subtitle="Tus datos y direcciones" back="/inicio" nav="inicio">
      <section className="gs rounded-[30px] p-[18px]">
        <div className="flex items-center gap-3.5">
          <span aria-hidden className="grid h-[68px] w-[68px] flex-none place-items-center rounded-full text-[24px] font-extrabold text-white"
            style={{ background: "linear-gradient(145deg,#7399B5,#183B56)", boxShadow: "0 0 0 4px #F6F2EC,0 0 0 6px #C18B58" }}>{iniciales(m)}</span>
          <div className="min-w-0 flex-1"><p className="text-[20px] font-extrabold leading-tight">{nombre}</p><p className="mt-0.5 truncate text-[13px] text-muted">{m.user.email}</p></div>
          <Link href="/hogar/datos" aria-label="Editar mis datos" className="g grid h-11 w-11 flex-none place-items-center rounded-full text-navy"><Icon name="pencil" size={19} stroke={2.2} /></Link>
        </div>
        <div className="mt-4 border-t border-[rgba(24,59,86,.1)] pt-3">
          <div className="flex items-baseline justify-between"><h2 className="text-[14px] font-extrabold">Para pedir un servicio necesitas</h2>
            <span className="text-[13px] font-bold text-[#8F5A1F]">{p.listos} de 3</span></div>
          <div role="progressbar" aria-valuemin={0} aria-valuemax={3} aria-valuenow={p.listos} aria-label="Datos listos" className="my-2 h-2 overflow-hidden rounded-full bg-[rgba(24,59,86,.10)]">
            <div className="h-full rounded-full" style={{ width: `${(p.listos / 3) * 100}%`, background: "linear-gradient(90deg,#7399B5,#183B56)" }} /></div>
          <ul>
            <Paso ok={p.nombre} texto="Tu nombre y apellidos" href="/hogar/datos" accion="Agregar" />
            <Paso ok={p.direccion} texto="Una dirección ubicada" href={props[0] ? `/hogar/direccion?p=${props[0].id}` : "/hogar/direccion?nueva=1"} accion="Agregar" />
            <Paso ok={p.telefono} texto="Tu teléfono para agendar" href="/hogar/datos" accion="Agregar" />
          </ul>
        </div>
      </section>

      <h2 className="mx-1 mb-2 mt-6 text-[17px] font-extrabold">Mis direcciones</h2>
      <div className="flex flex-col gap-2.5">
        {props.map((x) => (
          <Link key={x.id} href={`/hogar/direccion?p=${x.id}`} className="g flex items-center gap-3 rounded-[26px] p-3.5">
            <span aria-hidden className="icon-tile"><Icon name="pin" size={22} /></span>
            <span className="min-w-0 flex-1">
              <span className="flex flex-wrap items-center gap-2"><span className="text-[16px] font-extrabold">{x.name}</span>
                {x.address?.is_primary && <Chip tone="green" icon="check">Principal</Chip>}
                {!x.address?.complete && <Chip tone="cobre" icon="pin">Falta ubicarla</Chip>}</span>
              <span className="mt-0.5 block text-[13.5px] font-semibold leading-snug">{lineaDireccion(x.address) || "Todavía sin dirección"}</span>
              <span className="block text-[12.5px] text-muted">{x.address?.complete ? `Técnicos a menos de ${x.address.search_radius_km} km · ` : ""}{x.assets_count ?? 0} {x.assets_count === 1 ? "equipo" : "equipos"}</span>
            </span>
            <Icon name="chevron" size={18} stroke={2.4} />
          </Link>
        ))}
        {props.length < 5 && (
          <Link href="/hogar/direccion?nueva=1" className="flex min-h-[60px] items-center justify-center gap-2 rounded-[26px] border-2 border-dashed border-[rgba(24,59,86,.28)] text-[14.5px] font-extrabold text-navy">
            <Icon name="plus" size={19} stroke={2.4} />Agregar otra dirección</Link>
        )}
      </div>
      <p className="mx-1.5 mt-2 text-[12.5px] leading-snug text-muted">Puedes guardar hasta 5. Al pedir un servicio eliges en cuál.</p>

      <Link href="/hogar/privacidad" className="g mt-5 flex items-center gap-3 rounded-[26px] px-4 py-3.5">
        <span className="icon-tile"><Icon name="lock" size={20} /></span>
        <span className="flex-1"><span className="block text-[15px] font-extrabold">Quién ve mis datos</span><span className="block text-[12.5px] text-muted">Tú decides qué recibe cada técnico</span></span>
        <Icon name="chevron" size={18} stroke={2.4} />
      </Link>
    </Shell>
  );
}
