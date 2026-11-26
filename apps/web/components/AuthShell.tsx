import Link from "next/link";
import { Logo } from "./Logo";

/** Marco de las pantallas de entrada: logotipo, lema y el formulario de Clerk sobre vidrio. */
export function AuthShell({ children, back }: { children: React.ReactNode; back?: boolean }) {
  return (
    <main className="mx-auto flex min-h-dvh w-full max-w-md flex-col items-center px-4 pb-10 pt-8">
      <div className="flex w-full items-center">
        {back && <Link href="/" aria-label="Volver" className="g grid h-11 w-11 place-items-center rounded-full text-xl font-bold text-navy">‹</Link>}
      </div>
      <div className="mb-6 mt-2 flex flex-col items-center gap-2 text-center">
        <Logo size={56} />
        <p className="text-[22px] font-extrabold tracking-tight text-ink">NidoGuard</p>
        <p className="text-sm font-semibold text-muted">Mejor vida. Más valor.</p>
      </div>
      {children}
    </main>
  );
}
