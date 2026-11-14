"""Fuentes completas del ensayo FabLab, únicamente en su base aislada de QA.

Usa los mismos modelos, verificaciones y movimientos que la operación. Los
archivos declaran PRUEBA: no son evidencia de actividad de la Universidad.
"""
from calendar import monthrange
from datetime import datetime, time, timedelta
from decimal import Decimal

from django.core.files.base import ContentFile
from django.core.files.uploadedfile import SimpleUploadedFile
from django.db import transaction
from django.utils import timezone

from apps.documentos.presentation.escenario_ideal_base import (
    exigir_entorno_ideal, pdf_prueba, reloj_ideal,
)


def _momento(fecha, hora=9):
    return timezone.make_aware(datetime.combine(fecha, time(hora)))


def _guardar(objeto):
    objeto.full_clean()
    objeto.save()
    return objeto


def _archivo(codigo, titulo, lineas):
    return SimpleUploadedFile(codigo + '.pdf', pdf_prueba(titulo, lineas), 'application/pdf')


def _evidencia(unidad, actores, tipo, codigo, fecha, titulo, descripcion, *, detalle=None, **datos):
    from apps.documentos.presentation.medicion_metas import registrar_evidencia
    with reloj_ideal(fecha):
        return registrar_evidencia(unidad, actores['tecnico'], dict(
            tipo=tipo, codigo=codigo, fecha=fecha, titulo=titulo, descripcion=descripcion,
            responsable=actores['tecnico'], detalle=detalle or {}, **datos), verificar=True,
            archivo=_archivo(codigo, titulo, [
                unidad.nombre, f'Fecha de la actividad: {fecha:%d/%m/%Y}', descripcion,
                f'Responsable del ensayo: {actores["tecnico"].get_full_name()}',
                f'Datos comprobados en el escenario aislado: {detalle or datos}',
            ]))


@transaction.atomic
def poblar_gestion(unidad, actores, inicio, fin):
    """Crea una operación pequeña, trazable y coherente; no modifica la base real."""
    exigir_entorno_ideal()
    from apps.gestion_unidades.models.espacios import EspacioReservable
    from apps.gestion_unidades.presentation.auditoria import registrar_auditoria
    from apps.gestion_unidades.presentation.gestion import _operar_lote_consumible
    from apps.recursos.models.consumibles import (
        Consumible, ConsumiblePorEquipo, EntradaInventario, LoteConsumible,
    )
    from apps.recursos.models.equipos import EquiposServicios
    from apps.recursos.models.mantenimiento import MantenimientoEquipo, PlanMantenimientoEquipo
    from apps.recursos.models.prestamos import PrestamoEquipo
    from apps.recursos.models.software import SoftwareDisponible
    from apps.recursos.models.unidades import UnidadEquipo
    from apps.recursos.presentation.verificacion_equipos import verificar_existencia
    from apps.reservas.models.seguridad import RequisitoAcceso

    with reloj_ideal(inicio):
        if unidad.unidades_equipo_principal.exists() or unidad.evidencias_gestion.exists():
            raise ValueError('El ensayo requiere un laboratorio aislado sin fuentes previas; no reemplaza registros existentes.')
        tecnico = actores['tecnico']
        fecha_servicio = inicio + timedelta(days=1)
        espacios = []
        equipos = []
        definiciones = [
            ('IMP3D', 'Impresora 3D FDM', 'Área de fabricación aditiva', 'critico',
             'Volumen de trabajo 250 × 210 × 220 mm; filamento PLA de 1,75 mm; conexión USB.'),
            ('CNC', 'Fresadora CNC de escritorio', 'Área de mecanizado y prototipado', 'critico',
             'Mecanizado de prototipos en material blando; resguardo, parada de emergencia y extracción.'),
            ('CAD', 'Estación de diseño CAD', 'Área de diseño y preparación digital', 'normal',
             'Estación con 16 GB de memoria, almacenamiento SSD y pantalla para diseño y laminado.'),
        ]
        for numero, (codigo, nombre, area, criticidad, especificacion) in enumerate(definiciones, 1):
            espacio = _guardar(EspacioReservable(unidad=unidad, codigo='QA-FAB-' + codigo,
                nombre=area, tipo='area', ubicacion='Aulas 2 PB, aula 404 · sector ' + str(numero),
                capacidad=8, descripcion_publica='Escenario de ensayo del flujo completo de fabricación digital.',
                caracteristicas='Ventilación, iluminación, puesto delimitado y señalización de seguridad.',
                mobiliario_incluido='Mesa de trabajo, sillas y tomas protegidas.', politica_reserva='mixto'))
            ficha = EquiposServicios(codigo='QA-FAB-MODELO-' + codigo, nombre=nombre,
                descripcion='Modelo sintético para comprobar el expediente integral del laboratorio.',
                marca='Modelo de ensayo sin fabricante real', modelo='QA-' + codigo,
                caracteristicas_publicas=especificacion, especificaciones={'Alcance': especificacion},
                uso_publico='Diseño, preparación y fabricación de prototipos en las prácticas del escenario.',
                instrucciones_publicas='Completar la inducción, comprobar protecciones y solicitar supervisión técnica.',
                fecha_adquisicion=inicio - timedelta(days=365))
            ficha.ficha_tecnica.save('QA-FICHA-' + codigo + '.pdf', ContentFile(pdf_prueba(
                'Ficha técnica y procedimiento de uso · ' + nombre,
                [especificacion, 'Identificación: modelo sintético QA-' + codigo + ', sin fabricante real.',
                 'Antes del uso: inspección visual, área despejada y protección personal adecuada.',
                 'Operación: verificar parámetros de referencia y mantener supervisión técnica.',
                 'Cierre: detener, limpiar, registrar consumos y comunicar anomalías.',
                 'Mantenimiento: limpieza y prueba preventiva semestral según el plan del ensayo.'])), save=False)
            _guardar(ficha)
            equipo = _guardar(UnidadEquipo(equipo=ficha, laboratorio=unidad, codigo_unidad='QA-FAB-' + codigo + '-01',
                codigo_bien='QA-FAB-BIEN-' + str(numero), tipo_bien='BLD', numero_serie='QA-SERIE-' + codigo,
                custodio=tecnico.get_full_name() or tecnico.username,
                ubicacion_bodega='Aulas 2 PB, aula 404', ubicacion_especifica=area,
                fecha_adquisicion=inicio - timedelta(days=365), fecha_ingreso_bodega=inicio - timedelta(days=360),
                origen_adquisicion='asignacion_institucional', documento_adquisicion='ACTA-PRUEBA-FAB-2025',
                criticidad=criticidad, vida_util_anios=8, valor_referencial=Decimal('1500.00'),
                valor_contable=Decimal('1500.00'), observaciones='Bien sintético de ensayo; no es un registro patrimonial real.'))
            espacio.equipos_asociados.add(equipo)
            with reloj_ideal(inicio):
                verificar_existencia(equipo, tecnico, nota='PRUEBA: conteo físico, serie, etiqueta y ubicación cotejados en el escenario aislado.')
            equipos.append(equipo)
            espacios.append(espacio)

        software = _guardar(SoftwareDisponible(unidad=unidad, codigo='QA-FAB-SLICER',
            nombre='Laminador de fabricación digital', version='Configuración de ensayo',
            descripcion='Preparación de trayectorias y parámetros de impresión del escenario de prueba.',
            tipo_recurso='software', tipo_acceso='instalacion', licencias_totales=2, licencias_disponibles=2,
            instrucciones_acceso='Abrir en la estación CAD con el perfil institucional de prueba.'))
        software.equipos_instalados.add(equipos[0], equipos[2])

        consumible = _guardar(Consumible(unidad=unidad, codigo='QA-FAB-PLA', nombre='Filamento PLA de ensayo',
            familia='Filamentos', variante='PLA 1,75 mm', color='Blanco', presentacion='Bobina de 1 kg',
            cantidad_por_presentacion=Decimal('1000'), clasificacion='insumo', unidad_medida='g',
            ubicacion='Gabinete de materiales · estante A', minimo=Decimal('500'), stock_objetivo=Decimal('5000'),
            precio_unitario=Decimal('0.0250'), especificacion_tecnica='Filamento seco compatible con impresión FDM.'))
        ConsumiblePorEquipo.objects.create(consumible=consumible, equipo=equipos[0].equipo)
        from django.http import QueryDict
        from types import SimpleNamespace
        datos = QueryDict('', mutable=True)
        datos.update(dict(consumible_id=str(consumible.pk), codigo='QA-PLA-2026B-001', estado='bodega',
            bodega='Gabinete de materiales', estanteria='A', posicion='1', fecha_ingreso=inicio.isoformat(),
            documento_recepcion='ACTA-PRUEBA-RECEPCION-2026B', costo_unitario='0.0250', numero_presentaciones='5',
            observaciones='Cinco bobinas sintéticas de 1 kg identificadas individualmente para el ensayo.'))
        with reloj_ideal(inicio):
            lote, _, _ = _operar_lote_consumible(SimpleNamespace(POST=datos, user=tecnico), unidad)
            # Abrir sólo la bobina de trabajo: las otras cuatro siguen localizadas en bodega.
            datos.update(dict(registro_id=str(lote.pk), estado='en_uso', equipo_en_uso_id=str(equipos[0].pk),
                fecha_apertura=inicio.isoformat()))
            lote, _, _ = _operar_lote_consumible(SimpleNamespace(POST=datos, user=tecnico), unidad)
            registrar_auditoria(unidad=unidad, usuario=tecnico, accion='actualizar', objeto=lote,
                descripcion='Apertura de bobina y asignación al equipo del escenario de prueba.',
                anteriores={'estado': 'bodega'}, nuevos={'estado': lote.estado,
                    'equipo_en_uso': lote.equipo_en_uso_id, 'fecha_apertura': lote.fecha_apertura.isoformat()})
        # Consumo de preparación documentado, separado del que registran las prácticas.
        with reloj_ideal(fecha_servicio):
            EntradaInventario.objects.create(consumible=consumible, unidad=unidad, lote_inventario=lote,
                equipo=equipos[0], tipo='salida', motivo='consumo_produccion', cantidad=Decimal('100'),
                fecha=_momento(fecha_servicio), usuario=tecnico, referencia='QA-CALIBRACION-IMP3D',
                nota='Consumo de calibración: probetas dimensionales y purga; escenario de prueba.')

    planes, ordenes = [], []
    for equipo in equipos:
        with reloj_ideal(inicio):
            plan = _guardar(PlanMantenimientoEquipo(equipo=equipo,
                nombre='Programa preventivo anual · ' + equipo.codigo_unidad, tipo='preventivo',
                fecha_inicio=inicio, proxima_ejecucion=fecha_servicio, frecuencia_dias=180,
                responsable=tecnico, instrucciones='Limpiar, inspeccionar protecciones, ajustar y verificar funcionamiento.'))
            orden = MantenimientoEquipo.objects.create(equipo=equipo, unidad=unidad, plan=plan,
                titulo='Mantenimiento programado · ' + equipo.codigo_unidad,
                descripcion='Intervención prevista en el programa anual del escenario de prueba.',
                fecha_programada=_momento(fecha_servicio), responsable=tecnico, estado='programado',
                bloquea_agenda=False)
        with reloj_ideal(fecha_servicio):
            orden.estado, orden.fecha_inicio = 'en_proceso', _momento(fecha_servicio)
            orden.save()
            orden.informe.save(orden.codigo + '.pdf', ContentFile(pdf_prueba(
                'Informe de mantenimiento de ' + equipo.codigo_unidad,
                ['Orden: ' + orden.codigo, 'Plan: ' + plan.nombre,
                 'Procedimiento: limpieza, ajuste, inspección eléctrica y prueba de referencia.',
                 'Resultado: funcionamiento estable y protecciones operativas; sin repuestos requeridos.',
                 f'Fecha: {fecha_servicio:%d/%m/%Y}; técnico: {tecnico.get_full_name()}',
                 'Duración: 2 horas; costo interno estimado: USD 25.00.'])), save=False)
        with reloj_ideal(fecha_servicio, 11):
            orden.estado, orden.fecha_fin = 'completado', _momento(fecha_servicio, 11)
            orden.resultado = 'Procedimiento completado; dimensiones de referencia y protecciones dentro de criterio; equipo disponible.'
            orden.costo = Decimal('25.00')
            orden.save()
        planes.append(plan)
        ordenes.append(orden)

    fecha_infra = inicio + timedelta(days=2)
    with reloj_ideal(inicio):
        infra = _evidencia(unidad, actores, 'PLAN-INFRA', 'QA-PLAN-INFRA-2026B', inicio,
            'Plan de mantenimiento de infraestructura del FabLab',
            'Revisión de circuitos protegidos, ventilación, iluminación y señalización en las tres áreas.',
            detalle=dict(alcance_infraestructura='aplica', alcance_todo_laboratorio=True,
                justificacion_alcance='El plan incluye los tres espacios inventariados y sus instalaciones compartidas.',
                ubicacion='Aulas 2 PB, aula 404 · todas las áreas FabLab',
                intervencion='Verificación de circuitos, extracción, luminarias y señalización',
                criticidad='critica', fecha_programada=fecha_infra.isoformat(), frecuencia_dias=0))
    with reloj_ideal(fecha_infra):
        ejecucion_infra = _evidencia(unidad, actores, 'EJECUCION-INFRA', 'QA-EJEC-INFRA-2026B', fecha_infra,
            'Informe de mantenimiento de infraestructura del FabLab',
            'Instalaciones revisadas con mediciones de referencia y registro de las tres áreas; sin pendientes.',
            detalle=dict(plan_id=infra.pk, fecha_programada=fecha_infra.isoformat(),
                fecha_inicio=fecha_infra.isoformat(), fecha_fin=fecha_infra.isoformat(),
                resultado='Circuitos y tomas protegidos, extracción y luminarias funcionales, rutas despejadas y señalizadas.'))

    evidencias = [infra, ejecucion_infra]
    with reloj_ideal(fin):
        for equipo in equipos:
            evidencias.append(_evidencia(unidad, actores, 'FUNCIONALIDAD', 'QA-FUNC-' + equipo.codigo_unidad,
                fin, 'Prueba funcional · ' + equipo.codigo_unidad,
                'Verificación funcional al cierre del período con procedimiento, criterio y resultado documentados.',
                detalle=dict(equipo_id=equipo.pk, procedimiento='Ejecutar ciclo de referencia y verificar mandos, protecciones y resultado.',
                    criterio='Ciclo finalizado, mandos y parada operativos, resultado sin desviaciones respecto de la referencia de ensayo.',
                    resultado_funcional='operativo', hallazgos_funcionales='')))
        evidencias.append(_evidencia(unidad, actores, 'CAPACITACION', 'QA-CAP-2026B', fin,
            'Capacitación técnica en fabricación digital y seguridad',
            'Personal técnico completó 8 horas de ajuste de equipos, prevención de riesgos, segregación y trazabilidad de residuos.'))
        evidencias.append(_evidencia(unidad, actores, 'DIFUSION', 'QA-DIF-2026B', fin,
            'Jornada de difusión de servicios y resultados del FabLab',
            'Exposición de prototipos y demostración de reserva, seguridad y preparación digital para la comunidad universitaria.'))
        evidencias.append(_evidencia(unidad, actores, 'INVESTIGACION', 'QA-INV-2026B', fin,
            'Resultado de investigación aplicada: dispositivo de sujeción',
            'Se obtuvo un prototipo de sujeción, planos y protocolo dimensional; el informe registra pruebas y resultados del ensayo.',
            detalle=dict(proyecto='Desarrollo de utillajes de fabricación digital · ensayo 2026-B',
                tipo_producto='prototipo', producto='Prototipo de mordaza modular, planos y validación dimensional',
                beneficiario='Equipo académico de Ingeniería · escenario de prueba')))
        evidencias.append(_evidencia(unidad, actores, 'TRANSFERENCIA', 'QA-TRA-2026B', fin,
            'Informe de transferencia: utillaje y capacitación entregados',
            'Entrega de planos, prototipo y sesión de capacitación; el destinatario de prueba acepta los entregables descritos.',
            detalle=dict(proyecto='Transferencia de utillaje modular · ensayo 2026-B', tipo_producto='transferencia',
                producto='Utillaje, planos y taller de uso', beneficiario='Asociación receptora de ensayo, sin entidad real',
                aceptacion='aceptado', fecha_aceptacion=fin.isoformat(), referencia_aceptacion='ACTA-PRUEBA-ACEPTACION-2026B')))

    mes = inicio.replace(day=1)
    while mes <= fin:
        fecha = max(inicio, mes.replace(day=min(5, monthrange(mes.year, mes.month)[1])))
        with reloj_ideal(fecha):
            evidencias.append(_evidencia(unidad, actores, 'INSPECCION', 'QA-INS-' + mes.strftime('%Y%m'), fecha,
                'Inspección mensual de seguridad · ' + mes.strftime('%m/%Y'),
                'Inspección de las tres áreas: ventilación, protecciones, evacuación, EPP, materiales, limpieza y residuos.',
                detalle=dict(area='Todas las áreas de fabricación, mecanizado y diseño del FabLab',
                    condiciones_revisadas=['infraestructura', 'equipos', 'emergencias', 'proteccion', 'almacenamiento', 'limpieza', 'desechos'],
                    sin_hallazgos=True, hallazgos='', accion_correctiva='', estado_condiciones='seguro',
                    estado_accion='no_requiere', plazo_accion='')))
        mes = (mes.replace(day=28) + timedelta(days=4)).replace(day=1)

    requisito = _guardar(RequisitoAcceso(unidad=unidad, codigo='QA-INDUCCION',
        nombre='Inducción de seguridad FabLab', tipo='induccion', aplica_a=[], vigencia_dias=365,
        descripcion='Riesgos de equipos, protección personal, emergencias y segregación de materiales.'))

    prestamo = PrestamoEquipo(equipo=equipos[2], unidad=unidad, tipo='externo',
        solicitante=actores['docente'], institucion='Entidad receptora de prueba · no oficial',
        autorizado_por=actores['direccion'].get_full_name(), entregado_por=tecnico,
        proposito='Demostración académica de diseño digital en un evento del escenario de prueba.',
        fecha_salida=_momento(inicio + timedelta(days=20)),
        fecha_retorno_previsto=_momento(inicio + timedelta(days=21), 16),
        condicion_salida='bueno', bloquea_agenda=False)
    prestamo.acta.save('QA-ACTA-PRESTAMO.pdf', ContentFile(pdf_prueba('Acta de préstamo y devolución de ensayo',
        [equipos[2].codigo_unidad, 'Salida autorizada y recibida por los actores ficticios del ensayo.',
         'Se verificaron serie, accesorios, condiciones de salida y retorno sin novedades.'])), save=False)
    prestamo.estado = 'entregado'
    with reloj_ideal(inicio + timedelta(days=20)):
        prestamo.save()
    prestamo.estado, prestamo.fecha_retorno_real = 'devuelto', _momento(inicio + timedelta(days=21), 15)
    prestamo.recibido_por, prestamo.condicion_retorno = tecnico, 'bueno'
    prestamo.observaciones_retorno = 'Serie, accesorios y funcionamiento comprobados; sin novedades en el ensayo.'
    with reloj_ideal(inicio + timedelta(days=21), 15):
        prestamo.save()

    for objeto in [consumible, lote, *equipos, *planes]:
        objeto.refresh_from_db()
    return dict(equipo=equipos[0], equipos=equipos, espacio=espacios[0], espacios=espacios,
        consumible=consumible, lote=lote, lotes=list(LoteConsumible.objects.filter(consumible=consumible)),
        software=software, planes=planes, mantenimientos=ordenes,
        evidencias=evidencias, requisito_induccion=requisito, prestamo=prestamo)


@transaction.atomic
def completar_conciliaciones(unidad, actores, inicio, fin, practicas=None):
    """Cierra universos después de crear las prácticas; no infiere el total desde una meta."""
    exigir_entorno_ideal()
    from apps.recursos.models.desechos import RegistroDesecho
    from apps.reservas.models.reservas import Reserva
    from apps.reservas.models.seguridad import RegistroIngreso

    tecnico = actores['tecnico']
    reservas = list(Reserva.objects.filter(laboratorio=unidad, fecha__range=(inicio, fin))
        .prefetch_related('registros_participantes__usuario'))
    primeras = {}
    for reserva in reservas:
        for persona in reserva.registros_participantes.all():
            if persona.usuario_id is None:
                raise ValueError('El ensayo ideal no admite participantes anónimos.')
            primeras[persona.usuario_id] = min(primeras.get(persona.usuario_id, reserva.fecha), reserva.fecha)
    for reserva in reservas:
        for persona in reserva.registros_participantes.all():
            if not RegistroIngreso.objects.filter(reserva=reserva, participante=persona, usuario=persona.usuario,
                    ingresa=True, habilitaciones_vigentes=True).exists():
                raise ValueError('Registra el ingreso con inducción vigente antes de cerrar cada práctica del ensayo.')

    with reloj_ideal(fin):
        residuos = []
        for n, (nombre, cantidad, clase) in enumerate((
            ('Residuos de resina y material de limpieza de ensayo', '0.500', 'peligroso'),
            ('Componentes eléctricos descartados del ensayo', '0.250', 'especial'),
        ), 1):
            residuo = RegistroDesecho(unidad=unidad, fecha_generacion=inicio + timedelta(days=30 + n),
                clase=clase, clave_listado='CLAVE-PRUEBA-' + str(n), nombre=nombre,
                origen='Actividad de fabricación y mantenimiento del escenario de prueba', cantidad=Decimal(cantidad),
                unidad_medida='kg', envase='Contenedor de ensayo cerrado de 5 L', etiquetado=True,
                almacenamiento='Gabinete de residuos identificado · área técnica', etapa='entregado', fecha_entrega=fin,
                gestor_autorizado='Gestor ficticio de ensayo · no es un gestor real', licencia_gestor='LICENCIA-PRUEBA-NO-OFICIAL',
                manifiesto='MANIFIESTO-PRUEBA-' + str(n), responsable=tecnico, registrado_por=tecnico,
                observaciones='Registro sintético de trazabilidad; no declara autorización ambiental ni generación real.')
            residuo.documento.save('QA-MANIFIESTO-' + str(n) + '.pdf', ContentFile(pdf_prueba(
                'Manifiesto de desechos del escenario de prueba',
                [nombre, f'Cantidad de ensayo: {cantidad} kg.', 'Origen, contenedor y etiquetado registrados.',
                 'Receptor y autorización ficticios: documento sin validez ambiental.'])), save=False)
            _guardar(residuo)
            residuos.append(residuo)

        total = sum(r.es_efectiva for r in reservas)
        if not total:
            raise ValueError('Las prácticas efectivas deben registrarse antes de conciliar el uso.')
        actas = [_evidencia(unidad, actores, 'USO', 'QA-ACTA-USO-2026B', fin,
            'Acta de conciliación del uso del FabLab',
            f'Bitácora independiente del escenario: {total} sesiones realizadas y conciliadas con reserva y cierre.',
            desde=inicio, hasta=fin, total_observado=total),
            _evidencia(unidad, actores, 'DESECHOS', 'QA-ACTA-DESECHOS-2026B', fin,
                'Acta de conciliación de desechos generados',
                'Bitácora independiente del escenario: dos partidas generadas, etiquetadas y entregadas con manifiesto.',
                desde=inicio, hasta=fin, total_observado=len(residuos)),
            _evidencia(unidad, actores, 'INVENTARIO', 'QA-ACTA-INVENTARIO-2026B', fin,
                'Acta integral de inventario y revisión de criticidad',
                'Inventario físico de tres equipos, tres espacios, software instalado y filamento con lote y movimientos conciliados.',
                alcance=['equipos', 'espacios', 'insumos', 'software'], detalle={'revision_criticidad': True})]
    return dict(actas=actas, desechos=residuos, sesiones=total, usuarios_nuevos=len(primeras))
