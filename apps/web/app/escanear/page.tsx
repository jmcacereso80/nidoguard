"use client";
import { useEffect, useRef, useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { useQuery } from "@tanstack/react-query";
import jsQR from "jsqr";
import { parseNidoUrl } from "@/lib/nidoUrl";
import { Icon } from "@/components/Icon";
import { Kit, Space, useApi } from "@/lib/api";

const corner = "absolute h-12 w-12 border-white";

// Pide la camara trasera; si el celular o el navegador la rechazan (sin permiso no se reintenta),
// usa cualquier camara disponible.
async function openCamera(): Promise<MediaStream> {
  if (!navigator.mediaDevices?.getUserMedia) {
    throw Object.assign(new Error("sin mediaDevices"), { name: "NoMediaDevices" });
  }
  try {
    return await navigator.mediaDevices.getUserMedia({ video: { facingMode: { ideal: "environment" } }, audio: false });
  } catch (e) {
    if ((e as Error).name === "NotAllowedError" || (e as Error).name === "SecurityError") throw e;
    return await navigator.mediaDevices.getUserMedia({ video: true, audio: false });
  }
}

export default function Escanear() {
  const video = useRef<HTMLVideoElement>(null);
  const router = useRouter();
  const api = useApi();
  const [err, setErr] = useState<string | null>(null);
  const [ready, setReady] = useState(false);
  const [kitPath, setKitPath] = useState<string | null>(null);
  const kits = useQuery({ queryKey: ["kits"], queryFn: () => api<Kit[]>("/kits") });
  const spaces = useQuery({ queryKey: ["spaces"], queryFn: () => api<Space[]>("/spaces") });
  const [last, setLast] = useState<string | null>(null);
  useEffect(() => { setLast(sessionStorage.getItem("ng:last-space")); }, []);
  const spaceName = spaces.data?.find((s) => s.id === last)?.name;
  const used = kits.data?.reduce((n, k) => n + k.tags_used, 0) ?? 0;
  const total = kits.data?.reduce((n, k) => n + k.tags_total, 0) ?? 0;

  // Solo muestra la camara. No decodifica en bucle: la lectura es al tocar el boton.
  useEffect(() => {
    let stream: MediaStream | null = null; let stopped = false;
    (async () => {
      try {
        stream = await openCamera();
        // Si el efecto ya se cancelo (React lo monta dos veces en desarrollo), apaga esta camara.
        if (stopped) { stream.getTracks().forEach((t) => t.stop()); return; }
        if (!video.current) return;
        video.current.srcObject = stream;
        await video.current.play();
        if (!stopped) setReady(true);
      } catch (e) {
        // Una ejecucion cancelada o un play() interrumpido por otra carga no es un error real.
        if (stopped || (e as Error).name === "AbortError") return;
        const name = (e as Error).name || "Error";
        const msg = name === "NotAllowedError"
          ? "Permiso de cámara denegado. Actívalo en Ajustes del iPhone para este navegador."
          : name === "NoMediaDevices" || name === "SecurityError"
            ? "Este navegador no puede usar la cámara en esta dirección. Abre la página con https."
            : "No pudimos abrir la cámara.";
        setErr(`${msg} (${name})`);
      }
    })();
    return () => { stopped = true; stream?.getTracks().forEach((t) => t.stop()); };
  }, []);

  // Toma una foto del cuadro actual y busca un QR en ella.
  function leerCodigo() {
    const v = video.current;
    if (!v || v.readyState < v.HAVE_ENOUGH_DATA) {
      setErr("La cámara aún no está lista. Espera un segundo y vuelve a intentar.");
      return;
    }
    setErr(null);
    const canvas = document.createElement("canvas");
    canvas.width = v.videoWidth; canvas.height = v.videoHeight;
    const ctx = canvas.getContext("2d", { willReadFrequently: true })!;
    ctx.drawImage(v, 0, 0);
    const img = ctx.getImageData(0, 0, canvas.width, canvas.height);
    const code = jsQR(img.data, img.width, img.height);
    if (!code) {
      setErr("No encontramos un código. Acerca la etiqueta, con buena luz, y vuelve a intentar.");
      return;
    }
    const path = parseNidoUrl(code.data);
    if (!path) {
      setErr("Ese código no es de NidoGuard.");
      return;
    }
    // Una hoja de kit no es una etiqueta de equipo: pedimos confirmacion antes de activarla.
    if (path.startsWith("/k/")) { setKitPath(path); return; }
    router.push(path);
  }

  return (
    <main className="fixed inset-0 overflow-hidden text-white" style={{ background: "radial-gradient(circle at 50% 30%, #0E3F66, #02264D 70%)" }}>
      <video ref={video} playsInline muted className="absolute inset-0 h-full w-full object-cover opacity-70" />
      <div className="absolute inset-x-0 top-0 mx-auto flex max-w-md items-center justify-between px-4 pt-6">
        <Link href="/inicio" aria-label="Cerrar" className="grid h-11 w-11 place-items-center rounded-full border border-white/30 bg-white/15 backdrop-blur-xl"><Icon name="x" size={20} /></Link>
        <h1 className="text-lg font-extrabold">Escanear</h1>
        <span className="h-11 w-11" />
      </div>
      {total > 0 && (
        <p className="absolute inset-x-0 top-[88px] mx-auto flex w-fit items-center gap-2 rounded-full border border-white/30 bg-white/15 px-4 py-2 text-[13px] font-bold backdrop-blur-xl">
          <Icon name="home" size={15} />{spaceName ? `Registrando en ${spaceName}` : "Registrando equipos"} · {used} de {total}
        </p>
      )}
      <div className="absolute left-1/2 top-[140px] h-[250px] w-[250px] -translate-x-1/2" aria-hidden="true">
        <span className={`${corner} left-0 top-0 rounded-tl-3xl border-l-4 border-t-4`} /><span className={`${corner} right-0 top-0 rounded-tr-3xl border-r-4 border-t-4`} />
        <span className={`${corner} bottom-0 left-0 rounded-bl-3xl border-b-4 border-l-4`} /><span className={`${corner} bottom-0 right-0 rounded-br-3xl border-b-4 border-r-4`} />
        <span className="absolute inset-x-3 top-1/2 h-0.5 rounded bg-[var(--ng-copper)] shadow-[0_0_12px_var(--ng-copper)]" />
      </div>
      <div className="absolute inset-x-0 top-[420px] mx-auto flex max-w-md flex-col items-center gap-3 px-6 text-center">
        <p className="rounded-full border border-white/30 bg-white/15 px-5 py-2.5 text-[15px] font-bold backdrop-blur-xl">Apunta al QR de la etiqueta y toca el botón</p>
        {err && <p role="alert" className="rounded-2xl bg-white/90 px-4 py-3 text-sm font-bold text-[var(--ng-danger)]">{err}</p>}
      </div>
      <div className="absolute inset-x-0 bottom-8 mx-auto flex max-w-md flex-col items-center gap-3">
        <button onClick={leerCodigo} disabled={!ready} aria-label={ready ? "Leer código" : "Preparando cámara"}
          className="grid h-[82px] w-[82px] place-items-center rounded-full border-4 border-white disabled:opacity-50">
          <span className="block h-[62px] w-[62px] rounded-full bg-white" />
        </button>
        <p className="text-[13px] font-bold">{ready ? "Leer código" : "Preparando cámara…"}</p>
        <Link href="/k/activar" className="text-sm font-bold underline underline-offset-4">Aún no tengo etiquetas</Link>
      </div>
      {kitPath && (
        <div className="absolute inset-0 z-20 flex items-end bg-[rgba(2,38,77,.5)]" role="dialog" aria-modal="true" aria-label="Hoja de kit">
          <div className="gs mx-auto w-full max-w-md rounded-b-none rounded-t-[34px] px-5 pb-8 pt-5 text-ink">
            <p className="text-[20px] font-extrabold">Esto es una hoja de kit, no un equipo</p>
            <p className="mt-1 text-sm text-muted">Un kit se activa una sola vez y te da sus etiquetas. ¿Quieres activarlo ahora?</p>
            <div className="mt-4 grid grid-cols-2 gap-2.5">
              <button className="btn btn-copper w-full" onClick={() => router.push(kitPath)}>Activar kit</button>
              <button className="btn btn-ghost w-full" onClick={() => setKitPath(null)}>Cancelar</button>
            </div>
          </div>
        </div>
      )}
    </main>
  );
}
