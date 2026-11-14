"""Ayuda visual de una meta conservada, sin modificar la medición ni sus huellas."""
from django import template

register = template.Library()


@register.simple_tag
def ficha_meta_conservada(indicador):
    if not isinstance(indicador, dict):
        return None
    from apps.documentos.presentation.expediente_redaccion import ACTIVIDADES_PLAN
    from apps.documentos.presentation.politica_metas_unidades import ficha_indicador

    codigo = indicador.get('codigo', '')
    actividad = next((a for a in ACTIVIDADES_PLAN if a.codigo == codigo), None)
    original = ficha_indicador(actividad) if actividad else {}
    calculo = original.get('formula', 'Resultados válidos y respaldados ÷ meta conservada × 100, hasta 100 %.')
    if codigo == 'USO-EFECTIVO':
        calculo = 'Horas de uso efectivo acreditadas ÷ horas comprometidas del mismo tramo × 100, hasta 100 %.'
    pares = [('Origen', 'Compromiso conservado en la planificación y leído para este cierre.'),
        ('Indicador', indicador.get('indicador') or indicador.get('nombre') or codigo),
        ('Meta conservada', indicador.get('meta') or 'Sin meta independiente'),
        ('Exigencia', indicador.get('exigencia') or 'Según la planificación'),
        ('Cálculo', calculo),
        ('Respaldo', original.get('evidencia', 'Evidencia verificable del resultado y su período.')),
        ('Cambios', 'La referencia general orienta nuevas propuestas; no sustituye ni reduce esta meta ya conservada.')]
    if indicador.get('denominador') is not None:
        pares.append(('Universo observado', indicador['denominador']))
    return dict(titulo='Origen y cálculo · ' + str(indicador.get('indicador') or codigo), pares=pares)
