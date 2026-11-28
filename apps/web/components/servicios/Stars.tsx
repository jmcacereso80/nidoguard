"use client";
import { useState } from "react";

const TEXTO = ["", "Muy mala", "Mala", "Regular", "Buena", "Excelente"];

function Star({ on, size }: { on: boolean; size: number }) {
  return (
    <svg width={size} height={size} viewBox="0 0 24 24" aria-hidden="true">
      <path d="M12 2.8l2.8 5.9 6.4.8-4.7 4.4 1.2 6.4L12 17.2 6.3 20.3l1.2-6.4L2.8 9.5l6.4-.8L12 2.8z"
        fill={on ? "#C18B58" : "none"} stroke={on ? "#C18B58" : "#7399B5"} strokeWidth="1.8" strokeLinejoin="round" />
    </svg>
  );
}

/** Calificación de 1 a 5 estrellas. Sin onChange solo se muestra. */
export function Stars({ value, onChange, size = 36 }: { value: number; onChange?: (n: number) => void; size?: number }) {
  const [hover, setHover] = useState(0);
  const shown = hover || value;
  if (!onChange) return <span role="img" aria-label={`${value} de 5 estrellas`} className="inline-flex gap-0.5">{[1, 2, 3, 4, 5].map((n) => <Star key={n} on={n <= value} size={size} />)}</span>;
  return (
    <div>
      <div role="radiogroup" aria-label="Calificación de la atención" className="flex justify-center gap-1" onMouseLeave={() => setHover(0)}>
        {[1, 2, 3, 4, 5].map((n) => (
          <button key={n} type="button" role="radio" aria-checked={value === n} aria-label={`${n} de 5: ${TEXTO[n]}`} onClick={() => onChange(n)} onMouseEnter={() => setHover(n)}
            className="flex h-11 w-11 items-center justify-center rounded-full"><Star on={n <= shown} size={size} /></button>
        ))}
      </div>
      <p aria-live="polite" className="mt-1 h-5 text-center text-[13px] font-bold text-muted">{shown ? TEXTO[shown] : "Toca una estrella"}</p>
    </div>
  );
}
