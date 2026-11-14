"""Las subcarpetas automáticas del menú (cada área en las fichas de equipo, el escáner…) y cada elemento se
renombran, ordenan u ocultan desde «Contenidos de la ficha», sin tocar el área ni el equipo de origen."""
from datetime import date

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from apps.formacion.presentation.aula import contexto_aula
from apps.gestion_unidades.models.secciones import AjusteSeccionPlanta
from apps.recursos.models.recursos import CarpetaRecurso, ModuloUnidad, Recurso
from apps.recursos.models.equipos import EquiposServicios
from apps.gestion_unidades.models.espacios import EspacioReservable
from apps.directorio_unidades.models.core import Unidad
from apps.recursos.models.unidades import UnidadEquipo


class SubcarpetasAutomaticasTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.admin = get_user_model().objects.create_superuser('subcarpetas.admin', 's@example.org', 'clave')
        cls.lab = Unidad.objects.create(nombre='Laboratorio con subcarpetas', slug='lab-subcarpetas',
                                        dependencia='laboratorios', fecha_inicio=date(2026, 1, 1))
        cls.url = reverse('admin:directorio_unidades_unidad_contenidos', args=[cls.lab.pk])
        rv = EspacioReservable.objects.create(unidad=cls.lab, codigo='SUB-AREA-RV', nombre='Realidad virtual', capacidad=4, orden=1)
        meta = EspacioReservable.objects.create(unidad=cls.lab, codigo='SUB-AREA-META', nombre='Metaverso', capacidad=4, orden=2)
        cls.visor = UnidadEquipo.objects.create(
            codigo_unidad='SUB-VR-01-01', laboratorio=cls.lab,
            equipo=EquiposServicios.objects.create(codigo='SUB-VR-01', nombre='Visor de prueba'))
        cls.torre = UnidadEquipo.objects.create(
            codigo_unidad='SUB-PC-01-01', laboratorio=cls.lab,
            equipo=EquiposServicios.objects.create(codigo='SUB-PC-01', nombre='Torre de simulación'))
        rv.equipos_asociados.add(cls.visor)
        meta.equipos_asociados.add(cls.torre)

    def setUp(self):
        self.client.force_login(self.admin)

    def actuar(self, accion, **datos):
        return self.client.post(self.url, {'accion': accion, 'numero': '2.2', **datos}, follow=True)

    def fichas(self):
        """La carpeta «Equipos y fichas técnicas» tal como la recibe la ficha pública."""
        modulos = ModuloUnidad.objects.filter(unidad=self.lab, activo=True)
        return next(c for c in contexto_aula(self.lab, modulos)['aula']['carpetas'] if c['numero'] == '2.2')

    def test_el_organizador_muestra_las_subcarpetas_y_sus_elementos(self):
        pagina = self.client.get(self.url)
        self.assertContains(pagina, 'Subcarpetas automáticas')
        for texto in ('Escáner de equipos', 'Realidad virtual', 'Metaverso', 'Visor de prueba', 'Torre de simulación',
                      'name="grupo" value="area-sub-area-rv"', f'name="elemento" value="ficha-equipo-{self.torre.pk}"',
                      reverse('ficha_equipo_publica', args=[self.lab.slug, self.visor.codigo_unidad])):
            self.assertContains(pagina, texto)

    def test_se_renombran_ordenan_y_ocultan_y_la_ficha_lo_respeta(self):
        self.assertContains(self.actuar('renombrar_grupo', grupo='area-sub-area-rv', comun='Realidad virtual',
                                        nombre='Estaciones con visores'), 'ahora se llama «Estaciones con visores»')
        self.actuar('ordenar_grupo', grupo='area-sub-area-meta', direccion='subir',
                    orden='escaner,area-sub-area-rv,area-sub-area-meta')
        self.assertEqual([g['nombre'] for g in self.fichas()['grupos']],
                         ['Escáner de equipos', 'Metaverso', 'Estaciones con visores'])
        self.assertIn('Estaciones con visores', self.client.get(self.lab.get_absolute_url()).content.decode())
        # El escáner sale del menú; los dos equipos siguen contando.
        self.actuar('alternar_grupo', grupo='escaner')
        self.assertNotIn('data-id="escaner-equipos"', self.client.get(self.lab.get_absolute_url()).content.decode())
        self.assertEqual(self.fichas()['total'], 2)
        # Un equipo oculto deja su subcarpeta vacía, que desaparece; el equipo se conserva.
        self.assertContains(self.actuar('alternar_elemento', elemento=f'ficha-equipo-{self.torre.pk}',
                                        nombre='Torre de simulación'), 'el registro se conserva')
        self.assertEqual([g['nombre'] for g in self.fichas()['grupos']], ['Estaciones con visores'])
        self.assertNotIn(f'data-id="ficha-equipo-{self.torre.pk}"', self.client.get(self.lab.get_absolute_url()).content.decode())
        self.assertTrue(UnidadEquipo.objects.filter(pk=self.torre.pk, activa=True).exists())
        # En el organizador lo oculto sigue a la vista, marcado, para volver a mostrarlo.
        organizador = self.client.get(self.url).content.decode()
        nodo = organizador[organizador.index(f'value="ficha-equipo-{self.torre.pk}"') - 1500:
                           organizador.index(f'value="ficha-equipo-{self.torre.pk}"') + 900]
        self.assertIn('is-elemento is-oculta', nodo)
        self.assertIn('aria-checked="false"', nodo)
        self.assertIn('value="restablecer_seccion"', organizador)
        # Ocultar todo deja la sección pendiente; restablecer devuelve lo común.
        self.actuar('alternar_elemento', elemento=f'ficha-equipo-{self.visor.pk}', nombre='Visor de prueba')
        self.assertTrue(self.fichas()['pendiente'])
        self.actuar('restablecer_seccion')
        self.assertFalse(AjusteSeccionPlanta.objects.filter(unidad=self.lab, numero='2.2').exists())
        self.assertEqual([g['nombre'] for g in self.fichas()['grupos']],
                         ['Escáner de equipos', 'Realidad virtual', 'Metaverso'])

    def test_volver_al_nombre_comun_no_deja_ajustes_vacios_y_lo_invalido_se_rechaza(self):
        self.actuar('alternar_grupo', grupo='area-sub-area-rv')
        self.actuar('alternar_grupo', grupo='area-sub-area-rv')
        self.actuar('renombrar_grupo', grupo='area-sub-area-rv', comun='Realidad virtual', nombre='Otra')
        self.actuar('renombrar_grupo', grupo='area-sub-area-rv', comun='Realidad virtual', nombre='')
        self.assertFalse(AjusteSeccionPlanta.objects.filter(unidad=self.lab).exists())
        self.assertContains(self.actuar('alternar_grupo', grupo='<script>'), 'Ese elemento no existe en esta sección.')
        self.assertContains(self.actuar('alternar_grupo', grupo='escaner', numero='9.9'), 'Esa sección no existe')
        self.assertContains(self.actuar('ordenar_grupo', grupo='escaner', direccion='subir', orden='escaner,sin-area'),
                            'ya está primera')


class ArbolDeCarpetasYArchivosTests(TestCase):
    """Carpetas y archivos se renombran en su fila y se muestran u ocultan con un interruptor."""

    @classmethod
    def setUpTestData(cls):
        cls.admin = get_user_model().objects.create_superuser('arbol.admin', 'a@example.org', 'clave')
        cls.lab = Unidad.objects.create(nombre='Laboratorio en árbol', slug='lab-arbol', dependencia='laboratorios',
                                        fecha_inicio=date(2026, 1, 1))
        cls.url = reverse('admin:directorio_unidades_unidad_contenidos', args=[cls.lab.pk])

    def setUp(self):
        self.client.force_login(self.admin)

    def actuar(self, accion, **datos):
        return self.client.post(self.url, {'accion': accion, **datos}, follow=True)

    def test_carpetas_y_archivos_se_editan_en_su_fila(self):
        self.actuar('crear_carpeta', destino='s:2.4', nombre='Inventario', visibilidad='restringida')
        carpeta = CarpetaRecurso.objects.get(unidad=self.lab, nombre='Inventario')
        archivo = Recurso.objects.create(unidad=self.lab, carpeta=carpeta, nombre='Inventario Laboratorio',
                                         url='https://www.upec.edu.ec/', seguridad_verificada=True)
        pagina = self.client.get(self.url).content.decode()
        for marca in ('data-arbol-nombre', 'role="switch"', 'value="renombrar_archivo"', 'value="alternar_archivo"',
                      'admin/js/contenidos_ficha.js'):
            self.assertIn(marca, pagina)
        # Renombrar en la fila conserva quién ve la carpeta.
        self.actuar('editar_carpeta', carpeta=carpeta.pk, nombre='Inventario 2026')
        carpeta.refresh_from_db()
        self.assertEqual((carpeta.nombre, carpeta.visibilidad), ('Inventario 2026', 'restringida'))
        self.assertContains(self.actuar('renombrar_archivo', recurso=archivo.pk, nombre='Inventario general'),
                            'ahora se llama «Inventario general»')
        self.assertContains(self.actuar('alternar_archivo', recurso=archivo.pk), 'queda oculto; nada se borra')
        archivo.refresh_from_db()
        self.assertEqual((archivo.nombre, archivo.activo), ('Inventario general', False))
        self.assertContains(self.actuar('renombrar_archivo', recurso=archivo.pk, nombre='  '), 'Escriba un nombre.')
        otra = Unidad.objects.create(nombre='Otra unidad', slug='otra-arbol', dependencia='laboratorios',
                                     fecha_inicio=date(2026, 1, 1))
        ajeno = Recurso.objects.create(unidad=otra, nombre='Ajeno', url='https://www.upec.edu.ec/')
        self.assertEqual(self.client.post(self.url, {'accion': 'alternar_archivo', 'recurso': ajeno.pk}).status_code, 404)

    def test_la_carpeta_de_una_pestana_propia_se_ve_en_la_ficha(self):
        self.actuar('nueva_pestana', nombre='Semilleros')
        propia = ModuloUnidad.objects.get(unidad=self.lab, nombre='Semilleros')
        self.actuar('crear_carpeta', destino=f'm:{propia.pk}', nombre='Proyectos 2026')
        carpeta = CarpetaRecurso.objects.get(unidad=self.lab, nombre='Proyectos 2026')
        Recurso.objects.create(unidad=self.lab, carpeta=carpeta, nombre='Bases del concurso',
                               url='https://www.upec.edu.ec/', seguridad_verificada=True)
        ficha = self.client.get(self.lab.get_absolute_url()).content.decode()
        self.assertIn(f'data-modulo="{propia.clave}"', ficha)
        self.assertIn(f'data-target="#carpetaContenido{carpeta.pk}"', ficha)
        organizador = self.client.get(self.url)
        self.assertContains(organizador, 'Pestaña 7 · propia')
        self.assertContains(organizador, 'Proyectos 2026')


class AccesoEnBloqueTests(TestCase):
    """Publicar una carpeta con todos sus archivos, y su revisión de seguridad, sin abrir el editor de la unidad."""

    @classmethod
    def setUpTestData(cls):
        cls.admin = get_user_model().objects.create_superuser('acceso.admin', 'b@example.org', 'clave')
        cls.lab = Unidad.objects.create(nombre='Laboratorio con recursos', slug='lab-acceso-bloque',
                                        dependencia='laboratorios', fecha_inicio=date(2026, 1, 1))
        cls.url = reverse('admin:directorio_unidades_unidad_contenidos', args=[cls.lab.pk])

    def setUp(self):
        self.client.force_login(self.admin)
        self.client.post(self.url, {'accion': 'crear_carpeta', 'destino': 's:4.4', 'nombre': 'Recursos en línea',
                                    'visibilidad': 'interna'})
        self.carpeta = CarpetaRecurso.objects.get(unidad=self.lab, nombre='Recursos en línea')
        self.enlaces = [Recurso.objects.create(unidad=self.lab, carpeta=self.carpeta, nombre=nombre, visibilidad='interna',
                                               url='https://www.tinkercad.com/') for nombre in ('Tinkercad', 'Wokwi')]

    def test_la_carpeta_y_sus_archivos_se_publican_juntos(self):
        respuesta = self.client.post(self.url, {'accion': 'acceso_de_carpeta', 'carpeta': self.carpeta.pk,
                                                'visibilidad': 'publica', 'con_archivos': '1',
                                                'seguridad_verificada': '1'}, follow=True)
        self.assertContains(respuesta, 'y sus 2 archivos: ahora los ve pública')
        self.carpeta.refresh_from_db()
        self.assertEqual(self.carpeta.visibilidad, 'publica')
        self.assertEqual(set(Recurso.objects.filter(carpeta=self.carpeta).values_list('visibilidad', 'seguridad_verificada')),
                         {('publica', True)})

    def test_un_archivo_cambia_solo_y_sin_confirmar_no_queda_verificado(self):
        self.client.post(self.url, {'accion': 'editar_archivo', 'recurso': self.enlaces[0].pk, 'visibilidad': 'restringida'})
        self.enlaces[0].refresh_from_db()
        self.enlaces[1].refresh_from_db()
        self.assertEqual((self.enlaces[0].visibilidad, self.enlaces[0].seguridad_verificada), ('restringida', False))
        self.assertEqual(self.enlaces[1].visibilidad, 'interna')
        self.assertContains(self.client.get(self.url), 'value="acceso_de_carpeta"')
