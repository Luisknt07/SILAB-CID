"""Las propuestas editoriales son privadas, repetibles y no generan actividad académica."""
from datetime import date
from io import StringIO
from types import SimpleNamespace
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.core.management import call_command
from django.core.management.base import CommandError
from django.db import connection
from django.test import TestCase
from django.urls import reverse

from apps.formacion.management.commands.cargar_ejemplos_formacion import codigo_ejemplo
from apps.formacion.management.cursos_precargados.ejemplos_formacion import PROPUESTAS, UNIDAD_PREDETERMINADA, propuestas_para
from apps.formacion.models.cursos import Curso, EdicionCurso
from apps.directorio_unidades.models.core import Unidad


class EjemplosFormacionTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.gestor = get_user_model().objects.create_superuser('ejemplos-formacion-admin', 'ejemplos@example.org', 'clave')
        cls.unidad = Unidad.objects.create(
            nombre='Laboratorio de Logística de Prueba', slug=UNIDAD_PREDETERMINADA,
            dependencia='laboratorios', descripcion='Unidad de prueba', fecha_inicio=date(2026, 1, 1),
            administrador=cls.gestor)

    def cargar(self, *argumentos, unidad=None):
        salida = StringIO()
        opciones = {'stdout': salida}
        if unidad:
            opciones['unidad'] = unidad.slug
        call_command('cargar_ejemplos_formacion', *argumentos, **opciones)
        return salida.getvalue()

    def test_carga_siete_fichas_completas_sin_abrir_convocatorias(self):
        salida = self.cargar()
        cursos = list(Curso.objects.filter(unidad=self.unidad))
        self.assertEqual(len(cursos), len(PROPUESTAS))
        self.assertIn('7 borradores creados', salida)
        self.assertEqual({curso.clasificacion for curso in cursos},
                         {'taller', 'webinar', 'seminario', 'jornada', 'encuentro', 'congreso', 'capacitacion'})
        for curso in cursos:
            with self.subTest(curso=curso.codigo):
                curso.full_clean()
                self.assertFalse(curso.publicado)
                self.assertTrue(curso.activo)
                self.assertFalse(curso.ediciones.exists())
                self.assertFalse(curso.modulos.exists())
                self.assertFalse(curso.pago_transferencia or curso.pago_ventanilla or curso.pago_enlace)
                self.assertFalse(curso.emite_certificado)
                self.assertIsNone(curso.costo)
                self.assertTrue(all((curso.lema, curso.descripcion, curso.aprendizajes,
                                     curso.dirigido_a, curso.requisitos, curso.instructores, curso.duracion_horas)))
                self.assertIn(self.unidad.nombre, curso.descripcion)
                self.assertIn('La duración es orientativa', curso.descripcion)
                self.assertIn('Equipo académico por designar', curso.instructores)
                self.assertLessEqual(len(curso.codigo), 40)

    def test_repetir_preserva_textos_estados_y_ediciones_manuales(self):
        self.cargar()
        curso = Curso.objects.filter(unidad=self.unidad, origen='nativo').first()
        curso.nombre = 'Nombre ajustado por el equipo académico'
        curso.descripcion = 'Contenido editorial revisado por el gestor.'
        curso.publicado = True
        curso.activo = False
        curso.save()
        edicion = EdicionCurso.objects.create(curso=curso, nombre='Programación interna', anio=2026, activa=False)
        fecha_actualizacion = curso.fecha_actualizacion
        salida = self.cargar()
        curso.refresh_from_db()
        edicion.refresh_from_db()
        self.assertEqual(Curso.objects.filter(unidad=self.unidad).count(), 7)
        self.assertEqual(curso.nombre, 'Nombre ajustado por el equipo académico')
        self.assertEqual(curso.descripcion, 'Contenido editorial revisado por el gestor.')
        self.assertTrue(curso.publicado)
        self.assertFalse(curso.activo)
        self.assertEqual(curso.fecha_actualizacion, fecha_actualizacion)
        self.assertEqual(edicion.nombre, 'Programación interna')
        self.assertFalse(edicion.activa)
        self.assertIn('0 borradores creados; 7 fichas conservadas', salida)

    def test_nombre_preexistente_no_se_duplica_ni_se_reescribe(self):
        nombre = PROPUESTAS[0]['nombre']
        existente = Curso.objects.create(unidad=self.unidad, codigo='MANUAL-EXISTENTE',
            nombre='  ' + nombre.upper() + '  ', descripcion='Ficha original', publicado=True, activo=False)
        self.cargar()
        existente.refresh_from_db()
        self.assertEqual(Curso.objects.filter(unidad=self.unidad).count(), 7)
        self.assertEqual(existente.descripcion, 'Ficha original')
        self.assertEqual(existente.nombre, '  ' + nombre.upper() + '  ')
        self.assertTrue(existente.publicado)
        self.assertFalse(existente.activo)
        self.assertFalse(Curso.objects.filter(unidad=self.unidad, nombre=nombre).exists())

    def test_prefijo_cambiado_no_duplica_fichas_renombradas(self):
        with patch('apps.formacion.management.commands.cargar_ejemplos_formacion.sigla_de_unidad', return_value='LOG'):
            self.cargar()
        curso = Curso.objects.filter(unidad=self.unidad).first()
        codigo = curso.codigo
        curso.nombre = 'Título manual que debe mantenerse'
        curso.save(update_fields=['nombre'])
        with patch('apps.formacion.management.commands.cargar_ejemplos_formacion.sigla_de_unidad', return_value='NUEVA'):
            self.cargar()
        curso.refresh_from_db()
        self.assertEqual(Curso.objects.filter(unidad=self.unidad).count(), 7)
        self.assertEqual(curso.codigo, codigo)
        self.assertEqual(curso.nombre, 'Título manual que debe mantenerse')

    def test_otra_unidad_tiene_codigos_y_contenidos_independientes(self):
        otra = Unidad.objects.create(nombre='Unidad de Innovación de Prueba', slug='unidad-formacion-prueba',
            dependencia='laboratorios', descripcion='Otra unidad', fecha_inicio=date(2026, 1, 1))
        with patch('apps.formacion.management.commands.cargar_ejemplos_formacion.sigla_de_unidad', return_value='UNI'):
            self.cargar()
            self.cargar(unidad=otra)
        self.assertEqual(Curso.objects.count(), 14)
        self.assertEqual(Curso.objects.values('codigo').distinct().count(), 14)
        for curso in Curso.objects.filter(unidad=otra):
            self.assertIn(otra.nombre, curso.descripcion)
            self.assertNotIn(self.unidad.nombre, curso.descripcion)
        self.assertLessEqual(len(codigo_ejemplo(SimpleNamespace(pk=2**63 - 1), 7, 'SIGLALARGA')), 40)

    def test_simular_no_escribe_sql_ni_archivos_ni_llama_save(self):
        sentencias = []

        def solo_lectura(execute, sql, params, many, contexto):
            sentencia = sql.lstrip().upper()
            self.assertFalse(sentencia.startswith(('INSERT', 'UPDATE', 'DELETE', 'CREATE', 'ALTER', 'DROP',
                                                   'TRUNCATE', 'COPY', 'GRANT', 'REVOKE')))
            self.assertNotIn('FOR UPDATE', sentencia)
            sentencias.append(sentencia)
            return execute(sql, params, many, contexto)

        with connection.execute_wrapper(solo_lectura), \
                patch.object(Curso, 'save', side_effect=AssertionError('La simulación no guarda modelos')), \
                patch('django.core.files.storage.default_storage.save',
                      side_effect=AssertionError('La simulación no guarda archivos')):
            salida = self.cargar('--simular')
        self.assertIn('Simulación: se crearían 7 borradores', salida)
        self.assertTrue(sentencias)
        self.assertFalse(Curso.objects.exists())
        self.assertFalse(EdicionCurso.objects.exists())

    def test_borradores_externos_no_inventan_alianzas_ni_enlaces(self):
        self.cargar()
        externo = Curso.objects.get(unidad=self.unidad, origen='externo')
        self.assertEqual(externo.url_externa, '')
        self.assertEqual(externo.entidad_organizadora, '')
        self.assertEqual(externo.participacion_unidad, 'colaborador')
        self.assertIn('Indicar organizador y enlace confirmados antes de publicar', externo.descripcion)
        externo.full_clean()
        externo.publicado = True
        with self.assertRaises(ValidationError):
            externo.full_clean()

    def test_catalogo_publico_oculta_propuestas_y_gestor_puede_revisarlas(self):
        self.cargar()
        url = reverse('cursos_unidad', args=[self.unidad.slug])
        publico = self.client.get(url)
        self.assertEqual(publico.status_code, 200)
        self.assertEqual(publico.context['total_cursos'], 0)
        self.assertNotContains(publico, PROPUESTAS[0]['nombre'])
        self.client.force_login(self.gestor)
        privado = self.client.get(url)
        self.assertEqual(privado.status_code, 200)
        self.assertEqual(privado.context['total_cursos'], 7)
        self.assertContains(privado, PROPUESTAS[0]['nombre'])
        self.assertContains(privado, 'Enlace pendiente de confirmar')
        self.assertNotContains(privado, 'href="" target="_blank"')

    def test_unidad_inexistente_no_crea_datos(self):
        with self.assertRaises(CommandError):
            call_command('cargar_ejemplos_formacion', unidad='no-existe', stdout=StringIO())
        self.assertFalse(Curso.objects.exists())

    def test_datos_editoriales_se_copian_sin_mutar_el_catalogo_fuente(self):
        primeras = propuestas_para(self.unidad)
        primeras[0]['nombre'] = 'Cambio de una copia'
        siguientes = propuestas_para(self.unidad)
        self.assertEqual(siguientes[0]['nombre'], PROPUESTAS[0]['nombre'])
        self.assertNotIn('publicado', PROPUESTAS[0])
