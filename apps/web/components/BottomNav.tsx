import Link from "next/link";

const icon = { width: 24, height: 24, viewBox: "0 0 24 24", fill: "none", stroke: "currentColor", strokeWidth: 2, strokeLinecap: "round", strokeLinejoin: "round", "aria-hidden": true } as const;

function Item({ href, label, active, children }: { href: string; label: string; active: boolean; children: React.ReactNode }) {
  return (
    <Link href={href} aria-current={active ? "page" : undefined}
      className={`flex w-[84px] flex-col items-center gap-[3px] rounded-3xl py-2 text-[11px] font-bold leading-tight ${active ? "bg-[rgba(24,59,86,.10)] text-navy" : "text-muted"}`}>
      {children}<span>{label}</span>
    </Link>
  );
}

export function BottomNav({ active }: { active: "inicio" | "por-confirmar" }) {
  return (
    <nav aria-label="Principal" className="gs fixed inset-x-4 bottom-5 z-10 mx-auto flex h-[74px] max-w-[398px] items-center justify-between rounded-[37px] px-3">
      <Item href="/inicio" label="Inicio" active={active === "inicio"}>
        <svg {...icon}><path d="m3 10 9-7 9 7v10a1 1 0 0 1-1 1H4a1 1 0 0 1-1-1z" /></svg>
      </Item>
      <Link href="/escanear" aria-label="Escanear"
        className="-mt-9 grid h-[70px] w-[70px] flex-none place-items-center rounded-full border-4 border-white/90 text-white shadow-[0_14px_28px_rgba(24,59,86,.38)]"
        style={{ background: "linear-gradient(145deg,#7399B5,#183B56)" }}>
        <svg {...icon} width={30} height={30} strokeWidth={2.2}><path d="M3 7V5a2 2 0 0 1 2-2h2M17 3h2a2 2 0 0 1 2 2v2M21 17v2a2 2 0 0 1-2 2h-2M7 21H5a2 2 0 0 1-2-2v-2" /><path d="M7 12h10" /></svg>
      </Link>
      <Item href="/por-confirmar" label="Por confirmar" active={active === "por-confirmar"}>
        <svg {...icon}><path d="m5 12 5 5 9-10" /></svg>
      </Item>
    </nav>
  );
}
