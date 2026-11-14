"""Distribución revisable de necesidades contra una referencia presupuestaria.

Cada escenario conserva su fuente y su cálculo. No adjudica compras ni consume
el presupuesto: permite comparar alternativas y justificar el reparto.
"""
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP, ROUND_HALF_EVEN
from io import BytesIO

from django.contrib.auth import get_user_model
from django.core.exceptions import PermissionDenied, ValidationError
from django.db import transaction
from django.utils import timezone

from apps.documentos.models.asignacion import MarcoPresupuestoNecesidades, EscenarioAsignacionNecesidades
from apps.documentos.models.necesidades import RemisionNecesidades, huella_contenido
from .necesidades_remision import contenido_remision, puede_leer_remision


def _numero(valor, etiqueta, *, maximo=Decimal('999999999999'), decimales=2):
    try:
        numero = Decimal(str(valor).strip().replace(',', '.'))
        if (not numero.is_finite() or numero < 0 or numero > maximo
                or numero != numero.quantize(Decimal(1).scaleb(-decimales))):
            raise InvalidOperation
        return numero
    except (InvalidOperation, ValueError, TypeError):
        raise ValidationError(f'{etiqueta}: introduce un valor no negativo con hasta {decimales} decimales.')


def _texto(valor):
    from html import unescape
    from django.utils.html import strip_tags
    return ' '.join(unescape(strip_tags(str(valor or ''))).split())


def _autoridad(usuario, dependencia):
    vigente = get_user_model().objects.filter(pk=getattr(usuario, 'pk', None), is_active=True, is_staff=True).first()
    if not (vigente and dependencia.activa and (vigente.is_superuser or dependencia.receptores.filter(pk=vigente.pk).exists())):
        raise PermissionDenied('La referencia corresponde a Dirección o a los receptores activos de esta dependencia.')
    return vigente


def _dependencia_bloqueada(dependencia):
    """Recarga permisos y serializa cambios de referencia en la dependencia."""
    from apps.directorio_unidades.models.core import DependenciaAcademica
    try:
        return DependenciaAcademica.objects.select_for_update().get(pk=getattr(dependencia, 'pk', dependencia))
    except (DependenciaAcademica.DoesNotExist, ValueError, TypeError, OverflowError):
        raise ValidationError('Selecciona una dependencia vigente.') from None


def verificar_captura(registro):
    if registro.sha256 != huella_contenido(registro.contenido):
        raise ValidationError('El antecedente no supera la verificación de integridad.')
    return registro.contenido


def presupuesto_actual(dependencia, ejercicio):
    registro = MarcoPresupuestoNecesidades.objects.filter(dependencia=dependencia, anio_ejecucion=ejercicio).first()
    if registro:
        verificar_captura(registro)
    return registro


@transaction.atomic
def registrar_presupuesto(dependencia, ejercicio, usuario, *, disponible, referencia, concentracion=None):
    dependencia = _dependencia_bloqueada(dependencia)
    usuario = _autoridad(usuario, dependencia)
    if type(ejercicio) is not int or not 2021 <= ejercicio <= 2100:
        raise ValidationError('Selecciona un año de compras válido.')
    importe = _numero(disponible, 'Presupuesto disponible')
    referencia = _texto(referencia)
    if not referencia:
        raise ValidationError('Identifica la aprobación o fuente del presupuesto disponible.')
    tope = None if concentracion in (None, '') else _numero(concentracion, 'Máximo por unidad', maximo=Decimal('100'))
    if tope == 0:
        raise ValidationError('El máximo por unidad debe ser mayor que cero o quedar sin definir.')
    contenido = dict(version=1, dependencia=dependencia.pk, dependencia_nombre=dependencia.nombre,
        centro_costo=dependencia.centro_costo, ejercicio=ejercicio, disponible=str(importe),
        referencia=referencia, porcentaje_maximo_unidad=str(tope) if tope is not None else None)
    ultimo = presupuesto_actual(dependencia, ejercicio)
    if ultimo and ultimo.sha256 == huella_contenido(contenido):
        return ultimo
    return MarcoPresupuestoNecesidades.objects.create(dependencia=dependencia, anio_ejecucion=ejercicio,
        registrado_por=usuario, contenido=contenido, sha256=huella_contenido(contenido))


def comparar_demanda(lectura, presupuesto):
    """Lectura sin cambios; la demanda nunca se presenta como asignación."""
    unidades = []
    for unidad in lectura.get('unidades', []):
        gestion = unidad.get('gestion_inversion') or {}
        unidades.append(dict(id=unidad['id'], nombre=unidad['nombre'], solicitado=unidad.get('total'),
            estado=gestion.get('estado', 'sin_evidencia'),
            criterio=gestion.get('label', 'Sin captura de cumplimiento comparable'),
            corte=gestion.get('fecha_referencia', ''), explicacion=gestion.get('explicacion', ''),
            pendiente=not unidad.get('transferible'), necesidades=unidad.get('necesidades', [])))
    marco = verificar_captura(presupuesto) if presupuesto else None
    demanda = lectura.get('resumen', {}).get('total')
    diferencia = None
    if marco and demanda is not None:
        diferencia = str(Decimal(marco['disponible']) - Decimal(demanda))
    return dict(unidades=unidades, presupuesto=marco, saldo_si_cubre_todo=diferencia)


def filas_escenario(lectura):
    return [dict(clave=f"{u['id']}:{n['numero']}", unidad_id=u['id'], unidad=u['nombre'], **n)
        for u in lectura.get('unidades', []) if u.get('transferible') for n in u.get('necesidades', [])]


def _revision_actual(unidad, ejercicio):
    """Revisión expresa adicional; no reemplaza la evidencia del envío."""
    from apps.documentos.models.expediente import DocumentoExpediente
    from .priorizacion_necesidades import lectura_gestion_inversion
    documento = DocumentoExpediente.objects.select_related('unidad', 'exigido', 'recurso').filter(
        pk=unidad.get('documento_id'), unidad_id=unidad['id'], anio=ejercicio - 1).first()
    contenido = unidad.get('pac_datos')
    if documento and isinstance(contenido, dict) and contenido.get('inversion_gestion_version') == 1:
        return lectura_gestion_inversion(documento, contenido, actual=True)
    return dict(estado='sin_evidencia', label='Sin revisión comparable; requiere verificación de Dirección',
                fecha_referencia=timezone.localdate().isoformat())


@transaction.atomic
def registrar_escenario(remision, presupuesto, usuario, cantidades, *, distribucion, excepcion=''):
    # El cliente elige IDs; las cifras y las fuentes siempre se recuperan del
    # antecedente archivado. Una instancia local modificada no lo reemplaza.
    try:
        remision = RemisionNecesidades.objects.select_related('dependencia').get(pk=remision.pk)
        dependencia = _dependencia_bloqueada(remision.dependencia_id)
        remision = RemisionNecesidades.objects.select_for_update().get(pk=remision.pk)
        presupuesto = MarcoPresupuestoNecesidades.objects.select_for_update().get(pk=presupuesto.pk)
    except (RemisionNecesidades.DoesNotExist, MarcoPresupuestoNecesidades.DoesNotExist,
            AttributeError, ValueError, TypeError, OverflowError):
        raise ValidationError('Selecciona una remisión y una referencia presupuestaria archivadas.') from None
    remision.dependencia = dependencia
    usuario = _autoridad(usuario, remision.dependencia)
    if not puede_leer_remision(usuario, remision):
        raise PermissionDenied('La copia remitida no está disponible para esta cuenta.')
    if (presupuesto.dependencia_id != remision.dependencia_id
            or presupuesto.anio_ejecucion != remision.anio_ejecucion):
        raise ValidationError('El presupuesto y la remisión deben corresponder a la misma dependencia y año.')
    # Evita construir nuevas alternativas contra una referencia ya sustituida.
    vigente = presupuesto_actual(remision.dependencia, remision.anio_ejecucion)
    if not vigente or vigente.pk != presupuesto.pk:
        raise ValidationError('Cambió la referencia presupuestaria. Recarga el informe antes de preparar el escenario.')
    marco = verificar_captura(presupuesto)
    lectura = contenido_remision(remision)
    if not isinstance(cantidades, dict):
        raise ValidationError('Revisa las cantidades del escenario.')
    filas = filas_escenario(lectura)
    claves = {f['clave'] for f in filas}
    if set(cantidades) - claves:
        raise ValidationError('Hay necesidades ajenas a la copia remitida.')
    seleccionadas, por_unidad = [], {}
    for fila in filas:
        cantidad = _numero(cantidades.get(fila['clave']) or '0', 'Cantidad propuesta', decimales=4)
        if not cantidad:
            continue
        solicitada = _numero(fila['cantidad'], 'Cantidad solicitada', decimales=4)
        if cantidad > solicitada:
            raise ValidationError(f"{fila['item']}: la propuesta no puede superar la cantidad solicitada.")
        costo = _numero(fila['costo_unitario'], 'Costo de la necesidad', decimales=4)
        total = (cantidad * costo).quantize(Decimal('0.01'), rounding=(
            ROUND_HALF_UP if fila.get('compras_resumen_version') == 1 else ROUND_HALF_EVEN))
        seleccionadas.append(dict(fila, cantidad_propuesta=str(cantidad), importe_propuesto=str(total)))
        por_unidad[fila['unidad_id']] = por_unidad.get(fila['unidad_id'], Decimal('0')) + total
    if not seleccionadas:
        raise ValidationError('Selecciona al menos una necesidad con cantidad positiva.')
    total = sum(por_unidad.values(), Decimal('0'))
    disponible = Decimal(marco['disponible'])
    if total > disponible:
        raise ValidationError('El total propuesto supera el presupuesto disponible. Ajusta cantidades o fases.')
    distribucion, excepcion = _texto(distribucion), _texto(excepcion)
    if not distribucion:
        raise ValidationError('Justifica cómo el reparto atiende a las unidades, sus fases y sus necesidades.')
    comparacion, advertencias = [], []
    tope = marco.get('porcentaje_maximo_unidad')
    for unidad in lectura['unidades']:
        revision = _revision_actual(unidad, remision.anio_ejecucion) if unidad.get('transferible') else {}
        importe = por_unidad.get(unidad['id'], Decimal('0'))
        porcentaje = importe * 100 / disponible if disponible else Decimal('0')
        participacion = importe * 100 / total if total else Decimal('0')
        if importe and revision.get('estado') != 'favorable':
            advertencias.append(f"{unidad['nombre']}: propuesta condicionada a revisión ({revision.get('label', 'pendiente')}).")
        if importe and tope is not None and porcentaje > Decimal(tope):
            advertencias.append(f"{unidad['nombre']}: supera el máximo institucional de {tope} % del presupuesto.")
        if not importe and unidad.get('necesidades') and revision.get('estado') == 'favorable':
            advertencias.append(f"{unidad['nombre']}: cumplimiento favorable con necesidades sin cobertura en este escenario.")
        comparacion.append(dict(id=unidad['id'], nombre=unidad['nombre'], solicitado=unidad.get('total'),
            propuesto=str(importe), porcentaje_presupuesto=str(porcentaje.quantize(Decimal('0.01'))),
            porcentaje_reparto=str(participacion.quantize(Decimal('0.01'))), revision_actual=revision,
            evidencia_envio=unidad.get('gestion_inversion'), pendiente=not unidad.get('transferible')))
    if advertencias and not excepcion:
        raise ValidationError('Justifica las condiciones de prioridad o concentración antes de archivar: ' + ' '.join(advertencias))
    contenido = dict(version=1, remision=remision.pk, remision_sha256=remision.sha256,
        presupuesto=presupuesto.pk, presupuesto_sha256=presupuesto.sha256, marco=marco,
        corte=timezone.localdate().isoformat(), filas=seleccionadas, unidades=comparacion,
        total=str(total), saldo=str(disponible - total), distribucion=distribucion,
        excepcion=excepcion, advertencias=advertencias,
        alcance='Escenario para revisión. No adjudica ni ejecuta compras y no reserva fondos.')
    return EscenarioAsignacionNecesidades.objects.create(remision=remision, presupuesto=presupuesto,
        registrado_por=usuario, contenido=contenido, sha256=huella_contenido(contenido))


def excel_escenario(escenario):
    from openpyxl import Workbook
    from openpyxl.styles import Font, PatternFill, Alignment
    contenido = verificar_captura(escenario)
    libro = Workbook()
    hoja = libro.active
    hoja.title = 'DISTRIBUCION'
    hoja.append(['Unidad', 'Solicitado USD', 'Propuesto USD', '% del presupuesto', '% del reparto', 'Revisión al corte'])
    for unidad in contenido['unidades']:
        hoja.append([unidad['nombre'], float(unidad['solicitado']) if unidad['solicitado'] is not None else 'Pendiente',
            float(unidad['propuesto']), float(unidad['porcentaje_presupuesto']), float(unidad['porcentaje_reparto']),
            unidad['revision_actual'].get('label', 'Pendiente')])
    hoja.append(['Total propuesto', '', float(contenido['total'])])
    hoja.append(['Saldo de referencia', '', float(contenido['saldo'])])
    hoja.append(['Justificación del reparto', contenido['distribucion']])
    hoja.append(['Condiciones y excepciones', contenido['excepcion']])
    hoja.append(['Alcance', contenido['alcance']])
    hoja.append(['Referencia presupuestaria', contenido['marco']['referencia']])
    hoja.append(['Remisión / SHA256', f"{escenario.remision_id} / {contenido['remision_sha256']}"])
    hoja.append(['Escenario / SHA256', f'{escenario.pk} / {escenario.sha256}'])
    compras = libro.create_sheet('NECESIDADES PROPUESTAS')
    compras.append(['Unidad', 'Área', 'Necesidad', 'Cantidad solicitada', 'Cantidad propuesta', 'Costo unitario',
                    'Total propuesto', 'Mes', 'Semestre', 'Grupo de fases', 'Fase', 'Resultado verificable'])
    for f in contenido['filas']:
        compras.append([f['unidad'], f['area'], f['item'], float(f['cantidad']), float(f['cantidad_propuesta']),
            float(f['costo_unitario']), float(f['importe_propuesto']), f['mes'], f['semestre'],
            f.get('grupo_fases', ''), f.get('fase_numero', ''), f.get('resultado_fase', '')])
    for pagina in libro:
        pagina.freeze_panes = 'A2'
        pagina.auto_filter.ref = pagina.dimensions
        for celda in pagina[1]:
            celda.fill = PatternFill('solid', fgColor='285C3A')
            celda.font = Font(color='FFFFFF', bold=True)
        for fila in pagina:
            for celda in fila:
                # Los textos siempre son texto, incluso si parecen fórmulas.
                if isinstance(celda.value, str):
                    celda.data_type = 's'
                celda.alignment = Alignment(vertical='top', wrap_text=True)
        for col in pagina.columns:
            pagina.column_dimensions[col[0].column_letter].width = 27
    salida = BytesIO()
    libro.save(salida)
    return salida.getvalue()
