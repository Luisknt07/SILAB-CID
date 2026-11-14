"""Cumplimiento proporcional, borrador vivo y evidencias inmutables de la entrega."""
from unittest.mock import patch

from django.core.exceptions import ValidationError
from django.core.files.base import ContentFile
from django.db import connection
from django.test import SimpleTestCase
from django.test.utils import CaptureQueriesContext
from django.urls import reverse

from apps.documentos.presentation.evaluacion_cierre import (
    calcular_cierre, cierre_archivado, confirmar_cierre, lectura_cierre, medir_meta,
)
from apps.documentos.presentation.expediente import anexos_del, validar_documento
from apps.documentos.models.expediente import DocumentoElaborado
from apps.recursos.models.recursos import Recurso
from tests.integration.test_direccion_recibe_y_califica import BaseDelExpediente, ANIO
from tests.integration.utiles import (
    contenido_plan_completo, correspondencia_revisada, pdf_legible_prueba, recibir_documento_revisado,
)


class MetasProporcionalesTests(SimpleTestCase):
    def test_avance_cero_parcial_completo_y_superado(self):
        for realizado, esperado, excedente in [(0, 0, 0), (3, 50, 0), (6, 100, 0), (9, 100, 3)]:
            fila = medir_meta(dict(codigo='PRACTICAS', nombre='Prácticas', contador='practicas',
                                   meta='≥ 6 por período', registrado=realizado), {})
            self.assertEqual((fila['porcentaje'], fila['excedente']), (esperado, excedente))

    def test_porcentajes_sin_denominador_y_meta_cero_no_acreditan_cumplimiento(self):
        for meta in ['100 %', '0', 'según demanda', 'entre 3 y 8']:
            fila = medir_meta(dict(codigo='USO', nombre='Uso', contador='sesiones', meta=meta, registrado=50), {})
            self.assertTrue(fila['pendiente'])
            self.assertEqual(fila['porcentaje'], 0)

    def test_mantenimiento_mide_solo_lo_programado_en_equipos_criticos(self):
        fila = medir_meta(dict(codigo='MANTENIMIENTO', nombre='Mantenimiento', meta='≥ 80 % de lo programado',
                               registrado=20), dict(mantenimientos_criticos_programados=10,
                                                   mantenimientos_criticos_cumplidos=4))
        self.assertEqual(fila['porcentaje'], 50)
        self.assertEqual(fila['registrado'], 4)

    def test_generar_inventario_no_se_autocertifica_y_reservas_pendientes_no_suman_uso(self):
        fila = dict(codigo='INVENTARIO', nombre='Inventario', contador='inventarios', meta='1', registrado=1)
        self.assertEqual(medir_meta(fila, {})['porcentaje'], 0)
        fila.update(codigo='USO', nombre='Uso', contador='sesiones', meta='10', registrado=100)
        self.assertEqual(medir_meta(fila, dict(atendidas=3))['porcentaje'], 30)

    def test_mediciones_no_finitas_o_negativas_no_causan_error_ni_acreditan_cien(self):
        fila = dict(codigo='CAPACITACION', nombre='Capacitación', contador='actividades', meta='1')
        for valor in ('NaN', 'Infinity', '-Infinity', '-1', 'dato incorrecto'):
            with self.subTest(valor=valor):
                lectura = medir_meta(dict(fila, registrado=valor), {})
                self.assertTrue(lectura['pendiente'])
                self.assertEqual(lectura['porcentaje'], 0)
                self.assertIn('medición válida', lectura['motivo'])

    def test_universos_invalidos_no_causan_error_ni_acreditan_porcentaje(self):
        fila = dict(codigo='USO', nombre='Uso', meta='100 %')
        for universo in ('NaN', 'Infinity', '-Infinity', '-1', None, 'desconocido'):
            with self.subTest(universo=universo):
                lectura = medir_meta(fila, dict(mediciones_porcentuales={
                    'USO': dict(numerador=3, denominador=universo)}))
                self.assertTrue(lectura['pendiente'])
                self.assertEqual(lectura['porcentaje'], 0)

    def test_mantenimiento_heredado_con_universo_invalido_queda_pendiente(self):
        fila = dict(codigo='MANTENIMIENTO', nombre='Mantenimiento', meta='80 %')
        for universo in ('NaN', 'Infinity', '-1', None):
            with self.subTest(universo=universo):
                lectura = medir_meta(fila, dict(mantenimientos_criticos_programados=universo,
                    mantenimientos_criticos_cumplidos=1))
                self.assertTrue(lectura['pendiente'])
                self.assertEqual(lectura['porcentaje'], 0)

    def test_cobertura_superior_al_universo_exige_conciliar_antes_de_acreditar(self):
        fila = dict(codigo='USO', nombre='Uso', meta='100 %')
        lectura = medir_meta(fila, dict(mediciones_porcentuales={
            'USO': dict(numerador=4, denominador=3)}))
        self.assertTrue(lectura['pendiente'])
        self.assertEqual(lectura['porcentaje'], 0)
        self.assertIn('supera el universo', lectura['motivo'])


class CierreIndicadoresTests(BaseDelExpediente):
    def respaldar_anexos(self, documento):
        for anexo in anexos_del(documento):
            if not anexo.recurso_id and anexo.estado != 'no_aplica':
                anexo.recurso = Recurso.objects.create(
                    unidad=documento.unidad, nombre=f'Anexo de prueba {anexo.pk}',
                    archivo=ContentFile(pdf_legible_prueba('Respaldo del anexo del plan de esta prueba.'),
                                        name=f'anexo-plan-{anexo.pk}.pdf'), visibilidad='interna')
                anexo.version = anexo.recurso.version
                anexo.save(update_fields=['recurso', 'version'])

    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()
        from apps.core.models.periodos import PeriodoAcademico, VersionCalendarioAcademico
        from apps.documentos.presentation.expediente import cortes_del_anio

        inicio, fin = cortes_del_anio(ANIO)[cls.corte]
        periodo = PeriodoAcademico.objects.create(codigo=f'{ANIO}-{cls.corte}',
            anio_referencia=ANIO, ciclo=cls.corte, tipo='ordinario',
            ambito='carreras_centros', estado='publicado')
        VersionCalendarioAcademico.objects.create(periodo=periodo, numero=1, vigente=True,
            fecha_inicio_clases=inicio, fecha_fin_clases=fin, fecha_fin_periodo=fin)

    def test_plan_aprobado_informe_completo_y_registros_acreditan_promedio_proporcional(self):
        d, _ = self.archivado(self.laboratorio)
        plan = self.documento(self.laboratorio, codigo='PLANIFICACION')
        plan.marco_periodo, plan.tramo_inicio, plan.tramo_fin = d.marco_periodo, d.tramo_inicio, d.tramo_fin
        plan.recurso = Recurso.objects.create(unidad=self.laboratorio, nombre='Planificación revisada QA',
            archivo=ContentFile(pdf_legible_prueba(
                'Planificación semestral: prácticas y guías del laboratorio, exclusivamente para la prueba de cálculo.',
                firmado=True), name='planificacion-calculo-qa.pdf'), visibilidad='interna')
        plan.estado, plan.firma_verificada = 'validado', True
        plan.version = 1
        plan.save()
        # La nota sola no acredita el plan: Dirección debe confirmar el archivo
        # de esta unidad, tipo y período, igual que en la operación real.
        DocumentoElaborado.objects.update_or_create(documento=plan,
            defaults={'contenido': contenido_plan_completo(plan, self.direccion)})
        from apps.documentos.presentation.conformidad_planes import confirmar_conformidad
        self.respaldar_anexos(plan)
        confirmar_conformidad(plan, self.direccion, plan.version, plan.recurso.hash_sha256,
            confirmado=True, declaracion_correspondencia=correspondencia_revisada(plan))
        DocumentoElaborado.objects.update_or_create(documento=d, defaults={'contenido': {
            'resumen_ejecutivo': '<p>Tres prácticas ejecutadas y dos guías aprobadas.</p>',
            'logros': '<p>Atención documentada del período.</p>',
            'firma_nombre': 'Coordinación', 'firma_cargo': 'Responsable de la unidad',
        }})
        metas = dict(registros={}, filas=[
            dict(codigo='PRACTICAS', nombre='Prácticas', contador='practicas', meta='6', registrado=3),
            dict(codigo='GUIAS', nombre='Guías', contador='guias', meta='1', registrado=2),
        ])
        resultado = calcular_cierre(d, metas)
        self.assertTrue(resultado['plan_aprobado'])
        self.assertTrue(resultado['completo'])
        self.assertEqual(resultado['nota'], 75)
        self.assertEqual(resultado['filas'][1]['excedente'], 1)
        metas['filas'].append(dict(codigo='PRESTAMOS', nombre='Préstamos', contador='prestamos',
                                  meta='10', registrado=0, aplica=True, obligatoria=False))
        self.assertEqual(calcular_cierre(d, metas)['nota'], 75)
        metas['todas'] = metas['filas'] + [dict(codigo='INSUMOS', nombre='Insumos', contador='movimientos_insumos',
                                              meta='', registrado=0, aplica=False, obligatoria=False)]
        resultado = calcular_cierre(d, metas)
        self.assertEqual(resultado['nota'], 75)
        self.assertEqual(resultado['catalogo'][-1]['estado'], 'No aplica')

    def test_cambiar_anexo_despues_de_firmar_exige_preparar_informe_de_nuevo(self):
        from apps.documentos.presentation.expediente import _generar
        from apps.documentos.presentation.evaluacion_cierre import preparar_cierre
        d, _ = self.archivado(self.laboratorio)
        preparar_cierre(d, self.coordinador)
        _generar(anexos_del(d)[0], self.coordinador)
        with self.assertRaisesMessage(ValidationError, 'El contenido o los anexos cambiaron'):
            validar_documento(d, self.coordinador)
        d.refresh_from_db()
        self.assertNotEqual(d.estado, 'validado')

    def test_informe_vacio_y_sin_plan_aprobado_acredita_cero(self):
        d, _ = self.archivado(self.laboratorio)
        resultado = calcular_cierre(d)
        self.assertEqual(resultado['nota'], 0)
        self.assertFalse(resultado['plan_aprobado'])
        self.assertTrue(resultado['alertas'])

    def test_nota_historica_del_plan_no_sustituye_su_conformidad(self):
        from tests.integration.utiles import registrar_antecedente_evaluacion
        d, _ = self.archivado(self.laboratorio)
        plan = self.documento(self.laboratorio, codigo='PLANIFICACION')
        plan.marco_periodo, plan.tramo_inicio, plan.tramo_fin = d.marco_periodo, d.tramo_inicio, d.tramo_fin
        plan.recurso = Recurso.objects.create(unidad=self.laboratorio, nombre='Antecedente del plan',
            archivo=ContentFile(pdf_legible_prueba('Planificación antigua revisada.', firmado=True),
                                name='planificacion-antigua.pdf'))
        plan.estado, plan.firma_verificada, plan.version = 'validado', True, 1
        plan.save()
        DocumentoElaborado.objects.update_or_create(documento=plan,
            defaults={'contenido': contenido_plan_completo(plan, self.direccion)})
        self.respaldar_anexos(plan)
        recibir_documento_revisado(plan, self.direccion)
        registrar_antecedente_evaluacion(plan, self.direccion, 80, 'Evaluación histórica del plan.')
        resultado = calcular_cierre(d)
        self.assertFalse(resultado['plan_aprobado'])
        self.assertEqual(resultado['nota'], 0)
        plan.refresh_from_db()
        self.assertEqual(plan.evaluacion, 80)

    def test_enviar_calcula_anexos_sin_marcas_manuales_y_congela_resultado(self):
        d, _ = self.archivado(self.laboratorio)
        anteriores = {a.pk: a.recurso_id for a in anexos_del(d)}
        validar_documento(d, self.coordinador)
        d.refresh_from_db()
        datos = cierre_archivado(d)
        self.assertTrue(datos['congelado'])
        self.assertEqual(datos['nota'], 0)
        self.assertEqual(len(datos['anexos']), len(anteriores))
        self.assertTrue(all(a['detalle_indicadores'] for a in datos['anexos']))
        self.assertTrue(all(a['recurso'] == anteriores[a['documento']] for a in datos['anexos']))
        with patch('apps.documentos.presentation.evaluacion_cierre.calcular_cierre', side_effect=AssertionError('No recalcular un envío')):
            self.assertEqual(lectura_cierre(d), datos)
        self.assertIsNone(d.evaluacion)

    def test_el_calculo_enviado_anterior_se_conserva_sin_reinterpretar_obligaciones(self):
        from apps.formacion.models.practicas import RegistroAuditoriaUnidad
        d, _ = self.archivado(self.laboratorio)
        validar_documento(d, self.coordinador)
        d.refresh_from_db()
        audit = RegistroAuditoriaUnidad.objects.filter(objeto_id=str(d.pk), accion='enviar',
                                                       datos_nuevos__congelado=True).latest('pk')
        datos = audit.datos_nuevos
        datos.update(metodo='metas-cierre-1', nota=75)
        datos.pop('catalogo', None)
        audit.datos_nuevos = datos
        audit.save(update_fields=['datos_nuevos'])
        with patch('apps.documentos.presentation.evaluacion_cierre.calcular_cierre', side_effect=AssertionError('No recalcular')):
            self.assertEqual(lectura_cierre(d)['nota'], 75)

    def test_director_recibe_y_confirma_sin_poder_falsificar_nota_desde_cliente(self):
        d, _ = self.archivado(self.laboratorio)
        validar_documento(d, self.coordinador)
        recibir_documento_revisado(d, self.direccion)
        d.refresh_from_db()
        with self.assertRaises(ValidationError):
            confirmar_cierre(d, self.coordinador, d.version, d.recurso.hash_sha256, True)
        self.client.force_login(self.direccion)
        r = self.client.post(reverse('admin:reportes-cumplimiento-expediente'), dict(
            documento=d.pk, accion='confirmar_cierre', version=d.version, huella=d.recurso.hash_sha256,
            confirmado='1', evaluacion='100', criterio_0='100', comentario='Revisión general concluida'))
        self.assertEqual(r.status_code, 302)
        d.refresh_from_db()
        self.assertEqual(d.evaluacion, 0)
        self.assertIsNotNone(d.evaluado_en)
        r = self.client.post(reverse('admin:reportes-cumplimiento-expediente'), dict(
            documento=d.pk, accion='evaluar', version=d.version, huella=d.recurso.hash_sha256,
            confirmado='1', evaluacion='100'))
        self.assertEqual(r.status_code, 302)
        d.refresh_from_db()
        self.assertEqual(d.evaluacion, 0)

    def test_borrador_se_puede_ver_tras_envio_sin_reemplazar_archivo_ni_escribir(self):
        d, ruta = self.archivado(self.laboratorio)
        validar_documento(d, self.coordinador)
        d.refresh_from_db()
        anterior = (d.recurso_id, d.version, d.estado)
        self.client.force_login(self.coordinador)
        with CaptureQueriesContext(connection) as consultas:
            r = self.client.get(ruta, dict(anio=ANIO, corte=d.corte, gestionar=d.pk, borrador='1'))
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r['Content-Type'], 'application/pdf')
        self.assertEqual(r['Cache-Control'], 'private, no-store')
        self.assertTrue(r.content.startswith(b'%PDF'))
        self.assertFalse(any(q['sql'].lstrip().upper().startswith(('INSERT', 'UPDATE', 'DELETE')) for q in consultas))
        d.refresh_from_db()
        self.assertEqual((d.recurso_id, d.version, d.estado), anterior)

    def test_modal_ofrece_borrador_y_firmado_sin_lista_de_versiones(self):
        d, ruta = self.archivado(self.laboratorio)
        self.client.force_login(self.coordinador)
        r = self.client.get(ruta, dict(anio=ANIO, corte=d.corte, gestionar=d.pk, vista='versiones', fragment='1'))
        self.assertContains(r, 'Borrador del sistema')
        self.assertContains(r, 'Documento firmado para enviar')
        self.assertNotContains(r, 'Versión anterior')
        self.assertNotContains(r, 'Documentos anteriores')

    def test_administrador_ve_anexos_directos_y_no_los_cuatro_criterios_del_cierre(self):
        d, _ = self.archivado(self.laboratorio)
        validar_documento(d, self.coordinador)
        self.client.force_login(self.direccion)
        r = self.client.get(reverse('admin:reportes-cumplimiento-expediente'),
                            dict(anio=ANIO, corte=d.corte, unidad=d.unidad.slug, revisar=d.pk))
        self.assertContains(r, 'data-cierre-indicadores')
        self.assertNotContains(r, 'data-rubrica')
        for a in cierre_archivado(d)['anexos']:
            self.assertContains(r, reverse('recurso_unidad', args=[a['recurso']]))
