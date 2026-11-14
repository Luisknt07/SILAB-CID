"""Los PDFs se consultan dentro de la página conservando acceso y descargas."""
from datetime import date
from html.parser import HTMLParser
from pathlib import Path
from tempfile import TemporaryDirectory
from types import SimpleNamespace
from unittest.mock import patch
from urllib.parse import parse_qs, urlsplit

from django.contrib.auth import get_user_model
from django.contrib.admin.sites import AdminSite
from django.contrib.staticfiles import finders
from django.core.files.uploadedfile import SimpleUploadedFile
from django.template.loader import render_to_string
from django.test import SimpleTestCase, TestCase, override_settings
from django.urls import reverse

from apps.recursos.models.recursos import CarpetaRecurso, Recurso
from apps.formacion.models.cursos import CertificadoCurso, Curso, EdicionCurso, InscripcionCurso, LeccionCurso, ModuloCurso
from apps.reservas.models.reservas import GuiaActividadReserva
from apps.directorio_unidades.models.core import Unidad
from tests.integration.utiles import identificar


class _DocumentosHTML(HTMLParser):
    def __init__(self, html):
        super().__init__()
        self.enlaces = []
        self.scripts = []
        self.visores = []
        self.marcos = []
        self.feed(html)

    def handle_starttag(self, tag, attrs):
        datos = dict(attrs)
        if tag == 'a':
            self.enlaces.append(datos)
        elif tag == 'script' and datos.get('src'):
            self.scripts.append(datos['src'])
        elif tag in ('iframe', 'embed', 'object'):
            self.marcos.append(datos)
        if 'data-aula-pdf-modal' in datos:
            self.visores.append(datos)


class DependenciasVisorPdfTests(SimpleTestCase):
    def test_componente_compartido_incluye_controles_y_visor_local(self):
        html = render_to_string('portal/pages/unidades/aula/includes/visor_pdf_modal.html')
        documento = _DocumentosHTML(html)
        self.assertEqual(len(documento.visores), 1)
        self.assertTrue(any('portal/js/components/visor_pdf.js' in src for src in documento.scripts))
        self.assertTrue(any('portal/js/components/visor_pdf_modal.js' in src for src in documento.scripts))
        self.assertIn('data-visor-pdf', html)
        self.assertIn('data-cerrar-pdf', html)
        self.assertIn('data-descargar-pdf', html)
        self.assertEqual(documento.marcos, [])

    def test_recursos_pdfjs_locales_necesarios_estan_disponibles(self):
        for recurso in (
            'js/vendor/pdfjs/6.4.299/pdf.mjs',
            'js/vendor/pdfjs/6.4.299/pdf.worker.mjs',
            'js/vendor/pdfjs/6.4.299/standard_fonts/LiberationSans-Regular.ttf',
            'portal/js/components/visor_pdf.js',
            'portal/js/components/visor_pdf_modal.js',
            'portal/css/components/visor_pdf.css',
            'portal/css/components/visor_pdf_modal.css',
        ):
            with self.subTest(recurso=recurso):
                ubicado = finders.find(recurso)
                self.assertIsNotNone(ubicado)
                self.assertGreater(Path(ubicado).stat().st_size, 0)


class GuiasAdminVisorPdfTests(SimpleTestCase):
    def guia(self, *, estructurada=False, descarga=False):
        return SimpleNamespace(
            pk=17, titulo='Guía de práctica "Logística"',
            es_estructurada=estructurada, archivo='guias/practica.pdf',
            permite_descarga=descarga,
        )

    def abrir(self, guia):
        from apps.reservas.admin.reservas import GuiaActividadReservaAdmin

        gestor = GuiaActividadReservaAdmin(GuiaActividadReserva, AdminSite())
        return _DocumentosHTML(gestor.abrir_pdf(guia))

    def test_guia_pdf_descargable_ofrece_visor_y_descarga_separada(self):
        guia = self.guia(descarga=True)
        documento = self.abrir(guia)
        self.assertEqual(len(documento.enlaces), 2)
        vista, descarga = documento.enlaces
        url = reverse('ver_guia_actividad', args=[guia.pk])
        self.assertEqual(vista['href'], url)
        self.assertIn('data-ver-pdf', vista)
        self.assertEqual(vista['data-pdf-titulo'], guia.titulo)
        self.assertEqual(vista['data-pdf-descarga'], url + '?download=1')
        self.assertNotIn('data-pdf-sin-descarga', vista)
        self.assertNotIn('download', vista)
        self.assertEqual(descarga['href'], url + '?download=1')
        self.assertIn('download', descarga)
        self.assertTrue(all(enlace.get('target') != '_blank' for enlace in documento.enlaces))

    def test_guia_pdf_solo_visualizacion_oculta_descarga_en_modal(self):
        documento = self.abrir(self.guia())
        self.assertEqual(len(documento.enlaces), 1)
        vista = documento.enlaces[0]
        self.assertIn('data-ver-pdf', vista)
        self.assertIn('data-pdf-sin-descarga', vista)
        self.assertNotIn('data-pdf-descarga', vista)
        self.assertNotIn('download', vista)
        self.assertNotEqual(vista.get('target'), '_blank')

    def test_guia_estructurada_conserva_su_vista_html(self):
        guia = self.guia(estructurada=True)
        documento = self.abrir(guia)
        self.assertEqual(len(documento.enlaces), 1)
        vista = documento.enlaces[0]
        self.assertEqual(vista['href'], reverse('ver_guia_actividad', args=[guia.pk]))
        self.assertNotIn('data-ver-pdf', vista)
        self.assertNotIn('download', vista)
        self.assertNotEqual(vista.get('target'), '_blank')


class DocumentosAdminVisorPdfTests(SimpleTestCase):
    def test_archivo_del_expediente_usa_visor_aunque_la_ruta_no_tenga_extension(self):
        from apps.documentos.admin.expediente import DocumentoExpedienteAdmin
        from apps.documentos.models.expediente import DocumentoExpediente

        gestor = DocumentoExpedienteAdmin(DocumentoExpediente, AdminSite())
        objeto = SimpleNamespace(recurso_id=37, nombre_documental='Resolución de creación')
        documento = _DocumentosHTML(gestor.archivo(objeto))
        self.assertEqual(len(documento.enlaces), 1)
        enlace = documento.enlaces[0]
        self.assertEqual(enlace['href'], reverse('recurso_unidad', args=[37]))
        self.assertIn('data-ver-pdf', enlace)
        self.assertEqual(enlace['data-pdf-titulo'], objeto.nombre_documental)
        self.assertEqual(enlace['data-pdf-descarga'], enlace['href'] + '?download=1')
        self.assertNotIn('target', enlace)

    def test_informe_de_mejora_archivado_se_consulta_en_el_mismo_visor(self):
        from apps.documentos.admin.expediente import InformeMejoraAdmin
        from apps.documentos.models.mejora import InformeMejora

        gestor = InformeMejoraAdmin(InformeMejora, AdminSite())
        objeto = SimpleNamespace(recurso_id=41, recurso=SimpleNamespace(activo=True, version=3))
        documento = _DocumentosHTML(gestor.archivo_informe(objeto))
        enlace = documento.enlaces[0]
        self.assertEqual(enlace['href'], reverse('recurso_unidad', args=[41]))
        self.assertIn('data-ver-pdf', enlace)
        self.assertIn('v3', enlace['data-pdf-titulo'])
        self.assertNotIn('target', enlace)

    def test_reporte_de_centros_conserva_filtros_y_un_solo_visor_compartido(self):
        from apps.core.presentation.identidad import identidad_publica

        contexto = {
            'reporte': {'title': 'Proyectos del centro', 'scope': 'Centro autorizado',
                'pagination': {'count': 0, 'number': 1, 'num_pages': 1},
                'filters': {'categoria': 'proyectos'},
                'sections': [{'titulo': 'Proyectos', 'headers': ['Nombre'], 'rows': []}]},
            'pdf_url': '/centros-id/reportes/?centro=7&categoria=proyectos&formato=pdf&descargar=0',
            'exportaciones': [('Descargar PDF', '/centros-id/reportes/?centro=7&formato=pdf'),
                ('Descargar Excel', '/centros-id/reportes/?centro=7&formato=xlsx')],
        }
        contexto.update(identidad_publica())
        html = render_to_string('centros_id/informes.html', contexto)
        documento = _DocumentosHTML(html)
        enlace = next(a for a in documento.enlaces if a.get('href') == contexto['pdf_url'])
        self.assertIn('data-ver-pdf', enlace)
        self.assertNotIn('target', enlace)
        self.assertEqual(enlace['data-pdf-titulo'], contexto['reporte']['title'])
        self.assertEqual(len(documento.visores), 1)
        self.assertNotIn('Ver PDF', html)
        self.assertNotIn('Descargar PDF', html)
        urls_exportacion = {url for _, url in contexto['exportaciones']}
        descargas = [a for a in documento.enlaces
            if 'download' in a and a.get('href') in urls_exportacion]
        self.assertEqual(len(descargas), 2)
        self.assertTrue(all('target' not in a for a in descargas))


class VisorPdfIntegracionTests(TestCase):
    @classmethod
    def setUpClass(cls):
        cls.directorio_media = TemporaryDirectory(prefix='citt-visor-pdf-')
        cls.addClassCleanup(cls.directorio_media.cleanup)
        cls.ajustes_media = override_settings(MEDIA_ROOT=cls.directorio_media.name)
        cls.ajustes_media.enable()
        cls.addClassCleanup(cls.ajustes_media.disable)
        super().setUpClass()

    @classmethod
    def setUpTestData(cls):
        usuarios = get_user_model()
        cls.gestor = usuarios.objects.create_user('visor-pdf-gestor', password='clave')
        cls.persona = usuarios.objects.create_user('visor-pdf-persona', password='clave')
        cls.ajena = usuarios.objects.create_user('visor-pdf-ajena', password='clave')
        identificar(cls.gestor, tipo_usuario='administrativo', carrera='')
        identificar(cls.persona, tipo_usuario='estudiante')
        identificar(cls.ajena, tipo_usuario='estudiante')
        cls.unidad = Unidad.objects.create(
            nombre='Laboratorio visor PDF', slug='laboratorio-visor-pdf', dependencia='laboratorios',
            administrador=cls.gestor, descripcion='Pruebas del visor', fecha_inicio=date(2026, 1, 1),
        )
        cls.curso = Curso.objects.create(
            unidad=cls.unidad, codigo='VISOR-PDF-001', nombre='Curso con material privado',
            publicado=True, duracion_horas=40,
        )
        cls.grupo = EdicionCurso.objects.create(curso=cls.curso, nombre='Grupo del visor', anio=2026)
        bienvenida = ModuloCurso.objects.create(curso=cls.curso, titulo='Bienvenida pública', orden=1)
        LeccionCurso.objects.create(modulo=bienvenida, titulo='Presentación', tipo='texto')
        privado = ModuloCurso.objects.create(curso=cls.curso, titulo='Materiales para participantes', orden=2)
        cls.pdf = LeccionCurso.objects.create(
            modulo=privado, titulo='Guía privada en PDF', tipo='material', orden=1,
            archivo=SimpleUploadedFile('guia.PDF', b'%PDF-1.4 documento privado de prueba', content_type='application/pdf'),
        )
        cls.zip = LeccionCurso.objects.create(
            modulo=privado, titulo='Archivos de práctica', tipo='material', orden=2,
            archivo=SimpleUploadedFile('practica.zip', b'PK\x03\x04archivo de prueba', content_type='application/zip'),
        )
        cls.inscripcion = InscripcionCurso.objects.create(
            edicion=cls.grupo, usuario=cls.persona, estado='aceptada',
            nombres_completos='Participante del visor', documento='DOC-PDF-001',
        )
        cls.certificado = CertificadoCurso.objects.create(
            inscripcion=cls.inscripcion, codigo='CERT-VISOR-001', nombre='Participante del visor',
            documento='DOC-PDF-001', curso_nombre=cls.curso.nombre, clasificacion='Curso corto',
            horas=40, edicion=cls.grupo.nombre, unidad_nombre=cls.unidad.nombre,
        )

    def ruta(self, nombre, *extra):
        return reverse(nombre, args=[self.unidad.slug, self.curso.codigo, *extra])

    def html(self, respuesta):
        self.assertEqual(respuesta.status_code, 200)
        return _DocumentosHTML(respuesta.content.decode())

    def enlace(self, documento, ruta):
        encontrados = [enlace for enlace in documento.enlaces
                       if urlsplit(enlace.get('href', '')).path == ruta
                       and parse_qs(urlsplit(enlace.get('href', '')).query).get('formato', ['pdf']) == ['pdf']]
        self.assertTrue(encontrados, f'Falta el enlace al documento {ruta}')
        return encontrados[0]

    def comprobar_visor(self, documento):
        self.assertEqual(len(documento.visores), 1)
        self.assertTrue(any('portal/js/components/visor_pdf.js' in src for src in documento.scripts))
        self.assertTrue(any('portal/js/components/visor_pdf_modal.js' in src for src in documento.scripts))

    def comprobar_enlace_pdf(self, enlace):
        self.assertIn('data-ver-pdf', enlace)
        self.assertNotEqual(enlace.get('target'), '_blank')
        self.assertNotIn('download', enlace)

    def test_material_pdf_se_abre_en_visor_y_conserva_ruta_protegida_y_grupo(self):
        self.client.force_login(self.persona)
        respuesta = self.client.get(self.ruta('aula_curso_leccion', self.pdf.pk), {'edicion': self.grupo.pk})
        documento = self.html(respuesta)
        enlace = self.enlace(documento, self.ruta('material_leccion', self.pdf.pk))
        self.comprobar_enlace_pdf(enlace)
        self.assertIn('data-abre-material', enlace)
        self.assertEqual(parse_qs(urlsplit(enlace['href']).query)['edicion'], [str(self.grupo.pk)])
        self.assertFalse(any(self.pdf.archivo.name in enlace.get('href', '') for enlace in documento.enlaces))
        self.comprobar_visor(documento)

    def test_material_no_pdf_conserva_descarga_y_no_se_manda_al_visor(self):
        self.client.force_login(self.persona)
        documento = self.html(self.client.get(self.ruta('aula_curso_leccion', self.zip.pk)))
        enlace = self.enlace(documento, self.ruta('material_leccion', self.zip.pk))
        self.assertNotIn('data-ver-pdf', enlace)
        self.assertIn('download', enlace)
        self.assertIn('data-abre-material', enlace)

    def test_aula_y_perfil_consultan_certificado_propio_en_modal(self):
        self.client.force_login(self.persona)
        for url in (self.ruta('aula_curso'), reverse('mi_formacion')):
            with self.subTest(pagina=url):
                documento = self.html(self.client.get(url))
                self.comprobar_enlace_pdf(self.enlace(documento, self.ruta('mi_certificado')))
                self.comprobar_visor(documento)

    def test_reporte_personal_ofrece_pdf_en_modal_sin_perder_la_cohorte(self):
        self.client.force_login(self.persona)
        documento = self.html(self.client.get(self.ruta('seguimiento_curso'), {'edicion': self.grupo.pk}))
        enlaces = [enlace for enlace in documento.enlaces
                   if parse_qs(urlsplit(enlace.get('href', '')).query).get('formato') == ['pdf']]
        self.assertTrue(enlaces)
        self.comprobar_enlace_pdf(enlaces[0])
        self.assertEqual(parse_qs(urlsplit(enlaces[0]['href']).query)['edicion'], [str(self.grupo.pk)])
        self.comprobar_visor(documento)

    def test_verificacion_publica_pdf_usa_modal_y_no_expone_documento_de_identidad(self):
        verificar = reverse('verificar_certificado', args=[self.certificado.codigo])
        documento = self.html(self.client.get(verificar))
        enlace = self.enlace(documento, verificar)
        self.comprobar_enlace_pdf(enlace)
        self.comprobar_visor(documento)
        with patch('apps.formacion.presentation.certificados_cursos.pdf_del_certificado', return_value=b'%PDF-1.4 publico') as dibujar:
            respuesta = self.client.get(verificar, {'formato': 'pdf'})
        self.assertEqual(respuesta.status_code, 200)
        self.assertEqual(respuesta['Content-Type'], 'application/pdf')
        self.assertFalse(dibujar.call_args.args[1])

    def test_gestion_de_cursos_ofrece_reporte_y_certificado_en_el_mismo_visor(self):
        self.client.force_login(self.gestor)
        documento = self.html(self.client.get(reverse('gestion_unidad', args=[self.unidad.slug]), {
            'view': 'cursos', 'modo_cursos': 'participantes', 'curso_cursos': self.curso.pk,
        }))
        reporte = self.enlace(documento, reverse('gestion_cursos_pdf', args=[self.unidad.slug]))
        certificado = self.enlace(documento, self.ruta('certificado_curso_gestor', self.certificado.pk))
        self.comprobar_enlace_pdf(reporte)
        self.comprobar_enlace_pdf(certificado)
        self.comprobar_visor(documento)

    def test_pdf_material_sigue_privado_aunque_se_pida_desde_un_marco(self):
        url = self.ruta('material_leccion', self.pdf.pk)
        self.client.logout()
        self.assertEqual(self.client.get(url, {'_panel': '1'}).status_code, 302)
        self.client.force_login(self.ajena)
        self.assertEqual(self.client.get(url, {'_panel': '1'}).status_code, 403)
        self.client.force_login(self.persona)
        respuesta = self.client.get(url, {'_panel': '1', 'edicion': self.grupo.pk})
        self.assertEqual(respuesta.status_code, 200)
        self.assertEqual(respuesta['Content-Type'], 'application/pdf')
        self.assertIn('private', respuesta['Cache-Control'])
        self.assertIn('no-store', respuesta['Cache-Control'])
        self.assertEqual(respuesta['X-Content-Type-Options'], 'nosniff')
        self.assertTrue(respuesta['Content-Disposition'].startswith('inline;'))
        self.assertEqual(b''.join(respuesta.streaming_content), b'%PDF-1.4 documento privado de prueba')

    def test_visor_no_permite_consultar_certificados_de_otra_persona(self):
        self.client.force_login(self.ajena)
        with patch('apps.formacion.presentation.certificados_cursos.pdf_del_certificado') as dibujar:
            propio = self.client.get(self.ruta('mi_certificado'), {
                '_panel': '1', 'edicion': self.grupo.pk, 'inscripcion': self.inscripcion.pk,
            })
            gestor = self.client.get(self.ruta('certificado_curso_gestor', self.certificado.pk), {'_panel': '1'})
        self.assertEqual(propio.status_code, 404)
        self.assertEqual(gestor.status_code, 403)
        dibujar.assert_not_called()

    def test_certificado_previa_y_descarga_conservan_privacidad_y_disposicion(self):
        self.client.force_login(self.persona)
        with patch('apps.formacion.presentation.certificados_cursos.pdf_del_certificado', return_value=b'%PDF-1.4 certificado'):
            previa = self.client.get(self.ruta('mi_certificado'), {'_panel': '1', 'edicion': self.grupo.pk})
            descarga = self.client.get(self.ruta('mi_certificado'), {'edicion': self.grupo.pk, 'descargar': '1'})
        self.assertEqual(previa.status_code, 200)
        self.assertEqual(descarga.status_code, 200)
        self.assertEqual(previa.content, descarga.content)
        self.assertTrue(previa['Content-Disposition'].startswith('inline;'))
        self.assertTrue(descarga['Content-Disposition'].startswith('attachment;'))
        for respuesta in (previa, descarga):
            self.assertIn('private', respuesta['Cache-Control'])
            self.assertIn('no-store', respuesta['Cache-Control'])

    def test_reporte_de_gestion_sigue_limitado_a_personal_autorizado(self):
        self.client.force_login(self.ajena)
        respuesta = self.client.get(reverse('gestion_cursos_pdf', args=[self.unidad.slug]), {'_panel': '1'})
        self.assertEqual(respuesta.status_code, 403)

    def recurso_externo(self, url, *, descarga=False, visibilidad='publica'):
        carpeta = CarpetaRecurso.objects.create(unidad=self.unidad, nombre='Fuentes externas')
        return Recurso.objects.create(
            unidad=self.unidad, carpeta=carpeta, nombre='Guía externa',
            descripcion='Material de consulta del laboratorio.', url=url,
            seguridad_verificada=True, descargar=descarga, visibilidad=visibilidad,
        )

    def test_recurso_pdf_externo_usa_modal_sin_iframe_ni_inspeccion_de_sitios(self):
        recurso = self.recurso_externo('https://documentos.example.org/GUIA.PDF?version=2')
        with patch('apps.recursos.presentation.sitios_externos.permite_incrustar') as inspeccionar, \
                patch('apps.recursos.presentation.navegador_remoto.disponible') as navegador:
            respuesta = self.client.get(reverse('recurso_unidad', args=[recurso.pk]), {'visor': '1'})
        documento = self.html(respuesta)
        self.assertIs(respuesta.context['es_pdf'], True)
        self.assertIs(respuesta.context['incrustable'], False)
        self.assertIs(respuesta.context['navegador'], False)
        inspeccionar.assert_not_called()
        navegador.assert_not_called()
        enlace = next(enlace for enlace in documento.enlaces if enlace.get('href') == recurso.url)
        self.comprobar_enlace_pdf(enlace)
        self.assertEqual(enlace['data-pdf-titulo'], recurso.nombre)
        self.assertIn('data-pdf-sin-descarga', enlace)
        self.assertEqual(documento.marcos, [])
        self.comprobar_visor(documento)
        self.assertEqual(respuesta['X-Frame-Options'], 'SAMEORIGIN')
        self.assertIn('private', respuesta['Cache-Control'])

    def test_recurso_pdf_externo_descargable_conserva_la_opcion_en_el_visor(self):
        recurso = self.recurso_externo('https://documentos.example.org/manual.pdf', descarga=True)
        respuesta = self.client.get(reverse('recurso_unidad', args=[recurso.pk]), {'visor': '1'})
        documento = self.html(respuesta)
        enlace = next(enlace for enlace in documento.enlaces if enlace.get('href') == recurso.url)
        self.comprobar_enlace_pdf(enlace)
        self.assertNotIn('data-pdf-sin-descarga', enlace)
        self.assertEqual(documento.marcos, [])

    def test_recurso_web_con_pdf_en_query_conserva_el_tratamiento_de_sitio(self):
        recurso = self.recurso_externo('https://documentos.example.org/consulta.html?tema=guia.pdf')
        with patch('apps.recursos.presentation.sitios_externos.permite_incrustar', return_value=True) as inspeccionar:
            respuesta = self.client.get(reverse('recurso_unidad', args=[recurso.pk]), {'visor': '1'})
        documento = self.html(respuesta)
        self.assertIs(respuesta.context['es_pdf'], False)
        self.assertIs(respuesta.context['incrustable'], True)
        inspeccionar.assert_called_once_with(recurso.url, 'http://testserver')
        self.assertEqual(len(documento.marcos), 1)
        self.assertEqual(documento.marcos[0]['src'], recurso.url)
        self.assertFalse(any(enlace.get('href') == recurso.url and 'data-ver-pdf' in enlace
                             for enlace in documento.enlaces))

    def test_recurso_pdf_externo_interno_sigue_restringido_a_gestores(self):
        recurso = self.recurso_externo('https://documentos.example.org/interno.pdf', visibilidad='interna')
        url = reverse('recurso_unidad', args=[recurso.pk])
        with patch('apps.recursos.presentation.sitios_externos.permite_incrustar') as inspeccionar, \
                patch('apps.recursos.presentation.navegador_remoto.disponible') as navegador:
            self.client.logout()
            self.assertEqual(self.client.get(url, {'visor': '1', '_panel': '1'}).status_code, 404)
            self.client.force_login(self.ajena)
            self.assertEqual(self.client.get(url, {'visor': '1', '_panel': '1'}).status_code, 404)
            self.client.force_login(self.gestor)
            respuesta = self.client.get(url, {'visor': '1', '_panel': '1'})
        self.assertEqual(respuesta.status_code, 200)
        self.assertIs(respuesta.context['es_pdf'], True)
        inspeccionar.assert_not_called()
        navegador.assert_not_called()
