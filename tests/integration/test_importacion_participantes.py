"""Listas de participantes: lectura segura, revisión sin altas y confirmación aislada."""
import io
import zipfile
from datetime import date, timedelta
from decimal import Decimal
from unittest.mock import patch

from allauth.account.models import EmailAddress
from django.contrib.auth import get_user_model
from django.core.exceptions import PermissionDenied, ValidationError
from django.core.files.uploadedfile import SimpleUploadedFile
from django.db import IntegrityError, transaction
from django.test import SimpleTestCase, TestCase, override_settings
from django.urls import reverse
from django.utils import timezone
from openpyxl import Workbook, load_workbook

from apps.formacion.presentation.certificados_cursos import emitir_si_corresponde
from apps.recursos.presentation.importacion_archivos import leer_participantes
from apps.formacion.presentation.importacion_participantes import confirmar_importacion, revisar_importacion
from apps.formacion.presentation.importacion_participantes_views import CLAVE_SESION
from apps.formacion.presentation.matriculas_cursos import aplicar_invitaciones, cupos_disponibles
from apps.formacion.models.cursos import CertificadoCurso, Curso, EdicionCurso, InscripcionCurso, ParticipanteEvento
from apps.formacion.models.cursos_certificacion import ConfiguracionCertificadoCurso
from apps.formacion.models.cursos_inscripcion import InvitacionCurso
from apps.directorio_unidades.models.core import Unidad
from apps.core.models.usuarios_base import UserProfile


def csv_archivo(texto, nombre='participantes.csv'):
    return SimpleUploadedFile(nombre, texto.encode('utf-8-sig'), content_type='text/csv')


def xlsx_archivo(filas):
    libro = Workbook()
    for fila in filas:
        libro.active.append(fila)
    contenido = io.BytesIO()
    libro.save(contenido)
    libro.close()
    return SimpleUploadedFile('participantes.xlsx', contenido.getvalue())


def filas_evento(*datos):
    return [{'numero': i, 'datos': {'documento': documento, 'nombres_completos': nombre}, 'errores': []}
            for i, (documento, nombre) in enumerate(datos, start=2)]


class LecturaParticipantesTests(SimpleTestCase):
    def test_csv_y_excel_preservan_documentos_textuales_y_nombres_unicode(self):
        datos = [['cédula', 'nombres completos'], ['0102030400', 'María José Núñez']]
        for archivo in (xlsx_archivo(datos), csv_archivo('cédula;nombres completos\n0102030400;María José Núñez\n')):
            with self.subTest(nombre=archivo.name):
                filas = leer_participantes(archivo, 'evento')
                self.assertEqual(filas[0]['datos']['documento'], '0102030400')
                self.assertEqual(filas[0]['datos']['nombres_completos'], 'María José Núñez')
                self.assertEqual(filas[0]['errores'], [])

    def test_rechaza_documento_numerico_que_puede_haber_perdido_ceros(self):
        filas = leer_participantes(xlsx_archivo([['cedula', 'nombres_completos'], [102030400, 'Persona Ejemplo']]), 'evento')
        self.assertIn('ceros iniciales', ' '.join(filas[0]['errores']))

    def test_rechaza_formulas_y_vinculos_externos_del_excel(self):
        with self.assertRaisesMessage(ValidationError, 'fórmulas'):
            leer_participantes(xlsx_archivo([['cedula', 'nombres_completos'], ['DOC-10', '=SUM(1,2)']]), 'evento')
        libro = Workbook()
        libro.active.append(['cedula', 'nombres_completos'])
        libro.active.append(['DOC-10', 'Persona Ejemplo'])
        libro.active['B2'].hyperlink = 'https://example.invalid/datos'
        contenido = io.BytesIO()
        libro.save(contenido)
        libro.close()
        with self.assertRaisesMessage(ValidationError, 'vínculos'):
            leer_participantes(SimpleUploadedFile('enlace.xlsx', contenido.getvalue()), 'evento')

    def test_todas_las_filas_invalidas_y_duplicadas_tienen_errores(self):
        filas = leer_participantes(csv_archivo('cedula,nombres_completos\nDOC-10,Persona Ejemplo\nDOC-10,Otra Persona\n1234567890,<script>Nombre</script>\n'), 'evento')
        self.assertTrue(all(fila['errores'] for fila in filas))
        self.assertIn('fila 3', ' '.join(filas[0]['errores']))

    def test_limites_cabecera_vacio_extension_y_zip_expandido(self):
        archivos = [csv_archivo('cedula,nombres_completos\n'), csv_archivo('cedula,nombre_extra\nDOC-1,Persona'),
            csv_archivo('x' * (2 * 1024 * 1024 + 1)), csv_archivo('texto', 'archivo.xls'),
            csv_archivo('cedula,nombres_completos\n' + '\n'.join(f'DOC-{i},Persona Ejemplo' for i in range(501)))]
        comprimido = io.BytesIO()
        with zipfile.ZipFile(comprimido, 'w', zipfile.ZIP_DEFLATED) as paquete:
            paquete.writestr('xl/worksheets/sheet1.xml', 'x' * (21 * 1024 * 1024))
        archivos.append(SimpleUploadedFile('grande.xlsx', comprimido.getvalue()))
        for archivo in archivos:
            with self.subTest(nombre=archivo.name), self.assertRaises(ValidationError):
                leer_participantes(archivo, 'evento')

    def test_correo_vacio_se_admite_para_resolver_una_cuenta_en_backend(self):
        filas = leer_participantes(csv_archivo('cedula,nombres_completos,correo\nDOC-10,Persona Ejemplo,\n'), 'matricula')
        self.assertEqual(filas[0]['errores'], [])
        self.assertEqual(filas[0]['datos']['correo'], '')

    def test_excel_no_confia_en_dimension_declarada_para_ocultar_filas(self):
        original = xlsx_archivo([['cedula', 'nombres_completos'], ['DOC-100', 'Persona Ejemplo']])
        entrada, salida = io.BytesIO(original.read()), io.BytesIO()
        with zipfile.ZipFile(entrada) as origen, zipfile.ZipFile(salida, 'w', zipfile.ZIP_DEFLATED) as destino:
            for nombre in origen.namelist():
                contenido = origen.read(nombre)
                if nombre == 'xl/worksheets/sheet1.xml':
                    contenido = contenido.replace(b'<row r="2">', b'<row r="502">').replace(b'r="A2"', b'r="A502"').replace(b'r="B2"', b'r="B502"')
                destino.writestr(nombre, contenido)
        with self.assertRaisesMessage(ValidationError, '500'):
            leer_participantes(SimpleUploadedFile('dimension.xlsx', salida.getvalue()), 'evento')


class ImportacionParticipantesTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        users = get_user_model()
        cls.gestor = users.objects.create_user('gestor-importacion', 'gestor@example.invalid', 'clave')
        cls.alumno = users.objects.create_user('alumno-importacion', 'alumno@example.invalid', 'clave', first_name='Persona', last_name='Inscrita')
        cls.ajeno = users.objects.create_user('ajeno-importacion', 'ajeno@example.invalid', 'clave')
        cls.unidad = Unidad.objects.create(nombre='Laboratorio de importación', slug='lab-importacion', dependencia='laboratorios',
            administrador=cls.gestor, descripcion='.', fecha_inicio=date(2026, 1, 1))
        cls.otra = Unidad.objects.create(nombre='Otra unidad', slug='lab-importacion-ajeno', dependencia='laboratorios',
            administrador=cls.ajeno, descripcion='.', fecha_inicio=date(2026, 1, 1))
        cls.curso = Curso.objects.create(unidad=cls.unidad, codigo='IMPORT-001', nombre='Seminario de logística',
            publicado=True, emite_certificado=True, duracion_horas=8)
        cls.curso_ajeno = Curso.objects.create(unidad=cls.otra, codigo='IMPORT-002', nombre='Actividad ajena', publicado=True)
        hoy = timezone.localdate()
        cls.edicion = EdicionCurso.objects.create(curso=cls.curso, nombre='Grupo A', anio=hoy.year,
            inicio=hoy + timedelta(days=1), fin=hoy + timedelta(days=2), horas_certificadas=Decimal('7.5'), cupo=3)
        cls.segunda = EdicionCurso.objects.create(curso=cls.curso, nombre='Grupo B', anio=hoy.year,
            inicio=hoy + timedelta(days=1), fin=hoy + timedelta(days=2), horas_certificadas=8)
        cls.grupo_ajeno = EdicionCurso.objects.create(curso=cls.curso_ajeno, nombre='Grupo ajeno', anio=hoy.year)
        cls.config = ConfiguracionCertificadoCurso.objects.create(curso=cls.curso, categoria_evento='seminario', emisor='Facultad organizadora')
        EmailAddress.objects.create(user=cls.alumno, email=cls.alumno.email, verified=True, primary=True)
        perfil, _ = UserProfile.objects.get_or_create(user=cls.alumno)
        perfil.cedula = 'DOC-100'
        perfil.save(update_fields=['cedula'])

    def url(self, nombre, *extra):
        return reverse(nombre, args=[self.unidad.slug, self.curso.codigo, *extra])

    def confirmar(self, filas=None, **extra):
        return confirmar_importacion(self.edicion, filas or filas_evento(('DOC-200', 'María Pérez')), self.gestor,
            'evento', 'asistencia', 'Asistencia verificada en el registro del seminario.', True, **extra)

    def subir(self, modo='evento', texto='cedula,nombres_completos\nDOC-200,María Pérez\n', edicion=None):
        return self.client.post(self.url('importar_participantes_curso'), {'accion': 'revisar',
            'edicion': (edicion or self.edicion).pk, 'modo': modo, 'tipo': 'asistencia',
            'motivo': 'Asistencia verificada en el registro del seminario.', 'archivo': csv_archivo(texto)})

    def test_preview_completa_no_crea_personas_cuentas_ni_certificados(self):
        usuarios = get_user_model().objects.count()
        filas = filas_evento(('DOC-200', 'María Pérez'))
        actividad = revisar_importacion(self.edicion, filas, self.gestor, 'evento', 'asistencia', 'Registro del seminario verificado.', True)
        self.assertEqual(actividad['horas'], Decimal('7.5'))
        self.assertEqual(actividad['emisor'], 'Facultad organizadora')
        self.assertEqual(ParticipanteEvento.objects.count(), 0)
        self.assertEqual(CertificadoCurso.objects.count(), 0)
        self.assertEqual(get_user_model().objects.count(), usuarios)

    def test_evento_emite_sin_cuentas_ni_inscripciones_y_es_idempotente(self):
        usuarios = get_user_model().objects.count()
        resultado = self.confirmar()
        repetido = self.confirmar()
        self.assertEqual(resultado[0]['certificado_id'], repetido[0]['certificado_id'])
        certificado = CertificadoCurso.objects.get()
        self.assertIsNone(certificado.inscripcion_id)
        self.assertEqual(certificado.curso_origen, self.curso)
        self.assertEqual(certificado.edicion_origen, self.edicion)
        self.assertEqual(certificado.horas, Decimal('7.5'))
        self.assertEqual(certificado.emitido_por, self.gestor)
        self.assertTrue(certificado.motivo_emision)
        self.assertIsNone(certificado.nota_final)
        self.assertEqual(InscripcionCurso.objects.count(), 0)
        self.assertEqual(ParticipanteEvento.objects.count(), 1)
        self.assertEqual(get_user_model().objects.count(), usuarios)

    def test_reutiliza_inscripcion_aceptada_y_rechaza_identidad_conflictiva(self):
        inscripcion = InscripcionCurso.objects.create(edicion=self.edicion, usuario=self.alumno,
            estado='aceptada', documento='DOC-100', nombres_completos='Persona Inscrita')
        resultado = self.confirmar(filas_evento(('DOC-100', 'Persona Inscrita')))
        self.assertEqual(CertificadoCurso.objects.get(pk=resultado[0]['certificado_id']).inscripcion, inscripcion)
        self.assertEqual(ParticipanteEvento.objects.count(), 0)
        with self.assertRaises(ValidationError):
            self.confirmar(filas_evento(('DOC-100', 'Otra Identidad')))
        self.assertEqual(CertificadoCurso.objects.count(), 1)

    def test_error_en_segunda_emision_revierte_toda_la_lista(self):
        from apps.formacion.presentation import importacion_participantes as servicio
        original = servicio.emitir_certificado_externo
        def emitir(persona, *args, **kwargs):
            if persona.documento == 'DOC-201':
                raise ValidationError('Falló la comprobación de la segunda fila.')
            return original(persona, *args, **kwargs)
        with patch.object(servicio, 'emitir_certificado_externo', side_effect=emitir), self.assertRaises(ValidationError):
            self.confirmar(filas_evento(('DOC-200', 'María Pérez'), ('DOC-201', 'Luis Paz')))
        self.assertEqual(ParticipanteEvento.objects.count(), 0)
        self.assertEqual(CertificadoCurso.objects.count(), 0)

    def test_no_aprobacion_curso_sin_fechas_roles_ni_gestor_ajeno(self):
        filas = filas_evento(('DOC-200', 'María Pérez'))
        with self.assertRaises(PermissionDenied):
            confirmar_importacion(self.edicion, filas, self.ajeno, 'evento', 'asistencia', 'Registro verificado del seminario.', True)
        with self.assertRaises(ValidationError):
            confirmar_importacion(self.edicion, filas, self.gestor, 'evento', 'aprobacion', 'Registro verificado del seminario.', True)
        self.config.categoria_evento = 'curso'
        self.config.save(update_fields=['categoria_evento'])
        with self.assertRaises(ValidationError):
            self.confirmar()
        self.config.categoria_evento = 'seminario'
        self.config.save(update_fields=['categoria_evento'])
        self.edicion.fin = None
        self.edicion.save(update_fields=['fin'])
        with self.assertRaises(ValidationError):
            self.confirmar()
        self.assertEqual(CertificadoCurso.objects.count(), 0)

    def test_matricula_de_pago_no_exonera_y_reserva_cupo_incluso_al_vincular_invitacion(self):
        self.curso.costo = Decimal('25.00')
        self.curso.save(update_fields=['costo'])
        filas = [{'numero': 2, 'datos': {'documento': 'DOC-100', 'nombres_completos': 'Persona Inscrita', 'correo': self.alumno.email}, 'errores': []},
                 {'numero': 3, 'datos': {'documento': 'DOC-300', 'nombres_completos': 'Persona Invitada', 'correo': 'invitada@example.invalid'}, 'errores': []}]
        confirmar_importacion(self.edicion, filas, self.gestor, 'matricula')
        inscripcion = InscripcionCurso.objects.get(usuario=self.alumno)
        self.assertEqual(inscripcion.estado, 'pendiente')
        self.assertEqual(inscripcion.pago.estado, 'pendiente')
        self.assertEqual(inscripcion.pago.monto, Decimal('25.00'))
        self.assertEqual(inscripcion.pago.descuento, 0)
        self.assertEqual(cupos_disponibles(self.edicion), 1)
        self.assertFalse(InvitacionCurso.objects.get(correo=self.alumno.email).exonerar_matricula)
        confirmar_importacion(self.edicion, filas, self.gestor, 'matricula')
        self.assertEqual(InscripcionCurso.objects.count(), 1)
        self.assertEqual(InvitacionCurso.objects.count(), 2)
        invitada = get_user_model().objects.create_user('invitada-importacion', 'invitada@example.invalid', 'clave')
        EmailAddress.objects.create(user=invitada, email=invitada.email, verified=True)
        vinculadas = aplicar_invitaciones(invitada)
        self.assertEqual(len(vinculadas), 1)
        self.assertEqual(vinculadas[0].estado, 'pendiente')
        self.assertEqual(vinculadas[0].pago.monto, Decimal('25.00'))
        self.assertEqual(cupos_disponibles(self.edicion), 1)
        self.assertIsNone(emitir_si_corresponde(vinculadas[0]))

    def test_cupo_total_insuficiente_no_guarda_y_correo_vacio_resuelve_cuenta_verificada(self):
        filas = [{'numero': 2, 'datos': {'documento': 'DOC-100', 'nombres_completos': 'Persona Inscrita', 'correo': ''}, 'errores': []}]
        revisar_importacion(self.edicion, filas, self.gestor, 'matricula')
        self.assertEqual(filas[0]['datos']['correo'], self.alumno.email)
        self.edicion.cupo = 0
        self.edicion.save(update_fields=['cupo'])
        with self.assertRaises(ValidationError):
            confirmar_importacion(self.edicion, filas, self.gestor, 'matricula')
        self.assertEqual(InscripcionCurso.objects.count(), 0)
        self.assertEqual(InvitacionCurso.objects.count(), 0)
        desconocida = [{'numero': 2, 'datos': {'documento': 'DOC-999', 'nombres_completos': 'Persona Sin Cuenta', 'correo': ''}, 'errores': []}]
        revisar_importacion(self.edicion, desconocida, self.gestor, 'matricula')
        self.assertIn('Completa el correo', ' '.join(desconocida[0]['errores']))

    def test_exactamente_una_identidad_y_certificado_vigente_unico_en_base(self):
        resultado = self.confirmar()
        certificado = CertificadoCurso.objects.get(pk=resultado[0]['certificado_id'])
        campos = {'nombre': 'Persona', 'curso_nombre': 'Evento', 'clasificacion': 'Seminario', 'edicion': 'Grupo A', 'unidad_nombre': 'Laboratorio'}
        for identidad in ({}, {'participante_evento': certificado.participante_evento}):
            with self.subTest(identidad=bool(identidad)), self.assertRaises(IntegrityError), transaction.atomic():
                CertificadoCurso.objects.create(codigo='CERT-CONSTRAINT', **identidad, **campos)
        inscripcion = InscripcionCurso.objects.create(edicion=self.edicion, usuario=self.alumno)
        with self.assertRaises(IntegrityError), transaction.atomic():
            CertificadoCurso.objects.create(inscripcion=inscripcion, participante_evento=certificado.participante_evento,
                codigo='CERT-BOTH-IDS', **campos)

    def test_vistas_exigen_gestor_grupo_y_token_de_la_misma_sesion(self):
        self.client.force_login(self.ajeno)
        self.assertEqual(self.client.get(self.url('importar_participantes_curso')).status_code, 403)
        self.client.force_login(self.gestor)
        respuesta = self.subir(edicion=self.grupo_ajeno)
        self.assertEqual(respuesta.status_code, 200)
        self.assertTrue(respuesta.context['formulario'].errors)
        respuesta = self.subir()
        self.assertEqual(respuesta.status_code, 200)
        self.assertContains(respuesta, 'Facultad organizadora')
        estado = self.client.session[CLAVE_SESION]
        self.assertEqual(CertificadoCurso.objects.count(), 0)
        fallida = self.client.post(self.url('importar_participantes_curso'), {'accion': 'confirmar', 'token': 'alterado', 'confirmacion': 1})
        self.assertContains(fallida, 'no corresponde a esta sesión')
        self.assertEqual(CertificadoCurso.objects.count(), 0)
        self.client.force_login(self.ajeno)
        self.assertEqual(self.client.post(self.url('importar_participantes_curso'), {'accion': 'confirmar', 'token': estado['token'], 'confirmacion': 1}).status_code, 403)

    def test_confirmacion_web_idempotente_zip_y_grupo_muestran_certificados_externos(self):
        self.client.force_login(self.gestor)
        self.subir()
        token = self.client.session[CLAVE_SESION]['token']
        datos = {'accion': 'confirmar', 'token': token, 'confirmacion': '1'}
        respuesta = self.client.post(self.url('importar_participantes_curso'), datos)
        self.assertContains(respuesta, 'Importación completada')
        self.assertContains(respuesta, 'data-ver-pdf')
        self.client.post(self.url('importar_participantes_curso'), datos)
        self.assertEqual(CertificadoCurso.objects.count(), 1)
        descarga = self.client.post(self.url('descargar_certificados_importados'), {'token': token})
        with zipfile.ZipFile(io.BytesIO(b''.join(descarga.streaming_content))) as paquete:
            self.assertEqual(len(paquete.namelist()), 1)
            self.assertTrue(paquete.read(paquete.namelist()[0]).startswith(b'%PDF'))
        listado = self.client.get(self.url('inscritos_curso') + f'?edicion={self.edicion.pk}')
        self.assertContains(listado, 'Participantes externos del evento')
        self.assertContains(listado, 'María Pérez')
        self.assertEqual(listado.context['resumen_grupo']['certificados'], 1)

    def test_cambio_de_actividad_desde_revision_exige_nueva_revision(self):
        self.client.force_login(self.gestor)
        self.subir()
        token = self.client.session[CLAVE_SESION]['token']
        self.edicion.horas_certificadas = 10
        self.edicion.save(update_fields=['horas_certificadas'])
        respuesta = self.client.post(self.url('importar_participantes_curso'), {'accion': 'confirmar', 'token': token, 'confirmacion': '1'})
        self.assertContains(respuesta, 'datos de la actividad cambiaron')
        self.assertEqual(CertificadoCurso.objects.count(), 0)

    def test_anulacion_reemision_y_descarga_aisladas_y_qr_no_reactiva_anulado(self):
        certificado = CertificadoCurso.objects.get(pk=self.confirmar()[0]['certificado_id'])
        self.client.force_login(self.gestor)
        self.assertEqual(self.client.get(self.url('certificado_curso_gestor', certificado.pk)).status_code, 200)
        ajena = reverse('certificado_curso_gestor', args=[self.otra.slug, self.curso_ajeno.codigo, certificado.pk])
        self.client.force_login(self.ajeno)
        self.assertEqual(self.client.get(ajena).status_code, 404)
        self.client.force_login(self.gestor)
        self.client.post(self.url('anular_certificado', certificado.pk), {'motivo': 'Corrección institucional del registro.'})
        certificado.refresh_from_db()
        self.assertTrue(certificado.anulado)
        with self.assertRaisesMessage(ValidationError, 'anulado'):
            self.confirmar()
        self.client.post(self.url('reemitir_certificado', certificado.pk))
        self.assertEqual(CertificadoCurso.objects.filter(anulado=False).count(), 1)
        self.assertEqual(CertificadoCurso.objects.count(), 2)
        self.client.logout()
        verificacion = self.client.get(reverse('verificar_certificado', args=[certificado.codigo]) + '?formato=pdf')
        self.assertContains(verificacion, 'Certificado anulado')
        self.assertNotEqual(verificacion['Content-Type'], 'application/pdf')

    def test_plantillas_descargables_correo_y_cedula_como_texto(self):
        self.client.force_login(self.gestor)
        respuesta = self.client.get(self.url('plantilla_participantes_curso') + '?modo=evento')
        libro = load_workbook(io.BytesIO(respuesta.content))
        try:
            hoja = libro.active
            self.assertEqual([c.value for c in hoja[1]], ['cedula', 'nombres_completos'])
            self.assertEqual(hoja['A2'].number_format, '@')
            self.assertEqual(hoja.max_row, 501)
        finally:
            libro.close()
        with self.assertRaisesMessage(ValidationError, 'no contiene participantes'):
            leer_participantes(SimpleUploadedFile('plantilla.xlsx', respuesta.content), 'evento')
        csv = self.client.get(self.url('plantilla_participantes_curso') + '?modo=matricula&formato=csv')
        self.assertIn('cedula,nombres_completos,correo', csv.content.decode('utf-8-sig'))

    @override_settings(SESSION_ENGINE='django.contrib.sessions.backends.signed_cookies')
    def test_sesiones_de_cookie_no_reciben_listas_con_datos_personales(self):
        self.client.force_login(self.gestor)
        self.assertEqual(self.client.get(self.url('importar_participantes_curso')).status_code, 503)

    def test_documento_historico_en_minusculas_reutiliza_matricula_y_detecta_ambiguedad(self):
        inscripcion = InscripcionCurso.objects.create(edicion=self.edicion, usuario=self.alumno, estado='aceptada',
            documento='doc-100', nombres_completos='Persona Inscrita')
        resultado = self.confirmar(filas_evento(('DOC-100', 'Persona Inscrita')))
        self.assertEqual(CertificadoCurso.objects.get(pk=resultado[0]['certificado_id']).inscripcion, inscripcion)
        ParticipanteEvento.objects.create(edicion=self.edicion, documento='DOC-100', nombres_completos='Persona Inscrita')
        filas = filas_evento(('DOC-100', 'Persona Inscrita'))
        revisar_importacion(self.edicion, filas, self.gestor, 'evento', 'asistencia', 'Registro del evento verificado.', True)
        self.assertIn('varios registros', ' '.join(filas[0]['errores']))
        with self.assertRaises(ValidationError):
            self.confirmar(filas_evento(('DOC-100', 'Persona Inscrita')))
        self.assertEqual(CertificadoCurso.objects.count(), 1)

    def test_cedula_de_perfil_reutiliza_inscripcion_sin_documento_copiado(self):
        inscripcion = InscripcionCurso.objects.create(edicion=self.edicion, usuario=self.alumno, estado='aceptada')
        resultado = self.confirmar(filas_evento(('DOC-100', 'Persona Inscrita')))
        certificado = CertificadoCurso.objects.get(pk=resultado[0]['certificado_id'])
        self.assertEqual(certificado.inscripcion, inscripcion)
        self.assertEqual(certificado.documento, 'DOC-100')
        self.assertEqual(ParticipanteEvento.objects.count(), 0)

    def test_confirmacion_revalida_cupo_despues_de_la_revision(self):
        self.edicion.cupo = 1
        self.edicion.save(update_fields=['cupo'])
        filas = [{'numero': 2, 'datos': {'documento': 'DOC-100', 'nombres_completos': 'Persona Inscrita', 'correo': self.alumno.email}, 'errores': []}]
        revisar_importacion(self.edicion, filas, self.gestor, 'matricula')
        InvitacionCurso.objects.create(edicion=self.edicion, correo='reservado@example.invalid',
            documento='DOC-400', nombres_completos='Plaza Reservada')
        with self.assertRaises(ValidationError):
            confirmar_importacion(self.edicion, filas, self.gestor, 'matricula')
        self.assertEqual(InscripcionCurso.objects.count(), 0)
        self.assertEqual(InvitacionCurso.objects.count(), 1)

    def test_pago_verificado_se_conserva_y_no_se_aprueba_por_importar(self):
        from apps.formacion.models.cursos_inscripcion import PagoInscripcion
        self.curso.costo = Decimal('25.00')
        self.curso.save(update_fields=['costo'])
        inscripcion = InscripcionCurso.objects.create(edicion=self.edicion, usuario=self.alumno, estado='pendiente',
            documento='DOC-100', nombres_completos='Persona Inscrita')
        pago = PagoInscripcion.objects.create(inscripcion=inscripcion, monto_original=25, monto=20,
            descuento=20, estado='verificado', referencia='Comprobante conservado')
        filas = [{'numero': 2, 'datos': {'documento': 'DOC-100', 'nombres_completos': 'Persona Inscrita', 'correo': self.alumno.email}, 'errores': []}]
        confirmar_importacion(self.edicion, filas, self.gestor, 'matricula')
        inscripcion.refresh_from_db()
        pago.refresh_from_db()
        self.assertEqual(inscripcion.estado, 'aceptada')
        self.assertEqual(pago.estado, 'verificado')
        self.assertEqual(pago.monto, Decimal('20.00'))
        self.assertEqual(pago.referencia, 'Comprobante conservado')
        self.assertIsNone(emitir_si_corresponde(inscripcion))
        self.assertEqual(CertificadoCurso.objects.count(), 0)

    def test_revision_expirada_o_sin_confirmacion_no_emite_y_zip_rechaza_anulados(self):
        self.client.force_login(self.gestor)
        self.subir()
        estado = self.client.session[CLAVE_SESION]
        respuesta = self.client.post(self.url('importar_participantes_curso'), {'accion': 'confirmar', 'token': estado['token']})
        self.assertContains(respuesta, 'Confirma que revisaste')
        estado['creado'] = 0
        session = self.client.session
        session[CLAVE_SESION] = estado
        session.save()
        respuesta = self.client.post(self.url('importar_participantes_curso'), {'accion': 'confirmar', 'token': estado['token'], 'confirmacion': 1})
        self.assertContains(respuesta, 'expiró')
        self.assertEqual(CertificadoCurso.objects.count(), 0)
        self.subir()
        token = self.client.session[CLAVE_SESION]['token']
        self.client.post(self.url('importar_participantes_curso'), {'accion': 'confirmar', 'token': token, 'confirmacion': 1})
        certificado = CertificadoCurso.objects.get()
        certificado.anulado = True
        certificado.save(update_fields=['anulado'])
        self.assertEqual(self.client.post(self.url('descargar_certificados_importados'), {'token': token}).status_code, 409)

    def test_importacion_no_revoca_exoneracion_previamente_autorizada_por_unidad(self):
        self.curso.costo = Decimal('25.00')
        self.curso.save(update_fields=['costo'])
        invitacion = InvitacionCurso.objects.create(edicion=self.edicion, correo=self.alumno.email,
            documento='DOC-100', nombres_completos='Persona Inscrita', exonerar_matricula=True)
        filas = [{'numero': 2, 'datos': {'documento': 'DOC-100', 'nombres_completos': 'Persona Inscrita', 'correo': self.alumno.email}, 'errores': []}]
        confirmar_importacion(self.edicion, filas, self.gestor, 'matricula')
        invitacion.refresh_from_db()
        self.assertTrue(invitacion.exonerar_matricula)
        self.assertEqual(invitacion.inscripcion.estado, 'aceptada')
        self.assertEqual(invitacion.inscripcion.pago.estado, 'exonerado')
        self.assertEqual(invitacion.inscripcion.pago.monto, Decimal('0.00'))

    def test_reemision_externa_detecta_cedula_del_perfil_en_matricula_historica(self):
        # La persona recibió un certificado externo y después aparece una matrícula
        # histórica cuyo documento vive en su perfil, no en la copia de matrícula.
        resultado = self.confirmar(filas_evento(('DOC-100', 'Persona Inscrita')))
        anterior = CertificadoCurso.objects.get(pk=resultado[0]['certificado_id'])
        matricula = InscripcionCurso.objects.create(edicion=self.edicion, usuario=self.alumno,
            estado='aceptada', documento='', nombres_completos='Persona Inscrita')
        from apps.formacion.presentation.certificados_cursos import emitir_certificado_externo
        conservado = emitir_certificado_externo(anterior.participante_evento, self.gestor, 'asistencia',
            'Asistencia verificada en el registro del seminario.', True)
        self.assertEqual(conservado.pk, anterior.pk)
        self.assertEqual(conservado.codigo, anterior.codigo)
        self.assertEqual(conservado.diseno_certificado, anterior.diseno_certificado)
        verificacion = reverse('verificar_certificado', args=[anterior.codigo])
        self.assertContains(self.client.get(verificacion), anterior.codigo)
        self.assertTrue(self.client.get(verificacion, {'formato': 'pdf'}).content.startswith(b'%PDF'))
        CertificadoCurso.objects.filter(pk=anterior.pk).update(anulado=True)
        with self.assertRaisesMessage(ValidationError, 'matrícula'):
            emitir_certificado_externo(anterior.participante_evento, self.gestor, 'asistencia',
                'Asistencia verificada en el registro del seminario.', True, reemitir=True)
        self.assertEqual(CertificadoCurso.objects.count(), 1)
        self.assertFalse(CertificadoCurso.objects.filter(anulado=False).exists())
        self.assertEqual(InscripcionCurso.objects.get(pk=matricula.pk).documento, '')
        # Una copia explícita distinta prevalece sobre una cédula de perfil posterior.
        matricula.documento = 'DOC-OTRA-PERSONA'
        matricula.save(update_fields=['documento'])
        reemitido = emitir_certificado_externo(anterior.participante_evento, self.gestor, 'asistencia',
            'Asistencia verificada en el registro del seminario.', True, reemitir=True)
        self.assertEqual(reemitido.documento, 'DOC-100')

    def test_matricula_posterior_no_duplica_certificado_externo_del_mismo_grupo(self):
        from apps.formacion.presentation.certificados_cursos import emitir_certificado_evento
        from apps.formacion.models.cursos import LeccionCurso, ModuloCurso, ProgresoLeccion
        self.confirmar(filas_evento(('DOC-100', 'Persona Inscrita')))
        matricula = InscripcionCurso.objects.create(edicion=self.edicion, usuario=self.alumno,
            estado='aceptada', documento='', nombres_completos='Persona Inscrita')
        modulo = ModuloCurso.objects.create(curso=self.curso, titulo='Introducción')
        leccion = LeccionCurso.objects.create(modulo=modulo, titulo='Lectura', tipo='texto')
        ProgresoLeccion.objects.create(inscripcion=matricula, leccion=leccion)
        with self.assertRaisesMessage(ValidationError, 'identidad'):
            emitir_certificado_evento(matricula, self.gestor, 'asistencia',
                'Asistencia verificada en el registro del seminario.', True)
        self.assertIsNone(emitir_si_corresponde(matricula))
        self.assertEqual(CertificadoCurso.objects.count(), 1)
        self.assertFalse(matricula.certificados.exists())

    def test_identidad_externa_en_otro_grupo_no_bloquea_certificacion(self):
        from apps.formacion.presentation.certificados_cursos import emitir_certificado_evento
        self.confirmar(filas_evento(('DOC-100', 'Persona Inscrita')))
        matricula = InscripcionCurso.objects.create(edicion=self.segunda, usuario=self.alumno,
            estado='aceptada', documento='', nombres_completos='Persona Inscrita')
        certificado = emitir_certificado_evento(matricula, self.gestor, 'asistencia',
            'Asistencia verificada en el registro del seminario.', True)
        self.assertEqual(certificado.inscripcion, matricula)
        self.assertEqual(CertificadoCurso.objects.count(), 2)
        ParticipanteEvento.objects.create(edicion=self.segunda, documento='DOC-100',
            nombres_completos='Persona Inscrita')
        self.assertEqual(emitir_si_corresponde(matricula).pk, certificado.pk)
        self.assertEqual(emitir_certificado_evento(matricula, self.gestor, 'asistencia',
            'Asistencia verificada en el registro del seminario.', True).pk, certificado.pk)
        self.assertEqual(CertificadoCurso.objects.count(), 2)

    def test_emision_automatica_no_duplica_identidad_externa_previa(self):
        from apps.formacion.models.cursos import LeccionCurso, ModuloCurso, ProgresoLeccion
        self.confirmar(filas_evento(('DOC-100', 'Persona Inscrita')))
        matricula = InscripcionCurso.objects.create(edicion=self.edicion, usuario=self.alumno,
            estado='aceptada', documento='', nombres_completos='Persona Inscrita')
        modulo = ModuloCurso.objects.create(curso=self.curso, titulo='Introducción')
        leccion = LeccionCurso.objects.create(modulo=modulo, titulo='Lectura', tipo='texto')
        ProgresoLeccion.objects.create(inscripcion=matricula, leccion=leccion)
        self.assertIsNone(emitir_si_corresponde(matricula))
        self.assertEqual(CertificadoCurso.objects.count(), 1)
