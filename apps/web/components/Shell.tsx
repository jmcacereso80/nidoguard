import Link from "next/link";
import { Logo } from "./Logo";
import { BottomNav, NavKey } from "./BottomNav";
import { Icon } from "./Icon";

/** Marco comun. `big` = titulo grande de pestana (Equipos, Cuidado); sin `big` = encabezado con volver o logotipo. */
export function Shell({ title, subtitle, back, nav, big, right, children }: {
  title?: string; subtitle?: string; back?: string; nav?: NavKey; big?: boolean; right?: React.ReactNode; children: React.ReactNode;
}) {
  return (
    <main className={`mx-auto w-full max-w-md px-4 pt-6 ${nav ? "pb-32" : "pb-10"}`}>
      <header className={`flex min-h-11 items-center gap-3 ${big ? "" : "mb-5"}`}>
        {back ? (
          <Link href={back} aria-label="Volver" className="g grid h-11 w-11 flex-none place-items-center rounded-full text-navy"><Icon name="back" size={22} /></Link>
        ) : !big && <Logo />}
        <h1 className={`flex-1 font-extrabold leading-tight tracking-tight text-ink ${big ? "pt-3 text-[34px] tracking-[-0.8px]" : "text-[26px]"}`}>{title ?? "NidoGuard"}</h1>
        {right}
      </header>
      <p className="-mt-3 mb-3 text-[10px] tracking-wide text-muted/80">NidoGuard · {process.env.NEXT_PUBLIC_APP_VERSION ?? "sin versión"}</p>
      {subtitle && <p className="mb-4 mt-1 text-sm text-muted">{subtitle}</p>}
      {children}
      {nav && <BottomNav active={nav} />}
    </main>
  );
}

export function Card({ children, className = "" }: { children: React.ReactNode; className?: string }) {
  return <section className={`g p-5 ${className}`}>{children}</section>;
}

export function ErrorNote({ text }: { text: string | null }) {
  if (!text) return null;
  return <p role="alert" className="mt-3 rounded-2xl bg-white/80 px-4 py-3 text-sm font-bold text-[var(--ng-danger)]">{text}</p>;
}

/** Pantalla de una seccion que llega en una etapa posterior. */
export function Pronto({ icon, title, text }: { icon: string; title: string; text: string }) {
  return (
    <div className="g mt-2 flex flex-col items-center gap-3 rounded-[30px] px-6 py-10 text-center">
      <span className="grid h-16 w-16 place-items-center rounded-full text-ink" style={{ background: "linear-gradient(145deg,#E9C7A3,#C18B58)" }}><Icon name={icon} size={30} /></span>
      <p className="text-xl font-extrabold">{title}</p>
      <p className="text-sm text-muted">{text}</p>
      <span className="chip"><Icon name="clock" size={13} stroke={2.4} />Muy pronto</span>
    </div>
  );
}
