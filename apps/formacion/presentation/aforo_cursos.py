"""Aforo de varios grupos para listados públicos, sin caché persistente.

Las altas y pagos siguen usando cupos_disponibles dentro de sus transacciones.
Este resumen evita dos consultas por grupo al presentar la oferta vinculada.
"""
from django.db.models import Count, Q


def cupos_por_edicion(ediciones):
    from apps.formacion.models.cursos import InscripcionCurso
    from apps.formacion.models.cursos_inscripcion import InvitacionCurso

    ediciones = list(ediciones)
    resultado = {edicion.pk: None for edicion in ediciones}
    limitadas = {edicion.pk: edicion.cupo for edicion in ediciones if edicion.cupo is not None}
    if not limitadas:
        return resultado
    aceptadas = dict(InscripcionCurso.objects.filter(edicion_id__in=limitadas, estado='aceptada')
                     .order_by().values('edicion_id').annotate(total=Count('pk')).values_list('edicion_id', 'total'))
    reservadas = dict(InvitacionCurso.objects.filter(edicion_id__in=limitadas, activa=True).filter(
        Q(inscripcion__isnull=True) | Q(inscripcion__estado='pendiente', exonerar_matricula=False))
        .order_by().values('edicion_id').annotate(total=Count('pk')).values_list('edicion_id', 'total'))
    resultado.update({clave: max(cupo - aceptadas.get(clave, 0) - reservadas.get(clave, 0), 0)
                      for clave, cupo in limitadas.items()})
    return resultado
