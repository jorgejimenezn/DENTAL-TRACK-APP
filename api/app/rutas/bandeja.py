"""Bandeja de trabajo por área y acciones sobre el paso en que va cada caso.

- Producción: el sistema asigna cada paso a un técnico (área + tipo de trabajo, menor carga, respeta su tope).
  El técnico trabaja uno a la vez: inicia el que el sistema le entrega por prioridad y lo termina.
- Ingresos: aprobar (entra a producción), modificar (corrige el trabajo) o cancelar.
- QA: validar reaperturas (clasificación y motivo) y control de calidad (aprobar o devolver a un paso).
- Facturación: registrar el número de factura.
- Logística: asigna cada recolecta o entrega a un mensajero (o la marca hecha directamente).
- Mensajero: ve sus rutas y marca hecho (al entregar, nombre de quien recibe) o "no se pudo" con motivo.
- Admin y supervisor ven el resumen de todas las áreas y el detalle de una con ?area_id=; reasignan
  trabajos de producción a cualquier empleado.
"""
from fastapi import APIRouter, Depends, Response

from app.backend import llamar
from app.esquemas import AsignarIn, CancelarPasoIn, ModificacionIn, RechazoIn, TerminarIn, ValidacionRpIn
from app.seguridad import usuario_actual

router = APIRouter(tags=["Bandeja"])


@router.get("/bandeja", summary="Mi bandeja: producción asignada y pasos de mis áreas")
async def bandeja(area_id: int | None = None, u: dict = Depends(usuario_actual)):
    return await llamar("GET", "/bandeja", u, params={"area_id": area_id})


@router.post("/pasos/{paso_id}/iniciar", status_code=204, summary="Técnico: iniciar el siguiente trabajo")
async def iniciar(paso_id: int, u: dict = Depends(usuario_actual)):
    await llamar("POST", f"/pasos/{paso_id}/iniciar", u)
    return Response(status_code=204)


@router.post("/pasos/{paso_id}/terminar", status_code=204,
             summary="Terminar el paso (técnico, Ingresos aprueba, QA aprueba, Facturación, Logística)")
async def terminar(paso_id: int, datos: TerminarIn, u: dict = Depends(usuario_actual)):
    await llamar("POST", f"/pasos/{paso_id}/terminar", u, json=datos.model_dump())
    return Response(status_code=204)


@router.post("/pasos/{paso_id}/validar-rp", status_code=204, summary="QA: clasificar una reapertura")
async def validar_rp(paso_id: int, datos: ValidacionRpIn, u: dict = Depends(usuario_actual)):
    await llamar("POST", f"/pasos/{paso_id}/validar-rp", u, json=datos.model_dump())
    return Response(status_code=204)


@router.post("/pasos/{paso_id}/rechazar", status_code=204, summary="QA: devolver el caso a un paso de producción")
async def rechazar(paso_id: int, datos: RechazoIn, u: dict = Depends(usuario_actual)):
    await llamar("POST", f"/pasos/{paso_id}/rechazar", u, json=datos.model_dump())
    return Response(status_code=204)


@router.put("/pasos/{paso_id}/modificar", status_code=204, summary="Ingresos: corregir el trabajo antes de aprobar")
async def modificar(paso_id: int, datos: ModificacionIn, u: dict = Depends(usuario_actual)):
    await llamar("PUT", f"/pasos/{paso_id}/modificar", u, json=datos.model_dump(mode="json"))
    return Response(status_code=204)


@router.post("/pasos/{paso_id}/cancelar", status_code=204, summary="Ingresos: cancelar el caso")
async def cancelar(paso_id: int, datos: CancelarPasoIn, u: dict = Depends(usuario_actual)):
    await llamar("POST", f"/pasos/{paso_id}/cancelar", u, json=datos.model_dump())
    return Response(status_code=204)


@router.get("/pasos/{paso_id}/candidatos", summary="A quién se puede asignar el paso (mensajeros o empleados)")
async def candidatos(paso_id: int, u: dict = Depends(usuario_actual)):
    return await llamar("GET", f"/pasos/{paso_id}/candidatos", u)


@router.post("/pasos/{paso_id}/asignar", status_code=204,
             summary="Logística: asignar mensajero · Supervisor: reasignar trabajo de producción")
async def asignar(paso_id: int, datos: AsignarIn, u: dict = Depends(usuario_actual)):
    await llamar("POST", f"/pasos/{paso_id}/asignar", u, json=datos.model_dump())
    return Response(status_code=204)


@router.post("/pasos/{paso_id}/no-se-pudo", status_code=204,
             summary="Mensajero: recolecta o entrega no realizada (regresa a Logística)")
async def no_se_pudo(paso_id: int, datos: CancelarPasoIn, u: dict = Depends(usuario_actual)):
    await llamar("POST", f"/pasos/{paso_id}/no-se-pudo", u, json=datos.model_dump())
    return Response(status_code=204)
