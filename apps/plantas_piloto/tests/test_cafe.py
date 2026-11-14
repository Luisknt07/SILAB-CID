"""Carga conservadora, publicación y aislamiento del contenido de café."""
from decimal import Decimal
from datetime import date
from io import StringIO
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch

from django.core.exceptions import ValidationError
from django.core.management import call_command
from django.db import connection
from django.test import TestCase, override_settings
from django.test.utils import CaptureQueriesContext
from django.urls import reverse

from apps.directorio_unidades.models.core import Unidad
from apps.gestion_unidades.models.espacios import EspacioReservable
from apps.gestion_unidades.models.fichas import FichaContenido
from apps.gestion_unidades.models.operaciones import ConfiguracionOperativaUnidad
from apps.plantas_piloto.operacion.management.plantas.cafe import SLUG
from apps.plantas_piloto.operacion.models.produccion import EtapaReceta, InsumoReceta, LoteProducto, OrdenProduccion, Producto, Receta
from apps.recursos.models.consumibles import Consumible
from apps.recursos.models.recursos import ModuloUnidad, Recurso
from apps.recursos.models.unidades import UnidadEquipo
from apps.plantas_piloto.operacion.presentation.secciones_plantas import MAPA_PLANTA


class CafeContenidoTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.unidad = Unidad.objects.create(nombre='Planta de café', slug=SLUG, dependencia='plantas_piloto', clasificacion_funcional='planta_piloto', fecha_inicio=date(2026, 1, 1))
        ConfiguracionOperativaUnidad.objects.get_or_create(unidad=cls.unidad)
        for orden, (clave, (titulo, _)) in enumerate(MAPA_PLANTA.pestanas.items(), 1):
            ModuloUnidad.objects.get_or_create(unidad=cls.unidad, clave=clave, defaults={'nombre': titulo, 'orden': orden})
        for codigo in ('PPCA-BENEFICIO', 'PPCA-TORREFACCION'):
            EspacioReservable.objects.create(unidad=cls.unidad, codigo=codigo, nombre=codigo)

    def setUp(self):
        self.temporal = TemporaryDirectory()
        self.addCleanup(self.temporal.cleanup)
        self.ajustes = override_settings(MEDIA_ROOT=self.temporal.name)
        self.ajustes.enable()
        self.addCleanup(self.ajustes.disable)

    def cargar(self):
        call_command('preparar_planta_cafe', aplicar=True, stdout=StringIO())

    def test_simular_solo_hace_select_y_no_crea_archivos(self):
        with CaptureQueriesContext(connection) as consultas:
            call_command('preparar_planta_cafe', simular=True, stdout=StringIO())
        self.assertTrue(all(q['sql'].lstrip().upper().startswith('SELECT') for q in consultas), [q['sql'][:100] for q in consultas])
        self.assertFalse(Receta.objects.filter(unidad=self.unidad).exists())
        self.assertEqual(list(Path(self.temporal.name).rglob('*')), [])

    def test_carga_modelos_validos_sin_stock_activos_ni_operaciones(self):
        self.cargar()
        self.assertEqual(Receta.objects.filter(unidad=self.unidad).count(), 12)
        self.assertEqual(Producto.objects.filter(unidad=self.unidad).count(), 14)
        self.assertEqual(EtapaReceta.objects.filter(receta__unidad=self.unidad).count(), 59)
        self.assertFalse(Consumible.objects.filter(unidad=self.unidad).exclude(stock_total=0).exists())
        self.assertFalse(UnidadEquipo.objects.filter(laboratorio=self.unidad).exists())
        self.assertFalse(OrdenProduccion.objects.filter(unidad=self.unidad).exists())
        self.assertFalse(LoteProducto.objects.filter(unidad=self.unidad).exists())
        self.assertFalse(EtapaReceta.objects.filter(receta__unidad=self.unidad, punto_critico=True).exists())
        for model, filtro in ((Producto, {'unidad': self.unidad}), (Receta, {'unidad': self.unidad}),
                              (EtapaReceta, {'receta__unidad': self.unidad}), (InsumoReceta, {'receta__unidad': self.unidad})):
            for objeto in model.objects.filter(**filtro):
                objeto.full_clean()

    def test_repetir_conserva_ediciones_desactivaciones_y_archivos(self):
        self.cargar()
        receta = Receta.objects.get(codigo='CAF-R-LAVADO')
        receta.nombre = 'Proceso ajustado por la planta'
        receta.activa = False
        receta.save()
        recurso = Recurso.objects.filter(unidad=self.unidad).first()
        recurso.nombre = 'Guía editada por la unidad'
        recurso.activo = False
        recurso.save()
        config = ConfiguracionOperativaUnidad.objects.get(unidad=self.unidad)
        config.registra_produccion = False
        config.save()
        archivos = sorted(str(p) for p in Path(self.temporal.name).rglob('*') if p.is_file())
        self.cargar()
        receta.refresh_from_db()
        recurso.refresh_from_db()
        config.refresh_from_db()
        self.assertEqual(receta.nombre, 'Proceso ajustado por la planta')
        self.assertFalse(receta.activa)
        self.assertEqual(recurso.nombre, 'Guía editada por la unidad')
        self.assertFalse(recurso.activo)
        self.assertFalse(config.registra_produccion)
        self.assertEqual(archivos, sorted(str(p) for p in Path(self.temporal.name).rglob('*') if p.is_file()))
        self.assertEqual(Recurso.objects.filter(unidad=self.unidad).count(), 34)

    def test_fallo_retira_solo_archivos_nuevos_y_revierte_catalogo(self):
        previo = Path(self.temporal.name) / 'conservar.txt'
        previo.write_text('Archivo de la unidad', encoding='utf-8')
        with patch.object(Recurso, 'full_clean', side_effect=ValidationError('Revisión fallida')):
            with self.assertRaises(ValidationError):
                self.cargar()
        self.assertFalse(Receta.objects.filter(unidad=self.unidad).exists())
        self.assertEqual([p for p in Path(self.temporal.name).rglob('*') if p.is_file()], [previo])

    def test_publicacion_de_referencia_no_fabrica_validacion_institucional(self):
        self.cargar()
        fichas = FichaContenido.objects.filter(unidad=self.unidad, tipo='proceso')
        self.assertEqual(fichas.count(), 12)
        self.assertTrue(all(f.estado == 'publicada' and f.visibilidad == 'publica' and f.estado_validacion == 'pendiente' for f in fichas))
        receta = Receta.objects.get(codigo='CAF-R-LAVADO')
        response = self.client.get(reverse('ficha_proceso_publica', args=[SLUG, receta.pk]))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'escenario docente')

    def test_seis_pestanas_tienen_recursos_y_documentos_sin_scripts(self):
        self.cargar()
        recursos = Recurso.objects.filter(unidad=self.unidad).select_related('carpeta__modulo_config')
        self.assertEqual({r.carpeta.modulo_config.clave for r in recursos}, set(MAPA_PLANTA.pestanas))
        for r in recursos:
            if r.archivo and r.archivo.name.endswith('.html'):
                with r.archivo.open('rb') as archivo:
                    texto = archivo.read().decode('utf-8')
                self.assertNotIn('<script', texto)
                self.assertNotIn('<iframe', texto)
                self.assertIn('default-src &apos;none&apos;', texto)
                self.assertIn('lang="es"', texto)

    def test_calculadora_publica_es_lectura_y_no_se_abre_en_otra_planta(self):
        url = reverse('calculadora_cafe', args=[SLUG])
        with CaptureQueriesContext(connection) as consultas:
            response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertFalse(any(q['sql'].lstrip().upper().startswith(('INSERT', 'UPDATE', 'DELETE')) for q in consultas))
        self.assertEqual(self.client.post(url).status_code, 405)
        otra = Unidad.objects.create(nombre='Otra planta', slug='otra-planta', dependencia='plantas_piloto', fecha_inicio=date(2026, 1, 1))
        self.assertEqual(self.client.get(reverse('calculadora_cafe', args=[otra.slug])).status_code, 404)

    def test_empaque_cuenta_masa_y_envases_separados(self):
        self.cargar()
        receta = Receta.objects.get(codigo='CAF-R-MOL250')
        self.assertEqual(receta.rendimiento_esperado, Decimal('9.9'))
        self.assertEqual(receta.producto.unidad_medida, 'kg')
        self.assertEqual(set(receta.insumos.filter(consumible__clasificacion='empaque').values_list('forma_parte', flat=True)), {'no'})
        self.assertEqual(receta.insumos.get(forma_parte='base').cantidad, Decimal('10'))
