// Icono de cada equipo segun su tipo o nombre. Los nombres de icono viven en components/Icon.tsx.
/** Quita acentos y pasa a minusculas para comparar texto. */
const norm = (t: string) => t.toLowerCase().normalize("NFD").replace(/[\u0300-\u036f]/g, "");

// El orden importa: lo mas especifico va primero (lavavajillas antes de lavadora, microondas antes de horno).
const RULES: [RegExp, string][] = [
  [/refri|nevera|congelador|frigobar/, "fridge"],
  [/lavavajilla|lavaplato|lava ?plato/, "lavavajillas"],
  [/lavadora|secadora|lavaseca|lava ?seca/, "washer"],
  [/microonda|microwave/, "microondas"],
  [/tostador|tostadora/, "tostador"],
  [/horno/, "horno"],
  [/estufa|parrilla|cooktop|tarja|hornilla|anafre|cocineta/, "estufa"],
  [/freidora|air ?fryer/, "freidora"],
  [/cafetera|espresso|nespresso|dolce gusto|cafe\b/, "cafetera"],
  [/licuadora|blender|nutribullet|procesador/, "licuadora"],
  [/batidora|mezcladora|kitchenaid/, "batidora"],
  [/hervidor|kettle|jarra electrica/, "hervidor"],
  [/\bolla\b|arrocera|instant ?pot|vaporera|slow ?cooker|olla de presion/, "olla"],
  [/campana|extractor/, "campana"],
  [/dispensador|garrafon|despachador/, "dispensador"],
  [/aire|clima|minisplit|mini split/, "ac"],
  [/tele|\btv\b|pantalla|smart ?tv/, "tv"],
];

/** Icono segun el tipo o el nombre del equipo. */
export function equipmentIcon(a: { category?: string | null; name: string }) {
  const t = norm(`${a.category ?? ""} ${a.name}`);
  return RULES.find(([re]) => re.test(t))?.[1] ?? "box";
}
