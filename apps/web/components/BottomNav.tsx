import Link from "next/link";
import { Icon } from "./Icon";

export type NavKey = "inicio" | "equipos" | "cuidado" | "servicios";

function Item({ href, label, icon, active }: { href: string; label: string; icon: string; active: boolean }) {
  return (
    <Link href={href} aria-current={active ? "page" : undefined}
      className={`flex w-16 flex-col items-center gap-[3px] rounded-3xl py-2 text-[11px] font-bold leading-tight ${active ? "bg-[rgba(24,59,86,.10)] text-navy" : "text-muted"}`}>
      <Icon name={icon} size={24} stroke={active ? 2.2 : 1.8} /><span>{label}</span>
    </Link>
  );
}

export function BottomNav({ active }: { active: NavKey }) {
  return (
    <nav aria-label="Principal" className="gs fixed inset-x-4 bottom-5 z-10 mx-auto flex h-[74px] max-w-[398px] items-center justify-between rounded-[37px] px-2.5">
      <Item href="/inicio" label="Inicio" icon="home" active={active === "inicio"} />
      <Item href="/equipos" label="Equipos" icon="grid" active={active === "equipos"} />
      <Link href="/escanear" aria-label="Escanear"
        className="-mt-9 grid h-[70px] w-[70px] flex-none place-items-center rounded-full border-4 border-white/90 text-white shadow-[0_14px_28px_rgba(24,59,86,.38)]"
        style={{ background: "linear-gradient(145deg,#7399B5,#183B56)" }}>
        <Icon name="scan" size={30} stroke={2.2} />
      </Link>
      <Item href="/cuidado" label="Cuidado" icon="heart" active={active === "cuidado"} />
      <Item href="/servicios" label="Servicios" icon="headset" active={active === "servicios"} />
    </nav>
  );
}
