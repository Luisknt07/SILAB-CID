"""Ensayo integral exportable; bloqueado contra cualquier base operativa."""
import json
from datetime import date, timedelta
from pathlib import Path

from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from django.utils import timezone

from apps.documentos.presentation.escenario_ideal_base import (
    exigir_entorno_ideal, firmar_pdf_prueba, pdf_prueba, reloj_ideal,
)


def _declaracion(documento):
    from apps.documentos.presentation.expediente_archivos import identidad_documental
    return dict(identidad_documental(documento), revisado=True, version=documento.version)


def _actores(unidad=None):
    nombres = {'coordinacion': 'Coordinación', 'tecnico': 'Responsable técnico',
               'docente': 'Docente', 'direccion': 'Dirección'}
    nombres.update({f'estudiante{n}': f'Estudiante {n}' for n in range(1, 5)})
    actores = {}
    for clave, nombre in nombres.items():
        usuario = get_user_model().objects.create_user(username='prueba.ideal.fablab.' + clave,
            first_name=nombre, last_name='Prueba aislada', email=clave + '@example.invalid',
            is_staff=clave == 'direccion', is_superuser=clave == 'direccion', date_joined=timezone.now())
        usuario.set_unusable_password()
        usuario.save(update_fields=['password'])
        perfil = usuario.profile
        perfil.tipo_usuario = ('estudiante' if clave.startswith('estudiante') else
                               'docente' if clave == 'docente' else 'administrativo')
        perfil.facultad = 'agropecuarias_ambientales'
        perfil.carrera = 'computacion' if clave.startswith('estudiante') or clave == 'docente' else ''
        perfil.institucion = 'UPEC'
        if clave.startswith('estudiante'):
            perfil.nivel_academico = 'quinto_semestre'
            perfil.cedula = 'PRUEBA-' + str(usuario.pk)
        perfil.save()
        actores[clave] = usuario
    actores['estudiantes'] = [actores['estudiante' + str(n)] for n in range(1, 5)]
    actores['estudiante'] = actores['estudiantes'][0]
    return actores


def _redactar(documento, actores):
    from apps.documentos.models.expediente import DocumentoElaborado
    from apps.documentos.presentation.expediente_redaccion import valores_iniciales, avance
    contenido = valores_iniciales(documento)
    tipo = documento.exigido.fuente_reporte
    contenido.update(firma_nombre=actores['coordinacion'].get_full_name(),
        firma_cargo='Coordinación de FabLab · actor de ensayo',
        revisa_nombre=actores['direccion'].get_full_name(), revisa_cargo='Dirección · actor de ensayo')
    if tipo == 'planificacion':
        contenido.update(descripcion='<p>PRUEBA: laboratorio de fabricación digital para diseño CAD, '
            'prototipado, manufactura aditiva y comprobación de productos.</p>',
            objetivo_general='<p>Ejecutar seis prácticas de fabricación digital y documentar el uso, '
            'la seguridad, los recursos y los resultados del período 2026-B.</p>',
            objetivos_especificos='<ul><li>Planificar y ejecutar seis prácticas con guía aprobada, '
            'asistencia nominal y bitácora.</li><li>Registrar todas las sesiones y las inducciones.</li>'
            '<li>Completar el mantenimiento y verificar físicamente los recursos.</li>'
            '<li>Documentar un producto de investigación y una transferencia aceptada.</li></ul>',
            sectores=['docencia', 'tecnologia'], estado_operativo='A',
            diagnostico='<p>Escenario de ensayo: tres equipos identificados, tres espacios y software '
            'disponible. Se programa mantenimiento, inspección mensual y conciliación de inventario.</p>',
            necesidades='<p>Consumibles PLA, revisión preventiva de equipos, actualización de las guías '
            'y formación en registro de evidencias. Son necesidades sintéticas del ensayo.</p>',
            inversion=[dict(categoria='insumos', item='Filamento PLA de 1,75 mm, bobina de 1 kg',
                cantidad='5', justificacion='Prácticas de fabricación aditiva y puesta a punto.',
                prioridad='alta', costo_unitario='25', fuente='institucional')])
        for fila in contenido['actividades']['catalogo'].values():
            if fila['aplica']:
                fila['responsable'] = actores['tecnico'].get_full_name()
    elif tipo == 'informe':
        contenido.update(resumen_ejecutivo='<p>PRUEBA INTEGRAL: se completaron seis prácticas de '
            'dos horas, con cuatro estudiantes por sesión, guías vinculadas al syllabus, asistencia '
            'y bitácoras. Se documentaron mantenimiento, inventario, inspecciones, seguridad, '
            'desechos y resultados de investigación y transferencia.</p>',
            analisis_uso='<p>Las seis sesiones corresponden a una secuencia de diseño, laminado, '
            'fabricación, medición, ensamble y documentación. Se conciliaron las sesiones con una '
            'bitácora independiente de prueba. El período académico va del 17/08 al 08/12/2026.</p>',
            logros='<ul><li>Seis prácticas planificadas y seis ejecutadas, con su respaldo completo.</li>'
            '<li>Seis guías aprobadas y vinculadas '
            'al syllabus.</li><li>Recursos identificados y verificados; mantenimiento y controles '
            'de seguridad documentados.</li><li>Un producto y una transferencia con aceptación '
            'y respaldo de ensayo.</li></ul>', dificultades='', acciones=[],
            necesidades_siguiente='<p>Actualizar perfiles de laminado y mantener la capacitación '
            'en registro de evidencias durante el siguiente período.</p>',
            ejecucion_presupuestal=[dict(item='Cinco bobinas de PLA de 1 kg', planificado='125',
                ejecutado='125', estado='adquirido', observacion='Ingreso de cinco lotes de ensayo; recepción verificada.')])
    elif tipo == 'compras':
        contenido.update(anio_planificado=str(documento.anio + 1),
            justificacion='<p>PRUEBA: reposición planificada de consumibles y repuestos para sostener '
            'la capacidad de prototipado del siguiente año.</p>',
            capacidad='<p>Las compras mantienen los tres equipos y los tres espacios del laboratorio '
            'de ensayo, sin ampliar el aforo ni exigir instalaciones nuevas. El responsable técnico '
            'realiza la puesta a punto y el seguimiento preventivo; el filamento abastece las '
            'prácticas previstas y los repuestos sostienen la operación de la impresora.</p>',
            compras=[dict(item='Filamento PLA de 1,75 mm', categoria='insumos', cantidad='10',
                costo_unitario='25', prioridad='alta', justificacion='Sostener prácticas de fabricación aditiva.',
                fuente='institucional', trimestre='1'),
                dict(item='Juego de boquillas y repuestos', categoria='mantenimiento', cantidad='3',
                costo_unitario='35', prioridad='media', justificacion='Mantenimiento preventivo.',
                fuente='institucional', trimestre='1')])
    resultado = avance(tipo, contenido)
    if resultado['faltantes']:
        raise CommandError('Apartados incompletos de ' + documento.exigido.codigo + ': ' +
                           ', '.join(c.etiqueta for _, c in resultado['faltantes']))
    DocumentoElaborado.objects.create(documento=documento, contenido=contenido, version=1,
        actualizado_por=actores['coordinacion'])


def _entregar(documento, actores, *, evaluar=True, externo=None):
    from apps.documentos.presentation.expediente import (
        anexos_del, cargar_documento, evaluar_documento, generar_documento, recibir_documento,
        validar_anexo, validar_documento,
    )
    if externo is None:
        _redactar(documento, actores)
        generar_documento(documento, actores['coordinacion'])
        with documento.recurso.archivo.open('rb') as archivo:
            datos = archivo.read()
    else:
        datos = pdf_prueba(documento.nombre_documental, externo)
    if documento.exigido.requiere_firma:
        datos = firmar_pdf_prueba(datos)
    cargar_documento(documento, SimpleUploadedFile(documento.exigido.codigo + '-PRUEBA.pdf', datos,
        'application/pdf'), actores['coordinacion'], declaracion_correspondencia=_declaracion(documento))
    for anexo in anexos_del(documento):
        if anexo.recurso_id and anexo.estado != 'validado':
            validar_anexo(anexo, actores['coordinacion'])
    validar_documento(documento, actores['coordinacion'], declaracion_correspondencia=_declaracion(documento))
    if evaluar:
        recibir_documento(documento, actores['direccion'], declaracion_correspondencia=_declaracion(documento))
        evaluar_documento(documento, actores['direccion'], 100,
            'Evaluación de un actor ficticio en el ensayo aislado; no es aprobación institucional.',
            declaracion_correspondencia=_declaracion(documento))
    return documento


class Command(BaseCommand):
    help = 'Construye y exporta FabLab ideal sólo en test_citt_ideal_ con el ensayo aislado habilitado.'

    def add_arguments(self, parser):
        parser.add_argument('--referencia', required=True)

    @transaction.atomic
    def handle(self, *args, **opciones):
        exigir_entorno_ideal()
        from apps.core.models.periodos import PeriodoAcademico, VersionCalendarioAcademico
        from apps.directorio_unidades.models.core import Unidad
        from apps.documentos.presentation.escenario_ideal_gestion import poblar_gestion, completar_conciliaciones
        from apps.documentos.presentation.escenario_ideal_practicas import poblar_practicas, ejecutar_practicas
        from apps.documentos.presentation.expediente import construir_expediente
        from apps.gestion_unidades.models.espacios import ResponsableUnidad
        referencia = json.loads(Path(opciones['referencia']).read_text(encoding='utf8'))
        inicio, fin = date.fromisoformat(referencia['inicio']), date.fromisoformat(referencia['fin'])
        datos_unidad = referencia['unidad']
        if Unidad.objects.filter(slug=datos_unidad['slug']).exists():
            raise CommandError('El escenario ya existe en esta base; usa una base de ensayo vacía.')
        with reloj_ideal(inicio):
            actores = _actores()
            datos_unidad['nombre'] = '[PRUEBA INTEGRAL] ' + datos_unidad['nombre']
            datos_unidad['nombre_corto'] = 'FabLab · PRUEBA'
            datos_unidad['fecha_inicio'] = date.fromisoformat(datos_unidad['fecha_inicio'])
            unidad = Unidad.objects.create(**datos_unidad, administrador=actores['coordinacion'])
            for clave, rol in (('coordinacion', 'coordinacion'), ('tecnico', 'responsable_tecnico'), ('docente', 'laboratorista')):
                ResponsableUnidad.objects.create(unidad=unidad, usuario=actores[clave], rol=rol,
                    nombre=actores[clave].get_full_name(), recibe_reservas=clave != 'docente')
            periodo, _ = PeriodoAcademico.objects.get_or_create(codigo='2026-B', defaults=dict(
                nombre='Período académico 2026-B · ensayo', anio_referencia=2026, ciclo='B', tipo='ordinario',
                ambito='carreras_centros', semanas_planificadas=16, estado='publicado'))
            calendario = VersionCalendarioAcademico.objects.filter(periodo=periodo, vigente=True).first()
            if calendario and (calendario.fecha_inicio_clases != inicio or calendario.fecha_fin_periodo != fin):
                raise CommandError('El calendario del clon no coincide con el período solicitado para el ensayo.')
            if calendario is None:
                from django.db.models import Max
                numero = (VersionCalendarioAcademico.objects.filter(periodo=periodo).aggregate(
                    numero=Max('numero'))['numero'] or 0) + 1
                VersionCalendarioAcademico.objects.create(periodo=periodo, numero=numero, nombre='Calendario de ensayo',
                    fecha_inicio_clases=inicio, fecha_fin_clases=fin, fecha_fin_periodo=fin, vigente=True)
        with reloj_ideal(fin):
            recursos = poblar_gestion(unidad, actores, inicio, fin)
            practicas = poblar_practicas(unidad, actores, inicio, fin, recursos=recursos, ejecutar=False)
        with reloj_ideal(inicio):
            documentos = construir_expediente(unidad, 2026)
        def buscar(codigo):
            return next(d for d in documentos if d.exigido.codigo == codigo and d.corte in ('', 'B'))
        with reloj_ideal(inicio + timedelta(days=1)):
            _entregar(buscar('RESOLUCION-CREACION'), actores, externo=[
                'Referencia de prueba: PRUEBA-RES-FAB-2026-001. Autoridad: actor ficticio de Dirección.',
                'Objeto del ensayo: creación y alcance de un laboratorio de fabricación digital.',
                'Este archivo no sustituye la resolución auténtica de la Universidad.'])
            _entregar(buscar('PROTOCOLO-BIOSEGURIDAD'), actores, externo=[
                'Protocolo de ensayo FabLab, versión de prueba 01.',
                'Alcance: diseño CAD, impresión 3D y prototipado; responsables ficticios identificados.',
                'Registro de riesgos: superficies calientes, partes móviles, electricidad y materiales.',
                'Controles del escenario: inducción, EPP, resguardos, inspección y señalización.',
                'Condiciones de operación, limpieza, almacenamiento y respuesta a incidentes documentadas.',
                'Los procedimientos y la aprobación de este ejemplo no son documentos institucionales reales.'])
            _entregar(buscar('PLANIFICACION'), actores)
            _entregar(buscar('PLAN-COMPRAS-ANUAL'), actores)
        ejecutar_practicas(unidad, actores, inicio, fin, recursos=recursos, practicas=practicas)
        with reloj_ideal(fin):
            completar_conciliaciones(unidad, actores, inicio, fin, practicas)
        with reloj_ideal(fin):
            _entregar(buscar('INFORME-SEMESTRAL'), actores, evaluar=False)
        with reloj_ideal(fin + timedelta(days=1)):
            from apps.documentos.presentation.automatizacion_documental import procesar_expediente
            from apps.documentos.presentation.expediente import leer_expediente, del_periodo, cortes_del_anio
            actuales = del_periodo(leer_expediente(unidad, 2026), 'B', cortes_del_anio(2026))
            procesar_expediente(actuales, usuario=actores['coordinacion'])
            from apps.documentos.presentation.escenario_ideal_exportacion import exportar_escenario
            ruta = exportar_escenario(unidad, referencia, actuales, actores)
        self.stdout.write(self.style.SUCCESS('Escenario ideal exportado: ' + str(ruta)))
