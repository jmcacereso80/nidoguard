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
MARCA_FALLO = "## CÓMO PRESENTAR EL FALLO (NidoGuard)"
MARCA_TIPO = "## TIPO DE LLAMADA (NidoGuard)"
FIN_TIPO = "## FIN TIPO DE LLAMADA"
TIPO = f"""{MARCA_TIPO}
Esta llamada es de tipo: {{{{tipo}}}}. Lo que dice este bloque manda sobre el resto del guion.
- cotizar: sigue el guion de cotización de abajo.
- agendar, recordatorio o cancelar: NO es una cotización. NUNCA pidas precio, ni preguntes qué incluye, ni vuelvas a cotizar: el precio ({{{{precio}}}}) y la franja ({{{{franja_elegida}}}}) ya están acordados. Sigue solo las "REGLAS DE LA CITA" de más abajo y empieza diciendo para qué llamas (confirmar la visita, recordarla o avisar de la cancelación).
- fabricante: sigue solo lo que diga el guion del centro de atención.
{FIN_TIPO}

"""
REGLAS = f"""

{MARCA}
- Todos los precios son en PESOS MEXICANOS, siempre. Di las cantidades completas en español: "setecientos pesos", "mil doscientos pesos". Nunca digas "dólares", "USD" ni leas el signo $ en inglés. NUNCA preguntes la moneda ni "¿son pesos mexicanos?": si la otra persona da un monto sin decir la moneda, son pesos mexicanos y sigues adelante.
- Deja hablar. Una pausa corta no significa que la otra persona terminó: espera unos 1.5 segundos de silencio antes de responder. Nunca interrumpas ni completes sus frases.
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
REGLAS_FALLO = """

## CÓMO PRESENTAR EL FALLO (NidoGuard)
- El fallo lo REPORTA EL CLIENTE; tú no lo diagnosticas. OBLIGATORIO: nunca digas el fallo como hecho ni como frase directa. Cada vez que lo menciones empieza con "el cliente reporta que". Orden: equipo, luego "el cliente reporta que" y el fallo, y al final qué se necesita.
  Ejemplo: "Es un refrigerador Samsung. El cliente reporta que no enfría, pero la luz interior sí enciende. Necesita que lo revisen y le digan qué tiene."
- Usa las palabras del cliente: {{sintoma}}. Si es largo, di solo lo esencial en una o dos frases. No agregues causas ni piezas que el cliente no dijo.
- Después de decir el fallo, haz una pausa y pregunta: "¿Me explico bien o se lo repito?". Si pide que lo repitas, dilo más lento y con otras palabras sencillas, sin cambiar los hechos.
- Si te pregunta algo del fallo que no sabes (desde cuándo, si hizo ruido, si hay golpes de luz), dile que solo tienes lo que el cliente reportó y que lo ve el técnico en la visita. NUNCA lo inventes.
- Si no hay {{sintoma}}, di solo el trabajo que se pide ({{trabajo}}) y no menciones ningún fallo.
"""
REGLAS_AGENDA = """

## REGLAS DE LA CITA (NidoGuard)
Aplican SOLO cuando {{tipo}} es agendar, recordatorio o cancelar. Si es cotizar, ignora todo este bloque.
- La visita YA está acordada: el técnico dio esa disponibilidad al cotizar y el cliente la eligió. NO preguntes si puede ir. Di algo como: "Le llamo para dejar confirmada la visita que usted ofreció, {{franja_elegida}}, por {{precio}}."
- Pide solo la hora aproximada de llegada y el nombre de la persona que irá.
- ORDEN OBLIGATORIO para la cita, paso por paso, sin saltarte ninguno:
  Paso 1: confirma la visita y pide la hora aproximada y el nombre de quien irá. Espera la respuesta.
  Paso 2: pregunta EXACTAMENTE "¿Tiene dónde anotar o lo espero?" y NO digas nada más. Espera la respuesta.
  Paso 3: si dice que sí, espera en silencio hasta que diga que está listo. Si dice que no, di "Sin prisa, aquí lo espero" y vuelve a preguntar cuando regrese.
  Paso 4: solo entonces dicta la dirección. PROHIBIDO dar la dirección antes del paso 3.
- Ya que esté listo, dicta DESPACIO, en partes cortas y haciendo una pausa breve entre cada una: calle y número, colonia, ciudad y referencias. Dicta ({{direccion}}), el nombre de pila del cliente ({{nombre}}) y, si hay {{telefono_cliente}}, ese teléfono dígito por dígito, en grupos de tres o cuatro. Deletrea nombres de calle poco comunes si te lo piden.
- Al terminar pregunta: "¿Se lo repito o lo anotó completo?". Pídele que repita la dirección para asegurarte de que la tiene bien. Si algo le falta, repítelo sin molestarte.
- Si pregunta por el fallo del equipo: es lo que el cliente reportó ({{sintoma}}); preséntalo como "el cliente reporta que…" y no lo inventes.
- Si hay {{acceso}}, díselo tal cual (cómo se entra, qué identificación llevar). Si hay {{telefono_cliente}}, dile que puede hablar o escribir directo al cliente a ese número para coordinar el acceso o avisar al llegar. Si no hay teléfono, dile que NidoGuard le avisa al cliente.
- Solo si dice que ya no puede, pide otra fecha y hora concretas.
- Cierra diciendo que le avisas al cliente quién va y a qué hora.

## AVISO DE CANCELACIÓN (cuando {{tipo}} es cancelar)
- Esta llamada NO es para confirmar nada. Dile, con amabilidad y en una o dos frases, que el cliente canceló la visita de {{franja_elegida}} y que ya no es necesario que vaya. Ofrece una disculpa por la molestia y agradece su tiempo.
- NO des dirección, nombre ni teléfono del cliente. NO ofrezcas reagendar. Si pregunta el motivo, di que el cliente decidió cancelar. Despídete.
"""
AJUSTES = {
    "responsiveness": 0.45,           # espera antes de contestar (0 a 1; menos = mas paciente). ~1.5 s de pausa corta (era 3 s con 0.3)
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
    if not s.retell_agent_id_agenda or s.retell_agent_id_agenda == s.retell_agent_id:
        print("AVISO: RETELL_AGENT_ID_AGENDA está vacío o es el mismo que el cotizador. Las llamadas de confirmación, recordatorio y cancelación "
              "usan el agente cotizador (su saludo y su guion piden cotizar). Duplica el agente en Retell, ponle un saludo de cita y pon su id en RETELL_AGENT_ID_AGENDA.\n")
    for aid in sorted(ids):
        ag = httpx.get(f"{API}/get-agent/{aid}", headers=h, timeout=20); ag.raise_for_status(); ag = ag.json()
        eng = ag.get("response_engine") or {}
        print(f"Agente {aid[:8]}…: motor={eng.get('type')} idioma={ag.get('language')} | ahora: " +
              ", ".join(f"{k}={ag.get(k)}" for k in AJUSTES) + " | luego: " + ", ".join(f"{k}={v}" for k, v in AJUSTES.items()))
        llm_id = eng.get("llm_id") if eng.get("type") == "retell-llm" else None
        prompt = None
        if llm_id:
            l = httpx.get(f"{API}/get-retell-llm/{llm_id}", headers=h, timeout=20); l.raise_for_status(); prompt = l.json().get("general_prompt") or ""
            print(f"  prompt: se pondrán las reglas de voz (pesos y paciencia){' y las de la cita' if aid != s.retell_agent_id_fabricante else ''}")
        else:
            print("  Este agente no usa Retell LLM: agrega las reglas de voz a mano (están en admin/agentes.py).")
        if not a.aplicar:
            continue
        httpx.patch(f"{API}/update-agent/{aid}", json=AJUSTES, headers=h, timeout=20).raise_for_status()
        if llm_id:
            prompt = orig = prompt or ""
            if prompt.startswith(MARCA_TIPO) and FIN_TIPO in prompt:
                prompt = prompt.split(FIN_TIPO, 1)[1].lstrip()  # quita el bloque de tipo anterior (va siempre al inicio)
            base = (prompt or "").split(MARCA)[0].split(MARCA_CITA)[0].split(MARCA_EQUIPO)[0].split(MARCA_FALLO)[0].rstrip()  # quita nuestros bloques anteriores y los vuelve a poner (asi se pueden actualizar)
            nuevo = (TIPO if aid != s.retell_agent_id_fabricante else "") + base + REGLAS + (REGLAS_EQUIPO if aid != s.retell_agent_id_fabricante else "") + REGLAS_FALLO + (REGLAS_AGENDA if aid != s.retell_agent_id_fabricante else "")
            if nuevo != orig:
                httpx.patch(f"{API}/update-retell-llm/{llm_id}", json={"general_prompt": nuevo}, headers=h, timeout=20).raise_for_status()
        print("  aplicado.")
    if not a.aplicar:
        print("\nNo cambié nada. Corre con --aplicar para aplicarlo.")


if __name__ == "__main__":
    main()
