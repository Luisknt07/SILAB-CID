"""Infraestructura: programación real, ejecución trazable y otras unidades intactas."""
import io
from datetime import date
from tempfile import TemporaryDirectory
from types import SimpleNamespace
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase, override_settings
from django.urls import reverse
from django.utils import timezone
from reportlab.pdfgen import canvas

from apps.directorio_unidades.models.core import Unidad
from apps.documentos.models.infraestructura import es_laboratorio_infraestructura
from apps.documentos.models.medicion import EvidenciaGestionUnidad
from apps.documentos.presentation.infraestructura_laboratorios import (
    acciones_infraestructura, infraestructura_documentada,
)
from apps.documentos.presentation.medicion_metas import (
    medir_mantenimiento_integral, registrar_evidencia, rectificar_evidencia,
)
from apps.gestion_unidades.models.espacios import EspacioReservable


@override_settings(MEDICION_METAS_HABILITADA=True, MEDICION_SOLO_DEMO=False)
class InfraestructuraLaboratoriosTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.actor = get_user_model().objects.create_user(username='infraestructura-responsable-qa')
        cls.unidad = Unidad.objects.create(nombre='Infraestructura QA', slug='infraestructura-qa',
            dependencia='laboratorios', descripcion='Laboratorio aislado de pruebas',
            fecha_inicio=date(2026, 1, 1), administrador=cls.actor)
        cls.otra = Unidad.objects.create(nombre='Otro laboratorio QA', slug='otra-infraestructura-qa',
            dependencia='laboratorios', descripcion='Otro laboratorio aislado', administrador=cls.actor,
            fecha_inicio=date(2026, 1, 1))
        cls.observatorio = Unidad.objects.create(nombre='Observatorio QA', slug='observatorio-infra-qa',
            dependencia='observatorios', descripcion='Unidad de otro tipo', administrador=cls.actor,
            fecha_inicio=date(2026, 1, 1))
        cls.espacio = EspacioReservable.objects.create(unidad=cls.unidad, codigo='INFRA-AREA-QA',
            nombre='Sala técnica QA', capacidad=2)

    def setUp(self):
        carpeta = TemporaryDirectory(prefix='citt-qa-infraestructura-')
        self.addCleanup(carpeta.cleanup)
        media = override_settings(MEDIA_ROOT=carpeta.name)
        media.enable()
        self.addCleanup(media.disable)
        reloj = patch('django.utils.timezone.localdate', return_value=date(2026, 10, 17))
        reloj.start()
        self.addCleanup(reloj.stop)
        self.inicio, self.fin = date(2026, 7, 1), date(2026, 12, 31)

    def archivo(self, codigo):
        salida = io.BytesIO()
        pdf = canvas.Canvas(salida)
        pdf.drawString(35, 800, f'Respaldo verificable QA {codigo}: alcance, responsable, trabajo y resultado documentados.')
        pdf.save()
        return SimpleUploadedFile(codigo + '.pdf', salida.getvalue(), content_type='application/pdf')

    def datos_plan(self, codigo='PLAN-QA'):
        return dict(tipo='PLAN-INFRA', codigo=codigo, fecha=date(2026, 6, 30),
            titulo='Plan de mantenimiento eléctrico QA', descripcion='Revisión y mantenimiento de circuitos de la sala.',
            responsable=self.actor, detalle=dict(alcance_infraestructura='aplica',
                justificacion_alcance='El plan adjunto comprende la sala técnica y las instalaciones comunes del laboratorio QA.',
                alcance_todo_laboratorio=True,
                espacio_id=self.espacio.pk, ubicacion='Sala técnica QA',
                intervencion='Mantenimiento de tomas eléctricas', criticidad='critica',
                fecha_programada='2026-07-01', frecuencia_dias=30, fecha_fin_programacion='2026-12-31'))

    def plan(self, codigo='PLAN-QA', **cambios):
        datos = self.datos_plan(codigo)
        datos.update(cambios)
        return registrar_evidencia(self.unidad, self.actor, datos, verificar=True, archivo=self.archivo(codigo))

    def datos_ejecucion(self, plan, codigo='EJEC-QA', prevista='2026-07-01'):
        return dict(tipo='EJECUCION-INFRA', codigo=codigo, fecha=date(2026, 7, 2),
            titulo='Informe de mantenimiento realizado QA', descripcion='Trabajos finalizados y comprobación del resultado.',
            responsable=self.actor, detalle=dict(plan_id=plan.pk, fecha_programada=prevista,
                fecha_inicio='2026-07-01', fecha_fin='2026-07-02', resultado='Tomas reparadas y prueba funcional satisfactoria.'))

    def ejecucion(self, plan, codigo='EJEC-QA', **cambios):
        datos = self.datos_ejecucion(plan, codigo)
        datos.update(cambios)
        return registrar_evidencia(self.unidad, self.actor, datos, verificar=True, archivo=self.archivo(codigo))

    def lectura(self):
        return infraestructura_documentada(self.unidad, self.inicio, self.fin)

    def test_plan_anterior_y_calendario_futuro_se_separan_del_avance(self):
        plan = self.plan()
        lectura = self.lectura()
        self.assertEqual((lectura['programadas'], lectura['acreditadas'], len(lectura['futuras'])), (4, 0, 3))
        self.assertFalse(lectura['sin_plan'])
        self.assertEqual(lectura['ocurrencias'][0]['plan_id'], plan.pk)
        self.assertEqual(lectura['ocurrencias'][0]['criticidad'], 'critica')
        self.assertEqual(lectura['corte'], '2026-10-17')

    def test_ejecucion_respalda_una_ocurrencia_y_conserva_plan_y_ubicacion(self):
        plan = self.plan()
        ejecucion = self.ejecucion(plan)
        lectura = self.lectura()
        self.assertEqual((lectura['acreditadas'], lectura['cobertura']), (1, 25))
        self.assertEqual(lectura['ocurrencias'][0]['ejecucion_id'], ejecucion.pk)
        self.assertEqual(ejecucion.detalle['espacio_id'], self.espacio.pk)
        self.assertEqual(ejecucion.detalle['plan_codigo'], plan.codigo)
        self.assertEqual(len(ejecucion.detalle['plan_huella']), 64)
        self.assertEqual(len(ejecucion.detalle['plan_sha256']), 64)
        self.assertEqual(len(lectura['pendientes']), 3)

    def test_plan_y_ejecucion_exigen_archivo_legible_no_solo_enlace(self):
        datos = self.datos_plan()
        datos['enlace'] = 'https://example.org/plan-infra'
        with self.assertRaisesMessage(ValidationError, 'archivo'):
            registrar_evidencia(self.unidad, self.actor, datos, verificar=True)
        datos.pop('enlace')
        with self.assertRaisesMessage(ValidationError, 'legible'):
            registrar_evidencia(self.unidad, self.actor, datos, verificar=True,
                archivo=SimpleUploadedFile('invalido.pdf', b'%PDF-1.4 sin contenido real'))
        plan = self.plan()
        datos = self.datos_ejecucion(plan)
        datos['enlace'] = 'https://example.org/ejec-infra'
        with self.assertRaisesMessage(ValidationError, 'archivo'):
            registrar_evidencia(self.unidad, self.actor, datos, verificar=True)

    def test_rechaza_espacio_o_plan_de_otra_unidad_y_otra_tipologia(self):
        datos = self.datos_plan()
        with self.assertRaisesMessage(ValidationError, 'espacio'):
            registrar_evidencia(self.otra, self.actor, datos, verificar=True, archivo=self.archivo('AJENO'))
        plan = self.plan()
        with self.assertRaisesMessage(ValidationError, 'misma unidad'):
            registrar_evidencia(self.otra, self.actor, self.datos_ejecucion(plan), verificar=True,
                archivo=self.archivo('EJEC-AJENO'))
        with self.assertRaisesMessage(ValidationError, 'espacio'):
            registrar_evidencia(self.observatorio, self.actor, self.datos_plan(), verificar=False)
        self.assertTrue(infraestructura_documentada(self.observatorio, self.inicio, self.fin)['sin_plan'])
        self.assertEqual(len(acciones_infraestructura(self.observatorio, self.inicio, self.fin)), 2)

    def test_borrador_es_visible_pero_no_define_universo_verificado(self):
        registrar_evidencia(self.unidad, self.actor, self.datos_plan(), verificar=False)
        lectura = self.lectura()
        self.assertEqual((lectura['programadas'], lectura['planes_sin_verificar']), (0, 1))
        self.assertTrue(lectura['sin_plan'])
        self.assertEqual(len(lectura['pendientes']), 4)

    def test_no_duplica_cierre_de_misma_ocurrencia(self):
        plan = self.plan()
        self.ejecucion(plan)
        with self.assertRaisesMessage(ValidationError, 'ya tiene una ejecución'):
            self.ejecucion(plan, 'DUPLICADO-QA')
        self.assertEqual(self.lectura()['acreditadas'], 1)

    def test_rechaza_fecha_fuera_de_programa_y_ejecucion_futura_o_invertida(self):
        plan = self.plan()
        for cambios in [dict(fecha_programada='2026-07-05'), dict(fecha_inicio='2026-07-03'),
                        dict(fecha_fin='2026-07-03'), dict(plan_id=self.espacio.pk + 1000000)]:
            datos = self.datos_ejecucion(plan)
            datos['detalle'].update(cambios)
            with self.assertRaises(ValidationError):
                registrar_evidencia(self.unidad, self.actor, datos, verificar=True, archivo=self.archivo(str(cambios)))
        with self.assertRaisesMessage(ValidationError, 'futura'):
            self.ejecucion(plan, fecha=date(2026, 10, 18))

    def test_cambio_de_plan_o_archivo_invalida_el_cierre_sin_borrar_historial(self):
        plan = self.plan()
        self.ejecucion(plan)
        EvidenciaGestionUnidad.objects.filter(pk=plan.pk).update(descripcion='Plan sustituido fuera del flujo')
        self.assertEqual(self.lectura()['acreditadas'], 0)
        self.assertEqual(EvidenciaGestionUnidad.objects.filter(unidad=self.unidad).count(), 2)

    def test_rectificacion_conserva_historial_y_permite_cierre_nuevo(self):
        plan = self.plan()
        ejecucion = self.ejecucion(plan)
        rectificar_evidencia(self.unidad, self.actor, ejecucion.pk, 'Corregir informe de la intervención')
        self.assertEqual(self.lectura()['acreditadas'], 0)
        self.ejecucion(plan, 'SUSTITUCION-QA')
        lectura = self.lectura()
        self.assertEqual(lectura['acreditadas'], 1)
        self.assertEqual(len(lectura['ejecuciones']), 2)
        self.assertEqual(lectura['ejecuciones'][0]['estado_display'], 'Rectificado')

    def test_demostracion_no_acredita_y_no_puede_prestar_plan_a_datos_reales(self):
        with override_settings(MEDICION_SOLO_DEMO=True):
            plan = self.plan()
            self.ejecucion(plan)
        lectura = self.lectura()
        self.assertEqual((lectura['programadas'], lectura['acreditadas']), (0, 0))
        self.assertTrue(lectura['sin_plan'])
        datos = self.datos_ejecucion(plan, codigo='MEZCLA-QA', prevista='2026-07-31')
        with self.assertRaisesMessage(ValidationError, 'real o de demostración'):
            registrar_evidencia(self.unidad, self.actor, datos, verificar=True, archivo=self.archivo('MEZCLA-QA'))

    def test_plan_unico_sin_espacio_reservable_se_documenta_por_area(self):
        datos = self.datos_plan()
        datos['detalle'].update(espacio_id=None, ubicacion='Cubierta y canaletas', frecuencia_dias=0)
        self.plan(detalle=datos['detalle'])
        lectura = self.lectura()
        self.assertEqual(lectura['programadas'], 1)
        self.assertEqual(lectura['futuras'], [])

    def test_formulario_dinamico_guarda_plan_y_ejecucion_y_distingue_inspeccion(self):
        self.client.force_login(self.actor)
        ruta = reverse('fuentes_metas_unidad', args=[self.unidad.slug])
        datos = self.datos_plan()
        datos['fecha'] = '2026-07-01'
        post = dict(anio=2026, corte='B', verificar='on', responsable=self.actor.pk,
            archivo=self.archivo('FORM-PLAN'), **{k: v for k, v in datos.items() if k not in ('detalle', 'responsable')},
            **datos['detalle'])
        respuesta = self.client.post(ruta, post)
        self.assertEqual(respuesta.status_code, 302)
        plan = EvidenciaGestionUnidad.objects.get(codigo='PLAN-QA')
        post = self.datos_ejecucion(plan, codigo='FORM-EJEC')
        respuesta = self.client.post(ruta, dict(anio=2026, corte='B', verificar='on', responsable=self.actor.pk,
            archivo=self.archivo('FORM-EJEC'), **{k: v for k, v in post.items() if k not in ('detalle', 'responsable')},
            **post['detalle']))
        self.assertEqual(respuesta.status_code, 302)
        self.assertEqual(self.lectura()['acreditadas'], 1)
        respuesta = self.client.get(ruta, dict(anio=2026, corte='B', tipo='EJECUCION-INFRA'))
        self.assertContains(respuesta, 'Una inspección de condiciones no sustituye')
        self.assertContains(respuesta, 'Plan: PLAN-QA')
        self.assertNotContains(respuesta, 'name="condiciones_revisadas"')

    def test_ruta_permite_plan_de_infraestructura_en_observatorio(self):
        self.client.force_login(self.actor)
        ruta = reverse('fuentes_metas_unidad', args=[self.observatorio.slug])
        self.assertEqual(self.client.get(ruta, dict(tipo='PLAN-INFRA')).status_code, 200)

    def test_ambito_compartido_funciona_sin_modelo_para_pruebas_y_derivados(self):
        self.assertTrue(es_laboratorio_infraestructura(SimpleNamespace(dependencia='laboratorios')))
        self.assertTrue(es_laboratorio_infraestructura(SimpleNamespace(codigo_base='laboratorios', dependencia='derivada')))
        self.assertTrue(es_laboratorio_infraestructura(SimpleNamespace(codigo_base='observatorios', dependencia='observatorios')))
        self.assertFalse(es_laboratorio_infraestructura(SimpleNamespace(dependencia='sin_perfil_auditable')))

    def test_sin_plan_o_medicion_desactivada_no_se_inventa_cumplimiento(self):
        self.assertEqual(self.lectura()['programadas'], 0)
        self.assertTrue(self.lectura()['sin_plan'])
        self.plan()
        with override_settings(MEDICION_METAS_HABILITADA=False):
            self.assertEqual(self.lectura()['acreditadas'], 0)
            self.assertTrue(self.lectura()['sin_plan'])

    def test_plan_invalido_importado_no_rompe_la_lectura(self):
        datos = self.datos_plan()
        datos['detalle'] = dict(criticidad={'valor': 'critica'}, plan_id={'no': 'es id'})
        registrar_evidencia(self.unidad, self.actor, datos, verificar=False)
        lectura = self.lectura()
        self.assertEqual(lectura['programadas'], 0)
        self.assertEqual(lectura['planes_sin_verificar'], 1)

    def test_no_aplica_requiere_justificacion_archivo_y_conserva_fuente_de_alcance(self):
        detalle = dict(alcance_infraestructura='no_aplica', justificacion_alcance='')
        with self.assertRaisesMessage(ValidationError, 'Justifica'):
            self.plan(detalle=detalle)
        detalle['justificacion_alcance'] = 'Instalación arrendada mantenida por la administración central según acta QA.'
        declaracion = self.plan(detalle=detalle)
        lectura = self.lectura()
        self.assertTrue(lectura['alcance_declarado'])
        self.assertTrue(lectura['no_aplica'])
        self.assertFalse(lectura['sin_plan'])
        self.assertEqual(lectura['programadas'], 0)
        self.assertEqual(lectura['fuentes_alcance'][0]['pk'], declaracion.pk)
        self.assertEqual(len(lectura['fuentes_alcance'][0]['sha256']), 64)
        with self.assertRaisesMessage(ValidationError, 'plan de intervención aplicable'):
            self.ejecucion(declaracion)

    def test_no_aplica_no_oculta_cronograma_ya_declarado_y_es_anual(self):
        self.plan()
        detalle = dict(alcance_infraestructura='no_aplica', justificacion_alcance='Declaración contradictoria QA.')
        self.plan('NO-APLICA-QA', detalle=detalle)
        lectura = self.lectura()
        self.assertTrue(lectura['alcance_contradictorio'])
        self.assertFalse(lectura['alcance_declarado'])
        self.assertFalse(lectura['no_aplica'])
        self.assertEqual(lectura['programadas'], 4)
        # Una declaración de otro año no resuelve el alcance actual.
        EvidenciaGestionUnidad.objects.filter(tipo='PLAN-INFRA').delete()
        self.plan('ANIO-ANTERIOR-QA', fecha=date(2025, 12, 1), detalle=detalle)
        self.assertFalse(self.lectura()['alcance_declarado'])

    def test_no_aplica_con_intervencion_y_fecha_es_contradictorio(self):
        datos = self.datos_plan()
        datos['detalle'].update(alcance_infraestructura='no_aplica', justificacion_alcance='Motivo QA.')
        with self.assertRaisesMessage(ValidationError, 'contradictorios'):
            self.plan(detalle=datos['detalle'])

    def acta_criticidad_sin_equipos(self):
        return registrar_evidencia(self.unidad, self.actor, dict(tipo='INVENTARIO', codigo='ACTA-CRIT-QA',
            fecha=date(2026, 10, 17), titulo='Acta de revisión integral y criticidad QA',
            descripcion='Revisión física actual y clasificación del inventario, sin equipos críticos asignados.',
            responsable=self.actor, alcance=['equipos', 'software', 'espacios', 'insumos'],
            detalle={'revision_criticidad': True}), verificar=True, archivo=self.archivo('ACTA-CRIT-QA'))

    def test_medicion_integral_suma_ocurrencias_criticas_sin_contar_calendario_futuro(self):
        self.acta_criticidad_sin_equipos()
        plan = self.plan()
        self.ejecucion(plan)
        medicion = medir_mantenimiento_integral(self.unidad, self.inicio, self.fin)
        self.assertEqual((medicion['numerador'], medicion['denominador']), (1, 4))
        self.assertFalse(medicion['pendiente'])
        self.assertFalse(medicion['no_aplica_verificado'])
        self.assertEqual(medicion['programadas_futuras'], 3)
        self.assertTrue(medicion['equipos']['no_aplica_verificado'])
        self.assertEqual(medicion['infraestructura']['numerador'], 1)
        self.assertTrue(any(f.get('tipo') == 'EJECUCION-INFRA' for f in medicion['fuentes']))

    def test_medicion_integral_cero_revisado_es_no_aplicable_y_sin_fuentes_es_pendiente(self):
        medicion = medir_mantenimiento_integral(self.unidad, self.inicio, self.fin)
        self.assertTrue(medicion['pendiente'])
        self.assertFalse(medicion['no_aplica_verificado'])
        self.acta_criticidad_sin_equipos()
        self.plan(detalle=dict(alcance_infraestructura='no_aplica',
            justificacion_alcance='Instalación cubierta por la administración central, sin intervenciones propias según acta.'))
        medicion = medir_mantenimiento_integral(self.unidad, self.inicio, self.fin)
        self.assertEqual((medicion['numerador'], medicion['denominador']), (0, 0))
        self.assertTrue(medicion['no_aplica_verificado'])
        self.assertFalse(medicion['pendiente'])

    def test_plan_de_un_espacio_no_declara_universo_completo_si_faltan_otras_areas(self):
        otra_area = EspacioReservable.objects.create(unidad=self.unidad, codigo='INFRA-OTRA-QA',
            nombre='Otra área del laboratorio', capacidad=2)
        datos = self.datos_plan()
        datos['detalle']['alcance_todo_laboratorio'] = False
        self.plan(detalle=datos['detalle'])
        lectura = self.lectura()
        self.assertFalse(lectura['alcance_declarado'])
        self.assertEqual([e['pk'] for e in lectura['espacios_sin_cobertura']], [otra_area.pk])
        self.assertEqual(lectura['programadas'], 4)

    def test_alcance_global_congela_espacios_y_un_area_nueva_requiere_complementarlo(self):
        otra_area = EspacioReservable.objects.create(unidad=self.unidad, codigo='INFRA-OTRA-QA',
            nombre='Otra área del laboratorio', capacidad=2)
        plan = self.plan()
        self.assertTrue(self.lectura()['alcance_declarado'])
        self.assertEqual(plan.detalle['espacios_alcance'], [self.espacio.pk, otra_area.pk])
        nueva = EspacioReservable.objects.create(unidad=self.unidad, codigo='INFRA-NUEVA-QA',
            nombre='Área incorporada después del plan', capacidad=2)
        lectura = self.lectura()
        self.assertFalse(lectura['alcance_declarado'])
        self.assertEqual([e['pk'] for e in lectura['espacios_sin_cobertura']], [nueva.pk])

    def test_ubicacion_libre_sin_declaracion_global_no_confirma_todo_el_laboratorio(self):
        datos = self.datos_plan()
        datos['detalle'].update(espacio_id=None, ubicacion='Instalación de uso general', alcance_todo_laboratorio=False)
        self.plan(detalle=datos['detalle'])
        self.assertFalse(self.lectura()['alcance_declarado'])
        self.assertEqual([e['pk'] for e in self.lectura()['espacios_sin_cobertura']], [self.espacio.pk])

    def test_sql_no_convierte_demo_o_borrador_en_plan_real_verificado(self):
        with override_settings(MEDICION_SOLO_DEMO=True):
            demo = self.plan('DEMO-ALTERADO-QA')
        EvidenciaGestionUnidad.objects.filter(pk=demo.pk).update(demostracion=False)
        self.assertEqual(self.lectura()['programadas'], 0)
        self.assertFalse(self.lectura()['planes'][0]['verificada'])
        borrador = registrar_evidencia(self.unidad, self.actor,
            self.datos_plan('BORRADOR-ALTERADO-QA'), verificar=False, archivo=self.archivo('BORRADOR-ALTERADO-QA'))
        EvidenciaGestionUnidad.objects.filter(pk=borrador.pk).update(estado='validado',
            validado_por=self.actor, validado_en=timezone.now())
        self.assertEqual(self.lectura()['programadas'], 0)
        self.assertTrue(self.lectura()['sin_plan'])
