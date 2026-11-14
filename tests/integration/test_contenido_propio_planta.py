from datetime import date

from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from django.urls import reverse

from apps.recursos.models.recursos import CarpetaRecurso, ModuloUnidad, Recurso
from apps.directorio_unidades.models.core import Unidad
from tests.integration.test_reserva_por_proceso import BasePracticaPorProceso


class ContenidoPropioDeLaPlantaTests(BasePracticaPorProceso):
    """La ficha de la planta se arma con sus datos; el admin lleva a editarlos."""

    def pestana(self, html, clave):
        desde = html.rindex(f'data-modulo="{clave}"')
        hasta = html.find('class="modulo-carpeta-list', desde)
        return html[desde:hasta if hasta > 0 else None]

    def test_calidad_en_sus_secciones_numeradas(self):
        # El mapa completo, con las secciones pendientes, lo ve quien gestiona la planta.
        self.client.force_login(get_user_model().objects.create_superuser('gestor.mapa', 'g@example.org', 'clave'))
        html = self.client.get(self.unidad.get_absolute_url()).content.decode()
        calidad = self.pestana(html, 'calidad-inocuidad')
        posiciones = [calidad.index(f'data-seccion="5.{numero}"') for numero in range(1, 6)]
        self.assertEqual(posiciones, sorted(posiciones))
        self.assertIn('protocolos-control-', calidad)
        self.assertIn('plan-haccp-', calidad)
        self.assertIn('calidad-lotes-', calidad)
        self.assertNotIn('protocolos-control-', self.pestana(html, 'procesos-protocolos'))

    def test_el_publico_no_ve_secciones_vacias_y_2_1_solo_lleva_procesos(self):
        html = self.client.get(self.unidad.get_absolute_url()).content.decode()
        self.assertNotIn('Contenido pendiente de publicación por la unidad.', html)
        self.assertNotIn('Ficha del producto · proceso por configurar', html)
        procesos = self.pestana(html, 'procesos-protocolos')
        self.assertNotIn('data-id="ficha-producto-', procesos)
        # Cada producto, con o sin proceso, tiene su ficha técnica en 4.2 y su empaque en 4.3.
        produccion = self.pestana(html, 'produccion-lotes')
        self.assertIn('data-seccion="4.2"', produccion)
        self.assertIn('data-id="ficha-producto-', produccion)
        self.assertIn('data-id="empaque-presentacion"', produccion)

    def test_con_calidad_desactivada_no_se_muda_a_otra_pestana(self):
        ModuloUnidad.objects.filter(unidad=self.unidad, clave='calidad-inocuidad').update(activo=False)
        html = self.client.get(self.unidad.get_absolute_url()).content.decode()
        self.assertNotIn('protocolos-control-', html)
        self.assertNotIn('plan-haccp-', html)

    def test_una_carpeta_con_seccion_se_muestra_una_sola_vez(self):
        procesos = ModuloUnidad.objects.get(unidad=self.unidad, clave='procesos-protocolos')
        carpeta = CarpetaRecurso.objects.create(unidad=self.unidad, nombre='Manuales de la línea',
                                                modulo_config=procesos, seccion_planta='2.5', visibilidad='publica')
        recurso = Recurso.objects.create(unidad=self.unidad, carpeta=carpeta, nombre='Manual de pasteurización',
                                         descripcion='Manual', seguridad_verificada=True,
                                         archivo=SimpleUploadedFile('manual.html', b'<html>M</html>'))
        recurso.archivo.close()
        html = self.client.get(self.unidad.get_absolute_url()).content.decode()
        self.assertEqual(html.count(f'data-target="#carpetaContenido{carpeta.pk}"'), 1)

    def test_el_admin_de_la_planta_lleva_a_editar_su_contenido(self):
        admin = get_user_model().objects.create_superuser('contenido.admin', 'c@example.org', 'clave')
        self.client.force_login(admin)
        ficha = self.client.get(reverse('admin:plantas_piloto_plantapiloto_change', args=[self.unidad.pk]))
        self.assertContains(ficha, 'Contenido propio de la planta')
        for modelo, filtro in (('familiaproducto', 'unidad'), ('receta', 'unidad'), ('plancalidad', 'unidad'),
                               ('guiaactividadreserva', 'actividad__unidad'), ('unidadequipo', 'laboratorio')):
            enlace = reverse(f'admin:plantas_piloto_{modelo}_changelist') + f'?{filtro}__id__exact={self.unidad.pk}'
            self.assertContains(ficha, enlace)
            self.assertEqual(self.client.get(enlace).status_code, 200, modelo)
        self.assertContains(ficha, reverse('admin:plantas_piloto_plancalidad_add') + f'?unidad={self.unidad.pk}')
        laboratorio = Unidad.objects.create(nombre='Laboratorio sin planta', slug='lab-sin-planta',
                                            dependencia='laboratorios', fecha_inicio=date(2026, 1, 1))
        editor = self.client.get(reverse('admin:directorio_unidades_unidad_change', args=[laboratorio.pk]))
        self.assertNotContains(editor, 'Contenido propio de la planta')
        self.assertContains(editor, 'Contenido propio del laboratorio')

    def test_sin_permisos_no_ofrece_pantallas_ajenas(self):
        from apps.directorio_unidades.admin.unidades import UnidadAdmin, _PETICION_UNIDAD
        from django.contrib import admin
        from django.test import RequestFactory
        peticion = RequestFactory().get('/admin/')
        peticion.user = get_user_model().objects.create_user('sin.permisos', password='clave', is_staff=True)
        marca = _PETICION_UNIDAD.set(peticion)
        try:
            self.assertEqual(UnidadAdmin(Unidad, admin.site).contenido_propio(self.unidad),
                             'Su cuenta no tiene acceso a estas pantallas.')
        finally:
            _PETICION_UNIDAD.reset(marca)


class TableroDeLaPlantaTests(BasePracticaPorProceso):
    """Se entra por planta: su tablero reúne lo suyo en el orden de su ficha pública."""

    def setUp(self):
        super().setUp()
        self.admin = get_user_model().objects.create_superuser('tablero.admin', 't@example.org', 'clave')
        self.client.force_login(self.admin)
        self.url = reverse('admin:plantas_piloto_plantapiloto_tablero', args=[self.unidad.pk])

    def test_el_tablero_ordena_por_la_ficha_y_filtra_por_la_planta(self):
        from apps.gestion_unidades.admin.tablero_unidad import DESCRIPCIONES
        from apps.plantas_piloto.operacion.models.produccion import Receta
        tablero = self.client.get(self.url)
        self.assertEqual(tablero.status_code, 200)
        html = tablero.content.decode()
        orden = [html.index(t) for t in ('Información general', 'Procesos y protocolos', 'Equipos e infraestructura',
                                         'Producción y lotes', 'Calidad e inocuidad', 'Reservas y servicios',
                                         'Operación de la unidad')]
        self.assertEqual(orden, sorted(orden))
        self.assertContains(tablero, DESCRIPCIONES['Receta'])
        lista = reverse('admin:plantas_piloto_receta_changelist') + f'?unidad__id__exact={self.unidad.pk}'
        self.assertContains(tablero, lista)
        fila = [f for g in tablero.context['ficha'] for f in g['filas'] if f['lista'] == lista][0]
        self.assertEqual(fila['total'], Receta.objects.filter(unidad=self.unidad).count())
        # Cada herramienta de la planta aparece una sola vez entre las dos partes.
        listas = [f['lista'] for parte in ('ficha', 'operacion') for g in tablero.context[parte] for f in g['filas']]
        self.assertEqual(len(listas), len(set(listas)))

    def test_avisa_pestanas_desactivadas_y_secciones_sin_contenido(self):
        ModuloUnidad.objects.filter(unidad=self.unidad, clave='calidad-inocuidad').update(activo=False)
        tablero = self.client.get(self.url, {'revisar_ficha': '1'})
        self.assertContains(tablero, 'Pestañas desactivadas:')
        self.assertIn('Calidad e inocuidad', tablero.context['estado']['desactivados'])
        self.assertContains(tablero, '4.6 Desarrollo de producto')

    def test_el_area_entra_por_planta_y_describe_cada_herramienta(self):
        from apps.gestion_unidades.admin.tablero_unidad import DESCRIPCIONES
        area = self.client.get(reverse('admin:index'))
        self.assertContains(area, 'class="citt-admin-unidad"')
        self.assertContains(area, self.url)
        # Del área solo queda lo de todas las plantas; cada herramienta vive en el tablero de su planta.
        self.assertContains(area, 'Lista completa')
        self.assertContains(area, reverse('admin:plantas_piloto_plantapiloto_changelist'))
        self.assertNotContains(area, 'Vista general: todas las plantas juntas')
        self.assertNotContains(area, reverse('admin:plantas_piloto_plancalidad_changelist'))
        self.assertContains(self.client.get(self.url), DESCRIPCIONES['PlanCalidad'])

    def test_sin_permiso_no_abre_el_tablero(self):
        personal = get_user_model().objects.create_user('personal.planta', password='clave', is_staff=True)
        self.client.force_login(personal)
        # Fuera de su alcance la planta no existe para la cuenta: ni siquiera se revela.
        self.assertEqual(self.client.get(self.url).status_code, 404)
