"""Las cuatro tipologías acreditan sólo el alcance realmente revisado y atribuido."""
from datetime import date, timedelta
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.test import TestCase, override_settings
from django.utils import timezone

from apps.directorio_unidades.models.core import Unidad
from apps.documentos.models.medicion import EvidenciaGestionUnidad
from apps.documentos.models.respaldo_medicion import alcances_inventario, ESQUEMA_VERIFICACION
from apps.documentos.presentation.medicion_metas import (
    cobertura_mensual_inspecciones, evidencias_verificadas, registrar_evidencia, registros_de_gestion,
)
from apps.documentos.presentation.expediente_redaccion import actividades_para
from apps.documentos.presentation.medicion_vistas import EvidenciaForm
from apps.formacion.models.practicas import RegistroAuditoriaUnidad


@override_settings(MEDICION_METAS_HABILITADA=True, MEDICION_SOLO_DEMO=False)
class IntegridadMedicionUnidadesTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.actor = get_user_model().objects.create_user('integridad-cuatro-responsable')
        cls.director = get_user_model().objects.create_superuser(
            'integridad-cuatro-direccion', 'qa@example.invalid', 'clave-qa')
        cls.unidades = [Unidad.objects.create(nombre='Unidad QA ' + base,
            slug='integridad-cuatro-' + base.replace('_', '-'), dependencia=base,
            descripcion='Prueba aislada de integridad', administrador=cls.actor, fecha_inicio=date(2026, 1, 1))
            for base in ('laboratorios', 'plantas_piloto', 'centro_experimental', 'observatorios')]

    def evidencia(self, unidad, tipo='CAPACITACION', *, verificar=True, codigo='QA', **extra):
        hoy = timezone.localdate()
        datos = dict(tipo=tipo, codigo=codigo, fecha=hoy, titulo='Revisión QA ' + codigo,
            descripcion='Actividad y alcance comprobados por el responsable de la unidad.',
            responsable=self.actor, enlace=f'https://example.invalid/{unidad.pk}/{codigo}')
        if tipo in ('USO', 'DESECHOS'):
            datos.update(desde=hoy - timedelta(days=10), hasta=hoy, total_observado=2)
        if tipo == 'INVENTARIO':
            datos.update(alcance=list(alcances_inventario(unidad)))
        datos.update(extra)
        return registrar_evidencia(unidad, self.actor, datos, verificar=verificar)

    def validas(self, unidad):
        hoy = timezone.localdate()
        return evidencias_verificadas(unidad,
            list(EvidenciaGestionUnidad.objects.filter(unidad=unidad).select_related('recurso')),
            hoy - timedelta(days=15), hoy)

    def auditoria(self, evidencia):
        return RegistroAuditoriaUnidad.objects.get(entidad=EvidenciaGestionUnidad._meta.label,
            objeto_id=str(evidencia.pk), accion='crear')

    def test_fuentes_verificadas_guardan_estado_atribucion_y_sello_en_cuatro_bases(self):
        for unidad in self.unidades:
            with self.subTest(base=unidad.dependencia):
                e = self.evidencia(unidad)
                a = self.auditoria(e)
                self.assertEqual(a.datos_nuevos['esquema_verificacion'], ESQUEMA_VERIFICACION)
                self.assertEqual(a.datos_nuevos['validado_por'], self.actor.pk)
                self.assertEqual(a.usuario_id, self.actor.pk)
                self.assertEqual(len(a.datos_nuevos['verificacion_sha256']), 64)
                self.assertEqual([v.pk for v in self.validas(unidad)], [e.pk])

    def test_sql_no_promueve_borrador_ni_ejemplo_a_evidencia_real_en_cuatro_bases(self):
        for unidad in self.unidades:
            with self.subTest(base=unidad.dependencia):
                e = self.evidencia(unidad, verificar=False)
                EvidenciaGestionUnidad.objects.filter(pk=e.pk).update(estado='validado',
                    validado_por=self.actor, validado_en=timezone.now())
                self.assertEqual(self.validas(unidad), [])
                with override_settings(MEDICION_SOLO_DEMO=True):
                    demo = self.evidencia(unidad, codigo='DEMO')
                EvidenciaGestionUnidad.objects.filter(pk=demo.pk).update(demostracion=False)
                self.assertEqual(self.validas(unidad), [])

    def test_auditoria_debe_identificar_la_verificacion_original_y_su_actor(self):
        for unidad in self.unidades:
            with self.subTest(base=unidad.dependencia):
                e = self.evidencia(unidad)
                a = self.auditoria(e)
                datos = dict(a.datos_nuevos)
                RegistroAuditoriaUnidad.objects.filter(pk=a.pk).update(usuario=self.director)
                self.assertEqual(self.validas(unidad), [])
                RegistroAuditoriaUnidad.objects.filter(pk=a.pk).update(usuario=self.actor,
                    datos_nuevos={k: v for k, v in datos.items() if k != 'esquema_verificacion'})
                self.assertEqual(self.validas(unidad), [])

    def test_universo_y_tramos_de_uso_y_desechos_no_cambian_despues_de_verificar(self):
        for unidad in self.unidades:
            for tipo in ('USO', 'DESECHOS'):
                with self.subTest(base=unidad.dependencia, tipo=tipo):
                    e = self.evidencia(unidad, tipo, codigo=tipo)
                    self.assertIn(e.pk, [v.pk for v in self.validas(unidad)])
                    for campo, valor in (('total_observado', 1),
                            ('desde', e.desde + timedelta(days=1)),
                            ('hasta', e.hasta - timedelta(days=1))):
                        anterior = getattr(e, campo)
                        EvidenciaGestionUnidad.objects.filter(pk=e.pk).update(**{campo: valor})
                        self.assertNotIn(e.pk, [v.pk for v in self.validas(unidad)])
                        EvidenciaGestionUnidad.objects.filter(pk=e.pk).update(**{campo: anterior})

    def test_cambiar_atribucion_fecha_o_texto_requiere_nueva_verificacion(self):
        for unidad in self.unidades:
            with self.subTest(base=unidad.dependencia):
                e = self.evidencia(unidad)
                cambios = (('fecha', e.fecha - timedelta(days=1)), ('titulo', 'Otro título'),
                    ('descripcion', 'Otra conclusión documentada'), ('detalle', {'otro': 'alcance'}),
                    ('creado_por_id', self.director.pk), ('validado_por_id', self.director.pk),
                    ('validado_en', e.validado_en - timedelta(minutes=5)))
                for campo, valor in cambios:
                    anterior = getattr(e, campo)
                    EvidenciaGestionUnidad.objects.filter(pk=e.pk).update(**{campo: valor})
                    self.assertEqual(self.validas(unidad), [], campo)
                    EvidenciaGestionUnidad.objects.filter(pk=e.pk).update(**{campo: anterior})
                self.assertEqual(len(self.validas(unidad)), 1)

    def test_direccion_sin_responsabilidad_tecnica_no_verifica_evidencia_comun(self):
        for unidad in self.unidades:
            with self.subTest(base=unidad.dependencia):
                with self.assertRaisesMessage(ValidationError, 'responsable técnico'):
                    registrar_evidencia(unidad, self.director, dict(tipo='CAPACITACION',
                        codigo='DIRECCION', fecha=timezone.localdate(), titulo='Actividad QA',
                        descripcion='Respaldo pendiente de comprobación técnica', responsable=self.actor,
                        enlace='https://example.invalid/actividad'), verificar=True)

    def test_campos_del_cliente_no_sustituyen_la_operacion_de_verificacion(self):
        for unidad in self.unidades:
            with self.subTest(base=unidad.dependencia):
                e = self.evidencia(unidad, verificar=False, estado='validado',
                    validado_por=self.actor, validado_en=timezone.now(), demostracion=False)
                self.assertEqual(e.estado, 'borrador')
                self.assertIsNone(e.validado_por_id)
                self.assertEqual(self.validas(unidad), [])

    def test_inventario_respeta_alcance_digital_obs_y_sello_integral_en_cuatro_bases(self):
        for unidad in self.unidades:
            with self.subTest(base=unidad.dependencia):
                e = self.evidencia(unidad, 'INVENTARIO')
                hoy = timezone.localdate()
                self.assertEqual(registros_de_gestion(unidad, hoy - timedelta(days=15), hoy)
                    ['inventarios_verificados'], 1)
                self.assertIn('alcance_sha256', self.auditoria(e).datos_nuevos)
                EvidenciaGestionUnidad.objects.filter(pk=e.pk).update(detalle={'revision_criticidad': True})
                self.assertEqual(self.validas(unidad), [])
                form = EvidenciaForm(unidad=unidad, tipo='INVENTARIO', inicio=hoy, fin=hoy)
                self.assertEqual({clave for clave, _ in form.fields['alcance'].choices},
                    set(alcances_inventario(unidad)))
                self.assertIn('revision_criticidad', form.fields)
                alcance_incompleto = list(alcances_inventario(unidad))[1:]
                with self.assertRaises(ValidationError):
                    self.evidencia(unidad, 'INVENTARIO', codigo='INCOMPLETO', alcance=alcance_incompleto)

    @patch('django.utils.timezone.localdate', return_value=date(2026, 10, 17))
    def test_cobertura_mensual_verificada_para_tres_unidades_fisicas_sin_bioseguridad_obs(self, reloj):
        for unidad in self.unidades:
            with self.subTest(base=unidad.dependencia):
                inicio, fin = date(2026, 8, 17), date(2026, 12, 8)
                actuales = {a.codigo for a in actividades_para(unidad, version=3)}
                legadas = {a.codigo for a in actividades_para(unidad, version=2)}
                if unidad.dependencia == 'observatorios':
                    self.assertIsNone(cobertura_mensual_inspecciones(unidad, inicio, fin))
                    self.assertNotIn('INSPECCIONES', actuales)
                    self.assertNotIn('SEGURIDAD', actuales)
                    continue
                self.assertIn('INSPECCIONES', actuales)
                if unidad.dependencia != 'laboratorios':
                    self.assertNotIn('INSPECCIONES', legadas)
                self.assertEqual(cobertura_mensual_inspecciones(unidad, inicio, fin)['cubiertos_exigibles'], 0)
                self.evidencia(unidad, 'INSPECCION', fecha=date(2026, 8, 20), detalle=dict(
                    area='Área técnica QA', condiciones_revisadas=['equipos'], sin_hallazgos=True,
                    hallazgos='', accion_correctiva='', estado_condiciones='seguro',
                    estado_accion='no_requiere', plazo_accion=''))
                medida = registros_de_gestion(unidad, inicio, fin)['mediciones_porcentuales']['INSPECCIONES']
                self.assertEqual((medida['numerador'], medida['denominador']), (1, 2))

    def test_desechos_de_planta_y_centro_exigen_la_misma_trazabilidad_de_su_anexo(self):
        from apps.recursos.models.desechos import RegistroDesecho
        hoy = timezone.localdate()
        inicio = hoy - timedelta(days=10)
        for unidad in self.unidades:
            if unidad.dependencia not in ('plantas_piloto', 'centro_experimental'):
                continue
            with self.subTest(base=unidad.dependencia):
                self.evidencia(unidad, 'DESECHOS', total_observado=1)
                RegistroDesecho.objects.create(unidad=unidad, fecha_generacion=hoy,
                    clase='peligroso', nombre='Partida heredada sin respaldo QA', cantidad=1,
                    envase='Contenedor QA', etiquetado=True, etapa='entregado',
                    responsable=self.actor, gestor_autorizado='Gestor QA', manifiesto='MAN-QA',
                    fecha_entrega=hoy, licencia_gestor='', documento=None)
                medida = registros_de_gestion(unidad, inicio, hoy)['mediciones_porcentuales']['DESECHOS']
                self.assertEqual((medida['numerador'], medida['denominador']), (0, 1))
