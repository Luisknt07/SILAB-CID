"""Integración del catálogo completo: seguridad, aislamiento e idempotencia."""
import hashlib
import json
from io import StringIO
from unittest.mock import patch

from django.core.management import call_command
from django.core.management.base import CommandError
from django.db import connection
from django.test import TestCase
from django.test.utils import CaptureQueriesContext

from apps.plantas_piloto.operacion.presentation.secciones_plantas import MAPA_LABORATORIO
from apps.laboratorios.operacion.management.commands.preparar_logistica_contenidos import Command
from apps.laboratorios.operacion.management.commands.preparar_logistica_paso1 import contenido_recurso
from apps.laboratorios.operacion.management.laboratorios.logistica_catalogo import validar_catalogo
from apps.recursos.models.recursos import Recurso
from apps.formacion.models.practicas import RegistroAuditoriaUnidad
from tests.integration import test_preparar_logistica_paso1 as paso1_tests


class PrepararLogisticaContenidosTests(TestCase):
    # Reutiliza sólo la fixture del publicador original, sin duplicar sus pruebas.
    def setUp(self):
        paso1_tests.PrepararLogisticaPaso1Tests.setUp(self)
        self.recursos = Command()._recursos(list(self.unidad.asignaturas.all()))
        self.manifiesto.write_text(json.dumps({
            'sha256': [hashlib.sha256(contenido_recurso(r)).hexdigest()
                       for r in self.recursos if contenido_recurso(r)],
            'motor': 'Fixture aislada: sin antivirus ni publicación real',
            'resultado': 'sin_amenazas', 'fecha': '2026-10-12',
            'fuentes_enlaces_revisadas': True,
        }), encoding='utf-8')

    revisar = paso1_tests.PrepararLogisticaPaso1Tests.revisar

    def correr(self, **opciones):
        salida = StringIO()
        call_command('preparar_logistica_contenidos', stdout=salida, **opciones)
        return salida.getvalue()

    def aplicar(self):
        return self.correr(aplicar=True, manifiesto_revision=self.manifiesto)

    def test_paquete_cubre_las_28_secciones_con_identidades_y_bytes_unicos(self):
        self.assertEqual({r['seccion'] for r in self.recursos}, set(MAPA_LABORATORIO.secciones))
        self.assertEqual(len({r['clave'] for r in self.recursos}), len(self.recursos))
        contenidos = [contenido_recurso(r) for r in self.recursos if contenido_recurso(r)]
        self.assertEqual(len(set(contenidos)), len(contenidos))
        self.assertEqual(sum(r['clave'].startswith('practica-') for r in self.recursos), 12)
        self.assertEqual(sum(r['clave'].startswith('dataset-') for r in self.recursos), 12)
        self.assertEqual(sum(r['clave'].startswith('formacion-') for r in self.recursos), 7)
        self.assertEqual(sum(r['clave'].startswith('kit-') for r in self.recursos), 7)

    def test_simulacion_solo_select_sin_lectura_de_adjuntos_ni_archivos_nuevos(self):
        with patch('django.core.files.storage.FileSystemStorage._open', side_effect=AssertionError('No abrir adjuntos')):
            with CaptureQueriesContext(connection) as consultas:
                self.assertIn('[simulación SELECT]', self.correr(simular=True))
        self.assertTrue(all(q['sql'].lstrip().upper().startswith('SELECT') for q in consultas))
        self.assertFalse(Recurso.objects.exists())
        self.assertFalse(self.media.exists())
        self.assertFalse((self.base / 'var').exists())

    def test_revision_parcial_no_publica_csv_zip_ni_html(self):
        self.revisar()  # Sólo cubre el paquete original, no los nuevos bytes.
        with self.assertRaisesMessage(CommandError, 'no cubre los hashes exactos'):
            self.aplicar()
        self.assertFalse(Recurso.objects.exists())
        self.assertFalse(self.media.exists())
        self.assertFalse((self.base / 'var').exists())

    def test_publicacion_idempotente_preserva_ediciones_y_no_crea_oferta(self):
        self.aplicar()
        self.assertEqual(self.unidad.recursos.count(), len(self.recursos))
        self.assertFalse(self.unidad.cursos.exists())
        self.assertFalse(self.unidad.reservas.exists())
        original = list(self.unidad.recursos.values_list('pk', 'archivo', 'hash_sha256'))
        self.assertIn('sin cambios', self.aplicar())
        self.assertEqual(original, list(self.unidad.recursos.values_list('pk', 'archivo', 'hash_sha256')))
        self.assertEqual(RegistroAuditoriaUnidad.objects.count(), 1)
        self.assertEqual(len(list((self.base / 'var' / 'backups').glob('*.json'))), 1)
        recurso = self.unidad.recursos.get(palabras_clave__startswith='log-p1:practica-01;')
        recurso.nombre = 'Título revisado por el docente'
        recurso.activo = False
        recurso.save(update_fields=['nombre', 'activo'])
        carpeta = recurso.carpeta
        carpeta.nombre = 'Carpeta organizada por el administrador'
        carpeta.save(update_fields=['nombre'])
        self.assertIn('se conserva el recurso editado', self.aplicar())
        recurso.refresh_from_db()
        carpeta.refresh_from_db()
        self.assertEqual(recurso.nombre, 'Título revisado por el docente')
        self.assertFalse(recurso.activo)
        self.assertEqual(carpeta.nombre, 'Carpeta organizada por el administrador')
        self.assertFalse(self.otra.recursos.exists())

    def test_exporta_bytes_exactos_sin_escrituras_en_base_y_no_simula_aprobacion(self):
        destino = self.base / 'revision'
        with CaptureQueriesContext(connection) as consultas:
            texto = self.correr(exportar_directorio=destino)
        self.assertIn('La base no cambió', texto)
        self.assertTrue(all(q['sql'].lstrip().upper().startswith('SELECT') for q in consultas))
        inventario = json.loads((destino / 'inventario-revision.json').read_text(encoding='utf-8'))
        self.assertEqual(inventario['estado'], 'pendiente_de_revision')
        self.assertNotIn('resultado', inventario)
        for fila in inventario['adjuntos']:
            datos = (destino / fila['archivo']).read_bytes()
            self.assertEqual(hashlib.sha256(datos).hexdigest(), fila['sha256'])
        self.assertFalse(Recurso.objects.exists())
        with self.assertRaisesMessage(CommandError, 'ya existe'):
            self.correr(exportar_directorio=destino)
        for modo in ({'simular': True}, {'aplicar': True}):
            with self.assertRaisesMessage(CommandError, 'no se combina'):
                self.correr(exportar_directorio=self.base / 'otro', **modo)

    def test_rechaza_rutas_y_contenidos_ambiguos_antes_de_publicar(self):
        recurso = next(r for r in self.recursos if r.get('contenido'))
        for nombre in ('../fuera.csv', 'carpeta/datos.csv', 'carpeta\\datos.csv', 'C:escape.csv', 'datos.csv:ads', 'nul.csv'):
            with self.assertRaises(ValueError):
                validar_catalogo([{**recurso, 'nombre_archivo': nombre}])
        with self.assertRaises(TypeError):
            validar_catalogo([{**recurso, 'contenido': 'no bytes'}])
        with self.assertRaises(ValueError):
            validar_catalogo([recurso, recurso])
        with self.assertRaises(ValueError):
            validar_catalogo([{**recurso, 'html': '<p>duplicado</p>'}])

    def test_rollback_borra_solo_adjuntos_y_extracciones_recien_creados(self):
        original = Recurso.save
        def fallar_tras_extraer(recurso, *args, **kwargs):
            if recurso.es_zip and kwargs.get('update_fields') == ['palabras_clave']:
                self.assertTrue(recurso.directorio_extraido.is_dir())
                raise RuntimeError('Fallo posterior a extracción')
            return original(recurso, *args, **kwargs)
        previo = self.media / 'recursos' / 'archivos' / 'conservar'
        previo.mkdir(parents=True)
        (previo / 'original.txt').write_text('Histórico que debe conservarse', encoding='utf-8')
        with patch.object(Recurso, 'save', fallar_tras_extraer):
            with self.assertRaisesMessage(RuntimeError, 'Fallo posterior'):
                self.aplicar()
        self.assertFalse(Recurso.objects.exists())
        self.assertFalse(RegistroAuditoriaUnidad.objects.exists())
        self.assertEqual(list((self.media / 'recursos' / 'archivos').iterdir()), [previo])
        self.assertEqual((previo / 'original.txt').read_text(encoding='utf-8'), 'Histórico que debe conservarse')
