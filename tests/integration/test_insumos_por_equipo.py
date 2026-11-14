"""Los insumos de un equipo tienen una sola fuente: la relación estructurada.

El texto «insumos necesarios» y la marca «requiere insumos» se derivan de los
insumos compatibles registrados (los mismos que ofrece la reserva). Nadie los
edita a mano: ni el admin ni la consola de la unidad.
"""

from datetime import date

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from apps.recursos.models.consumibles import Consumible, ConsumiblePorEquipo
from apps.directorio_unidades.models.core import Unidad
from apps.recursos.models.unidades import UnidadEquipo


class InsumosDerivadosTests(TestCase):
    def setUp(self):
        self.unidad = Unidad.objects.create(nombre='Laboratorio de prototipado', slug='lab-prototipado',
                                            dependencia='laboratorios', fecha_inicio=date(2026, 1, 1))
        catalogo = UnidadEquipo._meta.get_field('equipo').related_model
        self.ficha = catalogo.objects.create(codigo='EQ-FDM', nombre='Impresora 3D FDM')
        self.activo = UnidadEquipo.objects.create(laboratorio=self.unidad, equipo=self.ficha,
                                                  codigo_unidad='UE-FDM-01', activa=True)
        self.pla = Consumible.objects.create(unidad=self.unidad, codigo='INS-PLA', nombre='Filamento PLA')
        self.petg = Consumible.objects.create(unidad=self.unidad, codigo='INS-PETG', nombre='Filamento PETG')

    def test_registrar_y_retirar_insumos_compatibles_actualiza_el_resumen(self):
        ConsumiblePorEquipo.objects.create(consumible=self.petg, equipo=self.ficha)
        ConsumiblePorEquipo.objects.create(consumible=self.pla, equipo=self.ficha)

        self.activo.refresh_from_db()
        self.assertTrue(self.activo.requiere_insumos)
        self.assertEqual(self.activo.insumos_necesarios, 'Filamento PETG, Filamento PLA')

        ConsumiblePorEquipo.objects.filter(consumible=self.petg).delete()
        self.activo.refresh_from_db()
        self.assertEqual(self.activo.insumos_necesarios, 'Filamento PLA')

        ConsumiblePorEquipo.objects.all().delete()
        self.activo.refresh_from_db()
        self.assertFalse(self.activo.requiere_insumos)
        self.assertEqual(self.activo.insumos_necesarios, '')

    def test_los_insumos_de_otra_unidad_no_cuentan_aunque_compartan_ficha(self):
        otra = Unidad.objects.create(nombre='Planta de lácteos', slug='planta-lacteos',
                                     dependencia='plantas_piloto', fecha_inicio=date(2026, 1, 1))
        ajeno = Consumible.objects.create(unidad=otra, codigo='INS-AJENO', nombre='Insumo ajeno')
        ConsumiblePorEquipo.objects.create(consumible=ajeno, equipo=self.ficha)

        self.activo.refresh_from_db()
        self.assertFalse(self.activo.requiere_insumos)
        self.assertEqual(list(self.activo.insumos_compatibles()), [])


class InsumosEnElAdminTests(TestCase):
    def setUp(self):
        self.client.force_login(get_user_model().objects.create_superuser('insumos.qa'))
        self.unidad = Unidad.objects.create(nombre='Laboratorio de prototipado', slug='lab-prototipado',
                                            dependencia='laboratorios', fecha_inicio=date(2026, 1, 1))
        catalogo = UnidadEquipo._meta.get_field('equipo').related_model
        self.ficha = catalogo.objects.create(codigo='EQ-FDM', nombre='Impresora 3D FDM')
        self.activo = UnidadEquipo.objects.create(laboratorio=self.unidad, equipo=self.ficha,
                                                  codigo_unidad='UE-FDM-01', activa=True)

    def test_la_ficha_del_activo_muestra_los_insumos_registrados_y_no_un_texto_editable(self):
        pla = Consumible.objects.create(unidad=self.unidad, codigo='INS-PLA', nombre='Filamento PLA')
        ConsumiblePorEquipo.objects.create(consumible=pla, equipo=self.ficha)

        for ruta in ('admin:recursos_unidadequipo_change', 'admin:laboratorios_unidadequipo_change'):
            with self.subTest(ruta=ruta):
                pagina = self.client.get(reverse(ruta, args=[self.activo.pk]))
                self.assertEqual(pagina.status_code, 200)
                self.assertContains(pagina, '<li>Filamento PLA</li>', html=True)
                self.assertContains(pagina, 'Administrar insumos compatibles')
                self.assertNotContains(pagina, 'name="insumos_necesarios"')
                self.assertNotContains(pagina, 'name="requiere_insumos"')

    def test_el_texto_de_cargas_anteriores_se_ve_como_heredado_hasta_registrar_insumos(self):
        UnidadEquipo.objects.filter(pk=self.activo.pk).update(
            requiere_insumos=True, insumos_necesarios='Papel en rollo A1 y cartucho de tinta')

        pagina = self.client.get(reverse('admin:recursos_unidadequipo_change', args=[self.activo.pk]))

        self.assertContains(pagina, 'Descripción heredada')
        self.assertContains(pagina, 'Papel en rollo A1 y cartucho de tinta')

    def test_el_enlace_administrar_lleva_a_los_insumos_de_esa_ficha_dentro_de_su_tipo(self):
        pagina = self.client.get(reverse('admin:laboratorios_unidadequipo_change', args=[self.activo.pk]))

        destino = reverse('admin:laboratorios_consumibleporequipo_changelist')
        self.assertContains(pagina, f'href="{destino}?equipo__id__exact={self.ficha.pk}"')
