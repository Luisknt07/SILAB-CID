"""Contrato de carga y acceso del curso docente: horas, archivos reales y protección del aula."""
import shutil
import tempfile
from datetime import date
from io import BytesIO, StringIO
from pathlib import Path
from zipfile import ZipFile

from django.contrib.auth import get_user_model
from django.core.management import call_command
from django.test import SimpleTestCase, TestCase, override_settings
from django.urls import reverse

from apps.formacion.management.cursos_precargados import aplicaciones_logisticas_ia as datos
from apps.formacion.models.cursos import Curso, LeccionCurso
from apps.directorio_unidades.models.core import Unidad


class ProgramaAplicacionesLogisticasTests(SimpleTestCase):
    def test_carga_de_trabajo_y_evaluacion_coinciden_con_el_programa_aprobado(self):
        self.assertEqual(datos.CURSO['duracion_horas'], 40)
        self.assertEqual(len(datos.MODULOS), 5)
        for _titulo, _descripcion, lecciones in datos.MODULOS:
            self.assertEqual(sum(campos['duracion_min'] for _tipo, _t, campos in lecciones if campos.get('obligatoria', True)), 480)
            self.assertEqual(lecciones[-1][0], 'evaluacion')
            self.assertEqual(len(lecciones[-1][2]['preguntas']), 8)
            self.assertTrue(any(tipo == 'deber' for tipo, _t, _c in lecciones))
        ampliaciones = [campos for _t, _d, lecciones in datos.MODULOS for _tipo, _titulo, campos in lecciones
                        if not campos.get('obligatoria', True)]
        self.assertEqual({campos['video_url'].rsplit('=', 1)[-1] for campos in ampliaciones},
                         {'WNjQclnnIWA', 'TmB8mXKs9jI'})
        self.assertEqual(sum(campos['duracion_min'] for campos in ampliaciones), 230)
        primera = datos.MODULOS[0][2][0]
        self.assertEqual(primera[0], 'video')
        self.assertEqual(primera[1], 'Bienvenida: tu ruta para crear una aplicación logística')
        self.assertIn('archivo_generado', primera[2])
        self.assertFalse(datos.EDICION['activa'])
        self.assertFalse(any(c in datos.EDICION for c in ('inicio', 'fin', 'cupo')))
        self.assertIn('no exige programación previa', datos.CURSO['requisitos'])


class CargaAplicacionesLogisticasTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.unidad = Unidad.objects.create(
            nombre='Laboratorio de Logística, Transporte y Cadena de Suministro',
            slug='laboratorio-logistica-comercio-internacional', dependencia='laboratorios',
            descripcion='Caso de prueba', fecha_inicio=date(2026, 1, 1))
        cls.admin = get_user_model().objects.create_superuser('gestor-ia', 'gestor@example.org', 'clave')

    def setUp(self):
        self.medios = tempfile.mkdtemp(prefix='citt-curso-ia-')
        self.ajustes = override_settings(MEDIA_ROOT=self.medios)
        self.ajustes.enable()
        self.addCleanup(self.ajustes.disable)
        self.addCleanup(shutil.rmtree, self.medios, ignore_errors=True)

    def cargar(self, *opciones):
        salida = StringIO()
        call_command('cargar_curso_precargado', 'aplicaciones-logisticas-ia', *opciones, stdout=salida)
        return salida.getvalue()

    def test_simulacion_no_crea_registros_ni_materiales(self):
        self.cargar('--simular')
        self.assertFalse(Curso.objects.filter(unidad=self.unidad).exists())
        self.assertFalse(any(Path(self.medios).rglob('*')))

    def test_carga_idempotente_con_pdfs_y_kit_reproducible(self):
        self.cargar()
        curso = Curso.objects.get(unidad=self.unidad)
        self.assertFalse(curso.publicado)
        self.assertFalse(curso.ediciones.get().activa)
        lecciones = LeccionCurso.objects.filter(modulo__curso=curso)
        antes = list(lecciones.values_list('pk', 'archivo'))
        self.assertIn('nada nuevo', self.cargar())
        self.assertEqual(antes, list(lecciones.values_list('pk', 'archivo')))
        guias = [leccion for leccion in lecciones if leccion.archivo.name.endswith('.pdf')]
        self.assertEqual(len(guias), 5)
        for guia in guias:
            with guia.archivo.open('rb') as archivo:
                self.assertEqual(archivo.read(4), b'%PDF')
        bienvenida = lecciones.order_by('modulo__orden', 'orden').first()
        self.assertEqual(bienvenida.tipo, 'video')
        self.assertTrue(bienvenida.archivo.name.endswith('.mp4'))
        with bienvenida.archivo.open('rb') as archivo:
            self.assertEqual(archivo.read(12)[4:8], b'ftyp')
        kit = lecciones.get(titulo='Kit del curso: aplicación, datos y plantillas (ZIP)')
        with kit.archivo.open('rb') as archivo:
            contenido = archivo.read()
        with ZipFile(BytesIO(contenido)) as zipfile:
            self.assertIsNone(zipfile.testzip())
            nombres = zipfile.namelist()
            self.assertIn('andina-distribucion/manage.py', nombres)
            self.assertIn('andina-distribucion/datos/productos_validos.csv', nombres)
            self.assertIn('andina-distribucion/datos/productos_invalidos.csv', nombres)
            self.assertFalse(any('/.venv/' in n or n.endswith('db.sqlite3') for n in nombres))
        self.assertEqual(contenido, datos.build_zip())

    def test_el_aula_y_los_descargables_conservan_el_control_de_acceso(self):
        self.cargar()
        curso = Curso.objects.get(unidad=self.unidad)
        curso.publicado = True
        curso.save(update_fields=['publicado'])
        argumentos = [self.unidad.slug, curso.codigo]
        portada = reverse('curso_unidad', args=argumentos)
        self.assertContains(self.client.get(portada), datos.CURSO['nombre'])
        self.client.force_login(self.admin)
        aula = self.client.get(reverse('aula_curso', args=argumentos))
        self.assertContains(aula, 'Andina Distribución')
        guias = list(LeccionCurso.objects.filter(modulo__curso=curso, tipo='material').exclude(archivo='')
                     .order_by('modulo__orden', 'orden'))
        ultima = next(leccion for leccion in reversed(guias) if leccion.modulo.orden == 5)
        descarga = reverse('material_leccion', args=[*argumentos, ultima.pk])
        respuesta = self.client.get(descarga)
        self.assertEqual(respuesta.status_code, 200)
        self.assertEqual(respuesta['Cache-Control'], 'private, no-store')
        self.assertTrue(b''.join(respuesta.streaming_content).startswith(b'%PDF'))
        self.client.logout()
        self.assertEqual(self.client.get(descarga).status_code, 302)
        primera = next(leccion for leccion in guias if leccion.modulo.orden == 1)
        respuesta = self.client.get(reverse('material_leccion', args=[*argumentos, primera.pk]))
        self.assertEqual(respuesta.status_code, 200)
        self.assertTrue(b''.join(respuesta.streaming_content).startswith(b'%PDF'))

    def test_bienvenida_publica_tiene_video_protegido_poster_y_subtitulos(self):
        self.cargar()
        curso = Curso.objects.get(unidad=self.unidad)
        curso.publicado = True
        curso.save(update_fields=['publicado'])
        bienvenida = LeccionCurso.objects.filter(modulo__curso=curso).order_by('modulo__orden', 'orden').first()
        base = [self.unidad.slug, curso.codigo, bienvenida.pk]
        respuesta = self.client.get(reverse('aula_curso_leccion', args=base))
        self.assertContains(respuesta, 'bienvenida-poster.png')
        self.assertContains(respuesta, 'bienvenida-es.vtt')
        self.assertContains(respuesta, 'controls playsinline preload="metadata"')
        self.assertNotContains(respuesta, 'autoplay')
        self.assertNotContains(respuesta, '[AULA_WIKI]')
        material = self.client.get(reverse('material_leccion', args=base))
        self.assertEqual(material.status_code, 200)
        self.assertEqual(material['Content-Type'], 'video/mp4')
        self.assertEqual(material['Cache-Control'], 'private, no-store')
        self.assertEqual(b''.join(material.streaming_content)[4:8], b'ftyp')
