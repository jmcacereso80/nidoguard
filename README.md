# NidoGuard

PWA de Patrimonio Inteligente. Mejor vida. Más valor. Reglas del proyecto en `CLAUDE.md`; estado de la etapa 1 en `docs/ESTADO_ETAPA_1.md`.

## Correr en tu Mac

Requisitos: Node 22+, pnpm, Python 3.11+, PostgreSQL 17 (o 16) corriendo.

```bash
cp .env.example .env            # llena tus valores (nunca se sube a git)
createdb nidoguard              # o crea la base desde pgAdmin

# API
python3 -m venv .venv && source .venv/bin/activate
pip install -e "apps/api[dev]"
cd apps/api && alembic upgrade head && uvicorn app.main:app --reload --port 8000

# Web (otra terminal, en la raiz)
pnpm install && pnpm --filter @nidoguard/web dev     # http://localhost:3000
```

Pruebas: `cd apps/api && pytest` (necesita `TEST_DATABASE_URL` apuntando a una base vacia de pruebas) y `pnpm --filter @nidoguard/web test`.

## Generar un lote de kits
```bash
cd apps/api && python -m admin.gen_batch --name "Lote 1" --kits 100 --tags-per-kit 20 --out ./salida
```
Escribe `kits.csv`, `etiquetas.csv` (URLs para grabar el NFC) y `hojas.pdf`. En la base solo quedan hashes de los códigos.

## Variables
`DATABASE_*`, `CLERK_API_KEY` (clave publicable), `CLERK_SECRET_KEY`, `CLAUDE_KEY`, `CLOUDFLARE_*`, y para las fotos `R2_BUCKET`, `R2_ACCESS_KEY_ID`, `R2_SECRET_ACCESS_KEY` (si no pones el secreto, se deriva del token de Cloudflare).
