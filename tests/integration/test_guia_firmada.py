"""Versión firmada con certificado electrónico (FirmaEC) de la guía aprobada."""

from tests.integration.utiles import verificar_pertenencia

import hashlib
import tempfile
from unittest.mock import patch
from datetime import date

from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase, override_settings
from django.urls import reverse

from apps.reservas.presentation.guia_firma_certificada import validar_pdf_firmado
from apps.reservas.models.reservas import GuiaActividadReserva
from apps.directorio_unidades.models.core import Unidad

PDF_FIRMADO = (
    b'%PDF-1.7\n1 0 obj << /Type /Catalog >> endobj\n'
    b'2 0 obj << /Type /Sig /Filter /Adobe.PPKLite /SubFilter /ETSI.CAdES.detached '
    b'/ByteRange [0 120 240 60] /Contents <00> >> endobj\n'
    b'trailer << /Root 1 0 R >>\n%%EOF\n'
)
PDF_SIN_FIRMA = b'%PDF-1.7\n1 0 obj << /Type /Catalog >> endobj\ntrailer << /Root 1 0 R >>\n%%EOF\n'


class ValidacionPdfFirmadoTests(TestCase):
    def test_limita_la_lectura_aunque_el_tamano_declarado_sea_incorrecto(self):
        archivo = SimpleUploadedFile('firma.pdf', b'%PDF' + b'x' * 30)
        with patch('apps.reservas.presentation.guia_firma_certificada.TAMANO_MAXIMO', 20):
            archivo.size = 1
            with self.assertRaisesMessage(ValueError, '20 MB'):
                validar_pdf_firmado(archivo)
        self.assertEqual(archivo.tell(), 0)

    def test_reconoce_una_firma_pades_y_rechaza_lo_demas(self):
        detalle = validar_pdf_firmado(SimpleUploadedFile('guia-firmada.pdf', PDF_FIRMADO, content_type='application/pdf'))
        self.assertEqual(detalle['firmas'], 1)
        self.assertEqual(detalle['sha256'], hashlib.sha256(PDF_FIRMADO).hexdigest())

        with self.assertRaisesMessage(ValueError, 'extensión .pdf'):
            validar_pdf_firmado(SimpleUploadedFile('guia.docx', PDF_FIRMADO))
        with self.assertRaisesMessage(ValueError, 'no es un PDF válido'):
            validar_pdf_firmado(SimpleUploadedFile('guia.pdf', b'hola'))
        with self.assertRaisesMessage(ValueError, 'no contiene una firma electrónica'):
            validar_pdf_firmado(SimpleUploadedFile('guia.pdf', PDF_SIN_FIRMA))


class VersionFirmadaTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        User = get_user_model()
        cls.docente = User.objects.create_user(
            'docente-firma', password='clave-segura', email='firma@upec.edu.ec',
            first_name='Docente', last_name='Firma',
        )
        perfil = cls.docente.profile
        perfil.tipo_usuario = 'docente'
        perfil.facultad = 'agropecuarias_ambientales'
        perfil.carrera = 'computacion'
        perfil.institucion = 'UPEC'
        perfil.save()
        verificar_pertenencia(cls.docente)
        cls.revisor = User.objects.create_user('revisor-firma', password='clave-segura')
        cls.ajeno = User.objects.create_user('ajeno-firma', password='clave-segura')
        cls.participante = User.objects.create_user('participante-firma', password='clave-segura')
        cls.unidad = Unidad.objects.create(
            nombre='Laboratorio de firmas',
            slug='laboratorio-firmas',
            dependencia='laboratorios',
            descripcion='Unidad para validar la versión firmada.',
            fecha_inicio=date(2026, 1, 1),
            administrador=cls.revisor,
        )

    def setUp(self):
        self._media = tempfile.TemporaryDirectory(ignore_cleanup_errors=True)
        self._override = override_settings(MEDIA_ROOT=self._media.name)
        self._override.enable()
        self.addCleanup(self._override.disable)
        self.addCleanup(self._media.cleanup)
        self.client.force_login(self.docente)
        respuesta = self.client.post(reverse('nueva_guia_practica', args=[self.unidad.slug]), {
            'proposito_codigo': 'docencia_practica',
            'subtipo_actividad': 'practica_curricular',
            'nombre_actividad': 'Titulación potenciométrica de vinagre comercial',
            'codigo_actividad': 'ACT-FIRMA-01',
            'descripcion_actividad': 'Práctica de química analítica.',
            'titulo': 'Guía de titulación potenciométrica',
            'codigo_guia': 'GUIA-FIRMA-01',
            'asignatura': 'Química Analítica',
            'carrera_semestre': 'Computación · cuarto semestre',
            'docente_responsable': 'Docente Firma',
            'categoria_uso': 'Docencia y práctica curricular',
            'duracion': '2 horas',
            'maximo_estudiantes': '20',
            'resultado_aprendizaje': 'Determina la acidez de una muestra.',
            'objetivos': 'Calibrar el potenciómetro.',
            'fundamento_teorico': 'Equilibrio ácido-base.',
            'equipos': 'Potenciómetro',
            'materiales': 'Vinagre',
            'medidas_seguridad': 'Usar gafas.',
            'formato_procedimiento': 'numerado',
            'procedimiento': 'Calibrar\nTitular\nRegistrar',
            'resultados_esperados': 'Curva de titulación.',
            'criterios_evaluacion': 'Precisión.',
            'manejo_residuos': 'Neutralizar.',
            'permite_descarga': 'on',
            'accion': 'enviar_revision',
        })
        self.assertEqual(respuesta.status_code, 302, getattr(respuesta, 'content', b'')[:600])
        self.guia = GuiaActividadReserva.objects.get(titulo='Guía de titulación potenciométrica')
        self.guia.actividad.participantes_autorizados.add(self.participante)
        self.url_subida = reverse('subir_guia_firmada', args=[self.guia.pk])
        self.url_vista = reverse('ver_guia_actividad', args=[self.guia.pk])

    def _pdf(self, contenido=PDF_FIRMADO, nombre='guia-firmada.pdf'):
        return SimpleUploadedFile(nombre, contenido, content_type='application/pdf')

    def test_revision_integrada_concentra_pdf_y_acciones_secundarias(self):
        self.client.force_login(self.revisor)
        respuesta = self.client.get(self.url_vista, {'_panel': '1'})
        self.assertEqual(respuesta.status_code, 200)
        self.assertEqual(respuesta.headers['X-Frame-Options'], 'SAMEORIGIN')
        cabecera = respuesta.content.decode().split('<header class="guide-hero', 1)[1].split('</header>', 1)[0]
        self.assertIn('data-ver-pdf', cabecera)
        self.assertIn('data-pdf-descarga=', cabecera)
        self.assertIn('guide-actions-more', cabecera)
        self.assertNotIn('target="_blank"', cabecera)
        self.assertNotIn('Descargar PDF', cabecera)

    def _aprobar(self):
        self.client.force_login(self.revisor)
        respuesta = self.client.post(
            reverse('cambiar_estado_guia_practica', args=[self.guia.pk]),
            {'accion': 'aprobar', 'observacion': 'Aprobada.'},
        )
        self.assertEqual(respuesta.status_code, 302, getattr(respuesta, 'content', b'')[:300])
        self.guia.refresh_from_db()
        self.assertEqual(self.guia.estado_publicacion, 'publicada')

    def test_reemplazo_conserva_archivo_anterior_y_audita_ambas_rutas(self):
        from apps.reservas.presentation.guia_firma_certificada import registrar_pdf_firmado
        from apps.formacion.models.practicas import RegistroAuditoriaUnidad
        self._aprobar()
        registrar_pdf_firmado(self.guia, self._pdf(), self.docente)
        anterior = self.guia.archivo_firmado.name
        storage = self.guia.archivo_firmado.storage
        registrar_pdf_firmado(self.guia, self._pdf(), self.docente)
        self.assertNotEqual(anterior, self.guia.archivo_firmado.name)
        self.assertTrue(storage.exists(anterior))
        evento = RegistroAuditoriaUnidad.objects.filter(
            entidad=self.guia._meta.label, objeto_id=str(self.guia.pk)).latest('pk')
        self.assertEqual(evento.datos_anteriores['archivo_firmado'], anterior)
        self.assertEqual(evento.datos_nuevos['archivo_firmado'], self.guia.archivo_firmado.name)
        self.assertEqual(evento.datos_nuevos['sha256'], hashlib.sha256(PDF_FIRMADO).hexdigest())

    def test_fallo_de_auditoria_conserva_la_carga_anterior(self):
        from pathlib import Path
        from apps.reservas.presentation.guia_firma_certificada import registrar_pdf_firmado
        self._aprobar()
        registrar_pdf_firmado(self.guia, self._pdf(), self.docente)
        anterior = self.guia.archivo_firmado.name
        archivos = set(Path(self._media.name).rglob('*.pdf'))
        with patch('apps.gestion_unidades.presentation.auditoria.registrar_auditoria', side_effect=RuntimeError('fallo')):
            with self.assertRaises(RuntimeError):
                registrar_pdf_firmado(self.guia, self._pdf(), self.docente)
        self.guia.refresh_from_db()
        self.assertEqual(self.guia.archivo_firmado.name, anterior)
        self.assertEqual(set(Path(self._media.name).rglob('*.pdf')), archivos)

    def test_ruta_directa_no_elude_permisos_y_no_publica_versiones_anteriores(self):
        from apps.reservas.presentation.guia_firma_certificada import registrar_pdf_firmado
        self._aprobar()
        self.guia.visibilidad = 'participantes'
        self.guia.save(update_fields=['visibilidad'])
        registrar_pdf_firmado(self.guia, self._pdf(), self.docente)
        anterior = self.guia.archivo_firmado.url
        self.client.force_login(self.ajeno)
        self.assertEqual(self.client.get(anterior).status_code, 404)
        self.client.force_login(self.docente)
        respuesta = self.client.get(anterior)
        self.assertEqual(respuesta.status_code, 200)
        for cerrar in respuesta._resource_closers:
            cerrar()
        registrar_pdf_firmado(self.guia, self._pdf(), self.docente)
        self.assertEqual(self.client.get(anterior).status_code, 404)

    def test_solo_se_carga_sobre_la_guia_aprobada_y_con_una_firma_real(self):
        # En borrador todavia no hay documento que firmar.
        self.guia.estado_publicacion = 'borrador'
        self.guia.save(update_fields=['estado_publicacion'])
        antes = self.client.post(self.url_subida, {'archivo_firmado': self._pdf()}, follow=True)
        self.assertContains(antes, 'en revisión o ya fue aprobada')
        self.guia.refresh_from_db()
        self.assertFalse(self.guia.archivo_firmado)

        # Durante la revision la persona autora descarga, firma y carga el PDF;
        # el laboratorio aprueba con la version firmada ya registrada.
        self.guia.estado_publicacion = 'revision'
        self.guia.save(update_fields=['estado_publicacion'])
        vista = self.client.get(self.url_vista)
        self.assertContains(vista, 'Firma la guía antes de la aprobación')
        en_revision = self.client.post(self.url_subida, {'archivo_firmado': self._pdf()}, follow=True)
        self.assertContains(en_revision, 'Versión firmada registrada')
        self.guia.refresh_from_db()
        self.assertTrue(self.guia.archivo_firmado)
        self._aprobar()
        self.guia.refresh_from_db()
        self.assertTrue(self.guia.archivo_firmado)
        self.client.force_login(self.docente)
        sin_firma = self.client.post(self.url_subida, {'archivo_firmado': self._pdf(PDF_SIN_FIRMA)}, follow=True)
        self.assertContains(sin_firma, 'no contiene una firma electrónica')
        self.guia.refresh_from_db()
        # Un archivo sin firma no reemplaza la version firmada ya registrada.
        self.assertTrue(self.guia.archivo_firmado)

        cargada = self.client.post(self.url_subida, {'archivo_firmado': self._pdf()}, follow=True)
        self.assertEqual(cargada.status_code, 200)
        self.assertContains(cargada, 'Versión firmada registrada')
        self.guia.refresh_from_db()
        self.assertTrue(self.guia.archivo_firmado)
        self.assertEqual(self.guia.firmado_por, self.docente)
        self.assertIsNotNone(self.guia.firmado_en)
        self.assertIn('1 firma detectada · SHA-256', self.guia.firma_certificada_resumen)
        self.assertContains(cargada, 'Versión firmada cargada')

        # La descarga entrega el PDF firmado, tambien a los participantes.
        descarga = self.client.get(self.url_vista + '?download=1')
        self.assertEqual(descarga.status_code, 200)
        self.assertEqual(b''.join(descarga.streaming_content), PDF_FIRMADO)
        self.assertIn('-firmada.pdf', descarga['Content-Disposition'])
        for cerrar in descarga._resource_closers:
            cerrar()
        self.client.force_login(self.participante)
        descarga_participante = self.client.get(self.url_vista + '?download=1')
        self.assertEqual(descarga_participante.status_code, 200)
        self.assertEqual(b''.join(descarga_participante.streaming_content), PDF_FIRMADO)
        for cerrar in descarga_participante._resource_closers:
            cerrar()
        # El lector en línea también entrega la versión firmada: es la oficial.
        vista_pdf = self.client.get(self.url_vista + '?preview=pdf')
        self.assertEqual(b''.join(vista_pdf.streaming_content), PDF_FIRMADO)
        self.assertTrue(vista_pdf['Content-Disposition'].startswith('inline'))
        for cerrar in vista_pdf._resource_closers:
            cerrar()

    def test_el_expediente_carga_la_version_firmada_sin_salir_de_su_ventana(self):
        self._aprobar()
        self.client.force_login(self.docente)

        respuesta = self.client.post(
            self.url_subida,
            {'archivo_firmado': self._pdf()},
            HTTP_X_REQUESTED_WITH='XMLHttpRequest',
        )

        self.assertEqual(respuesta.status_code, 200)
        datos = respuesta.json()
        self.assertTrue(datos['success'])
        self.assertIn('Versión firmada registrada', datos['message'])
        self.guia.refresh_from_db()
        self.assertTrue(self.guia.archivo_firmado)

        error = self.client.post(
            self.url_subida,
            {},
            HTTP_X_REQUESTED_WITH='XMLHttpRequest',
        )
        self.assertEqual(error.status_code, 400)
        self.assertIn('FirmaEC', error.json()['error'])

    def test_el_cajetin_de_firmas_reserva_el_espacio_de_la_firma_electronica(self):
        self._aprobar()
        self.client.force_login(self.docente)

        vista = self.client.get(self.url_vista)
        self.assertContains(vista, 'guide-signatures--final')
        self.assertContains(vista, 'guide-signature__space')
        self.assertContains(vista, 'Espacio para la firma electrónica (FirmaEC)')

        # El PDF se arma con el mismo cajetín, con una firma o con varias.
        una = self.client.get(self.url_vista + '?preview=pdf')
        self.assertTrue(una.content.startswith(b'%PDF'))
        contenido = dict(self.guia.contenido)
        contenido['firmas'] = {
            rol: {'activo': True, 'nombre': f'Persona {rol}', 'cargo': 'Cargo', 'fecha': ''}
            for rol in ('elaborado', 'revisado', 'aprobado')
        }
        self.guia.contenido = contenido
        self.guia.save(update_fields=['contenido'])
        tres = self.client.get(self.url_vista + '?preview=pdf')
        self.assertTrue(tres.content.startswith(b'%PDF'))

    def test_el_formulario_de_firma_no_se_repite_para_el_titular_de_la_reserva(self):
        self._aprobar()
        self.client.force_login(self.docente)

        pagina = self.client.get(self.url_vista)

        # La guía de esta prueba no nace de una reserva: la carga vive aquí.
        self.assertTrue(pagina.context['puede_cargar_firmada'])
        self.assertIsNone(pagina.context['reserva_para_firmar'])
        self.assertContains(pagina, 'name="archivo_firmado"')
        self.assertNotContains(pagina, 'guide-certified__redirect')

    def test_solo_autoria_o_personal_de_la_unidad_pueden_cargarla(self):
        self._aprobar()
        self.client.force_login(self.ajeno)
        self.assertEqual(self.client.post(self.url_subida, {'archivo_firmado': self._pdf()}).status_code, 404)
        self.client.force_login(self.participante)
        self.assertEqual(self.client.post(self.url_subida, {'archivo_firmado': self._pdf()}).status_code, 404)
        self.client.force_login(self.revisor)
        respuesta = self.client.post(self.url_subida, {'archivo_firmado': self._pdf()}, follow=True)
        self.assertContains(respuesta, 'Versión firmada registrada')
        self.guia.refresh_from_db()
        self.assertEqual(self.guia.firmado_por, self.revisor)
        with self.guia.archivo_firmado.open('rb') as archivo:
            self.assertEqual(archivo.read(), PDF_FIRMADO)
