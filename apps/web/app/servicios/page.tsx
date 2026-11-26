import { Shell, Pronto } from "@/components/Shell";
export default function Servicios() {
  return (
    <Shell title="Servicios" subtitle="Cuéntanos qué pasó y nos encargamos." big nav="servicios">
      <Pronto icon="headset" title="Pronto buscaremos al técnico por ti" text="Describe el problema de tu equipo y nosotros conseguimos, cotizamos y damos seguimiento." />
    </Shell>
  );
}
