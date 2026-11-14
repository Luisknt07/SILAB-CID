"""Los mínimos propuestos son alcanzables y no rebajan compromisos firmados."""
from types import SimpleNamespace
from django.test import SimpleTestCase, TestCase
from django.core.exceptions import ValidationError
from apps.documentos.presentation.expediente_redaccion import ACTIVIDADES_PLAN, actividades_para
from apps.documentos.presentation.politica_metas_unidades import propuesta_del_semestre
from apps.documentos.presentation.metas_plan import obligatoria_por_tipo, meta_con_minimo
from apps.documentos.presentation.evaluacion_cierre import evaluar_meta


class PoliticaMetasUnidadesTests(SimpleTestCase):
    def actividades(self, base='laboratorios', **kwargs):
        return {a.codigo: a for a in actividades_para(SimpleNamespace(codigo_base=base), **kwargs)}

    def test_minimo_dos_practicas_permide_inicio_y_cero_no_se_acepta(self):
        practica = self.actividades()['PRACTICAS']
        self.assertEqual(meta_con_minimo(practica, '2'), '2')
        self.assertTrue(obligatoria_por_tipo(practica))
        for valor in ('0', '1', '1.5'):
            with self.subTest(valor=valor), self.assertRaises(ValidationError):
                meta_con_minimo(practica, valor)

    def test_sugerencias_diferentes_por_capacidad_sin_cambiar_minimo(self):
        practica = self.actividades()['PRACTICAS']
        for recomendadas in (2, 4, 6):
            self.assertEqual(propuesta_del_semestre({'practicas_recomendadas': recomendadas}, practica), str(recomendadas))
        self.assertEqual(meta_con_minimo(practica, '2'), '2')

    def test_plan_anterior_conserva_su_minimo_y_no_recibe_indicadores_nuevos(self):
        anterior = self.actividades(version=2)
        self.assertIn('6', anterior['PRACTICAS'].minimo)
        self.assertNotIn('DATOS-ACTUALIZADOS', self.actividades('observatorios', version=2))
        with self.assertRaises(ValidationError):
            meta_con_minimo(anterior['PRACTICAS'], '2')

    def test_investigacion_transferencia_y_demanda_no_imponen_cuotas_generales(self):
        for codigo in ('INVESTIGACION', 'TRANSFERENCIA', 'SERVICIOS'):
            self.assertFalse(obligatoria_por_tipo(self.actividades()[codigo]))

    def test_observatorio_pide_datos_y_publicaciones_sin_laboratorio(self):
        actividades = self.actividades('observatorios')
        for codigo in ('BOLETINES', 'DATOS-ACTUALIZADOS', 'EVENTOS'):
            self.assertTrue(obligatoria_por_tipo(actividades[codigo]))
        for codigo in ('PRACTICAS', 'PRACTICAS-PLAN', 'GUIAS', 'DESECHOS', 'SEGURIDAD', 'USO'):
            self.assertNotIn(codigo, actividades)

    def test_planta_y_centro_no_imponen_practicas_si_no_hay_docencia_programada(self):
        for base in ('plantas_piloto', 'centro_experimental'):
            self.assertFalse(obligatoria_por_tipo(self.actividades(base)['PRACTICAS']))
        self.assertTrue(obligatoria_por_tipo(self.actividades('plantas_piloto')['PRODUCCION']))
        self.assertTrue(obligatoria_por_tipo(self.actividades('centro_experimental')['ENSAYOS']))

    def test_guia_vigente_anterior_acredita_sin_actualizacion_artificial_cada_semestre(self):
        guia = self.actividades()['GUIAS']
        fila = dict(codigo=guia.codigo, nombre=guia.nombre, meta='1', contador=guia.contador,
                    politica_metas=3, aplica=True, obligatoria=True)
        lectura = evaluar_meta(fila, dict(guias_acreditables=1, guias_periodo_acreditables=0))
        self.assertEqual(lectura['porcentaje'], 100)
        fila['politica_metas'] = 2
        self.assertEqual(evaluar_meta(fila, dict(guias_acreditables=1, guias_periodo_acreditables=0))['porcentaje'], 0)

    def test_catalogo_base_se_conserva_para_informes_historicos(self):
        self.assertIn('6', next(a for a in ACTIVIDADES_PLAN if a.codigo == 'PRACTICAS').minimo)

    def test_anexo_sin_meta_en_el_perfil_no_inventa_una_obligacion(self):
        from apps.documentos.presentation.evaluacion_cierre import detalle_anexo
        from apps.documentos.templatetags.reportes_estilo import exigencia_estilo
        cierre = dict(politica_metas=3, catalogo=[])
        fila, = detalle_anexo('REGISTRO-USO', cierre)
        self.assertEqual(fila['estado'], 'Anexo automático')
        self.assertFalse(fila['exigible'])
        self.assertEqual(exigencia_estilo(fila), 'informativo')
        legado, = detalle_anexo('REGISTRO-USO', dict(catalogo=[]))
        self.assertEqual(legado['estado'], 'Sin definir en planificación')

    def test_sin_compromiso_programado_se_distingue_de_no_aplica(self):
        from apps.documentos.templatetags.reportes_estilo import exigencia_estilo
        self.assertEqual(exigencia_estilo(dict(exigencia='Según programación', aplica=False)),
                         'segun-programacion')


class PropuestaSegunProgramacionTests(TestCase):
    def test_el_administrador_activo_cuenta_como_personal_y_apertura_en_el_semestre_es_inicial(self):
        from datetime import date
        from django.contrib.auth import get_user_model
        from apps.directorio_unidades.models.core import Unidad
        from apps.documentos.presentation.politica_metas_unidades import capacidad_de
        actor = get_user_model().objects.create_user(username='qa-capacidad-responsable')
        unidad = Unidad.objects.create(nombre='Laboratorio de apertura QA', slug='qa-capacidad-apertura',
            dependencia='laboratorios', administrador=actor, fecha_inicio=date(2026, 9, 1))
        lectura = capacidad_de(unidad, date(2026, 8, 17))
        self.assertEqual(lectura['personal'], 1)
        self.assertTrue(lectura['apertura_reciente'])
        self.assertEqual(lectura['practicas_recomendadas'], 2)

    def test_ocho_practicas_en_un_mes_no_se_confunden_con_un_solo_mes(self):
        from datetime import date, time
        from django.contrib.auth import get_user_model
        from apps.directorio_unidades.models.core import Unidad
        from apps.formacion.models.practicas import PlanificacionPractica
        from apps.formacion.models.asignaturas import Asignatura, TemaAsignatura
        from apps.documentos.presentation.expediente_redaccion import plan_inicial
        actor = get_user_model().objects.create_user(username='qa-propuesta-semestral')
        unidad = Unidad.objects.create(nombre='Laboratorio programación QA', slug='qa-propuesta-semestral',
            dependencia='laboratorios', administrador=actor, fecha_inicio=date(2026, 8, 1))
        asignatura = Asignatura.objects.create(unidad=unidad, codigo='PROTOTIPADO', nombre='Prototipado')
        for dia in range(1, 9):
            tema = TemaAsignatura.objects.create(asignatura=asignatura, orden=dia, nombre=f'Práctica {dia}')
            PlanificacionPractica.objects.create(unidad=unidad, fecha=date(2026, 9, dia),
                tema_asignatura=tema,
                hora_inicio=time(8), hora_fin=time(9), creado_por=actor, estado='aprobada',
                asignatura='Prototipado', docente_tutor='Docente QA', tema=f'Práctica {dia}',
                resultado_aprendizaje='Construir y comprobar una pieza.')
        plan = plan_inicial(SimpleNamespace(unidad=unidad), date(2026, 8, 17), date(2026, 12, 8))
        for codigo in ('PRACTICAS', 'PRACTICAS-PLAN'):
            self.assertEqual(plan['catalogo'][codigo]['meta'], '8')
            self.assertEqual(plan['catalogo'][codigo]['meses'], [9])
        self.assertEqual(plan['minimos_catalogo'], 3)
        self.assertTrue(plan['capacidad']['requiere_revision'])
