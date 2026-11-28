import Link from "next/link";
import { Icon } from "@/components/Icon";
import { NO_COBRO, Tone } from "@/lib/servicios";

const TONE: Record<Tone, { bg: string; fg: string }> = {
  green: { bg: "rgba(47,107,74,.16)", fg: "#235A3B" }, cobre: { bg: "rgba(193,139,88,.24)", fg: "#8F5A1F" },
  blue: { bg: "rgba(115,153,181,.28)", fg: "#183B56" }, gray: { bg: "rgba(24,59,86,.10)", fg: "#526574" },
};
export function Chip({ tone = "blue", icon, children }: { tone?: Tone; icon?: string; children: React.ReactNode }) {
  return <span className="chip" style={{ background: TONE[tone].bg, color: TONE[tone].fg }}>{icon && <Icon name={icon} size={13} stroke={2.4} />}{children}</span>;
}

/** Aviso fijo: aparece en cada pantalla donde hay un precio o una visita. */
export function NoCobro({ text = NO_COBRO }: { text?: string }) {
  return (
    <div className="flex items-start gap-2.5 rounded-[18px] px-3 py-2.5" style={{ background: "rgba(47,107,74,.13)" }}>
      <span className="mt-px text-[#235A3B]"><Icon name="wallet" size={18} stroke={2.2} /></span>
      <p className="text-[13px] font-semibold leading-snug text-[#1D4A31]">{text}</p>
    </div>
  );
}
export function Note({ icon = "info", children }: { icon?: string; children: React.ReactNode }) {
  return <p className="mx-1 mt-3 flex items-start gap-2 text-[12.5px] leading-snug text-muted"><span className="mt-px"><Icon name={icon} size={15} stroke={2.2} /></span><span>{children}</span></p>;
}
export function Label({ children }: { children: React.ReactNode }) { return <h2 className="mx-1.5 mb-2 mt-5 text-[14px] font-extrabold">{children}</h2>; }
export function Callout({ tone = "cobre", icon = "info", children }: { tone?: "cobre" | "red"; icon?: string; children: React.ReactNode }) {
  const c = tone === "red" ? { bg: "rgba(143,47,47,.10)", fg: "#5E1F1F" } : { bg: "rgba(193,139,88,.16)", fg: "#5E3B12" };
  return (
    <div className="flex items-start gap-2.5 rounded-[18px] px-3 py-2.5" style={{ background: c.bg }}>
      <span className="mt-px" style={{ color: tone === "red" ? "#8F2F2F" : "#8F5A1F" }}><Icon name={icon} size={18} stroke={2.2} /></span>
      <div className="text-[13px] leading-snug" style={{ color: c.fg }}>{children}</div>
    </div>
  );
}
export function Summary({ icon = "wrench", title, sub }: { icon?: string; title: string; sub?: string | null }) {
  return (
    <div className="g mt-3 flex items-center gap-3 rounded-[24px] p-3.5">
      <span className="icon-tile"><Icon name={icon} size={20} /></span>
      <div className="min-w-0"><p className="text-[14.5px] font-extrabold leading-snug">{title}</p>{sub && <p className="text-[12.5px] text-muted">{sub}</p>}</div>
    </div>
  );
}
export function ConsentCheck({ checked, onChange, children }: { checked: boolean; onChange: (v: boolean) => void; children: React.ReactNode }) {
  return (
    <label className="mt-3 flex min-h-11 items-start gap-3 text-[13px] leading-snug">
      <input type="checkbox" checked={checked} onChange={(e) => onChange(e.target.checked)} className="mt-0.5 h-[22px] w-[22px] flex-none accent-[#183B56]" />
      <span>{children}</span>
    </label>
  );
}
export function Steps({ items }: { items: [string, string][] }) {
  return (
    <div className="mt-3 flex flex-col gap-2.5">
      {items.map(([icon, text]) => (
        <div key={text} className="flex items-start gap-3">
          <span aria-hidden="true" className="grid h-[30px] w-[30px] flex-none place-items-center rounded-[10px] bg-[#E4EDF4] text-navy"><Icon name={icon} size={16} /></span>
          <span className="pt-1 text-[13px] leading-snug">{text}</span>
        </div>
      ))}
    </div>
  );
}
export function Timeline({ rows }: { rows: { state: "ok" | "now" | "wait"; text: string; sub?: string }[] }) {
  return (
    <div className="g mt-3 rounded-[26px] px-4 py-2">
      {rows.map((r) => (
        <div key={r.text} className="flex items-start gap-3 py-2.5">
          <span aria-hidden="true" className="grid h-7 w-7 flex-none place-items-center rounded-full"
            style={{ background: r.state === "ok" ? "#183B56" : r.state === "now" ? "rgba(115,153,181,.35)" : "rgba(24,59,86,.10)", color: r.state === "ok" ? "#fff" : r.state === "now" ? "#183B56" : "#526574" }}>
            <Icon name={r.state === "ok" ? "check" : r.state === "now" ? "phone" : "clock"} size={15} stroke={2.6} /></span>
          <div><p className={`text-[14.5px] ${r.state === "wait" ? "font-semibold text-muted" : "font-extrabold"}`}>{r.text}</p>{r.sub && <p className="mt-px text-[12.5px] text-muted">{r.sub}</p>}</div>
        </div>
      ))}
    </div>
  );
}
export function KV({ icon, k, v }: { icon: string; k: string; v: string }) {
  return (
    <div className="flex items-center gap-3 py-2.5">
      <span className="text-navy"><Icon name={icon} size={20} /></span>
      <div className="min-w-0 flex-1"><p className="text-[12.5px] text-muted">{k}</p><p className="text-[14px] font-extrabold leading-snug">{v}</p></div>
    </div>
  );
}
export const Hr = () => <div className="h-px bg-navy/10" />;
export function Hero({ icon = "calendar", kicker, title, sub }: { icon?: string; kicker: string; title: string; sub: string }) {
  return (
    <div className="mt-4 flex flex-col items-center gap-1.5 text-center">
      <span aria-hidden="true" className="gd grid h-[68px] w-[68px] place-items-center rounded-full"><Icon name={icon} size={32} stroke={2.2} /></span>
      <p className="mt-1.5 text-[13px] font-bold text-muted">{kicker}</p>
      <p className="text-[24px] font-extrabold capitalize leading-tight">{title}</p>
      <p className="text-[15px] font-bold">{sub}</p>
    </div>
  );
}
export function Actions({ children }: { children: React.ReactNode }) { return <div className="mt-4 flex flex-col gap-2.5">{children}</div>; }
export function TextLink({ href, onClick, children, danger }: { href?: string; onClick?: () => void; children: React.ReactNode; danger?: boolean }) {
  const cls = `mx-auto flex min-h-11 items-center px-3 text-[14px] font-extrabold ${danger ? "text-[var(--ng-danger)]" : "text-navy"}`;
  return href ? <Link href={href} className={cls}>{children}</Link> : <button type="button" onClick={onClick} className={cls}>{children}</button>;
}
