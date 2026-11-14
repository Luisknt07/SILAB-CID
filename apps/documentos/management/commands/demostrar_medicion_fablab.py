"""Escenario repetible, exclusivamente en una base local de demostración."""
import io
from datetime import date, datetime, time, timedelta

from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.files.base import ContentFile
from django.core.management.base import BaseCommand, CommandError
from django.db import connection
from django.utils import timezone

from apps.gestion_unidades.management.datos_demo import ComandoDatosDemostrativosMixin


class SimulacionTerminada(Exception):
    pass


class Command(ComandoDatosDemostrativosMixin, BaseCommand):
    help = 'Prepara FabLab con metas cumplidas, parciales y sin evidencia en una base DEMO aislada.'

    def add_arguments(self, parser):
        self.agregar_argumentos_datos_demo(parser)

    def handle(self, *args, **options):
        slug = self.validar_opciones_datos_demo(options)
        if not (settings.DEBUG and getattr(settings, 'MEDICION_SOLO_DEMO', False) and
                getattr(settings, 'MEDICION_METAS_HABILITADA', False) and
                str(connection.settings_dict['NAME']).startswith(('citt_demo_', 'test_citt_qa_'))):
            raise CommandError('Solo se permite en una base citt_demo_ aislada y con MEDICION_SOLO_DEMO.')
        from apps.directorio_unidades.models.core import Unidad
        from apps.documentos.presentation.expediente_operaciones import operacion_de_unidad
        if Unidad.objects.filter(slug=slug).exclude(nombre__startswith='[DEMO REPORTES]').exists():
            raise CommandError('La unidad existente no pertenece a este escenario de demostración.')
        # El escenario completo se revierte, incluidos archivos, al simular.
        from django.db import transaction
        try:
            with transaction.atomic():
                actor, actor_nuevo = get_user_model().objects.get_or_create(username='demo.reportes.fablab', defaults={
                    'first_name': 'Demostración', 'last_name': 'FabLab', 'is_active': True})
                if actor_nuevo:
                    actor.set_unusable_password()
                    actor.save(update_fields=['password'])
                unidad, _ = Unidad.objects.get_or_create(slug=slug, defaults={
                    'nombre': '[DEMO REPORTES] FabLab · Fabricación Digital y Prototipado',
                    'nombre_corto': 'FabLab · DEMOSTRACIÓN', 'dependencia': 'laboratorios',
                    'clasificacion_funcional': 'plataforma_tecnologica',
                    'descripcion': 'Escenario ficticio de medición automática; no corresponde a gestión real.',
                    'fecha_inicio': date(timezone.localdate().year, 1, 1), 'administrador': actor,
                    'area_conocimiento': 'ingenieria', 'facultad': 'Ingenierías', 'carreras': 'Computación'})
                with operacion_de_unidad(unidad.pk, actor):
                    self.preparar(unidad, actor)
                    if options.get('simular'):
                        raise SimulacionTerminada
        except SimulacionTerminada:
            self.stdout.write('SIMULACIÓN: escenario y archivos revertidos.')
            return
        self.stdout.write(self.style.SUCCESS('FabLab DEMO preparado. No se enviaron documentos ni se aprobaron notas.'))

    def preparar(self, unidad, actor):
        from apps.documentos.models.expediente import DocumentoElaborado
        from apps.documentos.models.medicion import EvidenciaGestionUnidad
        from apps.documentos.presentation.expediente import construir_expediente, cortes_del_anio
        from apps.documentos.presentation.expediente_redaccion import valores_iniciales
        from apps.documentos.presentation.medicion_metas import registrar_evidencia
        from apps.documentos.presentation.expediente_operaciones import recordar_archivo
        from apps.formacion.models.asignaturas import Asignatura, TemaAsignatura
        from apps.formacion.models.practicas import PlanificacionPractica, EjecucionPractica, EvidenciaPractica
        from apps.gestion_unidades.models.espacios import EspacioReservable, ResponsableUnidad
        from apps.recursos.models.desechos import RegistroDesecho
        from apps.recursos.models.equipos import EquiposServicios
        from apps.recursos.models.unidades import UnidadEquipo
        from apps.recursos.models.mantenimiento import MantenimientoEquipo
        from apps.reservas.models.reservas import Reserva, CatalogoActividadReserva, GuiaActividadReserva
        from apps.reservas.models.seguridad import RegistroIngreso, RequisitoAcceso, HabilitacionAcceso

        hoy = timezone.localdate()
        corte = 'B' if hoy.month >= 7 else 'A'
        inicio, fin = cortes_del_anio(hoy.year)[corte]
        dia = min(hoy, inicio + timedelta(days=20))
        def instante(d):
            return timezone.make_aware(datetime.combine(d, time(9)))
        actividad, _ = CatalogoActividadReserva.objects.get_or_create(unidad=unidad,
            nombre='[DEMO REPORTES] Prototipado y fabricación digital', defaults={'activo': True})
        responsable, _ = ResponsableUnidad.objects.get_or_create(unidad=unidad, usuario=actor,
            defaults={'rol': 'responsable_tecnico', 'nombre': '[DEMO REPORTES] Responsable ficticio'})
        espacio, _ = EspacioReservable.objects.get_or_create(unidad=unidad, codigo='DEMO-FAB-AREA',
            defaults={'nombre': '[DEMO REPORTES] Área de prototipado', 'capacidad': 8})
        asignatura, _ = Asignatura.objects.get_or_create(unidad=unidad, codigo='DEMO-FAB-ASIG',
            defaults={'nombre': '[DEMO REPORTES] Prototipado', 'carrera': 'Computación', 'semestre': 'Primero'})
        tema, _ = TemaAsignatura.objects.get_or_create(asignatura=asignatura, orden=1,
            defaults={'nombre': '[DEMO REPORTES] Construcción y comprobación de un prototipo',
                      'resultado_aprendizaje': 'Ejemplo ficticio: construye y verifica un prototipo de demostración.'})
        contenido_guia = dict(
            asignatura=asignatura.nombre, carrera_semestre='Computación · Primero · DEMOSTRACIÓN',
            docente_responsable='Docente ficticio DEMO', laboratorio=unidad.nombre,
            categoria_uso='Docencia · DEMOSTRACIÓN', duracion='Una hora de simulación', maximo_estudiantes=8,
            resultado_aprendizaje=tema.resultado_aprendizaje,
            objetivos='Ejemplo ficticio: construir una pieza y comprobar sus dimensiones.',
            fundamento_teorico='Ejemplo ficticio sobre fabricación aditiva y comprobación dimensional.',
            procedimiento='Ejemplo ficticio: preparar, fabricar y comparar una pieza de demostración.',
            medidas_seguridad='Ejemplo ficticio: protección y revisión del área antes de la actividad simulada.',
            resultados_esperados='Pieza ficticia identificada con un registro de comprobación de ejemplo.',
            criterios_evaluacion='Ejemplo ficticio: dimensiones previstas y observadas de una pieza simulada.',
            manejo_residuos='Ejemplo ficticio: separar los restos del material de demostración.',
            bibliografia=['Referencia ficticia de prueba; sin validez académica ni institucional.'],
        )
        guia, _ = GuiaActividadReserva.objects.get_or_create(
            actividad=actividad, titulo='[DEMO REPORTES] Guía de prototipado',
            defaults={'estado_publicacion': 'publicada', 'activo': True, 'subido_por': actor,
                      'es_estructurada': True, 'es_vigente': True, 'codigo_guia': 'DEMO-FAB-GUIA',
                      'aprobado_por': actor, 'aprobado_en': instante(dia), 'contenido': contenido_guia})
        for i in range(6):
            fecha = min(hoy, dia + timedelta(days=i))
            reserva, _ = Reserva.objects.get_or_create(laboratorio=unidad,
                titulo_solicitud=f'[DEMO REPORTES] Sesión de prototipado {i + 1}', defaults={
                    'usuario': actor, 'fecha': fecha, 'hora_inicio': time(9), 'hora_fin': time(10),
                    'equipo_codigo': 'DEMO-IMP3D', 'equipo_nombre': 'Impresora 3D DEMO',
                    'estado': 'completada', 'resultado_cierre': 'atendida',
                    'proposito_codigo': 'investigacion_innovacion' if i == 0 else 'docencia_practica',
                    'detalle_ejecucion': {'registrada_en': instante(fecha).isoformat(),
                        'hora_inicio_real': '09:00', 'hora_fin_real': '10:00'},
                    'descripcion_proyecto': 'Ejemplo ficticio para comprobar los indicadores.'})
            reserva.espacios_solicitados.add(espacio)
            plan, _ = PlanificacionPractica.objects.get_or_create(unidad=unidad,
                tema=f'[DEMO REPORTES] Práctica {i + 1}', defaults={
                    'fecha': fecha, 'hora_inicio': time(9), 'hora_fin': time(10), 'creado_por': actor,
                    'carrera': 'Computación', 'semestre': 'Primero', 'asignatura': asignatura.nombre,
                    'docente_tutor': 'Docente DEMO', 'actividad': actividad, 'guia': guia,
                    'tema_asignatura': tema, 'responsable_tecnico': responsable,
                    'resultado_aprendizaje': tema.resultado_aprendizaje, 'requiere_guia': True,
                    'estado': 'aprobada', 'revisado_por': actor, 'revisado_en': instante(fecha), 'reserva': reserva})
            if i < 5:
                ejecucion, _ = EjecucionPractica.objects.get_or_create(planificacion=plan, defaults={
                    'fecha_ejecucion': fecha, 'hora_inicio_real': time(9), 'hora_fin_real': time(10),
                    'estudiantes_asistentes': 8, 'recursos_utilizados': 'Impresora y material DEMO',
                    'responsable_tecnico': responsable,
                    'detalle_operativo': {'participantes': [dict(id=f'DEMO-{n}',
                        nombre=f'Participante ficticio DEMO {n}', asistencia_codigo='asistio') for n in range(1, 9)]},
                    'cumplimiento_resultado': 'si', 'creado_por': actor,
                    'estado': 'validada' if i != 3 else 'borrador', 'resultado': 'ejecutada',
                    'eliminado_en': instante(fecha) if i == 4 else None,
                    'validado_por': actor if i != 3 else None,
                    'validado_en': instante(fecha) if i != 3 else None})
                if not ejecucion.evidencias.filter(tipo='bitacora').exists():
                    evidencia = EvidenciaPractica(ejecucion=ejecucion, tipo='bitacora',
                        nombre_original=f'demo-practica-{i + 1}.pdf', subido_por=actor,
                        descripcion=f'DEMOSTRACIÓN: bitácora ficticia identificada de la práctica {i + 1}; sin validez institucional.')
                    evidencia.archivo.save(evidencia.nombre_original,
                        ContentFile(self.pdf(f'Práctica DEMO {i + 1}', evidencia.descripcion, fecha)), save=False)
                    recordar_archivo(evidencia.archivo)
                    evidencia.save()
        requisito, _ = RequisitoAcceso.objects.get_or_create(unidad=unidad, codigo='DEMO-INDUCCION',
            defaults={'nombre': 'Inducción de seguridad DEMO', 'tipo': 'induccion', 'obligatorio': True})
        for i in range(3):
            persona, persona_nueva = get_user_model().objects.get_or_create(username=f'demo.fablab.participante.{i+1}',
                defaults={'first_name': 'Participante DEMO', 'last_name': str(i + 1)})
            if persona_nueva:
                persona.set_unusable_password()
                persona.save(update_fields=['password'])
            RegistroIngreso.objects.get_or_create(reserva=reserva, usuario=persona, defaults={
                'nombre': persona.get_full_name(), 'categoria': 'estudiante', 'ingresa': True, 'registrado_por': actor})
            if i < 2:
                HabilitacionAcceso.objects.get_or_create(usuario=persona, requisito=requisito,
                    defaults={'fecha': inicio, 'origen': 'documento', 'documento': f'DEMO-IND-{i + 1}',
                              'otorgada_por': actor, 'activa': True})
        base, _ = EquiposServicios.objects.get_or_create(codigo='DEMO-IMP3D',
            defaults={'nombre': '[DEMO REPORTES] Impresora 3D', 'marca': 'Demostración'})
        equipo, _ = UnidadEquipo.objects.get_or_create(codigo_unidad='DEMO-FAB-IMP3D',
            defaults={'equipo': base, 'laboratorio': unidad, 'criticidad': 'critico', 'estado_unidad': 'disponible'})
        for i in range(5):
            fecha = min(hoy, dia + timedelta(days=i))
            MantenimientoEquipo.objects.get_or_create(equipo=equipo, titulo=f'[DEMO REPORTES] Mantenimiento {i+1}',
                defaults={'unidad': unidad, 'fecha_programada': instante(fecha), 'responsable': actor,
                    'estado': 'completado' if i < 4 else 'planificado',
                    'fecha_inicio': instante(fecha) if i < 4 else None,
                    'fecha_fin': instante(fecha) + timedelta(hours=1) if i < 4 else None,
                    'resultado': 'Comprobación ficticia satisfactoria.' if i < 4 else '', 'bloquea_agenda': False})
        for i in range(3):
            RegistroDesecho.objects.get_or_create(unidad=unidad, nombre=f'[DEMO REPORTES] Partida especial {i+1}',
                defaults={'fecha_generacion': dia, 'clase': 'especial', 'cantidad': 1, 'envase': 'Contenedor identificado',
                    'etiquetado': True, 'almacenamiento': 'Punto temporal DEMO', 'responsable': actor, 'registrado_por': actor})

        fuentes = [
            ('CAPACITACION', '01', 'Taller de impresión 3D', 'Se realizó un taller con constancia y asistencia ficticias.', {}),
            ('CAPACITACION', '02', 'Seguridad en fabricación', 'Se realizó una segunda capacitación ficticia.', {}),
            ('DIFUSION', '01', 'Muestra de prototipos', 'Se difundió un material de ejemplo sobre los resultados.', {}),
            ('INVENTARIO', '01', 'Acta de inventario físico',
                'Se cotejaron equipos, software, espacios y reactivos e insumos. Ejemplo ficticio.',
                {'alcance': ['equipos', 'software', 'espacios', 'insumos']}),
            ('INVESTIGACION', '01', 'Resultado de investigación documentado DEMO',
                'Informe ficticio de un prototipo obtenido y comprobado. No corresponde a un proyecto o resultado real.',
                {'detalle': dict(proyecto='[DEMO REPORTES] Proyecto ficticio de prototipado',
                    tipo_producto='prototipo', producto='[DEMO REPORTES] Prototipo ficticio comprobado',
                    beneficiario='[DEMO REPORTES] Grupo ficticio de investigación')}),
            ('USO', '01', 'Conciliación de sesiones', 'Bitácora independiente DEMO: 8 sesiones observadas; 6 registradas efectivamente.',
                {'desde': inicio, 'hasta': hoy, 'total_observado': 8}),
            ('DESECHOS', '01', 'Conciliación de desechos', 'Bitácora independiente DEMO: 4 partidas generadas; 3 registradas y acondicionadas.',
                {'desde': inicio, 'hasta': hoy, 'total_observado': 4}),
        ]
        for tipo, numero, titulo, descripcion, extra in fuentes:
            codigo = f'DEMO-{hoy.year}-{corte}-{tipo}-{numero}'
            if not EvidenciaGestionUnidad.objects.filter(unidad=unidad, codigo=codigo).exists():
                datos = dict(codigo=codigo, tipo=tipo, fecha=hoy, titulo=titulo,
                    descripcion=descripcion, responsable=actor, **extra)
                registrar_evidencia(unidad, actor, datos, verificar=True,
                    archivo=ContentFile(self.pdf(titulo, descripcion, hoy), name=codigo + '.pdf'))
        codigo = f'DEMO-{hoy.year}-{corte}-TRANSFERENCIA-01'
        if not EvidenciaGestionUnidad.objects.filter(unidad=unidad, codigo=codigo).exists():
            registrar_evidencia(unidad, actor, dict(codigo=codigo, tipo='TRANSFERENCIA', fecha=hoy,
                titulo='Transferencia pendiente de respaldo', responsable=actor,
                descripcion='Registro ficticio sin documento verificado: acredita cero.'), verificar=False)
        for doc in construir_expediente(unidad, hoy.year):
            if doc.corte == corte and doc.exigido.fuente_reporte in ('planificacion', 'informe'):
                contenido = valores_iniciales(doc)
                if doc.exigido.fuente_reporte == 'planificacion':
                    # Este caso compara una investigación respaldada y una
                    # transferencia incompleta. Son compromisos explícitos del
                    # caso, no cuotas generales para todas las unidades.
                    for codigo in ('INVESTIGACION', 'TRANSFERENCIA'):
                        contenido['actividades']['catalogo'][codigo].update(
                            aplica=True, obligatoria=True, meta='1')
                DocumentoElaborado.objects.get_or_create(documento=doc, defaults={
                    'contenido': contenido, 'version': 1, 'actualizado_por': actor})
        self.stdout.write(f'Unidad: {unidad.slug}; período: {hoy.year}-{corte}.')

    @staticmethod
    def pdf(titulo, descripcion, hoy):
        from reportlab.lib.pagesizes import A4
        from reportlab.pdfgen.canvas import Canvas
        from textwrap import wrap
        archivo = io.BytesIO()
        c = Canvas(archivo, pagesize=A4)
        c.setTitle('DEMOSTRACIÓN · ' + titulo)
        c.setFillColorRGB(.65, .13, .13)
        c.setFont('Helvetica-Bold', 16)
        c.drawString(45, 785, 'DEMOSTRACIÓN · SIN VALIDEZ INSTITUCIONAL')
        c.setFillColorRGB(.15, .35, .22)
        c.setFont('Helvetica-Bold', 14)
        c.drawString(45, 740, titulo)
        c.setFont('Helvetica', 11)
        c.drawString(45, 714, f'FabLab · Fecha: {hoy:%d/%m/%Y}')
        for n, linea in enumerate(wrap(descripcion, 85)):
            c.drawString(45, 670 - 18*n, linea)
        c.drawString(45, 560, 'Datos ficticios para comprobar el cálculo automático de metas.')
        c.save()
        return archivo.getvalue()
