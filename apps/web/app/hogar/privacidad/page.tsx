import { Shell } from "@/components/Shell";
import { Icon } from "@/components/Icon";

type Fila = [("si" | "no" | "ask"), React.ReactNode];
function Bloque({ icon, titulo, sub, filas }: { icon: string; titulo: string; sub: string; filas: Fila[] }) {
  const M = { si: ["#235A3B", "check"], no: ["#8F5A1F", "lock"], ask: ["#183B56", "user"] } as const;
  return (
    <section className="g mt-3 rounded-[28px] p-4">
      <div className="flex items-center gap-3"><span className="icon-tile"><Icon name={icon} size={22} /></span><div><h2 className="text-[16.5px] font-extrabold">{titulo}</h2><p className="text-[12.5px] text-muted">{sub}</p></div></div>
      <ul className="mt-2 divide-y divide-[rgba(24,59,86,.08)]">
        {filas.map(([k, t], i) => <li key={i} className="flex items-start gap-3 py-2.5"><span className="mt-0.5 flex-none" style={{ color: M[k][0] }}><Icon name={M[k][1]} size={18} stroke={2.6} /></span><span className="text-[13.5px] leading-snug">{t}</span></li>)}
      </ul>
    </section>
  );
}

export default function Privacidad() {
  return (
    <Shell title="Quién ve mis datos" subtitle="Tú decides qué recibe cada quien" back="/hogar">
      <Bloque icon="wrench" titulo="Los técnicos" sub="Los que cotizan y los que visitan" filas={[
        ["si", <><b>Antes de que elijas:</b> solo tu colonia y qué equipo es.</>],
        ["si", <><b>Cuando confirmas la visita:</b> tu dirección exacta y tu nombre de pila.</>],
        ["no", <><b>Tu teléfono:</b> solo si lo permites al agendar. Lo decides en cada cita.</>]]} />
      <Bloque icon="building" titulo="El fabricante" sub="Solo cuando agendas con él" filas={[
        ["si", "Tu nombre completo, teléfono, dirección y los datos del equipo. Los pide para agendar y los ves antes de autorizar."],
        ["ask", "Si pide que hable el titular, te damos la línea para que llames tú."]]} />
      <Bloque icon="shieldok" titulo="NidoGuard" sub="Lo que guardamos" filas={[
        ["si", "Tus datos para ayudarte a pedir servicios y llevar el historial de tus equipos."],
        ["no", "Las llamadas se registran para revisar errores. Tú nunca recibes la grabación: ves un extracto de lo que dijo el técnico, sin nombres ni datos."],
        ["si", "NidoGuard no cobra por el servicio ni vende tus datos."]]} />
    </Shell>
  );
}
