const P: Record<string, React.ReactNode> = {
  home: <path d="m3 10 9-7 9 7v10a1 1 0 0 1-1 1H4a1 1 0 0 1-1-1z" />,
  grid: <><rect x="3" y="3" width="7" height="7" rx="2" /><rect x="14" y="3" width="7" height="7" rx="2" /><rect x="3" y="14" width="7" height="7" rx="2" /><rect x="14" y="14" width="7" height="7" rx="2" /></>,
  scan: <><path d="M3 7V5a2 2 0 0 1 2-2h2M17 3h2a2 2 0 0 1 2 2v2M21 17v2a2 2 0 0 1-2 2h-2M7 21H5a2 2 0 0 1-2-2v-2" /><path d="M7 12h10" /></>,
  heart: <path d="M19 14c1.5-1.5 3-3.2 3-5.5A5.5 5.5 0 0 0 16.5 3c-1.7 0-3 .8-4.5 2.5C10.5 3.8 9.2 3 7.5 3A5.5 5.5 0 0 0 2 8.5c0 2.3 1.5 4 3 5.5l7 7z" />,
  headset: <><path d="M3 14v-2a9 9 0 0 1 18 0v2" /><path d="M21 15a2 2 0 0 1-2 2h-1v-5h1a2 2 0 0 1 2 2zM3 15a2 2 0 0 0 2 2h1v-5H5a2 2 0 0 0-2 2z" /></>,
  check: <path d="m5 12 5 5 9-10" />,
  plus: <path d="M12 5v14M5 12h14" />,
  search: <><circle cx="11" cy="11" r="7" /><path d="m20 20-3.5-3.5" /></>,
  chevron: <path d="m9 6 6 6-6 6" />,
  down: <path d="m6 9 6 6 6-6" />,
  x: <path d="M6 6l12 12M18 6 6 18" />,
  clock: <><circle cx="12" cy="12" r="9" /><path d="M12 7v5l3 2" /></>,
  user: <><circle cx="12" cy="8" r="4" /><path d="M4 21a8 8 0 0 1 16 0" /></>,
  sparkle: <><path d="M12 3l1.8 5.2L19 10l-5.2 1.8L12 17l-1.8-5.2L5 10l5.2-1.8z" /><path d="M19 17v4M17 19h4" /></>,
  tag: <><path d="M3 12V4h8l10 10-8 8z" /><circle cx="7.5" cy="8.5" r="1.2" /></>,
  camera: <><path d="M4 8h3l2-3h6l2 3h3v11H4z" /><circle cx="12" cy="13" r="3.5" /></>,
  file: <><path d="M6 3h8l4 4v14H6z" /><path d="M14 3v4h4M9 13h6M9 17h6" /></>,
  shield: <path d="M12 3 5 6v6c0 4.5 3 7.5 7 9 4-1.5 7-4.5 7-9V6z" />,
  wrench: <path d="M14.7 6.3a4 4 0 0 0-5 5L3 18l3 3 6.7-6.7a4 4 0 0 0 5-5l-2.4 2.4-2.6-.7-.7-2.6z" />,
  drop: <path d="M12 3s6 6.5 6 11a6 6 0 0 1-12 0c0-4.5 6-11 6-11z" />,
  fridge: <><rect x="6" y="2" width="12" height="20" rx="3" /><path d="M6 10h12M9 6v2M9 13v3" /></>,
  washer: <><rect x="4" y="2" width="16" height="20" rx="3" /><circle cx="12" cy="14" r="4.5" /><path d="M8 6h.01M11 6h.01" /></>,
  ac: <><rect x="3" y="4" width="18" height="8" rx="3" /><path d="M7 16l-1 3M12 16v3M17 16l1 3" /></>,
  tv: <><rect x="3" y="4" width="18" height="12" rx="2.5" /><path d="M8 20h8M12 16v4" /></>,
  box: <><path d="M3 7l9-4 9 4v10l-9 4-9-4z" /><path d="M3 7l9 4 9-4M12 11v10" /></>,
  sofa: <><path d="M4 11V8a3 3 0 0 1 3-3h10a3 3 0 0 1 3 3v3" /><path d="M2 14a2 2 0 0 1 4 0v2h12v-2a2 2 0 0 1 4 0v4H2z" /></>,
  bed: <><path d="M3 18V6M3 14h18v4M21 14v-2a3 3 0 0 0-3-3h-7v5" /><circle cx="7" cy="11" r="1.5" /></>,
  cloud: <path d="M6 14a4 4 0 0 1-1-7.9A4 4 0 0 1 12 4a4 4 0 0 1 7 2.1A4 4 0 0 1 18 14zM6 14v6h12v-6" />,
  bolt: <path d="M13 2 4 14h7l-1 8 9-12h-7z" />,
  back: <path d="m15 6-6 6 6 6" />,
  cafetera: <><path d="M4 21h14M5 21V5a2 2 0 0 1 2-2h8a2 2 0 0 1 2 2v3" /><path d="M5 8h12M11 8v2.5" /><path d="M9 21v-6.5h6V21" /><path d="M15 15.5h1.2a1.5 1.5 0 0 1 0 3H15" /></>,
  licuadora: <><path d="M7 3h10l-1.4 11H8.4z" /><path d="M6 3h12" /><path d="M17 6h2v4h-1.6" /><rect x="6" y="14" width="12" height="7" rx="2.5" /><path d="M12 17.5h.01" /></>,
  horno: <><rect x="3" y="4" width="18" height="16" rx="3" /><path d="M3 9h18" /><path d="M7 6.5h.01M10 6.5h.01" /><rect x="6.5" y="11.5" width="11" height="6" rx="1.5" /></>,
  microondas: <><rect x="3" y="5" width="18" height="14" rx="3" /><rect x="6" y="8" width="8" height="8" rx="1.5" /><path d="M17.5 8.5h.01M17.5 12h.01M17.5 15.5h.01" /></>,
  estufa: <><rect x="3" y="3" width="18" height="18" rx="3" /><circle cx="8.5" cy="8.5" r="2.5" /><circle cx="15.5" cy="8.5" r="2.5" /><circle cx="8.5" cy="15.5" r="2.5" /><circle cx="15.5" cy="15.5" r="2.5" /></>,
  lavavajillas: <><rect x="4" y="2.5" width="16" height="19" rx="3" /><path d="M4 7h16M7.5 4.8h.01M10.5 4.8h.01" /><circle cx="12" cy="14.5" r="4" /><path d="M10 14.5a2 2 0 0 1 2-2" /></>,
  tostador: <><rect x="3" y="9" width="18" height="10" rx="3" /><path d="M7 9V6.5A1.5 1.5 0 0 1 8.5 5h1A1.5 1.5 0 0 1 11 6.5V9M13 9V6.5A1.5 1.5 0 0 1 14.5 5h1A1.5 1.5 0 0 1 17 6.5V9" /><path d="M17.5 14h1.5" /></>,
  freidora: <><rect x="4" y="3" width="16" height="18" rx="5" /><path d="M9 7h6" /><rect x="7.5" y="11" width="9" height="6" rx="2" /><path d="M10 14h4" /></>,
  batidora: <><path d="M4 10c0-4 3-7 7-7h5a3 3 0 0 1 3 3v4z" /><path d="M12 10v4" /><path d="M5 14h14c0 4-3 6-7 6s-7-2-7-6z" /><path d="M9 21h6" /></>,
  hervidor: <><path d="M5 20v-7a6 6 0 0 1 12 0v7a1 1 0 0 1-1 1H6a1 1 0 0 1-1-1z" /><path d="m17 11 4-3" /><path d="M5 11H3.6a1.6 1.6 0 0 0 0 3H5" /><path d="M11 7V4.5" /></>,
  olla: <><path d="M5 10h14v8a3 3 0 0 1-3 3H8a3 3 0 0 1-3-3z" /><path d="M5 10a7 5 0 0 1 14 0" /><path d="M5 13H2.5M19 13h2.5" /><path d="M12 5V3.5" /></>,
  campana: <><path d="M8 3h8l3 9H5z" /><path d="M3 12h18" /><path d="M9 16v3M12 16v4M15 16v3" /></>,
  dispensador: <><path d="M9 2h6l1 4H8z" /><rect x="6" y="9" width="12" height="12" rx="2.5" /><path d="M10 14h4M12 14v3" /></>,
};

export function Icon({ name, size = 22, stroke = 2 }: { name: keyof typeof P | string; size?: number; stroke?: number }) {
  return (
    <svg width={size} height={size} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={stroke}
         strokeLinecap="round" strokeLinejoin="round" aria-hidden="true" style={{ flex: "none" }}>{P[name] ?? P.box}</svg>
  );
}

export const SPACE_ICONS = ["home", "sofa", "bed", "cloud", "wrench", "tv"] as const;

export { equipmentIcon } from "@/lib/equipmentIcon";
