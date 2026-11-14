"""Presupuesto de referencia, reparto comparable y conservación de escenarios."""
from copy import deepcopy
from decimal import Decimal
from io import BytesIO
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.core.exceptions import PermissionDenied, ValidationError
from django.test import TestCase
from openpyxl import load_workbook

from apps.directorio_unidades.models.core import DependenciaAcademica
from apps.documentos.models.asignacion import MarcoPresupuestoNecesidades, EscenarioAsignacionNecesidades
from apps.documentos.models.necesidades import RemisionNecesidades, huella_contenido
from apps.documentos.presentation.asignacion_necesidades import (
    comparar_demanda, excel_escenario, presupuesto_actual, registrar_escenario,
    registrar_presupuesto, verificar_captura,
)


class AsignacionNecesidadesTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        usuarios = get_user_model()
        cls.direccion = usuarios.objects.create_user('direccion-distribucion', is_superuser=True, is_staff=True)
        cls.decanato = usuarios.objects.create_user('decanato-distribucion', is_staff=True)
        cls.otro = usuarios.objects.create_user('otro-distribucion', is_staff=True)
        cls.gestor = usuarios.objects.create_user('gestor-distribucion')
        cls.dependencia = DependenciaAcademica.objects.create(nombre='Facultad de prueba de reparto', centro_costo='Centro de ingeniería')
        cls.dependencia.receptores.add(cls.decanato)
        cls.otra_dependencia = DependenciaAcademica.objects.create(nombre='Dependencia ajena de reparto', centro_costo='Centro ajeno')
        cls.otra_dependencia.receptores.add(cls.otro)

    def lectura(self):
        def unidad(pk, nombre, costo):
            return dict(id=pk, nombre=nombre, total=str(2 * costo), transferible=True,
                documento_id=pk, pac_datos={}, gestion_inversion=dict(estado='favorable',
                    label='Cumplimiento acreditado', fecha_referencia='2026-05-31'),
                necesidades=[dict(numero=1, id=f'necesidad-{pk}', area='Área de diseño',
                    item='Equipo de diseño', cantidad='2', costo_unitario=str(costo), total=str(2 * costo),
                    mes='Marzo', semestre=1, grupo_fases='Habilitación del área', fase_numero='1',
                    resultado_fase='Ejecutar las prácticas programadas')])
        return dict(anio_preparacion=2026, anio_ejecucion=2027,
            resumen=dict(total='400', unidades_total=2, evaluadas=2),
            unidades=[unidad(301, 'Unidad uno', Decimal('100')), unidad(302, 'Unidad dos', Decimal('100'))])

    def remision(self, lectura=None, dependencia=None):
        dependencia = dependencia or self.dependencia
        lectura = deepcopy(lectura or self.lectura())
        registro, _ = RemisionNecesidades.objects.get_or_create(dependencia=dependencia,
            anio_preparacion=2026, sha256=huella_contenido(lectura), defaults=dict(
                dependencia_nombre=dependencia.nombre, anio_ejecucion=2027, remitido_por=self.direccion,
                destinatarios=[dict(id=self.decanato.pk, nombre='Decanato')], contenido=lectura))
        return registro

    def presupuesto(self, *, disponible='400', concentracion=None, dependencia=None, usuario=None, referencia='Oficio de presupuesto aprobado'):
        return registrar_presupuesto(dependencia or self.dependencia, 2027, usuario or self.direccion,
            disponible=disponible, referencia=referencia, concentracion=concentracion)

    def escenario(self, remision=None, presupuesto=None, cantidades=None, *, revision=None, usuario=None,
                  distribucion='Atender la fase inicial de ambas unidades y conservar saldo.', excepcion=''):
        with patch('apps.documentos.presentation.asignacion_necesidades._revision_actual',
            return_value=revision or dict(estado='favorable', label='Cumplimiento acreditado', fecha_referencia='2026-10-20')):
            return registrar_escenario(remision or self.remision(), presupuesto or self.presupuesto(),
                usuario or self.direccion, cantidades if cantidades is not None else {'301:1': '1', '302:1': '1'},
                distribucion=distribucion, excepcion=excepcion)

    def test_presupuesto_es_explicito_idempotente_y_revisiones_no_sobrescriben(self):
        self.assertIsNone(presupuesto_actual(self.dependencia, 2027))
        primero = self.presupuesto(disponible='300', concentracion='60')
        igual = self.presupuesto(disponible='300', concentracion='60')
        siguiente = self.presupuesto(disponible='350', concentracion='65')
        self.assertEqual(primero.pk, igual.pk)
        self.assertNotEqual(siguiente.pk, primero.pk)
        self.assertEqual(presupuesto_actual(self.dependencia, 2027).pk, siguiente.pk)
        primero.refresh_from_db()
        self.assertEqual(primero.contenido['disponible'], '300')
        self.assertEqual(primero.contenido['porcentaje_maximo_unidad'], '60')

    def test_no_admite_cifras_negativas_no_finitas_ni_fuentes_vacias(self):
        for valor in ('-1', 'nan', 'inf', True, '1.001', '1e1000'):
            with self.subTest(valor=valor), self.assertRaises(ValidationError):
                self.presupuesto(disponible=valor)
        for valor in ('0', '-1', '101', 'nan'):
            with self.subTest(tope=valor), self.assertRaises(ValidationError):
                self.presupuesto(concentracion=valor)
        for referencia in ('<p> </p>', '<p>&nbsp;</p>'):
            with self.assertRaisesMessage(ValidationError, 'fuente del presupuesto'):
                self.presupuesto(referencia=referencia)
        self.assertEqual(MarcoPresupuestoNecesidades.objects.count(), 0)

    def test_permisos_recargan_actor_receptor_y_dependencia_vigentes(self):
        self.presupuesto(usuario=self.decanato)
        for usuario in (self.gestor, self.otro):
            with self.subTest(usuario=usuario.pk), self.assertRaises(PermissionDenied):
                self.presupuesto(usuario=usuario)
        self.dependencia.receptores.remove(self.decanato)
        with self.assertRaises(PermissionDenied):
            self.presupuesto(usuario=self.decanato)
        DependenciaAcademica.objects.filter(pk=self.dependencia.pk).update(activa=False)
        with self.assertRaises(PermissionDenied):
            self.presupuesto()  # La instancia anterior seguía marcada activa.

    def test_escenario_no_cambia_demanda_asignacion_no_ejecuta_compras_y_conserva_saldo(self):
        remision, presupuesto = self.remision(), self.presupuesto(disponible='300')
        original = deepcopy(remision.contenido)
        escenario = self.escenario(remision, presupuesto)
        self.assertEqual(escenario.contenido['total'], '200.00')
        self.assertEqual(escenario.contenido['saldo'], '100.00')
        self.assertEqual(len(escenario.contenido['filas']), 2)
        self.assertEqual([u['porcentaje_reparto'] for u in escenario.contenido['unidades']], ['50.00', '50.00'])
        self.assertEqual([u['porcentaje_presupuesto'] for u in escenario.contenido['unidades']], ['33.33', '33.33'])
        self.assertIn('No adjudica', escenario.contenido['alcance'])
        remision.refresh_from_db()
        presupuesto.refresh_from_db()
        self.assertEqual(remision.contenido, original)
        self.assertEqual(presupuesto.contenido['disponible'], '300')

    def test_propuesta_nueva_redondea_medios_centavos_como_la_demanda_y_no_oculta_exceso(self):
        lectura = self.lectura()
        lectura['resumen']['total'] = '.02'
        for unidad in lectura['unidades']:
            unidad.update(total='.01', compras_resumen_version=1)
            unidad['pac_datos']['compras_resumen_version'] = 1
            unidad['necesidades'][0].update(cantidad='1', costo_unitario='.005', total='.01',
                                          compras_resumen_version=1)
        remision = self.remision(lectura)
        presupuesto = self.presupuesto(disponible='.02')
        escenario = self.escenario(remision, presupuesto)
        self.assertEqual(escenario.contenido['total'], '0.02')
        self.assertEqual(escenario.contenido['saldo'], '0.00')
        self.assertEqual([fila['importe_propuesto'] for fila in escenario.contenido['filas']], ['0.01', '0.01'])
        self.assertEqual([Decimal(u['solicitado']) for u in escenario.contenido['unidades']],
                         [Decimal('.01'), Decimal('.01')])
        libro = load_workbook(BytesIO(excel_escenario(escenario)))
        self.addCleanup(libro.close)
        totales = [fila for fila in libro['DISTRIBUCION'].values if fila[0] == 'Total propuesto']
        self.assertEqual(totales[0][2], .02)
        with self.assertRaisesMessage(ValidationError, 'supera el presupuesto'):
            self.escenario(remision, self.presupuesto(disponible='.01'), excepcion='No puede autorizar un excedente.')

    def test_cantidades_y_fuentes_se_toman_de_remision_y_no_se_pueden_aumentar(self):
        remision, presupuesto = self.remision(), self.presupuesto()
        for cantidades, mensaje in (({'301:1': '3'}, 'superar la cantidad'),
                                     ({'301:1': '-1'}, 'no negativo'),
                                     ({'999:1': '1'}, 'ajenas'),
                                     ({'301:1': 'nan'}, 'no negativo'),
                                     ({'301:1': '0', '302:1': '0'}, 'al menos')):
            with self.subTest(cantidades=cantidades), self.assertRaisesMessage(ValidationError, mensaje):
                self.escenario(remision, presupuesto, cantidades)
        self.assertEqual(EscenarioAsignacionNecesidades.objects.count(), 0)

    def test_no_puede_superar_presupuesto_ni_con_justificacion(self):
        with self.assertRaisesMessage(ValidationError, 'supera el presupuesto'):
            self.escenario(presupuesto=self.presupuesto(disponible='150'),
                excepcion='Se solicita a pesar del déficit')
        self.assertEqual(EscenarioAsignacionNecesidades.objects.count(), 0)

    def test_concentracion_y_necesidades_favorables_sin_cobertura_requieren_motivo(self):
        presupuesto = self.presupuesto(disponible='200', concentracion='40')
        remision = self.remision()
        with self.assertRaisesMessage(ValidationError, 'supera el máximo institucional'):
            self.escenario(remision, presupuesto, {'301:1': '1', '302:1': '1'})
        with self.assertRaisesMessage(ValidationError, 'sin cobertura'):
            self.escenario(remision, presupuesto, {'301:1': '1'})
        with self.assertRaisesMessage(ValidationError, 'Justifica las condiciones'):
            self.escenario(remision, presupuesto, {'301:1': '1'}, excepcion='&nbsp;')
        escenario = self.escenario(remision, presupuesto, {'301:1': '1'},
            excepcion='La primera fase resuelve una limitación documentada; la otra unidad se atiende en la siguiente revisión.')
        self.assertEqual(len(escenario.contenido['advertencias']), 2)
        self.assertTrue(escenario.contenido['excepcion'])
        self.assertEqual(escenario.contenido['total'], '100.00')

    def test_prioridad_condicionada_necesita_motivo_y_no_pierde_evidencia_de_envio(self):
        revision = dict(estado='condicionada_mejora', label='Compromiso de mejora pendiente', fecha_referencia='2026-10-20')
        with self.assertRaisesMessage(ValidationError, 'condicionada a revisión'):
            self.escenario(revision=revision)
        escenario = self.escenario(revision=revision,
            excepcion='Se plantea reparar recursos esenciales con seguimiento de los compromisos de aprovechamiento.')
        for unidad in escenario.contenido['unidades']:
            self.assertEqual(unidad['revision_actual']['estado'], 'condicionada_mejora')
            self.assertEqual(unidad['evidencia_envio']['estado'], 'favorable')
        self.assertEqual(escenario.contenido['marco']['disponible'], '400')

    def test_referencia_sustituida_o_de_otro_centro_no_se_utiliza(self):
        presupuesto = self.presupuesto(disponible='300')
        self.presupuesto(disponible='350')
        with self.assertRaisesMessage(ValidationError, 'Cambió la referencia'):
            self.escenario(presupuesto=presupuesto)
        ajeno = self.presupuesto(dependencia=self.otra_dependencia)
        with self.assertRaisesMessage(ValidationError, 'misma dependencia'):
            self.escenario(presupuesto=ajeno)

    def test_recarga_las_fuentes_archivadas_ignora_mutaciones_locales_con_hash_recalculado(self):
        remision, presupuesto = self.remision(), self.presupuesto(disponible='300')
        remision.contenido['unidades'][0]['necesidades'][0]['cantidad'] = '1000'
        remision.sha256 = huella_contenido(remision.contenido)
        presupuesto.contenido['disponible'] = '1000000'
        presupuesto.sha256 = huella_contenido(presupuesto.contenido)
        with self.assertRaisesMessage(ValidationError, 'superar la cantidad'):
            self.escenario(remision, presupuesto, {'301:1': '3'})
        escenario = self.escenario(remision, presupuesto)
        self.assertEqual(escenario.contenido['marco']['disponible'], '300')
        self.assertEqual(escenario.contenido['filas'][0]['cantidad'], '2')

    def test_antecedentes_no_admiten_edicion_borrado_ni_reescritura_masiva(self):
        presupuesto, escenario = self.presupuesto(), self.escenario()
        for registro in (presupuesto, escenario):
            modelo = type(registro)
            for operacion in (lambda: registro.save(), lambda: registro.delete(),
                              lambda: modelo.objects.filter(pk=registro.pk).update(sha256='x' * 64),
                              lambda: modelo.objects.filter(pk=registro.pk).delete(),
                              lambda: modelo.objects.bulk_update([registro], ['contenido'])):
                with self.assertRaises(ValidationError):
                    operacion()
            registro.contenido['campo_inyectado'] = True
            with self.assertRaisesMessage(ValidationError, 'integridad'):
                verificar_captura(registro)

    def test_excel_conserva_programacion_fases_y_textos_no_se_convierten_en_formulas(self):
        lectura = self.lectura()
        lectura['unidades'][0]['nombre'] = '=1+1'
        escenario = self.escenario(remision=self.remision(lectura), distribucion='=NO_EJECUTAR()')
        libro = load_workbook(BytesIO(excel_escenario(escenario)), data_only=False)
        try:
            self.assertEqual(libro.sheetnames, ['DISTRIBUCION', 'NECESIDADES PROPUESTAS'])
            self.assertEqual(libro['DISTRIBUCION']['A2'].value, '=1+1')
            self.assertEqual(libro['DISTRIBUCION']['A2'].data_type, 's')
            self.assertEqual(libro['NECESIDADES PROPUESTAS']['H2'].value, 'Marzo')
            self.assertEqual(libro['NECESIDADES PROPUESTAS']['J2'].value, 'Habilitación del área')
            self.assertFalse(any(c.data_type == 'f' for h in libro for fila in h for c in fila))
        finally:
            libro.close()

    def test_demanda_incompleta_sigue_pendiente_y_no_se_presenta_como_cero(self):
        lectura = self.lectura()
        lectura['resumen']['total'] = None
        lectura['unidades'].append(dict(id=303, nombre='Unidad sin declaración', total=None,
            transferible=False, necesidades=[]))
        comparacion = comparar_demanda(lectura, self.presupuesto())
        self.assertIsNone(comparacion['saldo_si_cubre_todo'])
        self.assertIsNone(comparacion['unidades'][-1]['solicitado'])
        self.assertTrue(comparacion['unidades'][-1]['pendiente'])
        self.assertEqual(comparacion['unidades'][-1]['estado'], 'sin_evidencia')
