from datetime import date

from django.core.exceptions import ValidationError
from django.test import TestCase

from apps.centros_experimentales.operacion.models.perfil import PerfilCentroExperimental
from apps.laboratorios.operacion.models.perfil import PerfilLaboratorio, PerfilPlataformaTecnologica
from apps.observatorios.operacion.models.perfil import PerfilObservatorio
from apps.plantas_piloto.operacion.models.perfil import PerfilPlantaPiloto
from apps.directorio_unidades.models.core import Unidad


class PerfilesOperativosUnidadTests(TestCase):
    def crear_unidad(self, dependencia, slug, clasificacion_funcional=''):
        return Unidad.objects.create(
            nombre=f'Unidad {slug}',
            descripcion='Unidad para verificar la clasificación funcional.',
            fecha_inicio=date(2026, 8, 27),
            slug=slug,
            dependencia=dependencia,
            clasificacion_funcional=clasificacion_funcional,
            area_conocimiento='otro',
        )

    def test_cada_dependencia_recibe_clasificacion_y_perfil_predeterminados(self):
        casos = (
            ('laboratorios', 'laboratorio-academico', 'laboratorio_academico', PerfilLaboratorio),
            ('plantas_piloto', 'planta-piloto', 'planta_piloto', PerfilPlantaPiloto),
            (
                'centro_experimental',
                'centro-experimental',
                'centro_experimental',
                PerfilCentroExperimental,
            ),
            ('observatorios', 'observatorio', 'observatorio', PerfilObservatorio),
        )

        for dependencia, slug, clasificacion, modelo_perfil in casos:
            with self.subTest(dependencia=dependencia):
                unidad = self.crear_unidad(dependencia, slug)
                self.assertEqual(unidad.clasificacion_funcional, clasificacion)
                self.assertTrue(modelo_perfil.objects.filter(unidad=unidad).exists())

    def test_plataforma_tecnologica_conserva_catalogo_de_laboratorios(self):
        unidad = self.crear_unidad(
            'laboratorios',
            'fablab-pruebas',
            'plataforma_tecnologica',
        )

        self.assertEqual(unidad.dependencia, 'laboratorios')
        self.assertEqual(
            unidad.clasificacion_funcional,
            'plataforma_tecnologica',
        )
        self.assertTrue(
            PerfilPlataformaTecnologica.objects.filter(unidad=unidad).exists()
        )

    def test_laboratorio_puede_clasificarse_como_academico_id_o_mixto(self):
        for indice, clasificacion in enumerate((
            'laboratorio_academico',
            'laboratorio_id',
            'laboratorio_mixto',
        )):
            with self.subTest(clasificacion=clasificacion):
                unidad = self.crear_unidad(
                    'laboratorios',
                    f'laboratorio-{indice}',
                    clasificacion,
                )
                unidad.full_clean()
                self.assertTrue(
                    PerfilLaboratorio.objects.filter(unidad=unidad).exists()
                )

    def test_rechaza_clasificacion_incompatible_con_dependencia(self):
        unidad = self.crear_unidad(
            'observatorios',
            'observatorio-invalido',
            'planta_piloto',
        )

        with self.assertRaises(ValidationError) as error:
            unidad.full_clean()

        self.assertIn('clasificacion_funcional', error.exception.message_dict)

    def test_perfil_rechaza_unidad_de_otra_clasificacion(self):
        unidad = self.crear_unidad(
            'laboratorios',
            'laboratorio-para-perfil',
            'laboratorio_academico',
        )
        perfil_incompatible = PerfilObservatorio(unidad=unidad)

        with self.assertRaises(ValidationError) as error:
            perfil_incompatible.full_clean()

        self.assertIn('unidad', error.exception.message_dict)

    def test_cambiar_clasificacion_crea_el_nuevo_perfil_sin_borrar_historial(self):
        unidad = self.crear_unidad(
            'laboratorios',
            'laboratorio-reclasificable',
            'laboratorio_academico',
        )
        perfil_anterior = unidad.perfil_laboratorio

        unidad.clasificacion_funcional = 'plataforma_tecnologica'
        unidad.full_clean()
        unidad.save(update_fields=['clasificacion_funcional'])

        self.assertTrue(
            PerfilPlataformaTecnologica.objects.filter(unidad=unidad).exists()
        )
        self.assertTrue(
            PerfilLaboratorio.objects.filter(pk=perfil_anterior.pk).exists()
        )
