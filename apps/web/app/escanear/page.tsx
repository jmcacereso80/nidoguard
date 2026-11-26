"use client";
import { useEffect, useRef, useState } from "react";
import { useRouter } from "next/navigation";
import jsQR from "jsqr";
import { parseNidoUrl } from "@/lib/nidoUrl";
import { Shell, ErrorNote } from "@/components/Shell";

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
  const [err, setErr] = useState<string | null>(null);
  const [ready, setReady] = useState(false);

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
    router.push(path);
  }

  return (
    <Shell title="Escanear etiqueta" back="/inicio">
      <div className="gs overflow-hidden rounded-[30px] p-1.5"><div className="overflow-hidden rounded-[24px]">
        <video ref={video} playsInline muted className="aspect-square w-full object-cover" />
      </div></div>
      <p className="mt-3 text-center text-sm text-muted">Apunta al código QR y toca “Leer código”.</p>
      <button className="btn btn-copper mt-4 w-full" onClick={leerCodigo} disabled={!ready}>
        {ready ? "Leer código" : "Preparando cámara…"}
      </button>
      <ErrorNote text={err} />
    </Shell>
  );
}
