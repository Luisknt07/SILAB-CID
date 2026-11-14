"""El ERP de la planta: su menú, el mapa en su tablero y el acceso por módulo.

El personal de la planta consulta los módulos de la cadena productiva y opera
solo los que la coordinación le delegó; los demás los ve sin sus cifras. El mapa
abre los módulos del ERP en la misma pestaña y los de la administración en
Gestionar laboratorio, y cuenta cada sesión aparte de la producción real.
"""
from datetime import timedelta

from django.contrib.auth import get_user_model
from django.urls import reverse

from apps.plantas_piloto.operacion.presentation.planta_operativa import FLUJO, MODULOS, mapa_de_la_planta
from apps.gestion_unidades.presentation.permisos import permisos_operativos_unidad
from apps.gestion_unidades.models.espacios import ResponsableUnidad
from apps.plantas_piloto.operacion.models.erp import SesionERP
from tests.integration.test_produccion_planta import BasePlantaProduce


class ElErpDeLaPlantaTests(BasePlantaProduce):
    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()
        cls.tecnico = get_user_model().objects.create_user(
            username='tecnico.erp', password='Clave-segura-2026', email='tecnico.erp@upec.edu.ec',
        )
        ResponsableUnidad.objects.create(
            unidad=cls.unidad, usuario=cls.tecnico, nombre='Técnico de mantenimiento', rol='tecnico',
        )

    def consola(self, usuario):
        self.client.force_login(usuario)
        return self.client.get(reverse('erp_planta', args=[self.unidad.slug]))

    def test_el_menu_de_la_planta_tiene_todos_sus_modulos_agrupados(self):
        pagina = self.consola(self.coordinacion)
        self.assertEqual(pagina.status_code, 200)
        claves = [seccion['clave'] for seccion in pagina.context['secciones_navegacion']]
        self.assertEqual(claves, ['mapa', 'sesiones', 'planificacion', 'produccion', 'calidad', 'supervision'])
        for grupo in ('Inicio', 'Planificar', 'Producir', 'Ir a'):
            self.assertContains(pagina, f'class="unit-console__nav-group" role="presentation">{grupo}</span>')
        consola = self.client.get(reverse('gestion_unidad', args=[self.unidad.slug]))
        for grupo in ('Uso de la unidad', 'Formación', 'Recursos', 'Administrar'):
            self.assertContains(consola, f'class="unit-console__nav-group" role="presentation">{grupo}</span>')

    def test_el_tablero_muestra_el_mapa_y_cada_modulo_abre_su_seccion(self):
        pagina = self.consola(self.coordinacion)
        self.assertContains(pagina, 'Módulos y flujo de la cadena productiva')
        self.assertContains(pagina, '<button type="button" data-management-target="produccion">Abrir</button>')
        mapa = pagina.context['mapa_planta']
        self.assertEqual([paso['clave'] for paso in mapa['flujo']], list(FLUJO))
        self.assertTrue(all(modulo['acceso'] == 'opera' for modulo in mapa['modulos']))
        self.assertEqual(len(mapa['modulos']), len(MODULOS))
        # Lo que se administra en la consola se abre en su pestaña.
        self.assertContains(pagina, reverse('gestion_unidad', args=[self.unidad.slug]) + '?view=mantenimiento')

    def test_quien_no_opera_produccion_la_consulta_sin_formularios(self):
        pagina = self.consola(self.tecnico)
        self.assertEqual(pagina.status_code, 200)
        secciones = {seccion['clave']: seccion for seccion in pagina.context['secciones_navegacion']}
        self.assertTrue(secciones['produccion']['habilitada'])
        self.assertIn('solo consulta', secciones['produccion']['etiqueta'])
        self.assertTrue(secciones['calidad']['habilitada'])
        self.assertNotContains(pagina, 'data-agenda-operation-open="orden_produccion"')
        accesos = {modulo['clave']: modulo for modulo in pagina.context['mapa_planta']['modulos']}
        self.assertEqual(accesos['produccion']['acceso'], 'consulta')
        self.assertEqual(accesos['mantenimiento']['acceso'], 'opera')
        self.assertEqual(
            accesos['mantenimiento']['enlace'], reverse('gestion_unidad', args=[self.unidad.slug]) + '?view=mantenimiento',
        )
        # Sin acceso no se ven sus cifras.
        self.assertEqual(accesos['finanzas']['acceso'], 'sin_acceso')
        self.assertEqual(accesos['finanzas']['indicadores'], [])
        self.assertEqual(accesos['finanzas']['vista'], '')

    def test_la_orden_enlaza_su_proceso_sus_lotes_y_el_lote_su_control(self):
        orden = self.orden_de(self.planificar_queso(
            fecha_inicio=self.hoy.isoformat(), fecha_fin=(self.hoy + timedelta(days=1)).isoformat(),
        ))
        self.assertEqual(self.cerrar_queso(orden).status_code, 200)
        lote = orden.lotes.get(producto=orden.producto)
        pagina = self.consola(self.coordinacion)
        self.assertContains(pagina, reverse('ficha_proceso_publica', args=[self.unidad.slug, orden.receta_id]))
        self.assertContains(pagina, reverse('trazabilidad_lote', args=[self.unidad.slug, lote.pk]))
        self.assertContains(pagina, reverse('control_calidad', args=[self.unidad.slug]) + f'?lote_producto={lote.pk}')
        self.assertContains(pagina, reverse('simulador_balance', args=[self.unidad.slug]) + f'?receta={orden.receta_id}')

    def test_el_aula_lleva_al_erp_solo_a_quien_gestiona_la_planta(self):
        ficha = reverse('ficha_proceso_publica', args=[self.unidad.slug, self.receta_queso.pk])
        consola = reverse('erp_planta', args=[self.unidad.slug]) + '?view=produccion'
        self.assertNotContains(self.client.get(ficha), consola)
        self.client.force_login(self.coordinacion)
        self.assertContains(self.client.get(ficha), consola)

    def test_la_calidad_publica_resume_los_lotes_sin_su_detalle(self):
        orden = self.orden_de(self.planificar_queso(
            fecha_inicio=self.hoy.isoformat(), fecha_fin=(self.hoy + timedelta(days=1)).isoformat(),
        ))
        self.assertEqual(self.cerrar_queso(orden).status_code, 200)
        lote = orden.lotes.get(producto=orden.producto)
        self.client.logout()
        pagina = self.client.get(reverse('calidad_publica', args=[self.unidad.slug]))
        self.assertContains(pagina, 'CONTROL DE CALIDAD DE LOS LOTES, POR PRODUCTO')
        self.assertContains(pagina, lote.producto.nombre)
        self.assertNotContains(pagina, lote.codigo)

    def test_el_mapa_cuenta_cada_sesion_aparte_de_la_produccion_real(self):
        sesion = SesionERP.demostrativa_de(self.unidad)
        self.orden_de(self.planificar_queso(sesion_erp=sesion.codigo))
        permisos = permisos_operativos_unidad(self.coordinacion, self.unidad)

        def abiertas(mapa):
            produccion = next(modulo for modulo in mapa['modulos'] if modulo['clave'] == 'produccion')
            return dict(produccion['indicadores'])['Órdenes abiertas']

        self.assertEqual(abiertas(mapa_de_la_planta(self.unidad, permisos, {'produccion'})), 0)
        self.assertEqual(abiertas(mapa_de_la_planta(self.unidad, permisos, {'produccion'}, sesion)), 1)
