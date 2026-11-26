// Subida de una foto directo a R2 con porcentaje de avance.
export type Upload = { image_id: string; url: string; headers: Record<string, string> };

export function putWithProgress(upload: Upload, file: File, onProgress: (pct: number) => void) {
  return new Promise<void>((resolve, reject) => {
    const xhr = new XMLHttpRequest();
    xhr.open("PUT", upload.url);
    Object.entries(upload.headers).forEach(([k, v]) => xhr.setRequestHeader(k, v));
    xhr.upload.onprogress = (e) => { if (e.lengthComputable) onProgress(Math.round((e.loaded / e.total) * 100)); };
    xhr.onload = () => (xhr.status >= 200 && xhr.status < 300 ? resolve() : reject(new Error(`R2 respondió ${xhr.status}`)));
    xhr.onerror = () => reject(new Error("Sin conexión con el servidor de fotos"));
    xhr.send(file);
  });
}

export const sleep = (ms: number) => new Promise((r) => setTimeout(r, ms));
