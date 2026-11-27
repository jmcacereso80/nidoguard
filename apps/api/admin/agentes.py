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
MARCA_CITA = "## REGLAS DE LA CITA (NidoGuard)"
MARCA_EQUIPO = "## DATOS DEL EQUIPO (NidoGuard)"
REGLAS = f"""

{MARCA}
- Todos los precios son en PESOS MEXICANOS. Di las cantidades completas en español: "setecientos pesos", "mil doscientos pesos". Nunca digas "dólares", "USD" ni leas el signo $ en inglés. Si la otra persona da un monto sin moneda, confirma: "¿Son pesos mexicanos?".
- Deja hablar. Una pausa corta no significa que la otra persona terminó: espera unos 2 segundos de silencio antes de responder. Nunca interrumpas ni completes sus frases.
- Si la otra persona está pensando o buscando un dato, no llenes el silencio. Si pasan más de 6 segundos, di una sola vez: "Sin prisa, aquí sigo."
- Haz una pregunta a la vez y espera la respuesta completa.
- No uses muletillas ("ajá", "mjm") mientras la otra persona habla.
"""
REGLAS_EQUIPO = """

## DATOS DEL EQUIPO (NidoGuard)
- El equipo es {{equipo}}. Marca: {{marca}}. Modelo: {{modelo}}.
- Si el técnico pregunta por la marca o el modelo, díselos tal cual. Si dicen "sin dato", dile que no los tienes y que los puede ver en la placa del equipo durante la visita. NUNCA inventes una marca, un modelo ni un número de serie.
- Si pregunta algo más del equipo que no tengas (año, número de serie, si tiene garantía), dile que no lo tienes a la mano; no lo supongas.
"""
REGLAS_AGENDA = """

## REGLAS DE LA CITA (NidoGuard)
- La visita YA está acordada: el técnico dio esa disponibilidad al cotizar y el cliente la eligió. NO preguntes si puede ir. Di algo como: "Le llamo para dejar confirmada la visita que usted ofreció, {{franja_elegida}}, por {{precio}}."
- Pide solo la hora aproximada de llegada y el nombre de la persona que irá.
- En cuanto lo confirme, dale la dirección completa ({{direccion}}) y el nombre de pila del cliente ({{nombre}}). Si hay {{telefono_cliente}}, también ese teléfono. Pídele que repita la dirección para asegurarte.
- Si hay {{acceso}}, díselo tal cual (cómo se entra, qué identificación llevar). Si hay {{telefono_cliente}}, dile que puede hablar o escribir directo al cliente a ese número para coordinar el acceso o avisar al llegar. Si no hay teléfono, dile que NidoGuard le avisa al cliente.
- Solo si dice que ya no puede, pide otra fecha y hora concretas.
- Cierra diciendo que le avisas al cliente quién va y a qué hora.
"""
AJUSTES = {
    "responsiveness": 0.4,            # espera antes de contestar (0 a 1; menos = mas paciente). 30% mas rapido que 0.3
    "interruption_sensitivity": 1,    # si la persona habla encima, el agente se calla
    "enable_backchannel": False,      # sin "ajá" mientras habla
    "reminder_trigger_ms": 10500,     # no lo "despierta" antes de ~10 s de silencio (30% menos que 15 s)
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
            print(f"  prompt: se pondrán las reglas de voz (pesos y paciencia){' y las de la cita' if aid == s.retell_agent_id_agenda and aid != s.retell_agent_id else ''}")
        else:
            print("  Este agente no usa Retell LLM: agrega las reglas de voz a mano (están en admin/agentes.py).")
        if not a.aplicar:
            continue
        httpx.patch(f"{API}/update-agent/{aid}", json=AJUSTES, headers=h, timeout=20).raise_for_status()
        if llm_id:
            base = (prompt or "").split(MARCA)[0].split(MARCA_CITA)[0].split(MARCA_EQUIPO)[0].rstrip()  # quita nuestros bloques anteriores y los vuelve a poner (asi se pueden actualizar)
            nuevo = base + REGLAS + (REGLAS_EQUIPO if aid != s.retell_agent_id_fabricante else "") + (REGLAS_AGENDA if aid == s.retell_agent_id_agenda and aid != s.retell_agent_id else "")
            if nuevo != (prompt or ""):
                httpx.patch(f"{API}/update-retell-llm/{llm_id}", json={"general_prompt": nuevo}, headers=h, timeout=20).raise_for_status()
        print("  aplicado.")
    if not a.aplicar:
        print("\nNo cambié nada. Corre con --aplicar para aplicarlo.")


if __name__ == "__main__":
    main()
