/** Isotipo oficial (version clara): escudo marino, circulo cobre, curva azul, curva cobre. Pendiente: SVG vectorial entregado por diseno. */
export function Logo({ size = 30 }: { size?: number }) {
  return (
    <svg width={size * 0.9} height={size} viewBox="0 0 100 112" role="img" aria-label="NidoGuard" style={{ flex: "none", display: "block" }}>
      <path d="M50 7 88 29v33c0 20-18 35-38 43C30 97 12 82 12 62V29z" fill="none" stroke="#183B56" strokeWidth="11" strokeLinejoin="round" />
      <circle cx="50" cy="39" r="11" fill="#C18B58" />
      <path d="M28 57q22 21 44 0" fill="none" stroke="#7399B5" strokeWidth="9" strokeLinecap="round" />
      <path d="M27 71q22 13 44 0-9 22-22 22T27 71z" fill="#C18B58" />
    </svg>
  );
}
