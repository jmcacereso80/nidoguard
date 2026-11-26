import Link from "next/link";

export function Shell({ title, back, children }: { title?: string; back?: string; children: React.ReactNode }) {
  return (
    <main className="mx-auto w-full max-w-md px-4 pb-24 pt-6">
      <header className="mb-5 flex items-center gap-3">
        {back && <Link href={back} aria-label="Volver" className="grid h-10 w-10 place-items-center rounded-full glass">‹</Link>}
        <h1 className="text-2xl font-extrabold text-navy">{title ?? "NidoGuard"}</h1>
      </header>
      {children}
    </main>
  );
}

export function Card({ children, className = "" }: { children: React.ReactNode; className?: string }) {
  return <section className={`glass p-5 ${className}`}>{children}</section>;
}

export function ErrorNote({ text }: { text: string | null }) {
  if (!text) return null;
  return <p role="alert" className="mt-3 rounded-xl bg-red-50 px-3 py-2 text-sm font-semibold text-[var(--ng-danger)]">{text}</p>;
}
