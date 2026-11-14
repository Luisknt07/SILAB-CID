"""Necesidades anuales y cobertura semestral de recursos, sin doble captura.

Las necesidades del año N+1 se presentan en mayo del año N. El semestre
revisa la cobertura y la ejecución registrada; las redacciones anteriores
conservan sus previsiones como antecedentes documentales.
"""

from datetime import date
from decimal import Decimal
from copy import deepcopy

from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.test import TestCase
from django.urls import reverse

from apps.documentos.presentation.expediente import construir_expediente, cortes_del_anio, tramo_del_documento
from apps.documentos.presentation.expediente_catalogo import asegurar_catalogo
from apps.documentos.presentation.expediente_redaccion import avance, componer, obtener_redaccion, pdf_del_documento
from apps.documentos.presentation.recursos_periodo import preparar_recursos
from apps.finanzas.presentation.presupuesto import sugerencias_de_compra
from apps.recursos.models.consumibles import Consumible
from apps.documentos.models.expediente import DocumentoElaborado, DocumentoExigido, DocumentoExpediente
from apps.recursos.models.equipos import EquiposServicios
from apps.directorio_unidades.models.core import Unidad
from apps.recursos.models.unidades import UnidadEquipo
from tests.integration.utiles import identificar


class BaseDePresupuesto(TestCase):
    @classmethod
    def setUpTestData(cls):
        asegurar_catalogo()
        cls.coordinador = get_user_model().objects.create_user(
            'coordinador-presupuesto', password='clave-segura', first_name='Ana', last_name='Coordinadora')
        identificar(cls.coordinador, tipo_usuario='administrativo', carrera='')
        cls.unidad = Unidad.objects.create(
            nombre='Laboratorio de presupuesto', slug='laboratorio-presupuesto', dependencia='laboratorios',
            descripcion='Unidad de prueba.', fecha_inicio=date(2024, 1, 1), administrador=cls.coordinador,
            activo=True)

    def documento(self, codigo, corte=''):
        construir_expediente(self.unidad, 2026, date(2026, 9, 22))
        return DocumentoExpediente.objects.get(unidad=self.unidad, exigido__codigo=codigo, anio=2026, corte=corte)


class SugerenciasDeCompraTests(BaseDePresupuesto):
    def equipo(self, nombre, **campos):
        base = EquiposServicios.objects.create(codigo='TIPO-' + nombre[:8].upper().replace(' ', '-'), nombre=nombre)
        return UnidadEquipo.objects.create(equipo=base, laboratorio=self.unidad, codigo_unidad=f'EQ-{nombre[:6]}',
                                           **campos)

    def test_ve_la_vida_util_cumplida_las_bajas_sin_reemplazo_y_los_insumos_agotados(self):
        self.equipo('Torno viejo', fecha_adquisicion=date(2015, 3, 1), vida_util_anios=8, criticidad='critico',
                    valor_referencial=Decimal('12000'))
        self.equipo('Impresora al día', fecha_adquisicion=date(2025, 3, 1), vida_util_anios=8)
        self.equipo('Osciloscopio', fecha_adquisicion=date(2019, 11, 1), vida_util_anios=7)  # vence 11/2026
        self.equipo('Sierra dada de baja', fecha_baja=date(2026, 2, 1), motivo_baja='dano_irreparable',
                    observacion_baja='Diagnóstico técnico y retiro operativo documentado, pendiente de reposición.', activa=False)
        Consumible.objects.create(codigo='INS-PLA', unidad=self.unidad, nombre='Filamento PLA', stock_total=0,
                                  minimo=2, activo=True)

        sugerencias = sugerencias_de_compra(self.unidad, hoy=date(2026, 9, 22))

        items = {s['item'].split(' (')[0]: s for s in sugerencias}
        self.assertIn('Torno viejo', items)
        self.assertEqual(items['Torno viejo']['prioridad'], 'alta')
        self.assertIn('vida útil', items['Torno viejo']['motivo'])
        self.assertIn('Osciloscopio', items)
        self.assertIn('termina el', items['Osciloscopio']['motivo'])
        self.assertIn('Sierra dada de baja', items)
        self.assertIn('sin reemplazo', items['Sierra dada de baja']['motivo'])
        self.assertIn('Filamento PLA', items)
        self.assertEqual(items['Filamento PLA']['categoria'], 'insumos')
        self.assertNotIn('Impresora al día', items)
        # Lo urgente primero.
        self.assertEqual(sugerencias[0]['prioridad'], 'alta')


class PlanAnualDeComprasTests(BaseDePresupuesto):
    def test_se_presenta_en_mayo_para_el_anio_siguiente_y_cuenta_como_obligatorio(self):
        exigido = DocumentoExigido.objects.get(codigo='PLAN-COMPRAS-ANUAL')
        self.assertEqual((exigido.periodicidad, exigido.plazo_regla, exigido.abre_mes, exigido.vence_mes),
                         ('anual', 'meses', 5, 5))
        self.assertTrue(exigido.requiere_firma and exigido.redactable)

        plan = self.documento('PLAN-COMPRAS-ANUAL')

        self.assertEqual((plan.abre_el, plan.vence_el), (date(2026, 5, 1), date(2026, 5, 31)))
        self.assertEqual(plan.etiqueta_corte, 'Año 2026')
        self.assertEqual(plan.etiqueta_gestion, 'Necesidades 2027 · preparación 2026')
        self.assertTrue(plan.exigible)
        self.assertEqual(plan.semaforo(date(2026, 4, 10)), 'no_abierto')
        self.assertEqual(plan.semaforo(date(2026, 5, 10)), 'a_tiempo')
        self.assertEqual(plan.semaforo(date(2026, 6, 10)), 'vencido')
        self.assertEqual(plan.semaforo(date(2026, 9, 22)), 'vencido')

    def test_el_expediente_lo_muestra_en_la_carpeta_del_anio(self):
        self.client.force_login(self.coordinador)
        pagina = self.client.get(reverse('gestion_expediente_unidad', args=[self.unidad.slug]), {'anio': 2026})

        self.assertContains(pagina, 'Documentos administrativos del año 2026')
        self.assertEqual([d.exigido.codigo for d in pagina.context['del_anio']], ['PLAN-COMPRAS-ANUAL'])
        self.assertContains(pagina, 'Plan anual de compras y presupuesto para el año siguiente')

    def test_el_editor_trae_las_sugerencias_y_exige_compras_o_justificacion(self):
        UnidadEquipo.objects.create(equipo=EquiposServicios.objects.create(codigo='TIPO-FRES', nombre='Fresadora antigua'), laboratorio=self.unidad,
                                    codigo_unidad='EQ-FRE', fecha_adquisicion=date(2012, 1, 1), vida_util_anios=10,
                                    estado_unidad='obsoleto')
        plan = self.documento('PLAN-COMPRAS-ANUAL')
        redaccion = obtener_redaccion(plan)

        progreso = avance('compras', redaccion.contenido)
        self.assertIn('compras', [c.clave for _s, c in progreso['faltantes']])

        redaccion.contenido = {**redaccion.contenido,
                               'sin_compras_justificacion': '<p>El inventario cubre las actividades de 2027.</p>',
                               'capacidad': '<p>Sin cambios de capacidad.</p>',
                               'firma_nombre': 'Ana', 'firma_cargo': 'Coordinadora'}
        redaccion.save()
        progreso = avance('compras', redaccion.contenido)
        self.assertEqual(progreso['porcentaje'], 100)

        inicio, fin = tramo_del_documento(plan)
        compuesto = componer(plan, redaccion.contenido, inicio, fin)
        estado = next(s for s in compuesto['secciones'] if s['codigo'] == 'estado_equipos')
        self.assertIn('Fresadora antigua', str(estado['bloques']))
        self.assertIn('Obsoleto', str(estado['bloques']))
        self.assertEqual([s['codigo'] for s in compuesto['secciones']][:3],
                         ['general', 'estado_equipos', 'compras'])
        general = next(s for s in compuesto['secciones'] if s['codigo'] == 'general')
        self.assertIn(('Año de las compras', '2027'), general['bloques'][0]['pares'])
        self.client.force_login(self.coordinador)
        editor = self.client.get(reverse('redactar_documento_expediente', args=[self.unidad.slug, plan.pk]))
        self.assertEqual(editor.status_code, 200)
        self.assertContains(editor, 'Propuestas por área')
        self.assertContains(editor, 'Año planificado 2027')
        self.assertEqual(editor.context['tabla_compras'], 'compras')
        self.assertEqual(editor.context['sugerencias_compra'][0]['equipo_id'], UnidadEquipo.objects.get(codigo_unidad='EQ-FRE').pk)


class PresupuestoDelPeriodoTests(BaseDePresupuesto):
    def test_fila_inicial_vacia_no_completa_el_presupuesto_y_exige_una_decision(self):
        from tests.integration.test_expediente_redaccion import PLAN_COMPLETO
        from apps.documentos.presentation.expediente_redaccion import faltantes_del_editor
        contenido = deepcopy(PLAN_COMPLETO)
        contenido['inversion'] = [dict(categoria='equipos', item='', cantidad='', fuente='')]
        progreso = avance('planificacion', contenido)
        self.assertLess(progreso['porcentaje'], 100)
        self.assertFalse(progreso['secciones']['inversion'])
        self.assertIn('inversion', [c.clave for _, c in progreso['faltantes']])
        self.assertTrue(any('justifica por qué' in detalle for detalle in faltantes_del_editor(progreso)))
        contenido['sin_inversion_justificacion'] = '<p>Los recursos disponibles cubren las actividades previstas.</p>'
        self.assertEqual(avance('planificacion', contenido)['porcentaje'], 100)

    def test_editor_revisa_cobertura_y_conserva_el_presupuesto_anterior_sin_recapturarlo(self):
        from tests.integration.test_expediente_redaccion import PLAN_COMPLETO
        plan = self.documento('PLANIFICACION', corte='A')
        redaccion = obtener_redaccion(plan)
        contenido = deepcopy(PLAN_COMPLETO)
        contenido['inversion'] = [dict(categoria='equipos', item='Equipo para prácticas')]
        redaccion.contenido = contenido
        redaccion.save()
        self.client.force_login(self.coordinador)
        ruta = reverse('redactar_documento_expediente', args=[self.unidad.slug, plan.pk])
        respuesta = self.client.get(ruta)
        self.assertContains(respuesta, 'Recursos disponibles y cobertura de las actividades')
        self.assertContains(respuesta, 'Revisión de los recursos del semestre')
        self.assertContains(respuesta, 'Equipo para prácticas')
        self.assertContains(respuesta, 'Antecedente de la redacción anterior')
        self.assertNotContains(respuesta, 'name="inversion__item"')
        self.assertNotContains(respuesta, 'name="inversion__cantidad"')
        self.assertNotContains(respuesta, 'Presupuesto del período, ítem 1: completa cantidad')
        self.assertLess(respuesta.context['progreso']['porcentaje'], 100)
        boton = respuesta.content.decode().split('data-generar', 1)[1].split('>', 1)[0]
        self.assertIn('disabled', boton)

    def test_el_esquema_legado_conserva_su_presupuesto_y_la_rendicion_anterior(self):
        from tests.integration.test_expediente_redaccion import PLAN_COMPLETO

        plan = self.documento('PLANIFICACION', corte='A')
        redaccion = obtener_redaccion(plan)
        redaccion.contenido = deepcopy(PLAN_COMPLETO)
        redaccion.contenido['inversion'] = []
        progreso = avance('planificacion', redaccion.contenido)
        self.assertIn('inversion', [c.clave for _s, c in progreso['faltantes']])

        redaccion.contenido = {**redaccion.contenido, 'inversion': [
            {'categoria': 'equipos', 'item': 'Impresora 3D de resina', 'cantidad': '1', 'justificacion': 'Prácticas',
             'prioridad': 'alta', 'costo_unitario': '3500', 'fuente': 'institucional'}]}
        redaccion.save()
        progreso = avance('planificacion', redaccion.contenido)
        self.assertNotIn('inversion', [c.clave for _s, c in progreso['faltantes']])

        inicio, fin = cortes_del_anio(2026)['A']
        compuesto = componer(plan, redaccion.contenido, inicio, fin)
        inversion = next(s for s in compuesto['secciones'] if s['codigo'] == 'inversion')
        self.assertEqual(inversion['bloques'][0]['titulo'], 'Lo que el sistema sugiere')
        tabla = next(b for b in inversion['bloques'] if b.get('titulo') == 'Presupuesto del período')
        self.assertEqual(tabla['filas'][-1][-1], '3,500.00')

        informe = self.documento('INFORME-SEMESTRAL', corte='A')
        compuesto = componer(informe, obtener_redaccion(informe).contenido, inicio, fin)
        presupuesto = next(s for s in compuesto['secciones'] if s['codigo'] == 'presupuesto')
        self.assertEqual(presupuesto['bloques'][0]['titulo'], 'Actividades previstas en la planificación')
        self.assertIn('Impresora 3D de resina', str(presupuesto['bloques'][0]['filas']))
        self.assertIn('3,500.00', str(presupuesto['bloques'][0]['filas'][-1]))

    def test_editor_semestral_no_incorpora_otra_solicitud_de_compras_y_exige_revision_antes_del_pdf(self):
        from tests.integration.test_expediente_redaccion import PLAN_COMPLETO

        UnidadEquipo.objects.create(equipo=EquiposServicios.objects.create(codigo='TIPO-REC-SEM',
            nombre='Equipo con necesidad de reposición'), laboratorio=self.unidad, codigo_unidad='REC-SEM-01',
            fecha_adquisicion=date(2012, 1, 1), vida_util_anios=10)
        plan = self.documento('PLANIFICACION', corte='A')
        redaccion = obtener_redaccion(plan)
        redaccion.contenido = preparar_recursos(deepcopy(PLAN_COMPLETO))
        redaccion.version = 1
        redaccion.save()
        self.client.force_login(self.coordinador)
        editor = self.client.get(reverse('redactar_documento_expediente', args=[self.unidad.slug, plan.pk]))
        self.assertEqual(editor.status_code, 200)
        self.assertEqual(editor.context['sugerencias_compra'], [])
        self.assertEqual(editor.context['tabla_compras'], '')
        self.assertNotContains(editor, 'data-sugerencia-compra=')
        self.assertNotContains(editor, 'name="inversion__item"')
        self.assertContains(editor, 'name="revision_recursos"')
        with self.assertRaisesMessage(ValidationError, 'Revisión de los recursos del semestre'):
            pdf_del_documento(plan, redaccion, *tramo_del_documento(plan))

    def test_informe_del_nuevo_esquema_consulta_necesidades_del_ano_de_ejecucion_sin_repetir_la_solicitud(self):
        from tests.integration.test_expediente_redaccion import PLAN_COMPLETO

        plan = self.documento('PLANIFICACION', corte='A')
        redaccion = obtener_redaccion(plan)
        redaccion.contenido = preparar_recursos(deepcopy(PLAN_COMPLETO))
        redaccion.contenido['revision_recursos'] = 'revisado'
        redaccion.version = 1
        redaccion.save()
        anual = self.documento('PLAN-COMPRAS-ANUAL')
        anterior = DocumentoExpediente.objects.create(unidad=self.unidad, exigido=anual.exigido, anio=2025)
        compra = dict(categoria='equipos', item='Recurso solicitado para ejecutar en 2026', cantidad='1',
            justificacion='Actividades previstas', prioridad='alta', costo_unitario='100',
            fuente='institucional', trimestre='1')
        DocumentoElaborado.objects.create(documento=anterior, contenido=dict(compras=[compra]), version=1)
        DocumentoElaborado.objects.create(documento=anual,
            contenido=dict(compras=[dict(compra, item='Necesidad futura para ejecutar en 2027')]), version=1)
        informe = self.documento('INFORME-SEMESTRAL', corte='A')
        compuesto = componer(informe, obtener_redaccion(informe).contenido, *tramo_del_documento(informe))
        recursos = next(s for s in compuesto['secciones'] if s['codigo'] == 'presupuesto')
        texto = str(recursos['bloques'])
        self.assertIn('Recurso solicitado para ejecutar en 2026', texto)
        self.assertNotIn('Necesidad futura para ejecutar en 2027', texto)
        self.assertNotIn('Presupuesto del período', texto)
        self.assertIn('Egresos confirmados registrados en el semestre', texto)
