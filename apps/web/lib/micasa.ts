import type { Me } from "./api.ts";

/** Lo que falta para poder pedir un servicio: nombre, una direccion ubicada y telefono. */
export function pendientes(me: Me): { nombre: boolean; direccion: boolean; telefono: boolean; listos: number } {
  const nombre = !!me.user.first_name?.trim();
  const direccion = !!me.home?.properties.some((p) => p.address?.complete);
  const telefono = !!me.user.phone;
  return { nombre, direccion, telefono, listos: [nombre, direccion, telefono].filter(Boolean).length };
}

export function iniciales(me: Me): string {
  const a = (me.user.first_name ?? me.user.name ?? me.user.email ?? "?").trim()[0] ?? "?";
  const b = (me.user.last_name ?? "").trim()[0] ?? "";
  return (a + b).toUpperCase();
}

export function lineaDireccion(a?: { street: string | null; colony: string | null; city: string | null }): string {
  return a?.street ? [a.street, a.colony, a.city].filter(Boolean).join(", ") : "";
}

export function quitarLada(tel: string | null): string {
  return (tel ?? "").replace(/^\+52/, "");
}
