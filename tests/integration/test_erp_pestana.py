"""El ERP de la planta en su propia pestaña, aparte de «Gestionar laboratorio».

La consola administra la unidad (uso, recursos, mantenimiento, seguridad,
personal y reportes) y el ERP opera la cadena productiva (planificar, comprar,
producir, controlar y despachar). Comparten el JS y los formularios, pero cada
una pinta solo sus secciones y lleva a la otra. Un laboratorio que no produce no
tiene ERP.
"""
from datetime import date

from django.contrib.auth import get_user_model
from django.urls import reverse

from apps.directorio_unidades.models.core import Unidad
from tests.integration.test_produccion_planta import BasePlantaProduce


class ElErpEnSuPestanaTests(BasePlantaProduce):
    def pagina(self, nombre, usuario=None):
        self.client.force_login(usuario or self.coordinacion)
        return self.client.get(reverse(nombre, args=[self.unidad.slug]))

    def test_cada_pestana_pinta_lo_suyo_y_lleva_a_la_otra(self):
        consola = self.pagina('gestion_unidad')
        erp = self.pagina('erp_planta')
        self.assertEqual(
            [seccion['clave'] for seccion in erp.context['secciones_navegacion']],
            ['mapa', 'sesiones', 'planificacion', 'produccion', 'calidad', 'supervision'],
        )
        claves_consola = [seccion['clave'] for seccion in consola.context['secciones_navegacion']]
        for clave in ('reservas', 'recursos', 'mantenimiento', 'practicas', 'seguridad', 'reportes', 'configuracion'):
            self.assertIn(clave, claves_consola)
        for clave in ('mapa', 'sesiones', 'planificacion', 'produccion', 'calidad', 'supervision'):
            self.assertNotIn(clave, claves_consola)
            self.assertNotContains(consola, f'data-management-view="{clave}"')
        for clave in ('indicadores', 'reservas', 'recursos', 'mantenimiento', 'reportes', 'configuracion'):
            self.assertNotContains(erp, f'data-management-view="{clave}"')
        self.assertContains(erp, 'data-agenda-operation-form="orden_produccion"')
        self.assertNotContains(consola, 'data-agenda-operation-form="orden_produccion"')
        self.assertContains(consola, f'href="{reverse("erp_planta", args=[self.unidad.slug])}"')
        self.assertContains(erp, f'href="{reverse("gestion_unidad", args=[self.unidad.slug])}"')
        self.assertEqual(erp.context['vista_gestion'], 'mapa')
        self.assertContains(erp, 'Operar la planta')

    def test_el_mapa_abre_la_cadena_aqui_y_la_administracion_en_la_consola(self):
        mapa = self.pagina('erp_planta').context['mapa_planta']
        por_clave = {modulo['clave']: modulo for modulo in mapa['modulos']}
        self.assertEqual(por_clave['produccion']['vista'], 'produccion')
        self.assertEqual(por_clave['abastecimiento']['vista'], 'planificacion')
        self.assertEqual(por_clave['mantenimiento']['vista'], '')
        self.assertEqual(
            por_clave['mantenimiento']['enlace'],
            reverse('gestion_unidad', args=[self.unidad.slug]) + '?view=mantenimiento',
        )
        self.assertEqual({modulo['clave'] for modulo in mapa['modulos_erp']},
                         {'planificacion', 'abastecimiento', 'produccion', 'calidad', 'logistica'})

    def test_un_laboratorio_no_tiene_erp_y_quien_no_gestiona_solo_ve_sesiones(self):
        laboratorio = Unidad.objects.create(
            nombre='Laboratorio sin producción', descripcion='Solo reserva.',
            fecha_inicio=date(2026, 1, 1), dependencia='laboratorios',
            slug='laboratorio-sin-erp', administrador=self.coordinacion,
        )
        self.client.force_login(self.coordinacion)
        self.assertEqual(self.client.get(reverse('erp_planta', args=[laboratorio.slug])).status_code, 404)
        consola = self.client.get(reverse('gestion_unidad', args=[laboratorio.slug]))
        self.assertNotContains(consola, reverse('erp_planta', args=[laboratorio.slug]))
        # Quien no es de la planta no ve la producción real: entra a practicar en una sesión.
        ajeno = get_user_model().objects.create_user('ajeno.erp', 'ajeno.erp@upec.edu.ec', 'Clave-segura-2026')
        pagina = self.pagina('erp_planta', ajeno)
        self.assertEqual(pagina.status_code, 200)
        self.assertEqual([seccion['clave'] for seccion in pagina.context['secciones_navegacion']], ['sesiones'])
        self.assertNotContains(pagina, 'data-management-view="produccion"')
        self.assertNotContains(pagina, f'href="{reverse("gestion_unidad", args=[self.unidad.slug])}"')

    def test_la_ficha_el_aula_y_los_regresos_llevan_al_erp(self):
        url_erp = reverse('erp_planta', args=[self.unidad.slug])
        self.client.force_login(self.coordinacion)
        ficha = self.client.get(self.unidad.get_absolute_url())
        self.assertContains(ficha, f'href="{url_erp}"')
        proceso = self.client.get(reverse('ficha_proceso', args=[self.unidad.slug, self.receta_queso.pk]))
        self.assertContains(proceso, f'{url_erp}?view=produccion')
        aula = self.client.get(reverse('ficha_proceso_publica', args=[self.unidad.slug, self.receta_queso.pk]))
        self.assertEqual(aula.context['operar_url'], f'{url_erp}?view=produccion')
        _orden, lote = self.queso_disponible()
        traza = self.client.get(reverse('trazabilidad_lote', args=[self.unidad.slug, lote.pk]))
        self.assertEqual(traza.context['volver_url'], f'{url_erp}?view=produccion')
