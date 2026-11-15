"""El equipamiento de las fichas de área es inventario real: con código, área, insumos y software.

Lo que describe la ficha de cada área queda registrado una sola vez y lo leen igual la página del
área, la ficha del equipo, el menú del visualizador, la página de insumos y el reporte de recursos.
"""
from datetime import date
from io import StringIO

from django.contrib.auth import get_user_model
from django.core.management import call_command
from django.test import RequestFactory, TestCase
from django.urls import reverse

from apps.gestion_unidades.presentation.gestion_reportes import build_unit_report
from apps.gestion_unidades.management.fichas_area import FICHAS
from apps.recursos.models.consumibles import Consumible
from apps.gestion_unidades.models.fichas_area import ElementoFichaArea, FichaArea
from apps.recursos.models.equipos import EquiposServicios
from apps.gestion_unidades.models.espacios import EspacioReservable
from apps.recursos.models.software import SoftwareDisponible
from apps.directorio_unidades.models.core import Unidad
from apps.recursos.models.unidades import UnidadEquipo
from apps.recursos.presentation.existencias import describe_propuesta

SLUG = 'laboratorio-realidad-extendida'
AREA = 'XR-AREA-RA'


class EquipamientoTrazableTests(TestCase):
    # La ficha pública consulta también las articulaciones de Centros I+D.
    databases = {'default', 'centros'}

    @classmethod
    def setUpTestData(cls):
        cls.laboratorio = Unidad.objects.create(nombre='Laboratorio de Realidad Extendida', descripcion='.', slug=SLUG,
                                                fecha_inicio=date(2026, 1, 1), dependencia='laboratorios')
        for codigo in ('XR-AREA-RV', AREA):
            EspacioReservable.objects.create(unidad=cls.laboratorio, codigo=codigo, nombre=codigo, capacidad=4)
        # Un equipo que la unidad ya tenía con el mismo nombre que uno de la ficha: no se duplica.
        cls.nombre_existente = FICHAS[SLUG][AREA]['equipos'][0]['nombre']
        tipo = EquiposServicios.objects.create(codigo='XR-EQ-PREVIO', nombre=cls.nombre_existente,
                                               marca='Demostración', modelo='Registro de prueba')
        cls.previo = UnidadEquipo.objects.create(codigo_unidad='XR-UNIT-PREVIO-01', equipo=tipo, laboratorio=cls.laboratorio,
                                                 ubicacion_especifica='Mesa 1 — dato de prueba')
        prueba = EquiposServicios.objects.create(codigo='TEST-EQUIPO-XR', nombre='Equipo de Prueba para Debug')
        cls.de_prueba = UnidadEquipo.objects.create(codigo_unidad='UNIT-TEST-XR-01', equipo=prueba, laboratorio=cls.laboratorio)
        call_command('cargar_fichas_area', '--unidad', SLUG, stdout=StringIO())
        call_command('sincronizar_equipamiento_areas', '--unidad', SLUG, stdout=StringIO())

    def test_cada_elemento_de_la_ficha_queda_registrado_en_su_area(self):
        espacio = EspacioReservable.objects.get(unidad=self.laboratorio, codigo=AREA)
        elementos = ElementoFichaArea.objects.filter(ficha__espacio=espacio)
        self.assertFalse(elementos.filter(tipo='insumo', insumo_registrado__isnull=True).exists())
        self.assertFalse(elementos.filter(tipo='software', software_registrado__isnull=True).exists())
        for elemento in elementos.filter(tipo='equipo').select_related('registrado__equipo'):
            with self.subTest(equipo=elemento.nombre):
                if describe_propuesta(elemento) and elemento.registrado_id != self.previo.pk:
                    # Lo que la ficha describe como alta capacidad no se convierte en inventario: es propuesta.
                    self.assertEqual((elemento.solo_referencia, elemento.registrado_id), (True, None))
                    continue
                self.assertTrue(elemento.registrado.espacios_asociados.filter(pk=espacio.pk).exists())
                self.assertTrue(elemento.registrado.equipo.icono)
                if elemento.registrado_id != self.previo.pk:
                    self.assertEqual(elemento.registrado.estado_unidad, 'disponible')
        self.assertTrue(Consumible.objects.filter(unidad=self.laboratorio, elementos_de_ficha__isnull=False).exists())
        self.assertTrue(SoftwareDisponible.objects.filter(unidad=self.laboratorio, elementos_de_ficha__isnull=False).exists())

    def test_lo_ya_registrado_se_reutiliza_y_los_rellenos_y_pruebas_desaparecen(self):
        self.previo.refresh_from_db()
        self.assertEqual(UnidadEquipo.objects.filter(laboratorio=self.laboratorio, equipo__nombre=self.nombre_existente,
                                                     activa=True).count(),
                         max(1, int(FICHAS[SLUG][AREA]['equipos'][0]['cantidad'].split()[0] or 1)))
        self.assertTrue(ElementoFichaArea.objects.filter(registrado=self.previo).exists())
        self.assertEqual((self.previo.equipo.marca, self.previo.equipo.modelo), ('', ''))
        self.assertNotIn('dato de prueba', self.previo.ubicacion_especifica)
        self.de_prueba.refresh_from_db()
        self.assertFalse(self.de_prueba.activa)

    def test_la_sincronizacion_es_idempotente_y_la_simulacion_no_guarda(self):
        antes = UnidadEquipo.objects.count(), Consumible.objects.count(), SoftwareDisponible.objects.count()
        salida = StringIO()
        call_command('sincronizar_equipamiento_areas', '--unidad', SLUG, stdout=salida)
        self.assertIn('ya sincronizada', salida.getvalue())
        self.assertEqual(antes, (UnidadEquipo.objects.count(), Consumible.objects.count(), SoftwareDisponible.objects.count()))
        ElementoFichaArea.objects.filter(tipo='equipo').update(registrado=None)
        call_command('sincronizar_equipamiento_areas', '--unidad', SLUG, '--simular', stdout=StringIO())
        self.assertFalse(ElementoFichaArea.objects.filter(tipo='equipo', registrado__isnull=False).exists())

    def test_la_ficha_del_equipo_muestra_unidades_area_insumos_y_software(self):
        elemento = ElementoFichaArea.objects.filter(ficha__espacio__codigo=AREA, tipo='equipo').exclude(
            registrado=self.previo).select_related('registrado__equipo').first()
        pagina = self.client.get(reverse('ficha_equipo_publica', args=[SLUG, elemento.registrado.codigo_unidad]))
        self.assertEqual(pagina.status_code, 200)
        for visible in ('Identificación del equipo', 'Datos del registro', elemento.registrado.codigo_unidad,
                        elemento.registrado.equipo.codigo, reverse('area_unidad', args=[SLUG, AREA]),
                        'Por confirmar en el inventario', 'data-cita'):
            self.assertContains(pagina, visible)
        # Con la ficha publicada, la tabla del área dice cuántas unidades hay y cuántas están disponibles.
        FichaArea.objects.filter(espacio__unidad=self.laboratorio, espacio__codigo=AREA).update(publicada=True)
        area = self.client.get(reverse('area_unidad', args=[SLUG, AREA]))
        self.assertEqual(area.status_code, 200)
        self.assertContains(area, 'data-filtro="disponible"')

    def test_el_menu_agrupa_las_fichas_de_equipo_por_area(self):
        carpetas = self.client.get(self.laboratorio.get_absolute_url()).context['aula']['carpetas']
        fichas = next(carpeta for carpeta in carpetas if carpeta['id'] == 'FichasEquipo')
        nombres = [grupo['nombre'] for grupo in fichas['grupos']]
        self.assertIn(AREA, nombres)
        # Primero el escáner de equipos; el número de la carpeta cuenta solo equipos.
        self.assertEqual(fichas['grupos'][0]['botones'][0]['url'], reverse('escaner_unidad', args=[SLUG]))
        botones = [boton for grupo in fichas['grupos'][1:] for boton in grupo['botones']]
        # Un botón por tipo de equipo, no por unidad física; el visitante solo ve lo que está en servicio.
        tipos = UnidadEquipo.objects.publicos().filter(laboratorio=self.laboratorio).values('equipo').distinct().count()
        self.assertEqual(len(botones), tipos)
        self.assertEqual(fichas['total'], tipos)
        self.assertTrue(all(boton['icono'] for boton in botones))

    def test_insumos_y_reporte_de_recursos_leen_el_mismo_inventario(self):
        pagina = self.client.get(reverse('insumos_unidad', args=[SLUG]))
        self.assertEqual(pagina.status_code, 200)
        insumo = Consumible.objects.filter(unidad=self.laboratorio).first()
        self.assertContains(pagina, insumo.codigo)
        solicitud = RequestFactory().get('/', {'categoria_reporte': 'recursos'})
        solicitud.user = get_user_model().objects.create_superuser('auditor.xr', 'a@example.org', 'clave')
        filas = build_unit_report(solicitud, self.laboratorio)['dataset']['rows']
        codigos = {fila[1] for fila in filas}
        self.assertIn(insumo.codigo, codigos)
        self.assertIn(self.previo.codigo_unidad, codigos)
        self.assertNotIn(self.de_prueba.codigo_unidad, codigos)

    def test_software_insumos_y_menu_muestran_logos_iconos_y_direcciones(self):
        from apps.recursos.management.commands.sincronizar_equipamiento_areas import clave_de_programa

        programas = list(SoftwareDisponible.objects.filter(unidad=self.laboratorio, activo=True))
        claves = [clave_de_programa(programa.nombre) for programa in programas]
        self.assertEqual(len(claves), len(set(claves)), 'Hay programas repetidos en la unidad.')
        con_sitio = next(programa for programa in programas if programa.sitio_web)
        # Las áreas de un programa salen de fichas publicadas (un borrador no se muestra al público).
        FichaArea.objects.filter(espacio__unidad=self.laboratorio).update(publicada=True)
        pagina = self.client.get(reverse('software_unidad', args=[SLUG]))
        self.assertContains(pagina, con_sitio.sitio_web)
        self.assertContains(pagina, con_sitio.logo_publico_url)
        self.assertContains(pagina, reverse('area_unidad', args=[SLUG, AREA]))
        self.assertContains(pagina, 'aula-programa__logo')
        sin_foto = Consumible.objects.filter(unidad=self.laboratorio, imagen='', imagen_catalogo='').first()
        if sin_foto and not sin_foto.imagen_publica_url:
            self.assertContains(self.client.get(reverse('insumos_unidad', args=[SLUG])), sin_foto.icono)
        ficha = self.client.get(self.laboratorio.get_absolute_url())
        self.assertContains(ficha, f'data-url="{reverse("area_unidad", args=[SLUG, AREA])}"')

    def test_cada_tipo_de_equipo_queda_en_una_familia_de_producto(self):
        from apps.recursos.models.equipos import EquiposServicios as Tipo

        sin_familia = Tipo.objects.filter(unidades__laboratorio=self.laboratorio, unidades__activa=True,
                                          familia__isnull=True).distinct()
        self.assertFalse(sin_familia.exists(), list(sin_familia.values_list('nombre', flat=True)))
