"""Importación verificable de medios, sin crear existencias ni pisar trabajo manual."""
from copy import deepcopy
from datetime import date
import hashlib
from io import StringIO
import json
from pathlib import Path
from tempfile import TemporaryDirectory
from PIL import Image

from django.conf import settings
from django.core.management import call_command
from django.core.management.base import CommandError
from django.test import SimpleTestCase, TestCase

from apps.directorio_unidades.models.core import Unidad
from apps.formacion.models.practicas import RegistroAuditoriaUnidad
from apps.recursos.management.commands.importar_medios_fablab_2026 import SLUG, combinar, validar_svg
from django.core.exceptions import ValidationError
from apps.recursos.models.consumibles import Consumible
from apps.recursos.models.equipos import EquiposServicios, VideoEquipo
from apps.recursos.models.software import SoftwareDisponible
from apps.recursos.models.unidades import UnidadEquipo


class CombinarMediosTests(SimpleTestCase):
    def test_svg_estatico_conserva_paths_y_rechaza_contenido_activo_o_externo(self):
        with TemporaryDirectory(prefix='qa-svg-', dir=Path(settings.BASE_DIR) / 'var') as carpeta:
            archivo = Path(carpeta) / 'logo.svg'
            archivo.write_text('<svg xmlns="http://www.w3.org/2000/svg"><defs><linearGradient id="g"/></defs>'
                               '<path id="p" d="M0 0L1 1" fill="url(#g)"/><use href="#p"/></svg>', encoding='utf-8')
            validar_svg(archivo)
            prohibidos = ['<script>alert(1)</script>', '<foreignObject/>', '<path onload="alert(1)"/>',
                          '<image href="https://example.org/a.png"/>', '<image href="data:image/png,x"/>',
                          '<path style="fill:url(https://example.org/a.svg#g)"/>',
                          '<style>@import "https://example.org/a.css";</style>',
                          '<set attributeName="href" to="javascript:alert(1)"/>']
            for cuerpo in prohibidos:
                with self.subTest(cuerpo=cuerpo), self.assertRaises(ValidationError):
                    archivo.write_text('<svg xmlns="http://www.w3.org/2000/svg">' + cuerpo + '</svg>', encoding='utf-8')
                    validar_svg(archivo)
            archivo.write_text('<!DOCTYPE svg [<!ENTITY x "externo">]><svg xmlns="http://www.w3.org/2000/svg"/>', encoding='utf-8')
            with self.assertRaises(ValidationError):
                validar_svg(archivo)

    def test_conserva_campos_manuales_y_completa_lista_por_url(self):
        actual = {'estado': 'identidad_pendiente', 'limite': 'Observación propia',
                  'documentos': [{'url': 'https://example.org/manual', 'titulo': 'Título manual'}]}
        previo = deepcopy(actual)
        nuevo = {'estado': 'modelo_identificado', 'limite': 'Referencia',
                 'documentos': [{'url': 'https://example.org/manual', 'titulo': 'Otro título',
                                  'fuente': 'https://example.org/fabricante'}]}
        combinado = combinar(actual, nuevo)
        self.assertEqual(combinado['estado'], 'identidad_pendiente')
        self.assertEqual(combinado['limite'], 'Observación propia')
        self.assertEqual(combinado['documentos'][0]['titulo'], 'Título manual')
        self.assertEqual(combinado['documentos'][0]['fuente'], 'https://example.org/fabricante')
        self.assertEqual(len(combinado['documentos']), 1)
        self.assertEqual(actual, previo)

    def test_reemplazo_revisado_conserva_medios_no_mencionados(self):
        actual = {'estado': 'identidad_pendiente', 'documentos': [{'url': 'https://example.org/manual', 'titulo': 'Manual'}]}
        combinado = combinar(actual, {'estado': 'modelo_identificado'}, reemplazar=True)
        self.assertEqual(combinado['estado'], 'modelo_identificado')
        self.assertEqual(combinado['documentos'], actual['documentos'])


class ImportarMediosFabLabTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        Unidad.objects.filter(slug=SLUG).update(slug='fablab-medios-historico-qa')
        cls.unidad = Unidad.objects.create(nombre='FabLab medios QA', slug=SLUG, dependencia='laboratorios', fecha_inicio=date(2026, 1, 1))
        cls.otra = Unidad.objects.create(nombre='Otra unidad medios QA', slug='otra-medios-qa', dependencia='laboratorios', fecha_inicio=date(2026, 1, 1))
        cls.modelo = EquiposServicios.objects.create(codigo='MED-MOD-QA', nombre='Impresora medios QA', marca='Fabricante QA', modelo='Variante QA')
        cls.activo = UnidadEquipo.objects.create(codigo_unidad='MED-ACT-QA', equipo=cls.modelo, laboratorio=cls.unidad)
        cls.software = SoftwareDisponible.objects.create(unidad=cls.unidad, codigo='MED-SW-QA', nombre='Programa medios QA', activo=False, licencias_totales=0, licencias_disponibles=0)
        cls.material = Consumible.objects.create(unidad=cls.unidad, codigo='MED-CONS-QA', nombre='Material medios QA', clasificacion='material', stock_total=0)

    def setUp(self):
        self.carpeta = TemporaryDirectory(prefix='qa-medios-', dir=Path(settings.BASE_DIR) / 'var')
        self.addCleanup(self.carpeta.cleanup)
        self.raiz = Path(self.carpeta.name)
        self.override = self.settings(STATICFILES_DIRS=[self.raiz / 'static'])
        self.override.enable()
        self.addCleanup(self.override.disable)
        self.ruta = 'img/catalogo/fablab/oficiales/qa-medios-unico.png'
        destino = self.raiz / 'static' / self.ruta
        destino.parent.mkdir(parents=True)
        Image.new('RGB', (2, 2), color='white').save(destino)
        self.hash = hashlib.sha256(destino.read_bytes()).hexdigest()

    def entrada(self, tipo, objeto, **datos):
        return {'tipo': tipo, 'id': objeto.pk, 'codigo': objeto.codigo,
                'identidad': {'nombre': objeto.nombre},
                'medios_referencia': {'estado': 'modelo_identificado', 'limite': 'Referencia del fabricante; no acredita recepción.'}, **datos}

    def imagen(self, **datos):
        return {'ruta_estatica': self.ruta, 'sha256': self.hash, 'fuente': 'https://example.org/fabricante',
                'credito': '© Fabricante QA · imagen del modelo de referencia',
                'licencia': 'No se acredita licencia abierta; consultar términos del fabricante.', **datos}

    def ejecutar(self, entradas, aplicar=True):
        manifiesto = self.raiz / 'manifiesto.json'
        manifiesto.write_text(json.dumps({'version': 1, 'unidad': SLUG, 'recursos': entradas}), encoding='utf-8')
        salida = StringIO()
        call_command('importar_medios_fablab_2026', manifiesto=str(manifiesto), aplicar=aplicar, stdout=salida)
        return salida.getvalue()

    def test_simula_sin_cambiar_medios_inventario_o_auditoria(self):
        antes = (UnidadEquipo.objects.count(), Consumible.objects.count(), SoftwareDisponible.objects.count())
        self.ejecutar([self.entrada('equipo', self.modelo, imagen=self.imagen())], aplicar=False)
        self.modelo.refresh_from_db()
        self.assertFalse(self.modelo.imagen_catalogo)
        self.assertEqual(self.modelo.medios_referencia, {})
        self.assertEqual(antes, (UnidadEquipo.objects.count(), Consumible.objects.count(), SoftwareDisponible.objects.count()))
        self.assertFalse(RegistroAuditoriaUnidad.objects.filter(unidad=self.unidad).exists())

    def test_aplicar_y_repetir_no_duplica_video_ni_auditoria(self):
        videos = [{'url': 'https://youtu.be/AbCdEfGhIj1', 'titulo': 'Uso oficial QA', 'canal': 'Fabricante QA'},
                  {'url': 'https://www.youtube.com/watch?v=AbCdEfGhIj1&t=20', 'titulo': 'Mismo video', 'canal': 'Fabricante QA'}]
        entrada = self.entrada('equipo', self.modelo, imagen=self.imagen(), videos=videos)
        self.ejecutar([entrada])
        self.modelo.refresh_from_db()
        fecha = self.modelo.fecha_actualizacion
        self.ejecutar([entrada])
        self.modelo.refresh_from_db()
        self.assertEqual(self.modelo.imagen_catalogo, self.ruta)
        self.assertEqual(VideoEquipo.objects.filter(equipo=self.modelo).count(), 1)
        self.assertEqual(RegistroAuditoriaUnidad.objects.filter(unidad=self.unidad).count(), 1)
        self.assertEqual(self.modelo.fecha_actualizacion, fecha)
        self.assertEqual(self.modelo.medios_referencia['imagen']['credito'], self.imagen()['credito'])

    def test_foto_local_y_su_credito_manual_se_conservan(self):
        self.modelo.imagen = 'propias/foto-del-responsable.png'
        self.modelo.imagen_catalogo = 'img/manual/catalogo-existente.png'
        self.modelo.credito_imagen = 'Crédito manual'
        self.modelo.fuente_imagen = 'https://example.org/manual'
        self.modelo.medios_referencia = {'estado': 'modelo_identificado', 'imagen': {
            'fuente': 'https://example.org/manual', 'credito': 'Autor propio', 'licencia': 'Autorización propia'}}
        self.modelo.save()
        entrada = self.entrada('equipo', self.modelo, imagen=self.imagen(), medios_referencia={
            'estado': 'modelo_identificado', 'imagen': {'fuente': 'https://example.org/catalogo', 'credito': 'Catálogo'}})
        salida = self.ejecutar([entrada])
        self.modelo.refresh_from_db()
        self.assertIn('local protegido', salida)
        self.assertEqual(self.modelo.imagen.name, 'propias/foto-del-responsable.png')
        self.assertEqual(self.modelo.imagen_catalogo, 'img/manual/catalogo-existente.png')
        self.assertEqual(self.modelo.credito_imagen, 'Crédito manual')
        self.assertEqual(self.modelo.medios_referencia['imagen']['credito'], 'Autor propio')

    def test_recurso_ajeno_impide_aplicar_tambien_la_primera_entrada(self):
        ajeno = SoftwareDisponible.objects.create(unidad=self.otra, nombre='Programa ajeno QA', codigo='AJENO-QA')
        with self.assertRaisesMessage(CommandError, 'no pertenece'):
            self.ejecutar([self.entrada('consumible', self.material), self.entrada('software', ajeno)])
        self.material.refresh_from_db()
        self.assertEqual(self.material.medios_referencia, {})
        self.assertFalse(RegistroAuditoriaUnidad.objects.filter(unidad=self.unidad).exists())

    def test_catalogo_solo_se_retira_con_esperado_exacto_y_no_borra_cambios_posteriores(self):
        esperado = {'catalogo': 'img/catalogo/familias/ejemplo-generico.jpg', 'credito': 'Foto del tipo', 'fuente': 'https://example.org/tipo'}
        self.modelo.imagen_catalogo, self.modelo.credito_imagen, self.modelo.fuente_imagen = esperado.values()
        self.modelo.save()
        entrada = self.entrada('equipo', self.modelo, limpiar_catalogo=True, imagen={'esperado': esperado},
                               medios_referencia={'estado': 'identidad_pendiente', 'limite': 'Falta identificar el modelo.'})
        self.ejecutar([entrada])
        self.ejecutar([entrada])
        self.modelo.refresh_from_db()
        self.assertEqual(self.modelo.imagen_catalogo, '')
        self.modelo.imagen_catalogo = 'img/manual/foto-nueva.jpg'
        self.modelo.save(update_fields=['imagen_catalogo'])
        with self.assertRaisesMessage(CommandError, 'esperado'):
            self.ejecutar([entrada])
        self.modelo.refresh_from_db()
        self.assertEqual(self.modelo.imagen_catalogo, 'img/manual/foto-nueva.jpg')

    def test_hash_incorrecto_y_video_de_dominio_falso_no_guardan(self):
        casos = [self.entrada('equipo', self.modelo, imagen=self.imagen(sha256='0' * 64)),
                 self.entrada('equipo', self.modelo, videos=[{'url': 'https://example.org/?v=AbCdEfGhIj1',
                     'titulo': 'Dominio ajeno', 'canal': 'Canal QA'}])]
        for entrada in casos:
            with self.subTest(entrada=entrada), self.assertRaises(CommandError):
                self.ejecutar([entrada])
        self.modelo.refresh_from_db()
        self.assertEqual(self.modelo.medios_referencia, {})
        self.assertFalse(VideoEquipo.objects.filter(equipo=self.modelo).exists())

    def test_archivo_html_con_extension_png_no_se_admite_aunque_coincida_el_hash(self):
        archivo = self.raiz / 'static' / self.ruta
        archivo.write_text('<html>No es una imagen</html>', encoding='utf-8')
        sha = hashlib.sha256(archivo.read_bytes()).hexdigest()
        with self.assertRaisesMessage(CommandError, 'imagen válida'):
            self.ejecutar([self.entrada('equipo', self.modelo, imagen=self.imagen(sha256=sha))])

    def test_equipo_compartido_por_m2m_admite_documentos_sin_tocar_mediciones(self):
        self.activo.laboratorio = self.otra
        self.activo.save(update_fields=['laboratorio'])
        self.activo.laboratorios.add(self.unidad)
        self.modelo.origen_datos_tecnicos = 'medido'
        self.modelo.especificaciones = {'Valor medido': 'Validado'}
        self.modelo.save()
        entrada = self.entrada('equipo', self.modelo, informacion={'descripcion': 'Referencia', 'especificaciones': {'Nueva': 'Referencia'}},
            medios_referencia={'estado': 'modelo_identificado', 'documentos': [{'url': 'https://example.org/manual', 'titulo': 'Manual oficial'}]})
        self.ejecutar([entrada])
        self.modelo.refresh_from_db()
        self.assertEqual(self.modelo.especificaciones, {'Valor medido': 'Validado'})
        self.assertFalse(self.modelo.descripcion)
        self.assertEqual(self.modelo.medios_referencia['documentos'][0]['titulo'], 'Manual oficial')

    def test_metadatos_manuales_solo_cambian_con_esperado_y_una_repeticion_es_vacia(self):
        self.material.medios_referencia = {'estado': 'identidad_pendiente', 'limite': 'Observación propia'}
        self.material.save(update_fields=['medios_referencia'])
        nuevo = {'estado': 'modelo_identificado', 'limite': 'Modelo contrastado'}
        entrada = self.entrada('consumible', self.material, medios_referencia=nuevo)
        self.ejecutar([entrada])
        self.material.refresh_from_db()
        self.assertEqual(self.material.medios_referencia['limite'], 'Observación propia')
        entrada['medios_referencia_esperado'] = deepcopy(self.material.medios_referencia)
        self.ejecutar([entrada])
        self.ejecutar([entrada])
        self.material.refresh_from_db()
        self.assertEqual(self.material.medios_referencia, nuevo)
        self.material.medios_referencia['limite'] = 'Nueva edición manual'
        self.material.save(update_fields=['medios_referencia'])
        with self.assertRaisesMessage(CommandError, 'cambió desde la revisión'):
            self.ejecutar([entrada])
