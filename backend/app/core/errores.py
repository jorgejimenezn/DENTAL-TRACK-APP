"""Errores de negocio: los servicios los lanzan y main.py los convierte en respuestas HTTP."""


class ErrorNegocio(Exception):
    def __init__(self, detalle: str, status: int = 400):
        self.detalle = detalle
        self.status = status
        super().__init__(detalle)


class NoEncontrado(ErrorNegocio):
    def __init__(self, detalle: str = "Registro no encontrado"):
        super().__init__(detalle, 404)


class Conflicto(ErrorNegocio):
    def __init__(self, detalle: str):
        super().__init__(detalle, 409)


class NoAutorizado(ErrorNegocio):
    def __init__(self, detalle: str = "Credenciales inválidas"):
        super().__init__(detalle, 401)
