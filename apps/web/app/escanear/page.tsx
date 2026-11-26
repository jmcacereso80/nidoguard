"use client";
import { useEffect, useRef, useState } from "react";
import { useRouter } from "next/navigation";
import jsQR from "jsqr";
import { parseNidoUrl } from "@/lib/nidoUrl";
import { Shell, Card, ErrorNote } from "@/components/Shell";

export default function Escanear() {
  const video = useRef<HTMLVideoElement>(null);
  const router = useRouter();
  const [err, setErr] = useState<string | null>(null);

  useEffect(() => {
    let stream: MediaStream | null = null; let raf = 0; let stopped = false;
    const canvas = document.createElement("canvas");
    (async () => {
      try {
        stream = await navigator.mediaDevices.getUserMedia({ video: { facingMode: "environment" } });
        if (!video.current) return;
        video.current.srcObject = stream; await video.current.play();
        const tick = () => {
          if (stopped || !video.current) return;
          const v = video.current;
          if (v.readyState === v.HAVE_ENOUGH_DATA) {
            canvas.width = v.videoWidth; canvas.height = v.videoHeight;
            const ctx = canvas.getContext("2d", { willReadFrequently: true })!;
            ctx.drawImage(v, 0, 0);
            const img = ctx.getImageData(0, 0, canvas.width, canvas.height);
            const code = jsQR(img.data, img.width, img.height);
            if (code) {
              const path = parseNidoUrl(code.data);
              if (path) { stopped = true; router.push(path); return; }
              setErr("Ese código no es de NidoGuard.");
            }
          }
          raf = requestAnimationFrame(tick);
        };
        tick();
      } catch { setErr("No pudimos abrir la cámara. Revisa el permiso en tu navegador."); }
    })();
    return () => { stopped = true; cancelAnimationFrame(raf); stream?.getTracks().forEach((t) => t.stop()); };
  }, [router]);

  return (
    <Shell title="Escanear etiqueta" back="/inicio">
      <Card className="overflow-hidden !p-0">
        <video ref={video} playsInline muted className="aspect-square w-full object-cover" />
      </Card>
      <p className="mt-3 text-center text-sm text-ink/70">Apunta al código QR de la etiqueta.</p>
      <ErrorNote text={err} />
    </Shell>
  );
}
