"""Corregir un ejemplo comercial no cambia bienes, existencias ni medios propios."""
from copy import deepcopy
from datetime import date
from decimal import Decimal
from types import SimpleNamespace

from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.template.loader import render_to_string
from django.test import SimpleTestCase, TestCase
from django.urls import reverse

from apps.directorio_unidades.models.core import Unidad
from apps.formacion.models.practicas import RegistroAuditoriaUnidad
from apps.gestion_unidades.presentation.edicion_registro import REGISTRO, formulario_de
from apps.gestion_unidades.presentation.plantillas_ficha import ficha_estandar
from apps.recursos.models.consumibles import Consumible
from apps.recursos.models.equipos import EquiposServicios, VideoEquipo
from apps.recursos.models.medios import validar_medios_referencia
from apps.recursos.models.software import SoftwareDisponible
from apps.recursos.models.unidades import UnidadEquipo
from apps.recursos.presentation.edicion_equipo import _guardar_videos
from apps.recursos.presentation.referencia_editor import CAMPOS_REFERENCIA, firma_video, videos_vigentes
from tests.integration.utiles import identificar


def medios():
    return {'estado': 'referencia_provisional',
            'identidad_propuesta': {'marca': 'Marca ejemplo', 'modelo': 'Modelo anterior', 'sku': 'QA-1'},
            'descripcion_referencia': 'Descripción del producto anterior.',
            'imagen': {'fuente': 'https://example.org/anterior', 'credito': 'Fabricante anterior'},
            'documentos': [{'titulo': 'Manual anterior', 'url': 'https://example.org/manual'}],
            'videos': [{'titulo': 'Video anterior', 'url': 'https://www.youtube.com/watch?v=aaaaaaaaaaa'}]}


def datos_referencia(prefix='registro', **cambios):
    datos = {'referencia_marca': 'Marca ejemplo', 'referencia_modelo': 'Modelo anterior',
             'referencia_sku': 'QA-1', 'referencia_variante': '', 'referencia_presentacion': '',
             'referencia_descripcion': 'Descripción del producto anterior.', 'referencia_presente': '1'}
    datos.update(cambios)
    return {prefix + '-' + campo: valor for campo, valor in datos.items()}


class ReferenciaComercialPuraTests(SimpleTestCase):
    def programa(self, **campos):
        return SoftwareDisponible(nombre='Programa de la unidad', medios_referencia=medios(),
            licencias_totales=0, licencias_disponibles=0, **campos)

    def formulario(self, instancia, datos=None, clave='software'):
        return formulario_de(REGISTRO[clave], None, ('nombre',), datos=datos, instancia=instancia)

    def test_campos_legibles_solo_para_referencia_existente_no_confirmada(self):
        for estado, habilitado in (('referencia_provisional', True), ('documentado_por_confirmar', True),
                                   ('modelo_identificado', False), ('identidad_pendiente', False)):
            with self.subTest(estado=estado):
                programa = self.programa()
                programa.medios_referencia['estado'] = estado
                formulario = self.formulario(programa)
                self.assertEqual(formulario.referencia_editable, habilitado)
                self.assertEqual(set(CAMPOS_REFERENCIA).issubset(formulario.fields), habilitado)
                self.assertNotIn('medios_referencia', formulario.fields)
        programa = self.programa()
        programa.medios_referencia = {}
        self.assertFalse(self.formulario(programa).referencia_editable)

    def test_descripcion_sola_conserva_la_procedencia_y_los_enlaces(self):
        programa = self.programa(logo_catalogo='img/software/anterior.png')
        anterior = deepcopy(programa.medios_referencia)
        formulario = self.formulario(programa, {'registro-nombre': programa.nombre,
            **datos_referencia(referencia_descripcion='Descripción revisada por la unidad.')})
        self.assertTrue(formulario.is_valid(), formulario.errors)
        self.assertEqual(programa.medios_referencia, anterior, 'Validar no escribe la referencia.')
        formulario.save(commit=False)
        self.assertEqual(programa.medios_referencia['documentos'], anterior['documentos'])
        self.assertEqual(programa.medios_referencia['imagen'], anterior['imagen'])
        self.assertFalse(programa.medios_referencia.get('medios_por_revisar'))
        self.assertEqual(programa.logo_catalogo, 'img/software/anterior.png')

    def test_otra_identidad_invalida_medios_y_conserva_stock_marca_y_foto_local(self):
        insumo = Consumible(nombre='Material de la unidad', marca='Marca física', stock_total=Decimal('7.50'),
            medios_referencia=medios(), imagen='unidad/foto-propia.jpg',
            imagen_catalogo='img/catalogo/anterior.jpg', fuente_imagen='https://example.org/anterior')
        anterior = deepcopy(insumo.medios_referencia)
        formulario = self.formulario(insumo, {'registro-nombre': insumo.nombre,
            **datos_referencia(referencia_modelo='Otro producto')}, clave='insumo')
        self.assertTrue(formulario.is_valid(), formulario.errors)
        formulario.save(commit=False)
        self.assertEqual((insumo.marca, insumo.stock_total, insumo.imagen.name),
                         ('Marca física', Decimal('7.50'), 'unidad/foto-propia.jpg'))
        self.assertEqual(insumo.imagen_catalogo, '')
        self.assertTrue(insumo.imagen_publica_url.endswith('/unidad/foto-propia.jpg'))
        self.assertEqual(insumo.medios_referencia['referencia_anterior']['datos'], anterior)
        self.assertTrue(insumo.medios_referencia['medios_por_revisar'])
        for clave, esperado in (('imagen', {}), ('documentos', []), ('videos', []), ('descripcion_referencia', '')):
            self.assertEqual(insumo.medios_referencia[clave], esperado)

    def test_variante_y_presentacion_tambien_pueden_cambiar_el_producto(self):
        for campo in ('referencia_sku', 'referencia_variante', 'referencia_presentacion'):
            with self.subTest(campo=campo):
                programa = self.programa()
                formulario = self.formulario(programa, {'registro-nombre': programa.nombre,
                    **datos_referencia(**{campo: 'Nueva variante', 'referencia_descripcion': 'Descripción nueva revisada.'})})
                self.assertTrue(formulario.is_valid(), formulario.errors)
                formulario.save(commit=False)
                self.assertTrue(programa.medios_referencia['medios_por_revisar'])
                self.assertEqual(programa.medios_referencia['descripcion_referencia'], 'Descripción nueva revisada.')

    def test_formulario_abierto_antes_no_borra_la_propuesta_por_omision(self):
        programa = self.programa()
        anterior = deepcopy(programa.medios_referencia)
        formulario = self.formulario(programa, {'registro-nombre': programa.nombre})
        self.assertTrue(formulario.is_valid(), formulario.errors)
        formulario.save(commit=False)
        self.assertEqual(programa.medios_referencia, anterior)

    def test_propuesta_incompleta_y_campos_excesivos_no_guardan_metadatos(self):
        for cambios, campo in (({'referencia_modelo': ''}, 'referencia_modelo'),
                               ({'referencia_marca': ''}, 'referencia_marca'),
                               ({'referencia_modelo': 'X' * 301}, 'referencia_modelo'),
                               ({'referencia_descripcion': 'X' * 2001}, 'referencia_descripcion')):
            with self.subTest(cambios=campo):
                programa = self.programa()
                anterior = deepcopy(programa.medios_referencia)
                formulario = self.formulario(programa, {'registro-nombre': programa.nombre, **datos_referencia(**cambios)})
                self.assertFalse(formulario.is_valid())
                self.assertIn(campo, formulario.errors)
                self.assertEqual(programa.medios_referencia, anterior)

    def test_catalogos_pendientes_no_reaparecen_por_fallback_y_fotos_propias_prevalecen(self):
        for recurso, campo in ((self.programa(logo_catalogo='img/software/anterior.png'), 'logo_publico_url'),
            (Consumible(nombre='Filamento PLA', imagen_catalogo='img/catalogo/anterior.png'), 'imagen_publica_url'),
            (EquiposServicios(nombre='Equipo', imagen_catalogo='img/catalogo/anterior.png'), 'imagen_publica_url')):
            with self.subTest(tipo=type(recurso).__name__):
                recurso.medios_referencia = {**medios(), 'medios_por_revisar': True}
                self.assertNotIn('anterior.png', getattr(recurso, campo))
                propio = 'logo' if isinstance(recurso, SoftwareDisponible) else 'imagen'
                setattr(recurso, propio, 'unidad/foto-propia.jpg')
                self.assertTrue(getattr(recurso, campo).endswith('/unidad/foto-propia.jpg'))
        with self.assertRaises(ValidationError):
            validar_medios_referencia({**medios(), 'medios_por_revisar': 'false'})

    def test_campos_de_referencia_se_escapan_sin_json_crudo(self):
        programa = self.programa()
        programa.medios_referencia['identidad_propuesta']['modelo'] = '\"><script>alert(1)</script>'
        programa.medios_referencia['descripcion_referencia'] = '</textarea><script>alert(2)</script>'
        formulario = self.formulario(programa)
        html = render_to_string('portal/pages/unidades/includes/editor_referencia_comercial.html', {'formulario': formulario})
        self.assertIn('referencia_modelo', html)
        self.assertIn('&lt;script&gt;', html)
        self.assertNotIn('<script>', html)
        self.assertNotIn('medios_referencia', html)

    def test_videos_por_revisar_no_caen_en_otra_familia_ni_ocultan_nuevos(self):
        antiguo = SimpleNamespace(pk=1, url='https://youtu.be/aaaaaaaaaaa', titulo='Anterior', canal='Fabricante')
        propio = SimpleNamespace(pk=2, url='https://youtu.be/bbbbbbbbbbb', titulo='Nuevo manual', canal='Unidad')
        familia = SimpleNamespace(videos=SimpleNamespace(all=lambda: [propio]))
        tipo = SimpleNamespace(videos=SimpleNamespace(all=lambda: [antiguo]), familia_id=1, familia=familia,
            medios_referencia={**medios(), 'videos_por_revisar': [firma_video(antiguo)]})
        self.assertEqual(videos_vigentes(tipo), [])
        tipo.videos = SimpleNamespace(all=lambda: [antiguo, propio])
        self.assertEqual(videos_vigentes(tipo), [propio])

    def test_ficha_conserva_acceso_a_corregir_referencia_y_revisar_videos_ocultos(self):
        tipo = EquiposServicios(nombre='Equipo por confirmar', medios_referencia={
            **medios(), 'videos': [], 'videos_por_revisar': [{'id': 1, 'url': 'https://youtu.be/aaaaaaaaaaa'}]})
        contexto = {'unidad': Unidad(nombre='Unidad', slug='unidad'),
            'detalle': {'tipo': tipo, 'estandar': {'videos': [], 'especificaciones': [], 'fotos': []}, 'unidades': []},
            'editar_ficha_url': '/editar-equipo/', 'unidad_equipo': SimpleNamespace(codigo_unidad='REF-1')}
        html = render_to_string('portal/pages/unidades/aula/equipo.html', contexto)
        self.assertIn('/editar-equipo/?seccion=modelo#modelo', html)
        self.assertIn('/editar-equipo/?seccion=videos#videos', html)
        self.assertIn('requieren revisión', html)
        self.assertNotIn('i.ytimg.com/vi/aaaaaaaaaaa', html)
        contexto['editar_ficha_url'] = ''
        publico = render_to_string('portal/pages/unidades/aula/equipo.html', contexto)
        self.assertNotIn('id="videos"', publico)
        self.assertNotIn('seccion=modelo', publico)


class EdicionReferenciaComercialTests(TestCase):
    databases = {'default', 'centros'}

    @classmethod
    def setUpTestData(cls):
        cls.gestor = get_user_model().objects.create_user('gestor-ref-comercial', password='clave')
        identificar(cls.gestor, tipo_usuario='administrativo', carrera='')
        cls.unidad = Unidad.objects.create(nombre='Unidad de referencias editables', slug='unidad-ref-comercial',
            dependencia='laboratorios', descripcion='.', fecha_inicio=date(2026, 1, 1), administrador=cls.gestor)
        cls.tipo = EquiposServicios.objects.create(codigo='REF-COM-MOD', nombre='Modelo de la unidad', medios_referencia=medios(),
            imagen_catalogo='img/catalogo/anterior.jpg', fuente_imagen='https://example.org/anterior',
            especificaciones={'Modelo de referencia': 'Marca ejemplo Modelo anterior', 'Dato propio': 'Conservar'})
        cls.activo = UnidadEquipo.objects.create(codigo_unidad='REF-COM-ACT', laboratorio=cls.unidad, equipo=cls.tipo)
        cls.manual = VideoEquipo.objects.create(equipo=cls.tipo, url='https://youtu.be/aaaaaaaaaaa', titulo='Video manual', canal='Unidad')
        cls.programa = SoftwareDisponible.objects.create(unidad=cls.unidad, codigo='REF-COM-SW', nombre='Programa de la unidad',
            licencias_totales=3, licencias_disponibles=2, medios_referencia=medios())
        cls.material = Consumible.objects.create(unidad=cls.unidad, codigo='REF-COM-MAT', nombre='Material de la unidad',
            marca='Marca física', stock_total=Decimal('7.50'), medios_referencia=medios())

    def setUp(self):
        self.client.force_login(self.gestor)

    def url(self):
        return reverse('editar_equipo_ficha', args=[self.unidad.slug, self.activo.codigo_unidad])

    def test_modelo_se_edita_sin_json_y_video_manual_se_conserva_hasta_revision_explicita(self):
        editor = self.client.get(self.url(), {'seccion': 'modelo', 'fragmento': '1'})
        self.assertContains(editor, 'name="modelo-referencia_modelo"')
        self.assertNotContains(editor, 'name="modelo-medios_referencia"')
        datos = {'seccion': 'modelo', 'modelo-nombre': self.tipo.nombre, 'modelo-marca': '', 'modelo-modelo': '',
            'modelo-origen_datos_tecnicos': 'referencia',
            **datos_referencia('modelo', referencia_modelo='Producto nuevo')}
        respuesta = self.client.post(self.url(), datos, HTTP_X_REQUESTED_WITH='fetch')
        self.assertEqual(respuesta.json(), {'ok': True})
        self.tipo.refresh_from_db()
        self.assertFalse(self.tipo.marca)
        self.assertFalse(self.tipo.modelo)
        self.assertEqual(self.tipo.especificaciones, {'Modelo de referencia': 'Marca ejemplo Producto nuevo', 'Dato propio': 'Conservar'})
        self.assertTrue(VideoEquipo.objects.filter(pk=self.manual.pk).exists(), 'La referencia no borra videos manuales.')
        self.assertEqual(ficha_estandar(self.tipo)['videos'], [])
        self.assertEqual(UnidadEquipo.objects.filter(equipo=self.tipo).count(), 1)
        auditoria = RegistroAuditoriaUnidad.objects.get(entidad=self.tipo._meta.label, objeto_id=str(self.tipo.pk))
        self.assertEqual((auditoria.usuario_id, auditoria.unidad_id), (self.gestor.pk, self.unidad.pk))
        self.assertEqual(auditoria.datos_anteriores['medios_referencia']['identidad_propuesta']['modelo'], 'Modelo anterior')
        self.client.post(self.url(), {'seccion': 'videos', 'videos': 'https://youtu.be/aaaaaaaaaaa | Video manual | Unidad'},
                         HTTP_X_REQUESTED_WITH='fetch')
        self.tipo.refresh_from_db()
        self.assertFalse(self.tipo.medios_referencia['videos_por_revisar'])
        self.assertEqual(len(ficha_estandar(self.tipo)['videos']), 1)

    def test_guardar_conjunto_de_videos_en_mismo_cambio_no_los_rehabilita(self):
        self.tipo.medios_referencia = {**medios(), 'videos_por_revisar': [firma_video(self.manual)]}
        self.tipo.save(update_fields=['medios_referencia'])
        _guardar_videos(self.tipo, [{'url': self.manual.url, 'titulo': 'Título corregido', 'canal': 'Otro canal'},
                                  {'url': 'https://youtu.be/bbbbbbbbbbb', 'titulo': 'Nuevo video', 'canal': 'Unidad'}],
                        confirmar_referencia=False)
        self.tipo.refresh_from_db()
        self.assertTrue(self.tipo.medios_referencia['videos_por_revisar'])
        self.assertEqual(self.tipo.videos.count(), 2)
        self.manual.refresh_from_db()
        self.assertEqual(self.manual.titulo, 'Título corregido')
        self.assertEqual(videos_vigentes(self.tipo), [])

    def test_propuesta_no_cambia_especificaciones_medidas_ni_foto_propia(self):
        self.tipo.origen_datos_tecnicos = 'medido'
        self.tipo.imagen = 'unidad/foto-propia.jpg'
        self.tipo.save(update_fields=['origen_datos_tecnicos', 'imagen'])
        originales = deepcopy(self.tipo.especificaciones)
        datos = {'seccion': 'modelo', 'modelo-nombre': self.tipo.nombre, 'modelo-marca': '', 'modelo-modelo': '',
            'modelo-origen_datos_tecnicos': 'medido', **datos_referencia('modelo', referencia_modelo='Producto nuevo')}
        respuesta = self.client.post(self.url(), datos, HTTP_X_REQUESTED_WITH='fetch')
        self.assertEqual(respuesta.json(), {'ok': True})
        self.tipo.refresh_from_db()
        self.assertEqual(self.tipo.especificaciones, originales)
        self.assertEqual(self.tipo.imagen.name, 'unidad/foto-propia.jpg')
        self.assertTrue(self.tipo.imagen_publica_url.endswith('/unidad/foto-propia.jpg'))

    def test_registro_software_y_material_comparten_edicion_con_actor_y_sin_cambiar_stock(self):
        for clave, objeto in (('software', self.programa), ('insumo', self.material)):
            with self.subTest(clave=clave):
                url = reverse('editar_registro', args=[self.unidad.slug, clave, objeto.pk])
                self.assertContains(self.client.get(url, {'fragmento': '1'}), 'name="registro-referencia_modelo"')
                datos = {'registro-nombre': objeto.nombre, **datos_referencia(referencia_modelo='Otro producto')}
                if clave == 'software':
                    datos.update({f'registro-{campo}': getattr(objeto, campo) for campo in
                        ('tipo_recurso', 'tipo_acceso', 'uso_en_equipo', 'licencias_totales', 'licencias_disponibles')})
                else:
                    datos.update({'registro-codigo': objeto.codigo, 'registro-marca': objeto.marca,
                        'registro-clasificacion': objeto.clasificacion, 'registro-cantidad_por_presentacion': '1',
                        'registro-unidad_medida': objeto.unidad_medida or ''})
                datos['registro-activo'] = 'on'
                respuesta = self.client.post(url, datos, HTTP_X_REQUESTED_WITH='fetch')
                self.assertEqual(respuesta.json(), {'ok': True})
                objeto.refresh_from_db()
                self.assertEqual(objeto.medios_referencia['identidad_propuesta']['modelo'], 'Otro producto')
                auditoria = RegistroAuditoriaUnidad.objects.get(entidad=objeto._meta.label, objeto_id=str(objeto.pk))
                self.assertEqual(auditoria.usuario_id, self.gestor.pk)
        self.assertEqual((self.programa.licencias_totales, self.programa.licencias_disponibles), (3, 2))
        self.assertEqual((self.material.stock_total, self.material.marca), (Decimal('7.50'), 'Marca física'))

    def test_gestor_parcial_de_modelo_compartido_no_cambia_su_referencia(self):
        otra = Unidad.objects.create(nombre='Otra unidad con el mismo modelo', slug='otra-unidad-ref-comercial',
            dependencia='laboratorios', descripcion='.', fecha_inicio=date(2026, 1, 1))
        UnidadEquipo.objects.create(codigo_unidad='REF-COM-OTRA', laboratorio=otra, equipo=self.tipo)
        self.assertNotContains(self.client.get(self.url(), {'seccion': 'modelo'}), 'name="modelo-referencia_modelo"')
        self.client.post(self.url(), {'seccion': 'modelo', 'unidad-estado_unidad': 'disponible',
            'unidad-criticidad': 'normal', **datos_referencia('modelo', referencia_modelo='No autorizado')})
        self.tipo.refresh_from_db()
        self.assertEqual(self.tipo.medios_referencia['identidad_propuesta']['modelo'], 'Modelo anterior')

    def test_adscripcion_secundaria_m2m_tambien_protege_el_modelo_compartido(self):
        otra = Unidad.objects.create(nombre='Unidad secundaria con acceso', slug='unidad-secundaria-ref-comercial',
            dependencia='laboratorios', descripcion='.', fecha_inicio=date(2026, 1, 1))
        self.activo.laboratorios.add(otra)
        self.assertNotContains(self.client.get(self.url(), {'seccion': 'modelo'}), 'name="modelo-referencia_modelo"')
        respuesta = self.client.post(self.url(), {'seccion': 'modelo', 'unidad-estado_unidad': 'disponible',
            'unidad-criticidad': 'normal', **datos_referencia('modelo', referencia_modelo='No autorizado')},
            HTTP_X_REQUESTED_WITH='fetch')
        self.assertEqual(respuesta.json(), {'ok': True})
        self.tipo.refresh_from_db()
        self.assertEqual(self.tipo.medios_referencia['identidad_propuesta']['modelo'], 'Modelo anterior')
