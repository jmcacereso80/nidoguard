import Link from "next/link";
import { Logo } from "@/components/Logo";

const puntos = [
  { t: "Registra con una foto", d: "Escaneas la etiqueta, fotografías la placa y listo." },
  { t: "Cuida lo que ya tienes", d: "Te recordamos mantenimientos y garantías a tiempo." },
  { t: "Conserva su valor", d: "Todo queda en un expediente para cuando quieras vender." },
];

export default function Bienvenida() {
  return (
    <main className="mx-auto flex min-h-dvh w-full max-w-md flex-col px-4 pb-10 pt-14">
      <div className="flex flex-1 flex-col items-center justify-center text-center">
        <Logo size={96} />
        <h1 className="mt-5 text-[36px] font-extrabold leading-[1.1] tracking-[-0.9px] text-ink">NidoGuard</h1>
        <p className="mt-2 text-base font-semibold text-muted">Mejor vida. Más valor.</p>
      </div>
      <ul className="flex flex-col gap-2.5">
        {puntos.map((p) => (
          <li key={p.t} className="g flex items-center gap-3 rounded-[22px] px-4 py-3">
            <span className="icon-tile" aria-hidden="true">✓</span>
            <span><span className="block text-[15px] font-bold leading-tight">{p.t}</span><span className="block text-[12.5px] text-muted">{p.d}</span></span>
          </li>
        ))}
      </ul>
      <div className="mt-6 flex flex-col gap-3">
        <Link className="btn w-full" href="/sign-up">Crear mi cuenta</Link>
        <Link className="btn btn-ghost w-full" href="/sign-in">Ya tengo cuenta</Link>
      </div>
    </main>
  );
}
