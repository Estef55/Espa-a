"""Errores propios del procesamiento y las adaptaciones (integrante 2).

``AdaptationUnavailable`` hereda de ``RuntimeError`` a propósito: la API ya traduce
``RuntimeError`` a HTTP 501 («esta capacidad no está disponible en el servidor»).
"""


class AdaptationUnavailable(RuntimeError):
    """La adaptación pedida no existe o falta un motor local para generarla."""


class ProcessingError(Exception):
    """Fallo inesperado al procesar un documento (no es culpa del usuario ni una capacidad ausente)."""


UNAVAILABLE_REASON = ("La traducción no está disponible: no hay un motor de traducción conectado y los textos en quechua "
                      "requieren validación con hablantes de la comunidad antes de usarse.")
