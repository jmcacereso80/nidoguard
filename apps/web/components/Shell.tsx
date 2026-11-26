import Link from "next/link";
import { Logo } from "./Logo";
import { BottomNav } from "./BottomNav";

export function Shell({ title, back, nav, children }: { title?: string; back?: string; nav?: "inicio" | "por-confirmar"; children: React.ReactNode }) {
  return (
    <main className={`mx-auto w-full max-w-md px-4 pt-6 ${nav ? "pb-32" : "pb-10"}`}>
      <header className="mb-5 flex min-h-11 items-center gap-3">
        {back ? (
          <Link href={back} aria-label="Volver" className="g grid h-11 w-11 flex-none place-items-center rounded-full text-xl font-bold text-navy">‹</Link>
        ) : <Logo />}
        <h1 className="text-[28px] font-extrabold leading-tight tracking-tight text-ink">{title ?? "NidoGuard"}</h1>
      </header>
      {children}
      <p className="mt-8 text-center text-[10px] tracking-wide text-muted/60">NidoGuard · {process.env.NEXT_PUBLIC_APP_VERSION ?? "sin versión"}</p>
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
