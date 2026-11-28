"""Como se atiende un equipo: un tecnico va a la casa ('domicilio') o se lleva a un centro de servicio ('llevar').
Por ahora es una lista en codigo por tipo de equipo; se mueve a una tabla cuando haya mas casos."""
from .manuales import norm

LLEVAR = {
    "licuadora", "batidora", "cafetera", "tostador", "plancha", "aspiradora", "secadora de pelo", "ventilador",
    "microondas", "horno de microondas", "freidora de aire", "olla de presion", "olla arrocera", "procesador de alimentos",
    "extractor de jugos", "licuadora de inmersion", "tostadora", "hervidor", "cafetera de capsulas", "robot aspirador",
}


def service_mode(category: str | None) -> str:
    """'llevar' para equipos chicos que se llevan a un centro de servicio; 'domicilio' para el resto (o si no se sabe)."""
    return "llevar" if category and norm(category) in {norm(x) for x in LLEVAR} else "domicilio"
