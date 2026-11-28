// Version de la app (commit con el que arranco la web), para saber que version estas viendo.
export function AppVersion({ className = "" }: { className?: string }) {
  return (
    <p className={`pointer-events-none text-center text-[10px] tracking-wide ${className}`}>
      NidoGuard · {process.env.NEXT_PUBLIC_APP_VERSION ?? "sin versión"}
    </p>
  );
}
