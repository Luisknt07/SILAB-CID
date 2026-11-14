"""Exporta el resultado real del motor de ensayo a una consulta de sólo lectura."""
import hashlib
import json
from datetime import date, timedelta
from pathlib import Path
from uuid import uuid4

from django.conf import settings
from django.core.management.base import CommandError

from apps.documentos.presentation.escenario_ideal_base import exigir_entorno_ideal


def directorio_escenario(slug, anio, corte):
    return Path(settings.BASE_DIR) / 'var/escenarios_ideales' / slug / f'{anio}-{corte}'


def _marcar_copia(datos):
    from io import BytesIO

    from pypdf import PdfReader, PdfWriter
    from pypdf.generic import ArrayObject, NameObject
    from reportlab.pdfgen.canvas import Canvas

    documento = PdfWriter(clone_from=PdfReader(BytesIO(datos)))
    for pagina in documento.pages:
        # Los identificadores de la base aislada no pertenecen al portal
        # operativo. La copia de consulta conserva el texto de los respaldos
        # pero no permite abrir rutas de otra base con esos identificadores.
        if '/Annots' in pagina:
            anotaciones = [ref for ref in pagina['/Annots']
                           if ref.get_object().get('/Subtype') != '/Link']
            if anotaciones:
                pagina[NameObject('/Annots')] = ArrayObject(anotaciones)
            else:
                del pagina['/Annots']
        pagina.transfer_rotation_to_content()
        caja = pagina.cropbox
        marca = BytesIO()
        lienzo = Canvas(marca, pagesize=(float(caja.width), float(caja.height)), invariant=1)
        lienzo.setFillColorRGB(0.65, 0.15, 0.12)
        lienzo.setFont('Helvetica', 7)
        lienzo.drawString(15, float(caja.height) - 15,
            'PRUEBA INTEGRAL - DATOS SINTETICOS - SIN VALIDEZ INSTITUCIONAL')
        lienzo.save()
        pagina.merge_translated_page(PdfReader(marca).pages[0],
            float(caja.left), float(caja.bottom))
    salida = BytesIO()
    documento.write(salida)
    return salida.getvalue()


def exportar_escenario(unidad, referencia, documentos, actores):
    exigir_entorno_ideal()
    from apps.documentos.models.expediente import DocumentoExpediente
    from apps.documentos.presentation.automatizacion_documental import completar_controles, procesar_documento
    from apps.documentos.presentation.calidad_automatica_laboratorios import ContextoCalidad
    from apps.documentos.presentation.evaluacion_cierre import lectura_cierre
    from apps.documentos.presentation.expediente import _generar, cortes_del_anio, leer_expediente, del_periodo
    from apps.documentos.presentation.progreso_general import progreso_general
    anio, corte = referencia['anio'], referencia['corte']
    inicio, fin = date.fromisoformat(referencia['inicio']), date.fromisoformat(referencia['fin'])
    documentos = del_periodo(leer_expediente(unidad, anio), corte, cortes_del_anio(anio))
    informe = next(d for d in documentos if d.exigido.codigo == 'INFORME-SEMESTRAL')
    lectura = lectura_cierre(informe)
    contexto = ContextoCalidad(unidad, inicio, fin)
    diagnostico = {d.exigido.codigo: contexto.analizar(d.exigido.codigo) for d in documentos if d.exigido.es_anexo}
    progreso = progreso_general(documentos)
    salida_diagnostico = Path(settings.MEDIA_ROOT).parent / 'diagnostico.json'
    salida_diagnostico.write_text(json.dumps(dict(progreso=progreso['porcentaje'],
        nota=informe.nota, lectura=lectura, calidad=diagnostico,
        controles={d.exigido.codigo: d.automatizacion for d in documentos}),
        default=str, ensure_ascii=False, indent=2), encoding='utf8')
    pendientes = [f for f in lectura['filas'] if f.get('exigible') and
                  (f.get('pendiente') or not f.get('definida') or f.get('porcentaje') != 100)]
    if pendientes or informe.nota != 100 or progreso['porcentaje'] != 100:
        reglas = sorted({h['regla'] for r in diagnostico.values() for h in r['hallazgos']})
        raise CommandError('El motor no confirmó el escenario completo. Metas: ' +
            ', '.join(f['codigo'] for f in pendientes) + '; reglas: ' + ', '.join(reglas) +
            f'; nota cierre={informe.nota}; general={progreso["porcentaje"]}. Consulta diagnostico.json.')
    # El plan de mantenimiento es anual y acompaña al período A. También se
    # incluye en la consulta integral, sin duplicar el peso de las cinco entregas.
    mantenimiento = DocumentoExpediente.objects.select_related('unidad', 'exigido', 'recurso').get(
        unidad=unidad, anio=anio, exigido__codigo='PLAN-MANTENIMIENTO')
    if not mantenimiento.recurso_id:
        _generar(mantenimiento, actores['coordinacion'])
        procesar_documento(mantenimiento, usuario=actores['coordinacion'])
    documentos = [*documentos, mantenimiento]
    completar_controles(documentos)
    incidencias = [d.exigido.codigo for d in documentos if d.exigido.es_anexo and
                   d.automatizacion.get('hallazgos')]
    if incidencias:
        raise CommandError('El ensayo conserva incidencias en anexos: ' + ', '.join(incidencias))
    orden = {codigo: numero for numero, codigo in enumerate((
        'RESOLUCION-CREACION', 'PROTOCOLO-BIOSEGURIDAD', 'PLANIFICACION',
        'INDICADORES-PLAN', 'PLAN-MANTENIMIENTO', 'PLAN-COMPRAS-ANUAL', 'INFORME-SEMESTRAL'))}
    documentos.sort(key=lambda d: (orden.get(d.exigido.codigo, len(orden)), d.exigido.orden, d.pk))
    destino = directorio_escenario(referencia['unidad']['slug'], anio, corte)
    generacion = uuid4().hex
    archivos = destino / generacion
    archivos.mkdir(parents=True)
    filas = []
    for numero, documento in enumerate(documentos, 1):
        if not documento.recurso_id:
            raise CommandError('Falta el PDF de ' + documento.exigido.codigo)
        with documento.recurso.archivo.open('rb') as archivo:
            original = archivo.read()
        copia = _marcar_copia(original)
        nombre = documento.exigido.codigo + '.pdf'
        (archivos / nombre).write_bytes(copia)
        control = documento.automatizacion
        filas.append(dict(numero=numero, codigo=documento.exigido.codigo, nombre=documento.nombre_documental,
            anexo=documento.exigido.es_anexo, estado=documento.estado,
            resultado=str(documento.nota) if documento.nota is not None else None,
            fuente='Dirección de prueba' if documento.evaluado_por_id else 'Sistema',
            control=control['label'], hallazgos=control.get('hallazgos', []),
            archivo=generacion + '/' + nombre, sha256=hashlib.sha256(copia).hexdigest(),
            original_sha256=hashlib.sha256(original).hexdigest()))
    from apps.formacion.models.practicas import EjecucionPractica, PlanificacionPractica
    from apps.reservas.models.reservas import Reserva, GuiaActividadReserva
    resumen_datos = dict(practicas_planificadas=PlanificacionPractica.objects.filter(unidad=unidad).count(),
        practicas_ejecutadas=EjecucionPractica.objects.filter(planificacion__unidad=unidad).count(),
        guias=GuiaActividadReserva.objects.filter(actividad__unidad=unidad).count(),
        sesiones=Reserva.objects.filter(laboratorio=unidad, estado='completada').count(),
        estudiantes=len(actores['estudiantes']), horas=12,
        equipos=unidad.unidades_equipo_principal.count())
    manifiesto = dict(version=1, es_prueba=True, unidad=referencia['unidad'], anio=anio, corte=corte,
        inicio=inicio.isoformat(), fin=fin.isoformat(), corte_simulado=(fin + timedelta(days=1)).isoformat(),
        general=str(progreso['porcentaje']), nota_cierre=str(informe.nota), resumen=resumen_datos,
        indicadores=[{k: f.get(k) for k in ('codigo', 'nombre', 'indicador', 'meta', 'registrado',
            'porcentaje', 'exigible', 'estado', 'motivo')} for f in lectura['filas']], documentos=filas)
    temporal = destino / 'manifiesto.tmp'
    temporal.write_text(json.dumps(manifiesto, default=str, ensure_ascii=False, indent=2), encoding='utf8')
    temporal.replace(destino / 'manifiesto.json')
    return destino / 'manifiesto.json'
