"""Los Centros I+D se administran y se publican aparte de las unidades."""

from django.contrib import admin
from django.contrib.auth import get_user_model
from django.test import RequestFactory, TestCase
from django.urls import reverse

from apps.centros_id.models import CentroID


class RegistroCentrosIDTests(TestCase):
    def setUp(self):
        self.autor = get_user_model().objects.create_superuser('centros.qa')
        self.peticion = RequestFactory().get('/admin/')
        self.peticion.user = self.autor

    def crear(self, nombre='Centro de Agroindustria', slug='centro-agroindustria',
              area='agroindustria', activo=True):
        return CentroID.objects.create(
            nombre=nombre, slug=slug, area=area, activo=activo,
            proposito='Acompaña a productores en calidad alimentaria.')

    def test_tiene_area_propia_fuera_de_laboratorios_y_unidades(self):
        areas = {a['name']: a for a in admin.site.get_app_list(self.peticion)}
        self.assertIn('Centros de Investigación y Desarrollo', areas)
        propia = {m['object_name'] for m in areas['Centros de Investigación y Desarrollo']['models']}
        self.assertEqual(propia, {'CentroID', 'Componente', 'EquipoCentro', 'ProcesoArea', 'Integrante', 'Grupo', 'Proyecto',
                                  'Resultado', 'CasoExito', 'Aliado', 'Servicio', 'SolicitudCentro', 'Convocatoria',
                                  'Novedad', 'DocumentoCentro', 'CarpetaCentro', 'Zona', 'HerramientaCentro',
                                  'HorarioRecurso', 'BloqueoRecurso', 'HabilitacionEquipo', 'LineaInvestigacion'})
        for tipo in ('Laboratorios', 'Plantas piloto', 'Centros experimentales', 'Observatorios'):
            self.assertFalse(propia & {m['object_name'] for m in areas[tipo]['models']})

    def test_la_portada_lista_los_centros_activos_y_omite_los_retirados(self):
        self.crear()
        self.crear('Centro Digital', 'centro-digital', 'digitales', activo=False)

        pagina = self.client.get(reverse('centros_id'))

        self.assertEqual(pagina.status_code, 200)
        self.assertContains(pagina, 'Centro de Agroindustria')
        self.assertNotContains(pagina, 'Centro Digital')

    def test_sin_centros_registrados_la_portada_lo_dice_y_no_se_rompe(self):
        """Publicar el registro no puede romper la página mientras esté vacía."""
        pagina = self.client.get(reverse('centros_id'))

        self.assertEqual(pagina.status_code, 200)
        self.assertContains(pagina, 'Los Centros I+D de la institución aparecerán aquí cuando se registren.')
        # El catálogo vacío no ofrece accesos a secciones retiradas.
        self.assertNotContains(pagina, 'Tres puertas de entrada')

    def test_el_area_prioritaria_sobrevive_a_un_codigo_desconocido(self):
        """Un código retirado no puede dejar la portada sin poder dibujarse."""
        centro = self.crear()
        CentroID.objects.filter(pk=centro.pk).update(area='area_retirada')
        centro.refresh_from_db()

        self.assertIsNone(centro.area_prioritaria)
        self.assertEqual(centro.nombre_area, 'area_retirada')
        self.assertEqual(centro.icono, 'iconsminds-building')
        self.assertEqual(self.client.get(reverse('centros_id')).status_code, 200)
