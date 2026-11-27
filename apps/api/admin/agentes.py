"""Ajusta los agentes de Retell para que hablen en pesos y no corten a quien habla.

Uso:
  python -m admin.agentes ajustar            muestra que cambiaria (no cambia nada)
  python -m admin.agentes ajustar --aplicar  lo aplica a los agentes de .env (RETELL_AGENT_ID, _FABRICANTE, _AGENDA)
Nunca imprime llaves. Es idempotente: se puede correr varias veces.
"""
import argparse
import httpx
from app.config import get_settings

API = "https://api.retellai.com"
MARCA = "## REGLAS DE VOZ (NidoGuard)"
REGLAS = f"""

{MARCA}
- Todos los precios son en PESOS MEXICANOS. Di las cantidades completas en español: "setecientos pesos", "mil doscientos pesos". Nunca digas "dólares", "USD" ni leas el signo $ en inglés. Si la otra persona da un monto sin moneda, confirma: "¿Son pesos mexicanos?".
- Deja hablar. Una pausa corta no significa que la otra persona terminó: espera al menos 3 segundos de silencio antes de responder. Nunca interrumpas ni completes sus frases.
- Si la otra persona está pensando o buscando un dato, no llenes el silencio. Si pasan más de 8 segundos, di una sola vez: "Sin prisa, aquí sigo."
- Haz una pregunta a la vez y espera la respuesta completa.
- No uses muletillas ("ajá", "mjm") mientras la otra persona habla.
"""
AJUSTES = {
    "responsiveness": 0.3,            # espera mas antes de contestar (0 a 1; menos = mas paciente)
    "interruption_sensitivity": 1,    # si la persona habla encima, el agente se calla
    "enable_backchannel": False,      # sin "ajá" mientras habla
    "reminder_trigger_ms": 15000,     # no lo "despierta" antes de 15 s de silencio
    "reminder_max_count": 1,
}


def main():
    ap = argparse.ArgumentParser(); ap.add_argument("cmd", choices=["ajustar"]); ap.add_argument("--aplicar", action="store_true")
    a = ap.parse_args()
    s = get_settings()
    if not s.retell_api_key:
        raise SystemExit("Falta RETELL_API_KEY en el .env.")
    ids = {x for x in (s.retell_agent_id, s.retell_agent_id_fabricante, s.retell_agent_id_agenda) if x}
    if not ids:
        raise SystemExit("No hay ningún RETELL_AGENT_ID en el .env.")
    h = {"Authorization": f"Bearer {s.retell_api_key}"}
    for aid in sorted(ids):
        ag = httpx.get(f"{API}/get-agent/{aid}", headers=h, timeout=20); ag.raise_for_status(); ag = ag.json()
        eng = ag.get("response_engine") or {}
        print(f"Agente {aid[:8]}…: motor={eng.get('type')} idioma={ag.get('language')} | ahora: " +
              ", ".join(f"{k}={ag.get(k)}" for k in AJUSTES) + " | luego: " + ", ".join(f"{k}={v}" for k, v in AJUSTES.items()))
        llm_id = eng.get("llm_id") if eng.get("type") == "retell-llm" else None
        prompt = None
        if llm_id:
            l = httpx.get(f"{API}/get-retell-llm/{llm_id}", headers=h, timeout=20); l.raise_for_status(); prompt = l.json().get("general_prompt") or ""
            print(f"  prompt: {'ya trae las reglas de voz' if MARCA in prompt else 'se agregarán las reglas de voz (pesos y paciencia)'}")
        else:
            print("  Este agente no usa Retell LLM: agrega las reglas de voz a mano (están en admin/agentes.py).")
        if not a.aplicar:
            continue
        httpx.patch(f"{API}/update-agent/{aid}", json=AJUSTES, headers=h, timeout=20).raise_for_status()
        if llm_id and MARCA not in (prompt or ""):
            httpx.patch(f"{API}/update-retell-llm/{llm_id}", json={"general_prompt": (prompt or "") + REGLAS}, headers=h, timeout=20).raise_for_status()
        print("  aplicado.")
    if not a.aplicar:
        print("\nNo cambié nada. Corre con --aplicar para aplicarlo.")


if __name__ == "__main__":
    main()
