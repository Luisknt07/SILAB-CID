"""El equipamiento por familia de producto: el mismo equipo en varias unidades, con su uso, para dirigir compras."""
from datetime import date, time, timedelta

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from apps.recursos.presentation.equipamiento_institucional import familias, recomendacion
from apps.recursos.management.commands.sincronizar_equipamiento_areas import asignar_familia
from apps.recursos.models.equipos import EquiposServicios, FamiliaEquipo
from apps.reservas.models.reservas import Reserva
from apps.directorio_unidades.models.core import Unidad
from apps.recursos.models.unidades import UnidadEquipo
from tests.integration.utiles import identificar


class EquipamientoInstitucionalTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.director = get_user_model().objects.create_user('director-equipos', password='clave', is_staff=True,
                                                            is_superuser=True)
        cls.estudiante = get_user_model().objects.create_user('estudiante-equipos', password='clave')
        identificar(cls.estudiante, tipo_usuario='estudiante')
        cls.xr = Unidad.objects.create(nombre='Realidad Extendida', slug='xr-familias', dependencia='laboratorios',
                                       descripcion='.', fecha_inicio=date(2020, 1, 1))
        cls.fab = Unidad.objects.create(nombre='FabLab', slug='fab-familias', dependencia='laboratorios',
                                        descripcion='.', fecha_inicio=date(2020, 1, 1))
        cls.visor_xr = EquiposServicios.objects.create(codigo='FAM-VR-XR', nombre='Visores autónomos de la flota')
        cls.visor_fab = EquiposServicios.objects.create(codigo='FAM-VR-FAB', nombre='Visores de realidad virtual')
        for tipo in (cls.visor_xr, cls.visor_fab):
            asignar_familia(tipo, {'tipos con familia': 0}, tipo.nombre)
        cls.xr_equipos = [UnidadEquipo.objects.create(codigo_unidad=f'FAM-XR-{n}', equipo=cls.visor_xr, laboratorio=cls.xr)
                          for n in range(1, 4)]
        cls.fab_equipos = [UnidadEquipo.objects.create(codigo_unidad=f'FAM-FAB-{n}', equipo=cls.visor_fab, laboratorio=cls.fab)
                           for n in range(1, 3)]

    def test_el_mismo_producto_de_dos_unidades_cae_en_una_familia(self):
        self.visor_xr.refresh_from_db()
        self.visor_fab.refresh_from_db()
        self.assertIsNotNone(self.visor_xr.familia)
        self.assertEqual(self.visor_xr.familia, self.visor_fab.familia)
        self.assertEqual(self.visor_xr.familia.nombre, 'Visores de realidad virtual y mixta')
        familia = next(item for item in familias() if item['clave'] == self.visor_xr.familia.slug)
        self.assertEqual(familia['total'], 5)
        self.assertEqual({unidad['unidad'].slug: unidad['total'] for unidad in familia['unidades']}, {'xr-familias': 3, 'fab-familias': 2})
        self.assertIn('aún no hay reservas atendidas', familia['recomendacion'])

    def test_el_uso_de_las_reservas_atendidas_decide_el_diagnostico(self):
        hoy = timezone.localdate()
        for dia in range(30):
            Reserva.objects.create(
                laboratorio=self.xr, usuario=self.director, equipo_nombre='Visor',
                unidades_seleccionadas='[{"codigo": "FAM-XR-1"}, {"codigo": "FAM-XR-2"}, {"codigo": "FAM-XR-3"}]',
                fecha=hoy - timedelta(days=dia + 1), hora_inicio=time(7, 0), hora_fin=time(19, 0), estado='completada',
                resultado_cierre='atendida', detalle_ejecucion={
                    'registrada_en': timezone.now().isoformat(), 'horario_real': {'inicio': '07:00', 'fin': '19:00'},
                    'asistentes_total': 10, 'equipos': [{'id': str(e.pk), 'codigo': e.codigo_unidad} for e in self.xr_equipos]},
                proposito_codigo='docencia_practica', titulo_solicitud='Práctica', numero_participantes=10)
        familia = next(item for item in familias() if item['clave'] == FamiliaEquipo.objects.get().slug)
        por_unidad = {unidad['unidad'].slug: unidad for unidad in familia['unidades']}
        self.assertEqual(por_unidad['xr-familias']['estado'], 'equilibrada')
        self.assertEqual(por_unidad['fab-familias']['estado'], 'sin_uso')
        self.assertEqual(por_unidad['xr-familias']['horas_por_equipo'], 360.0)
        demandada = [{'unidad': self.xr, 'total': 3, 'estado': 'demandada', 'horas_por_equipo': 600},
                     {'unidad': self.fab, 'total': 2, 'estado': 'sin_uso', 'horas_por_equipo': 0}]
        self.assertIn('trasladar o compartir', recomendacion(demandada))

    def test_la_foto_heredada_de_la_familia_no_repite_el_aviso(self):
        from collections import Counter

        from apps.recursos.presentation.catalogo_inventario import credito_heredado, heredar_foto

        self.assertEqual(credito_heredado('Foto de otro equipo de su familia · Foto de otro equipo de su familia · '),
                         'Foto de otro equipo de su familia')
        self.assertEqual(credito_heredado('Wikimedia Commons'), 'Foto de otro equipo de su familia · Wikimedia Commons')
        EquiposServicios.objects.filter(pk=self.visor_xr.pk).update(imagen_catalogo='img/visor.png', credito_imagen='Autor X')
        heredar_foto(self.visor_fab, Counter())
        tercero = EquiposServicios.objects.create(codigo='FAM-VR-3', nombre='Otro visor', familia=self.visor_xr.familia)
        heredar_foto(tercero, Counter())
        tercero.refresh_from_db()
        self.assertEqual(tercero.credito_imagen, 'Foto de otro equipo de su familia · Autor X')

    def test_el_tablero_es_para_la_direccion_y_se_descarga(self):
        url = reverse('equipamiento_institucional')
        self.client.force_login(self.estudiante)
        self.assertEqual(self.client.get(url).status_code, 403)
        self.client.force_login(self.director)
        pagina = self.client.get(url, {'q': 'visores'})
        self.assertContains(pagina, 'Visores de realidad virtual y mixta')
        self.assertContains(pagina, 'Realidad Extendida')
        csv = self.client.get(url, {'formato': 'csv'})
        self.assertEqual(csv['Content-Type'], 'text/csv; charset=utf-8')
        detalle = self.client.get(reverse('familia_equipo_institucional', args=[FamiliaEquipo.objects.get().slug]))
        self.assertContains(detalle, 'FAM-FAB-2')
        self.assertContains(detalle, reverse('ficha_equipo_publica', args=['xr-familias', 'FAM-XR-1']))
