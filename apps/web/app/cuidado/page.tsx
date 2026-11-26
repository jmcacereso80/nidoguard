import { Shell, Pronto } from "@/components/Shell";
export default function Cuidado() {
  return (
    <Shell title="Cuidado" subtitle="Lo que conviene hacer para que tus equipos duren más." big nav="cuidado">
      <Pronto icon="heart" title="Pronto te diremos qué cuidar" text="Aquí verás limpiezas, revisiones y avisos de garantía de cada equipo, con fecha y paso a paso." />
    </Shell>
  );
}
