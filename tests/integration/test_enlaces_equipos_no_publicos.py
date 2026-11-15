"""Un visitante no recibe enlaces a equipos que no puede abrir, y la galería de un área no repite sus imágenes de referencia."""
from datetime import date
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from apps.directorio_unidades.models.core import Unidad
from apps.gestion_unidades.models.espacios import EspacioReservable
from apps.gestion_unidades.models.fichas_area import ElementoFichaArea, FichaArea
from apps.gestion_unidades.models.interior import MARCA_IMAGEN_REFERENCIAL, MedioInterior
from apps.gestion_unidades.presentation.area_unidad import medios_de
from apps.recursos.models.equipos import EquiposServicios
from apps.recursos.models.software import SoftwareDisponible
from apps.recursos.models.unidades import UnidadEquipo


class EnlacesAEquiposNoPublicosTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.gestor = get_user_model().objects.create_user('gestor-enlaces', password='clave')
        cls.unidad = Unidad.objects.create(nombre='Unidad de enlaces QA', slug='enlaces-equipos-qa', dependencia='laboratorios',
                                           fecha_inicio=date(2020, 1, 1), administrador=cls.gestor)
        cls.area = EspacioReservable.objects.create(unidad=cls.unidad, codigo='ENL-AREA-01', nombre='Desarrollo', activo=True)
        cls.ficha = FichaArea.objects.create(espacio=cls.area, publicada=True,
                                             distribucion='Puestos | Probar | Visor QA; Torre QA')
        visor = EquiposServicios.objects.create(codigo='ENL-MOD-01', nombre='Visor QA')
        torre = EquiposServicios.objects.create(codigo='ENL-MOD-02', nombre='Torre QA')
        cls.disponible = UnidadEquipo.objects.create(equipo=visor, laboratorio=cls.unidad, codigo_unidad='ENL-VISOR-01',
                                                     estado_unidad='disponible')
        cls.reservado = UnidadEquipo.objects.create(equipo=torre, laboratorio=cls.unidad, codigo_unidad='ENL-TORRE-01',
                                                    estado_unidad='no_disponible')
        cls.area.equipos_asociados.add(cls.disponible, cls.reservado)
        cls.elemento_disponible = ElementoFichaArea.objects.create(ficha=cls.ficha, tipo='equipo', nombre='Visor QA',
                                                                   registrado=cls.disponible)
        cls.elemento_reservado = ElementoFichaArea.objects.create(ficha=cls.ficha, tipo='equipo', nombre='Torre QA',
                                                                  registrado=cls.reservado)
        cls.programa = SoftwareDisponible.objects.create(unidad=cls.unidad, nombre='Motor de pruebas QA', activo=True)
        cls.programa.equipos_instalados.add(cls.disponible, cls.reservado)
        cls.url_disponible = reverse('ficha_equipo_publica', args=[cls.unidad.slug, cls.disponible.codigo_unidad])
        cls.url_reservado = reverse('ficha_equipo_publica', args=[cls.unidad.slug, cls.reservado.codigo_unidad])

    def referencia(self, elemento):
        with patch('apps.recursos.presentation.equipo_referencia.objeto_visible_para', return_value=True), patch(
            'apps.recursos.presentation.equipo_referencia.visibles_para', side_effect=lambda elementos, *_: elementos,
        ):
            return self.client.get(reverse('ficha_equipo_referencia', args=[self.unidad.slug, elemento.pk]))

    def test_el_equipo_no_disponible_no_tiene_ficha_publica(self):
        self.assertEqual(self.client.get(self.url_disponible).status_code, 200)
        self.assertEqual(self.client.get(self.url_reservado).status_code, 404)

    def test_la_ficha_de_referencia_solo_redirige_al_equipo_que_el_visitante_puede_abrir(self):
        self.assertRedirects(self.referencia(self.elemento_disponible), self.url_disponible, fetch_redirect_response=False)
        # Antes redirigía a una ficha que respondía 404; ahora muestra la referencia.
        self.assertEqual(self.referencia(self.elemento_reservado).status_code, 200)
        self.client.force_login(self.gestor)
        self.assertRedirects(self.referencia(self.elemento_reservado), self.url_reservado, fetch_redirect_response=False)

    def test_el_catalogo_de_software_no_enlaza_equipos_que_el_visitante_no_puede_abrir(self):
        url = reverse('software_unidad', args=[self.unidad.slug])
        pagina = self.client.get(url)
        self.assertContains(pagina, self.programa.nombre)
        self.assertContains(pagina, self.url_disponible)
        self.assertNotContains(pagina, self.url_reservado)
        self.client.force_login(self.gestor)
        self.assertContains(self.client.get(url), self.url_reservado)

    def test_la_pagina_del_area_no_enlaza_equipos_que_el_visitante_no_puede_abrir(self):
        url = reverse('area_unidad', args=[self.unidad.slug, self.area.codigo])
        with patch('apps.gestion_unidades.presentation.area_unidad.visibles_para', side_effect=lambda elementos, *_: elementos):
            pagina = self.client.get(url)
        self.assertEqual(pagina.status_code, 200)
        self.assertContains(pagina, self.url_disponible)
        self.assertNotContains(pagina, self.url_reservado)


class GaleriaDeAreaTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.unidad = Unidad.objects.create(nombre='Unidad de galería QA', slug='galeria-area-qa', dependencia='laboratorios',
                                           fecha_inicio=date(2020, 1, 1))
        cls.area = EspacioReservable.objects.create(unidad=cls.unidad, codigo='GAL-AREA-01', nombre='Sala', activo=True)

    def foto(self, titulo, archivo, referencial=False, orden=1):
        return MedioInterior.objects.create(
            unidad=self.unidad, espacio=self.area, tipo='foto', titulo=titulo, imagen=f'unidades/interior/{archivo}', orden=orden,
            descripcion=(MARCA_IMAGEN_REFERENCIAL + ' (copia)') if referencial else 'Foto de la unidad')

    def test_la_imagen_de_referencia_repetida_se_muestra_una_vez_y_rotulada(self):
        # Al integrar dos áreas, la misma imagen de referencia llega dos veces con archivos distintos.
        self.foto('Realidad extendida', 'a.png', referencial=True)
        self.foto('  realidad EXTENDIDA ', 'b.png', referencial=True, orden=2)
        galeria = medios_de(self.area, None)['galeria']
        self.assertEqual([(imagen['titulo'], imagen['referencial']) for imagen in galeria], [('Realidad extendida', True)])

    def test_las_fotos_propias_no_se_descartan_aunque_compartan_titulo(self):
        self.foto('Sala', 'propia-1.png')
        self.foto('Sala', 'propia-2.png', orden=2)
        self.foto('Sala', 'referencia.png', referencial=True, orden=3)
        galeria = medios_de(self.area, None)['galeria']
        self.assertEqual([imagen['referencial'] for imagen in galeria], [False, False, True])
        self.assertEqual(medios_de(self.area, None)['portada'], galeria[0])
