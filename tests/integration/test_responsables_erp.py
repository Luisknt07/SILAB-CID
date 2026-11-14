"""Responsables en el ERP y datos maestros fuera del alcance de las sesiones.

Cada proceso y cada plan maestro dicen quién del personal de la planta responde
por ellos. En una sesión de práctica no aparecen los botones para editar datos
maestros: se opera la cadena, no el catálogo.
"""
from django.contrib.auth import get_user_model
from django.urls import reverse

from apps.recursos.models.consumibles import Consumible
from apps.plantas_piloto.operacion.models.planificacion import PlanMaestro
from apps.plantas_piloto.operacion.models.produccion import Receta
from apps.gestion_unidades.models.espacios import ResponsableUnidad
from apps.plantas_piloto.operacion.models.erp import SesionERP
from tests.integration.test_produccion_planta import BasePlantaProduce
from tests.integration.utiles import identificar


class LosResponsablesDelErpTests(BasePlantaProduce):
    def test_el_proceso_y_el_plan_tienen_su_responsable(self):
        responsable = ResponsableUnidad.objects.filter(unidad=self.unidad, activo=True).first()
        respuesta = self.operar(
            modulo='receta', producto_id=self.receta_queso.producto_id, codigo='LAC-REC-RESPONSABLE',
            nombre='Queso con responsable', cantidad_base='10', unidad_base='litros de leche',
            rendimiento_esperado='1.2', duracion_horas='2', activa='on', responsable_id=responsable.pk,
            insumo_consumible=[str(Consumible.objects.get(codigo='LAC-INS-LECHE').pk)], insumo_cantidad=['10'],
            insumo_obligatorio=['si'],
        )
        self.assertEqual(respuesta.status_code, 200, respuesta.content)
        self.assertEqual(Receta.objects.get(codigo='LAC-REC-RESPONSABLE').responsable, responsable)
        plan = self.operar(
            modulo='plan_maestro', nombre='Semana de quesos', desde=self.hoy.isoformat(),
            hasta=self.hoy.isoformat(), estado='borrador', responsable_id=responsable.pk,
        )
        self.assertEqual(plan.status_code, 200, plan.content)
        self.assertEqual(PlanMaestro.objects.get(pk=plan.json()['registro']['id']).responsable, responsable)
        self.client.force_login(self.coordinacion)
        erp = self.client.get(reverse('erp_planta', args=[self.unidad.slug]))
        self.assertContains(erp, f'Responsable: {responsable.nombre_publico}')

    def test_en_una_sesion_no_se_ofrecen_los_datos_maestros(self):
        estudiante = get_user_model().objects.create_user('estudiante.maestros', 'em@upec.edu.ec', 'Clave-segura-2026')
        identificar(estudiante, tipo_usuario='estudiante')
        sesion = SesionERP.objects.create(unidad=self.unidad, nombre='Práctica', tipo='individual', responsable=estudiante)
        self.client.force_login(estudiante)
        pagina = self.client.get(reverse('erp_planta', args=[self.unidad.slug]), {'sesion': sesion.codigo})
        self.assertContains(pagina, 'data-agenda-operation-open="orden_produccion"')
        for maestro in ('producto', 'receta', 'plan_calidad', 'parametro_calidad'):
            self.assertNotContains(pagina, f'data-agenda-operation-open="{maestro}"')
        self.client.force_login(self.coordinacion)
        real = self.client.get(reverse('erp_planta', args=[self.unidad.slug]))
        self.assertContains(real, 'data-agenda-operation-open="receta"')
