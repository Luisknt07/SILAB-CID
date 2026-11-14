"""Fuentes reales, conciliaciones independientes y escenario DEMO aislado."""
import io
from datetime import date, time
from pathlib import Path
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.core.files.uploadedfile import SimpleUploadedFile
from django.core.management import call_command
from django.core.management.base import CommandError
from django.conf import settings
from django.db import connection
from django.test import TestCase, override_settings
from django.urls import reverse
from django.utils import timezone

from apps.directorio_unidades.models.core import Unidad
from apps.documentos.models.medicion import EvidenciaGestionUnidad
from apps.documentos.presentation.evaluacion_cierre import medir_meta, calcular_cierre
from apps.documentos.presentation.medicion_metas import registrar_evidencia, registros_de_gestion, rectificar_evidencia
from apps.reservas.models.reservas import Reserva
from apps.reservas.models.seguridad import RegistroIngreso, HabilitacionAcceso, RequisitoAcceso
from tests.integration.test_direccion_recibe_y_califica import BaseDelExpediente


@override_settings(MEDICION_METAS_HABILITADA=True)
class MedicionMetasTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.actor = get_user_model().objects.create_user(username='medicion-responsable')
        cls.unidad = Unidad.objects.create(nombre='FabLab QA', slug='fablab-medicion', dependencia='laboratorios',
            descripcion='Unidad de pruebas', fecha_inicio=date(2026, 1, 1), administrador=cls.actor)
        cls.otra = Unidad.objects.create(nombre='Otra unidad', slug='otra-medicion', dependencia='laboratorios',
            descripcion='Otra unidad', fecha_inicio=date(2026, 1, 1))

    def setUp(self):
        self.inicio = date(2026, 7, 1)
        self.hoy = date(2026, 10, 16)
        self.fin = date(2026, 12, 31)
        self.reloj = patch('django.utils.timezone.localdate', return_value=self.hoy)
        self.reloj.start()
        self.addCleanup(self.reloj.stop)

    def evidencia(self, tipo='CAPACITACION', codigo='QA-01', verificar=True, **extra):
        datos = dict(
            tipo=tipo, codigo=codigo, titulo='Actividad realizada', fecha=self.hoy,
            descripcion='Resultado documentado de la actividad.', responsable=self.actor,
            enlace=f'https://example.org/evidencias/{codigo}')
        datos.update(extra)
        return registrar_evidencia(self.unidad, self.actor, datos, verificar=verificar)

    def registros(self):
        return registros_de_gestion(self.unidad, self.inicio, self.fin)

    def reserva(self, dia=None, efectiva=True):
        return Reserva.objects.create(laboratorio=self.unidad, usuario=self.actor,
            fecha=dia or self.hoy, hora_inicio=time(9), hora_fin=time(10),
            equipo_codigo='QA', equipo_nombre='Impresora QA', estado='completada',
            resultado_cierre='atendida' if efectiva else '',
            detalle_ejecucion={'registrada_en': '2026-10-16T09:00:00-05:00'} if efectiva else {})

    def test_vacio_no_acredita_y_borrador_no_suma(self):
        self.assertEqual(self.registros()['gestion_capacitacion'], 0)
        self.evidencia(verificar=False)
        self.assertEqual(self.registros()['gestion_capacitacion'], 0)
        with self.assertRaises(ValidationError):
            self.evidencia(codigo='VACIA', descripcion='')

    def test_verificada_suma_y_repetir_fuente_no_duplica_credito(self):
        e = self.evidencia()
        self.assertEqual(self.registros()['gestion_capacitacion'], 1)
        with self.assertRaises(ValidationError):
            registrar_evidencia(self.unidad, self.actor, dict(tipo=e.tipo, codigo='OTRO', fecha=self.hoy,
                titulo=e.titulo, descripcion=e.descripcion, responsable=self.actor, enlace=e.enlace), verificar=True)

    def test_rectificar_conserva_fuente_y_historial_pero_resta_credito(self):
        e = self.evidencia()
        with self.assertRaises(ValidationError):
            rectificar_evidencia(self.unidad, self.actor, e.pk, '')
        rectificar_evidencia(self.unidad, self.actor, e.pk, 'Se corrigió la fecha de la actividad.')
        e.refresh_from_db()
        self.assertEqual(e.estado, 'anulado')
        self.assertTrue(e.enlace)
        self.assertEqual(self.registros()['gestion_capacitacion'], 0)

    def test_filas_importadas_incompletas_y_ajenas_no_acreditan(self):
        e = self.evidencia()
        EvidenciaGestionUnidad.objects.filter(pk=e.pk).update(descripcion='')
        self.assertEqual(self.registros()['gestion_capacitacion'], 0)
        EvidenciaGestionUnidad.objects.filter(pk=e.pk).update(descripcion='Contenido', unidad=self.otra)
        self.assertEqual(self.registros()['gestion_capacitacion'], 0)

    def test_inventario_exige_acta_integral_de_los_cuatro_componentes(self):
        with self.assertRaises(ValidationError):
            self.evidencia('INVENTARIO', alcance=['equipos'])
        with self.assertRaises(ValidationError):
            self.evidencia('INVENTARIO', alcance=['equipos', 'software', 'espacios'])
        self.evidencia('INVENTARIO', alcance=['equipos', 'software', 'espacios', 'insumos'])
        self.assertEqual(self.registros()['inventarios_verificados'], 1)
        lectura = medir_meta(dict(codigo='INVENTARIO', nombre='Inventario', contador='inventarios', meta='1'), self.registros())
        self.assertEqual(lectura['porcentaje'], 100)

    def test_porcentaje_usa_universo_independiente_y_solo_atenciones_efectivas(self):
        self.reserva()
        self.reserva(efectiva=False)
        self.evidencia('USO', desde=self.inicio, hasta=self.hoy, total_observado=2)
        r = self.registros()
        lectura = medir_meta(dict(codigo='USO', nombre='Uso', meta='100 %'), r)
        self.assertEqual((lectura['registrado'], lectura['denominador'], lectura['porcentaje']), (1, 2, 50))
        self.assertFalse(lectura['pendiente'])

    def test_porcentaje_sin_universo_o_con_total_incoherente_queda_pendiente(self):
        e = self.evidencia('USO', desde=self.inicio, hasta=self.hoy, total_observado=0)
        fila = dict(codigo='USO', nombre='Uso', meta='100 %')
        self.assertTrue(medir_meta(fila, self.registros())['pendiente'])
        self.reserva()
        self.assertEqual(medir_meta(fila, self.registros())['porcentaje'], 0)
        e.refresh_from_db()
        self.assertEqual(e.total_observado, 0)

    def test_tramos_incompletos_no_acreditan_y_solapados_se_rechazan(self):
        self.reserva()
        self.evidencia('USO', desde=self.hoy, hasta=self.hoy, total_observado=1)
        lectura = medir_meta(dict(codigo='USO', nombre='Uso', meta='100 %'), self.registros())
        self.assertTrue(lectura['pendiente'])
        self.assertIn('todo el período', lectura['motivo'])
        with self.assertRaises(ValidationError):
            self.evidencia('USO', codigo='SEGUNDO', desde=self.inicio, hasta=self.hoy, total_observado=2)

    def test_subir_archivo_y_error_no_deja_archivo_huerfano(self):
        from apps.documentos.management.commands.demostrar_medicion_fablab import Command
        pdf = Command.pdf('Acta de prueba', 'Constancia de una actividad realizada con su resultado y sus participantes documentados.', self.hoy)
        anteriores = {str(p) for p in Path(settings.MEDIA_ROOT).rglob('*') if p.is_file()}
        datos = dict(tipo='CAPACITACION', codigo='ARCHIVO-QA', fecha=self.hoy,
            titulo='Archivo QA', descripcion='Resultado', responsable=self.actor)
        with self.assertRaises(ValidationError):
            registrar_evidencia(self.unidad, self.actor, dict(datos, descripcion=''), verificar=True,
                archivo=SimpleUploadedFile('acta.pdf', pdf))
        despues = {str(p) for p in Path(settings.MEDIA_ROOT).rglob('*') if p.is_file()}
        self.assertEqual(anteriores, despues)
        e = registrar_evidencia(self.unidad, self.actor, datos, verificar=True,
            archivo=SimpleUploadedFile('acta.pdf', pdf))
        self.assertTrue(e.recurso.hash_sha256)
        self.assertEqual(e.recurso.visibilidad, 'interna')
        self.assertTrue(e.recurso.archivo.storage.exists(e.recurso.archivo.name))
        self.client.force_login(self.actor)
        ruta = reverse('respaldo_meta_unidad', args=[self.unidad.slug, e.pk])
        respuesta = self.client.get(ruta)
        self.assertEqual(respuesta.status_code, 200)
        self.assertEqual(respuesta['Content-Type'], 'application/pdf')
        self.assertEqual(b''.join(respuesta.streaming_content), pdf)
        self.assertEqual(self.client.get(reverse('respaldo_meta_unidad', args=[self.otra.slug, e.pk])).status_code, 404)
        director = get_user_model().objects.create_superuser(username='medicion-direccion', password='QA')
        self.client.force_login(director)
        self.assertEqual(self.client.get(ruta).status_code, 200)
        self.client.logout()
        self.assertEqual(self.client.get(ruta).status_code, 302)
        with self.assertRaisesMessage(ValidationError, 'No se cuenta dos veces'):
            registrar_evidencia(self.unidad, self.actor, dict(datos, codigo='MISMO-ARCHIVO'), verificar=True,
                archivo=SimpleUploadedFile('copia.pdf', pdf))
        # Una sustitución/importación que cambia la huella invalida la verificación anterior.
        from apps.recursos.models.recursos import Recurso
        Recurso.objects.filter(pk=e.recurso_id).update(hash_sha256='0' * 64)
        self.assertEqual(self.registros()['gestion_capacitacion'], 0)

    def test_pdf_en_blanco_y_pdf_corrupto_no_acreditan(self):
        from pypdf import PdfWriter
        datos = io.BytesIO()
        pdf = PdfWriter()
        pdf.add_blank_page(width=600, height=800)
        pdf.write(datos)
        blanco = datos.getvalue()
        for contenido in (blanco, b'%PDF-1.4\nArchivo roto'):
            with self.assertRaises(ValidationError):
                registrar_evidencia(self.unidad, self.actor, dict(tipo='CAPACITACION', codigo='BLANCO',
                    fecha=self.hoy, titulo='Acta vacía', descripcion='Ejemplo', responsable=self.actor),
                    verificar=True, archivo=SimpleUploadedFile('acta.pdf', contenido))
        self.assertEqual(self.registros()['gestion_capacitacion'], 0)

    def test_seguridad_primera_entrada_y_todas_inducciones_vigentes(self):
        r = self.reserva()
        requisito = RequisitoAcceso.objects.create(unidad=self.unidad, codigo='IND', nombre='Seguridad', tipo='induccion')
        for i in range(3):
            usuario = get_user_model().objects.create_user(username=f'medicion-nuevo-{i}')
            RegistroIngreso.objects.create(reserva=r, usuario=usuario, nombre=usuario.username, categoria='estudiante')
            if i < 2:
                HabilitacionAcceso.objects.create(usuario=usuario, requisito=requisito,
                    fecha=self.inicio, documento=f'Constancia-{i}')
            if i == 0:
                RegistroIngreso.objects.create(reserva=self.reserva(dia=date(2026, 6, 1)), usuario=usuario,
                    nombre=usuario.username, categoria='estudiante')
        r = self.registros()['mediciones_porcentuales']['SEGURIDAD']
        self.assertEqual((r['numerador'], r['denominador']), (1, 2))
        RequisitoAcceso.objects.create(unidad=self.unidad, codigo='IND-2', nombre='Equipos', tipo='induccion')
        self.assertEqual(self.registros()['mediciones_porcentuales']['SEGURIDAD']['numerador'], 0)

    def test_ingreso_sin_identidad_impide_cumplimiento_falso(self):
        RegistroIngreso.objects.create(reserva=self.reserva(), nombre='Sin identidad')
        r = self.registros()['mediciones_porcentuales']['SEGURIDAD']
        self.assertTrue(r['pendiente'])

    def test_formulario_acotado_y_sin_escrituras_por_get(self):
        self.client.force_login(self.actor)
        ruta = reverse('fuentes_metas_unidad', args=[self.unidad.slug]) + '?anio=2026&corte=B&tipo=CAPACITACION'
        self.assertContains(self.client.get(ruta), 'Guardar evidencia')
        self.assertEqual(EvidenciaGestionUnidad.objects.count(), 0)
        self.assertEqual(self.client.get(reverse('fuentes_metas_unidad', args=[self.otra.slug])).status_code, 403)
        self.assertEqual(self.client.post(ruta, {'accion': 'rectificar', 'evidencia': 'invalido'}).status_code, 404)

    def test_formulario_guarda_verificado_y_muestra_error_sin_archivo(self):
        self.client.force_login(self.actor)
        ruta = reverse('fuentes_metas_unidad', args=[self.unidad.slug]) + '?anio=2026&corte=B&tipo=CAPACITACION'
        datos = dict(codigo='FORM-QA', fecha='2026-10-16', titulo='Capacitación realizada',
            descripcion='Constancia y resultados de la capacitación.', responsable=self.actor.pk,
            verificar='on', enlace='https://example.org/capacitacion/form-qa')
        respuesta = self.client.post(ruta, datos)
        self.assertEqual(respuesta.status_code, 302)
        self.assertEqual(self.registros()['gestion_capacitacion'], 1)
        respuesta = self.client.post(ruta, dict(datos, codigo='SIN-FUENTE', enlace=''))
        self.assertContains(respuesta, 'Adjunta un archivo')
        self.assertEqual(self.registros()['gestion_capacitacion'], 1)

    def test_ejemplos_conservan_marca_incluso_si_se_rectifican(self):
        with override_settings(MEDICION_SOLO_DEMO=True):
            e = self.evidencia()
            self.assertTrue(e.demostracion)
            rectificar_evidencia(self.unidad, self.actor, e.pk, 'Rectificación DEMO')
            self.assertTrue(self.registros()['evidencias_demo'])

    def test_comando_rechaza_base_operativa(self):
        with override_settings(ALLOW_DEMO_DATA_COMMANDS=True, DEBUG=True, MEDICION_SOLO_DEMO=False):
            with self.assertRaises(CommandError):
                call_command('demostrar_medicion_fablab', unidad='fablab-demo', confirmar_datos_demo=True, stdout=io.StringIO())

    @override_settings(ALLOW_DEMO_DATA_COMMANDS=True, DEBUG=True, MEDICION_SOLO_DEMO=True)
    def test_comando_bloquea_nombre_operativo_aunque_se_habiliten_banderas_demo(self):
        anteriores = Unidad.objects.count(), get_user_model().objects.count()
        # Solo se modifica la etiqueta que valida el comando: la conexión real
        # permanece en PostgreSQL QA y el rechazo ocurre antes de consultar.
        with patch.dict(connection.settings_dict, NAME='citt_db'):
            with self.assertRaisesMessage(CommandError, 'base citt_demo_ aislada'):
                call_command('demostrar_medicion_fablab', unidad='fablab-demo',
                             confirmar_datos_demo=True, stdout=io.StringIO())
        self.assertEqual(anteriores, (Unidad.objects.count(), get_user_model().objects.count()))

    @override_settings(ALLOW_DEMO_DATA_COMMANDS=True, DEBUG=True, MEDICION_SOLO_DEMO=True)
    def test_comando_exige_confirmacion_y_rechaza_unidad_que_no_es_demostrativa(self):
        with patch.dict(connection.settings_dict, NAME='test_citt_qa_medicion'):
            with self.assertRaisesMessage(CommandError, 'confirmar-datos-demo'):
                call_command('demostrar_medicion_fablab', unidad='fablab-demo', stdout=io.StringIO())
            with self.assertRaisesMessage(CommandError, 'no pertenece a este escenario'):
                call_command('demostrar_medicion_fablab', unidad=self.unidad.slug,
                             confirmar_datos_demo=True, stdout=io.StringIO())

    @override_settings(ALLOW_DEMO_DATA_COMMANDS=True, DEBUG=True, MEDICION_SOLO_DEMO=True)
    def test_escenario_completo_idempotente_y_mediciones(self):
        with patch.dict(connection.settings_dict, NAME='test_citt_qa_medicion'):
            from apps.documentos.models.expediente import DocumentoExpediente
            opciones = dict(unidad='fablab-demo', confirmar_datos_demo=True, stdout=io.StringIO())
            call_command('demostrar_medicion_fablab', **opciones)
            demo = Unidad.objects.get(slug='fablab-demo')
            documentos = DocumentoExpediente.objects.filter(unidad=demo)
            d = documentos.get(exigido__codigo='INFORME-SEMESTRAL', corte='B')
            lectura = calcular_cierre(d)
            filas = {f['codigo']: f for f in lectura['catalogo']}
            esperados = {'USO': 75, 'DESECHOS': 0, 'SEGURIDAD': 66.67, 'INVENTARIO': 100,
                'CAPACITACION': 100, 'DIFUSION': 100, 'TRANSFERENCIA': 0, 'PRACTICAS': 50,
                'PRACTICAS-PLAN': 100, 'MANTENIMIENTO': 0, 'INVESTIGACION': 100, 'GUIAS': 100,
                'INSPECCIONES': 0}
            self.assertEqual({k: filas[k]['porcentaje'] for k in esperados}, esperados)
            # Los ejemplos sin manifiestos/gestión completa, revisión del universo
            # crítico ni inspecciones mensuales no simulan acreditación documental.
            self.assertEqual(lectura['avance_metas'], 60.9)
            self.assertEqual(lectura['nota'], 0)
            self.assertTrue(lectura['demostracion'])
            self.assertFalse(lectura['plan_aprobado'])
            self.assertEqual(lectura['metodo'], 'metas-laboratorios-1')
            from apps.documentos.presentation.cumplimiento_practicas import conteos_del_periodo
            from apps.documentos.presentation.medicion_metas import resultados_documentados
            from apps.documentos.presentation.expediente import cortes_del_anio
            inicio, fin = cortes_del_anio(self.hoy.year)['B']
            acreditacion = conteos_del_periodo(demo, inicio, fin)
            self.assertEqual((acreditacion['planificaciones_acreditables'], acreditacion['guias_acreditables'],
                              acreditacion['practicas_acreditables']), (6, 1, 3))
            resultados = resultados_documentados(demo, inicio, fin, 'INVESTIGACION')
            self.assertEqual((resultados['verificados'], resultados['reales'], resultados['demostracion']), (1, 0, 1))
            self.assertEqual(EvidenciaGestionUnidad.objects.get(unidad=demo, tipo='INVENTARIO').alcance,
                             ['equipos', 'software', 'espacios', 'insumos'])
            # Las identidades DEMO no incorporan contraseñas de acceso utilizables.
            self.assertFalse(demo.administrador.has_usable_password())
            self.assertFalse(self.client.login(username=demo.administrador.username, password=''))
            self.assertFalse(any(u.has_usable_password() for u in get_user_model().objects.filter(
                username__startswith='demo.fablab.participante.')))
            total = EvidenciaGestionUnidad.objects.filter(unidad=demo).count()
            call_command('demostrar_medicion_fablab', **opciones)
            self.assertEqual(EvidenciaGestionUnidad.objects.filter(unidad=demo).count(), total)
            self.assertFalse(documentos.filter(estado='validado').exists())
            # Incluso con un archivo cargado y firma indicada, un período DEMO no se envía.
            from apps.documentos.presentation.expediente import validar_documento
            d.recurso = EvidenciaGestionUnidad.objects.filter(unidad=demo, recurso__isnull=False).first().recurso
            d.estado, d.firma_verificada, d.entregado_en = 'cargado', True, timezone.now()
            # Este caso comprueba el rechazo de una entrega DEMO del contrato
            # anterior; la guarda del nuevo semestre completo tiene sus
            # propias pruebas y no debe ocultar esta validación independiente.
            d.marco_periodo = 'academico_legacy'
            d.tramo_inicio, d.tramo_fin = inicio, fin
            d.save()
            from tests.integration.utiles import correspondencia_revisada
            with self.assertRaisesMessage(ValidationError, 'demostración'):
                validar_documento(d, demo.administrador,
                                  declaracion_correspondencia=correspondencia_revisada(d))
            d.refresh_from_db()
            self.assertEqual(d.estado, 'cargado')

    @override_settings(ALLOW_DEMO_DATA_COMMANDS=True, DEBUG=True, MEDICION_SOLO_DEMO=True)
    def test_simulacion_revierte_datos_y_archivos(self):
        with patch.dict(connection.settings_dict, NAME='test_citt_qa_medicion'):
            anteriores = {str(p) for p in Path(settings.MEDIA_ROOT).rglob('*') if p.is_file()}
            call_command('demostrar_medicion_fablab', unidad='fablab-simulacion', confirmar_datos_demo=True,
                         simular=True, stdout=io.StringIO())
            self.assertFalse(Unidad.objects.filter(slug='fablab-simulacion').exists())
            self.assertEqual(anteriores, {str(p) for p in Path(settings.MEDIA_ROOT).rglob('*') if p.is_file()})


@override_settings(MEDICION_METAS_HABILITADA=True)
class FuentesDelInformeFirmadoTests(BaseDelExpediente):
    def test_cambiar_fuentes_despues_de_preparar_obliga_a_regenerar_antes_de_enviar(self):
        from apps.documentos.presentation.expediente import validar_documento
        from apps.documentos.presentation.evaluacion_cierre import preparar_cierre
        from apps.documentos.models.expediente import DocumentoElaborado
        from apps.documentos.models.expediente import DocumentoExpediente
        from apps.documentos.presentation.expediente_redaccion import valores_iniciales
        plan = self.documento(self.laboratorio, codigo='PLANIFICACION')
        # Mantener el contrato de esta regresión histórica antes de preparar
        # los archivos: aquí se comprueba que una fuente cambiada invalida lo
        # firmado, sin intentar acreditar un semestre de gestión anticipado.
        DocumentoExpediente.objects.filter(unidad=self.laboratorio, anio=plan.anio,
            corte=plan.corte).update(marco_periodo='academico_legacy')
        plan.refresh_from_db()
        DocumentoElaborado.objects.create(documento=plan, contenido=valores_iniciales(plan), version=1)
        documento, _ = self.archivado(self.laboratorio)
        preparado = preparar_cierre(documento, self.coordinador)
        self.assertIn('CAPACITACION', {f['codigo'] for f in preparado['catalogo']})
        registrar_evidencia(self.laboratorio, self.coordinador, dict(tipo='CAPACITACION',
            codigo='POSTERIOR-A-LA-FIRMA', fecha=timezone.localdate(), titulo='Capacitación posterior',
            descripcion='Actividad registrada después de preparar el archivo firmado.',
            responsable=self.coordinador, enlace='https://example.org/constancia-posterior'), verificar=True)
        with self.assertRaisesMessage(ValidationError, 'fuentes de medición cambiaron'):
            validar_documento(documento, self.coordinador)
        documento.refresh_from_db()
        self.assertNotEqual(documento.estado, 'validado')
