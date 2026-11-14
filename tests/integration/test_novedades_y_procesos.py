"""Fase 3: novedades de cada unidad y procesos y productos de los laboratorios.

Las novedades llegan a la sección 1.6 de la ficha, a su página propia, a la nota completa
dentro del portal y a «Noticias»; un borrador solo lo ve quien gestiona la unidad. Los
procesos de un laboratorio usan las tablas de producción y se muestran sin lotes en 3.1,
3.2 y 3.3; las plantas siguen con sus propias secciones.
"""
from datetime import date, timedelta

from django.apps import apps
from django.contrib import admin
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.test import TestCase, override_settings
from django.urls import reverse
from django.utils import timezone

from apps.portal.presentation.views import proveedor_novedades
from apps.gestion_unidades.admin.configuracion import NovedadUnidadInline
from apps.directorio_unidades.admin.unidades import UnidadAdmin
from apps.gestion_unidades.presentation.novedades import novedades_del_portal, publicadas
from apps.recursos.models.consumibles import Consumible
from apps.gestion_unidades.models.espacios import EspacioReservable
from apps.plantas_piloto.operacion.models.produccion import EtapaReceta, InsumoReceta, Producto, Receta
from apps.gestion_unidades.models.novedades import NovedadUnidad
from apps.recursos.models.software import SoftwareDisponible
from apps.directorio_unidades.models.core import Unidad


def unidad(nombre, dependencia='laboratorios', **datos):
    return Unidad.objects.create(nombre=nombre, descripcion='.', fecha_inicio=date(2026, 1, 1),
                                 slug=nombre.lower().replace(' ', '-'), dependencia=dependencia, **datos)


class NovedadesTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.laboratorio = unidad('Laboratorio con novedades')
        cls.gestor = get_user_model().objects.create_user('gestor.novedades', 'g@example.org', 'clave')
        cls.laboratorio.administrador = cls.gestor
        cls.laboratorio.save(update_fields=['administrador'])
        hoy = timezone.localdate()
        cls.noticia = cls.novedad('Inauguramos el área de impresión 3D', destacada=True)
        cls.borrador = cls.novedad('Nota en preparación', publicada=False)
        cls.futura = cls.novedad('Se publica la próxima semana', fecha_publicacion=hoy + timedelta(days=7))
        cls.evento = cls.novedad('Taller abierto de fabricación', categoria='evento',
                                 fecha_evento=timezone.now() + timedelta(days=3), lugar='Bloque B')
        cls.pasado = cls.novedad('Feria del año pasado', categoria='evento',
                                 fecha_evento=timezone.now() - timedelta(days=30))
        cls.convocatoria = cls.novedad('Retos de prototipado', categoria='convocatoria', cierre=hoy + timedelta(days=10))
        inactiva = unidad('Unidad retirada', activo=False)
        NovedadUnidad.objects.create(unidad=inactiva, titulo='De una unidad inactiva', resumen='.', publicada=True)

    @classmethod
    def novedad(cls, titulo, **datos):
        return NovedadUnidad.objects.create(unidad=cls.laboratorio, titulo=titulo, resumen=f'Resumen de {titulo}.',
                                            publicada=datos.pop('publicada', True), **datos)

    def test_solo_se_publica_lo_publicado_vigente_y_de_unidades_activas(self):
        titulos = set(publicadas().values_list('titulo', flat=True))
        self.assertIn('Inauguramos el área de impresión 3D', titulos)
        for oculto in ('Nota en preparación', 'Se publica la próxima semana', 'De una unidad inactiva'):
            self.assertNotIn(oculto, titulos)

    def test_un_evento_necesita_fecha_y_una_convocatoria_su_cierre(self):
        with self.assertRaises(ValidationError):
            NovedadUnidad(unidad=self.laboratorio, titulo='x', resumen='x', categoria='evento').clean()
        with self.assertRaises(ValidationError):
            NovedadUnidad(unidad=self.laboratorio, titulo='x', resumen='x', categoria='convocatoria').clean()

    def test_la_ficha_ofrece_la_seccion_1_6_y_su_pagina(self):
        ficha = self.client.get(self.laboratorio.get_absolute_url())
        url = reverse('novedades_unidad', args=[self.laboratorio.slug])
        self.assertContains(ficha, url)
        self.assertContains(ficha, 'Novedades y avisos (4)')
        pagina = self.client.get(url)
        self.assertContains(pagina, 'Inauguramos el área de impresión 3D')
        self.assertNotContains(pagina, 'Nota en preparación')
        # Quien gestiona la unidad ve también su borrador, marcado.
        self.client.force_login(self.gestor)
        pagina = self.client.get(url)
        self.assertContains(pagina, 'Nota en preparación')
        self.assertContains(pagina, 'Borrador')

    def test_la_nota_completa_vive_en_el_portal_y_el_borrador_no_es_publico(self):
        respuesta = self.client.get(self.noticia.get_absolute_url())
        self.assertContains(respuesta, 'Inauguramos el área de impresión 3D')
        self.assertContains(respuesta, self.laboratorio.get_absolute_url())
        self.assertEqual(self.client.get(self.borrador.get_absolute_url()).status_code, 404)
        self.client.force_login(self.gestor)
        self.assertContains(self.client.get(self.borrador.get_absolute_url()), 'Borrador')

    def test_noticias_publica_portada_agenda_y_convocatorias_abiertas(self):
        contenido = novedades_del_portal()
        self.assertEqual(contenido['destacadas'][0], self.noticia)
        self.assertEqual(contenido['agenda'], [self.evento])
        self.assertEqual(contenido['convocatorias'], [self.convocatoria])
        pagina = self.client.get(reverse('noticias'))
        for visible in ('Inauguramos el área de impresión 3D', 'Taller abierto de fabricación', 'Retos de prototipado',
                        self.noticia.get_absolute_url()):
            self.assertContains(pagina, visible)
        self.assertNotContains(pagina, 'Innovación para una agricultura más sostenible')

    @override_settings(PORTAL_NEWS_PROVIDER='')
    def test_sin_proveedor_noticias_conserva_su_contenido_institucional(self):
        pagina = self.client.get(reverse('noticias'))
        self.assertContains(pagina, 'Innovación para una agricultura más sostenible')
        self.assertNotContains(pagina, 'Inauguramos el área de impresión 3D')

    @override_settings(PORTAL_NEWS_PROVIDER='os.system')
    def test_el_portal_solo_acepta_el_proveedor_registrado(self):
        with self.assertRaises(ValueError):
            proveedor_novedades()

    def test_una_unidad_sin_mapa_numerado_tambien_las_muestra(self):
        centro = unidad('Centro con novedades', dependencia='centro_experimental')
        NovedadUnidad.objects.create(unidad=centro, titulo='Cosecha abierta', resumen='.', publicada=True)
        self.assertContains(self.client.get(centro.get_absolute_url()), reverse('novedades_unidad', args=[centro.slug]))

    def test_las_novedades_se_editan_en_la_ficha_de_la_unidad(self):
        self.assertIn(NovedadUnidadInline, UnidadAdmin.inlines)
        self.client.force_login(self.gestor)
        editor = self.client.get(reverse('admin:directorio_unidades_unidad_change', args=[self.laboratorio.pk]))
        self.assertContains(editor, 'Novedades: noticias, logros, eventos y convocatorias')


class ProcesosDeLaboratorioTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.laboratorio = unidad('Laboratorio con procesos')
        cls.area = EspacioReservable.objects.create(unidad=cls.laboratorio, codigo='LP-IMP', nombre='Impresión 3D',
                                                    capacidad=4)
        cls.pieza = Producto.objects.create(unidad=cls.laboratorio, codigo='LP-PIEZA', nombre='Pieza impresa',
                                            unidad_medida='pieza', descripcion='Prototipo funcional en PLA.')
        cls.privado = Producto.objects.create(unidad=cls.laboratorio, codigo='LP-INT', nombre='Producto interno',
                                              unidad_medida='pieza', publico=False)
        cls.proceso = Receta.objects.create(unidad=cls.laboratorio, producto=cls.pieza, codigo='LP-FDM',
                                            nombre='Impresión FDM de una pieza', cantidad_base=1, unidad_base='pieza',
                                            rendimiento_esperado=1)
        laminar = EtapaReceta.objects.create(receta=cls.proceso, orden=1, nombre='Laminar el modelo',
                                             espacio=cls.area, duracion_min=20,
                                             instrucciones='Elegir altura de capa y relleno según el uso.')
        EtapaReceta.objects.create(receta=cls.proceso, orden=2, nombre='Imprimir', espacio=cls.area, duracion_min=120,
                                   punto_control=True, parametro='Temperatura de boquilla', limite='200 a 215 °C')
        filamento = Consumible.objects.create(codigo='LP-PLA', nombre='Filamento PLA', unidad=cls.laboratorio)
        InsumoReceta.objects.create(receta=cls.proceso, consumible=filamento, etapa=laminar, cantidad=35)
        cls.proceso.software.add(SoftwareDisponible.objects.create(unidad=cls.laboratorio, nombre='PrusaSlicer'))
        cls.inactivo = Receta.objects.create(unidad=cls.laboratorio, producto=cls.pieza, codigo='LP-OLD',
                                             nombre='Proceso retirado', cantidad_base=1, unidad_base='pieza',
                                             rendimiento_esperado=1, activa=False)
        EtapaReceta.objects.create(receta=cls.inactivo, orden=1, nombre='Paso viejo')

    def test_la_ficha_ofrece_procesos_metodos_y_productos(self):
        ficha = self.client.get(self.laboratorio.get_absolute_url())
        url = reverse('proceso_laboratorio', args=[self.laboratorio.slug, self.proceso.pk])
        self.assertContains(ficha, url)
        self.assertContains(ficha, '2 etapas · 2 h 20 min')
        self.assertContains(ficha, 'Métodos y parámetros (1)')
        self.assertContains(ficha, 'Productos y servicios (1)')
        self.assertNotContains(ficha, 'Proceso retirado')
        self.assertIn('procesos-productos', [modulo.clave for modulo in ficha.context['modulos']])

    def test_el_proceso_se_lee_paso_a_paso(self):
        pagina = self.client.get(reverse('proceso_laboratorio', args=[self.laboratorio.slug, self.proceso.pk]))
        for visible in ('Laminar el modelo', 'Temperatura de boquilla', '200 a 215 °C', 'Filamento PLA', 'PrusaSlicer',
                        'Pieza impresa', reverse('area_unidad', args=[self.laboratorio.slug, 'LP-IMP'])):
            self.assertContains(pagina, visible)
        self.assertNotContains(pagina, '<table')
        self.assertEqual(self.client.get(
            reverse('proceso_laboratorio', args=[self.laboratorio.slug, self.inactivo.pk])).status_code, 404)
        otro = unidad('Otro laboratorio de procesos')
        self.assertEqual(self.client.get(reverse('proceso_laboratorio', args=[otro.slug, self.proceso.pk])).status_code,
                         404)

    def test_metodos_y_productos(self):
        metodos = self.client.get(reverse('metodos_laboratorio', args=[self.laboratorio.slug]))
        self.assertContains(metodos, 'Elegir altura de capa y relleno según el uso.')
        productos = self.client.get(reverse('productos_laboratorio', args=[self.laboratorio.slug]))
        self.assertContains(productos, 'Prototipo funcional en PLA.')
        self.assertNotContains(productos, 'Producto interno')

    def test_el_laboratorio_edita_sus_procesos_en_su_seccion(self):
        for nombre in ('Receta', 'Producto'):
            self.assertIn(apps.get_model('laboratorios', nombre), admin.site._registry)
        # Su administrador ve solo los procesos de su laboratorio y puede crear otros.
        administrador = get_user_model().objects.create_user('admin.procesos', 'a@example.org', 'clave')
        self.laboratorio.administrador = administrador
        self.laboratorio.save(update_fields=['administrador'])
        ajeno = unidad('Laboratorio ajeno de procesos')
        Receta.objects.create(unidad=ajeno, producto=Producto.objects.create(
            unidad=ajeno, codigo='AJ', nombre='Ajeno', unidad_medida='pieza'), codigo='AJ-R', nombre='Proceso ajeno',
            cantidad_base=1, unidad_base='pieza', rendimiento_esperado=1)
        self.client.force_login(administrador)
        lista = self.client.get(reverse('admin:laboratorios_receta_changelist')
                                + f'?unidad__id__exact={self.laboratorio.pk}')
        self.assertEqual(lista.status_code, 200)
        self.assertContains(lista, 'Impresión FDM de una pieza')
        self.assertNotContains(lista, 'Proceso ajeno')
        ajena = self.client.get(reverse('admin:laboratorios_receta_changelist') + f'?unidad__id__exact={ajeno.pk}')
        self.assertNotContains(ajena, 'Proceso ajeno', status_code=ajena.status_code)
        self.assertEqual(self.client.get(reverse('admin:laboratorios_receta_add')).status_code, 200)

    def test_una_planta_conserva_sus_secciones_de_produccion(self):
        planta = unidad('Planta sin procesos de laboratorio', dependencia='plantas_piloto')
        Receta.objects.create(unidad=planta, producto=Producto.objects.create(
            unidad=planta, codigo='PL-1', nombre='Queso', unidad_medida='kg'), codigo='PL-R', nombre='Queso fresco',
            cantidad_base=10, unidad_base='kg', rendimiento_esperado=1)
        ficha = self.client.get(planta.get_absolute_url())
        self.assertNotContains(ficha, 'data-id="productos-laboratorio"')
        self.assertNotContains(ficha, 'data-id="metodos-laboratorio"')
