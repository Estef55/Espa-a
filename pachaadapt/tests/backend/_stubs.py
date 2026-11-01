"""Doble MÍNIMO de FastAPI/Pydantic, SOLO para pruebas, y solo cuando no están instalados.

Permite importar los routers y ejecutar sus funciones de ruta directamente. NO verifica el
comportamiento HTTP real (validación de cuerpos, códigos de respuesta, OpenAPI): eso requiere
FastAPI real (ver docs/integrante3/GUIA_EJECUCION.md). Con FastAPI real instalado no se usa.
"""
import sys
import types
from types import SimpleNamespace


def install() -> bool:
    try:
        import fastapi, pydantic  # noqa: F401
        return False
    except ImportError:
        pass

    class HTTPException(Exception):
        def __init__(self, status_code, detail=None):
            super().__init__(str(detail))
            self.status_code, self.detail = status_code, detail

    class APIRouter:
        def __init__(self, prefix="", tags=None):
            self.prefix, self.routes = prefix, []

        def _reg(self, method):
            def decorator(path, **kw):
                def wrap(fn):
                    self.routes.append(SimpleNamespace(path=self.prefix + path, methods={method}, endpoint=fn, kw=kw))
                    return fn
                return wrap
            return decorator

        def __getattr__(self, name):
            if name in ("get", "post", "put", "delete", "patch"):
                return self._reg(name.upper())
            raise AttributeError(name)

    class FastAPI(APIRouter):
        def __init__(self, title="", version=""):
            super().__init__()

        def include_router(self, router):
            self.routes.extend(router.routes)

    class BaseModel:
        model_config: dict = {}

        def __init__(self, **kw):
            names = set()
            for c in type(self).__mro__:
                names |= set(getattr(c, "__annotations__", {}))
            names.discard("model_config")
            unknown = set(kw) - names
            if unknown and self.model_config.get("extra") == "forbid":
                raise ValueError(f"extra fields: {unknown}")
            self._set = set(kw)
            for n in names:
                setattr(self, n, kw.get(n, getattr(type(self), n, None)))
            self._names = names

        def model_dump(self, exclude_unset=False, exclude_none=False):
            out = {n: getattr(self, n) for n in self._names}
            if exclude_unset:
                out = {k: v for k, v in out.items() if k in self._set}
            if exclude_none:
                out = {k: v for k, v in out.items() if v is not None}
            return out

    fa = types.ModuleType("fastapi")
    fa.APIRouter, fa.HTTPException, fa.Request, fa.FastAPI = APIRouter, HTTPException, object, FastAPI
    fa.Depends = lambda dep: ("DEPENDS", dep)
    resp = types.ModuleType("fastapi.responses")
    resp.PlainTextResponse = type("PlainTextResponse", (), {})
    pyd = types.ModuleType("pydantic")
    pyd.BaseModel, pyd.ConfigDict = BaseModel, dict
    sys.modules.update({"fastapi": fa, "fastapi.responses": resp, "pydantic": pyd})
    return True
