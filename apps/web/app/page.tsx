import Link from "next/link";
import { Shell, Card } from "@/components/Shell";

export default function Landing() {
  return (
    <Shell>
      <Card>
        <p className="text-lg font-bold text-navy">Mejor vida. Más valor.</p>
        <p className="mt-2 text-ink/80">Registra los equipos de tu casa, cuídalos y conserva su valor para cuando quieras venderlos.</p>
        <div className="mt-5 flex flex-col gap-3">
          <Link className="btn" href="/sign-up">Crear mi cuenta</Link>
          <Link className="btn btn-ghost" href="/sign-in">Ya tengo cuenta</Link>
        </div>
      </Card>
    </Shell>
  );
}
