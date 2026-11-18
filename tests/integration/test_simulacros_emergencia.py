"""Simulacros y prácticas de emergencia: una constancia que la unidad registra, sin meta.

- la unidad los registra donde registra sus inspecciones, con el mismo permiso y con su respaldo;
- un simulacro rectificado queda anulado;
- no son una meta: no cambian la nota del informe ni las mediciones del período;
- no van en el anexo de reportes de seguridad: se presentan en su documento de «Respaldo para auditoría»;
- el observatorio, que no lleva inspecciones físicas, no los registra.
"""
from datetime import date
from io import BytesIO
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase, override_settings
from django.urls import reverse

from apps.directorio_unidades.models.core import Unidad
from apps.documentos.models.medicion import EvidenciaGestionUnidad
from apps.documentos.presentation.anexos_evidencia import constructor_de, contexto_del_anexo, metas_del_anexo
from apps.documentos.presentation.evaluacion_cierre import calcular_cierre, evaluar_meta
from apps.documentos.presentation.expediente import anexos_del, construir_expediente, tramo_del_documento
from apps.documentos.presentation.expediente_redaccion import ACTIVIDADES_PLAN, filas_del_plan, registros_del_periodo
from apps.documentos.presentation.medicion_metas import (
    rectificar_evidencia, registrar_evidencia, registros_de_gestion,
)
from apps.formacion.models.practicas import RegistroAuditoriaUnidad
from apps.gestion_unidades.presentation.reportes_condiciones import acciones_condiciones

ANEXO = 'INDUCCION-SEGURIDAD'


def _acta_en_pdf():
    """Un PDF legible y ficticio, como el acta que adjunta la unidad."""
    from reportlab.lib.pagesizes import A4
    from reportlab.pdfgen.canvas import Canvas

    archivo = BytesIO()
    lienzo = Canvas(archivo, pagesize=A4)
    lienzo.setFont('Helvetica', 11)
    lienzo.drawString(45, 780, 'Acta ficticia de un simulacro de prueba, sin validez institucional.')
    lienzo.drawString(45, 760, 'Participantes de ejemplo y tiempos de evacuación inventados para la prueba.')
    lienzo.save()
    return archivo.getvalue()


def _informe(unidad):
    documentos = construir_expediente(unidad, 2026, hoy=date(2026, 10, 17))
    return next(d for d in documentos if d.exigido.codigo == 'INFORME-SEMESTRAL' and d.corte == 'B')


def _anexo(unidad):
    return next(a for a in anexos_del(_informe(unidad), incluir_no_aplica=True) if a.exigido.codigo == ANEXO)


@override_settings(MEDICION_METAS_HABILITADA=True, MEDICION_SOLO_DEMO=False)
class SimulacrosDeEmergenciaTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        usuarios = get_user_model().objects
        cls.responsable = usuarios.create_user('responsable-simulacros', first_name='Rita', last_name='Responsable')
        cls.ajeno = usuarios.create_user('ajeno-simulacros')
        cls.unidad = Unidad.objects.create(
            nombre='Laboratorio de simulacros de prueba', slug='simulacros-prueba', dependencia='laboratorios',
            descripcion='Unidad ficticia', fecha_inicio=date(2025, 1, 1), administrador=cls.responsable)
        cls.observatorio = Unidad.objects.create(
            nombre='Observatorio de simulacros de prueba', slug='simulacros-observatorio', dependencia='observatorios',
            descripcion='Unidad ficticia', fecha_inicio=date(2025, 1, 1), administrador=cls.responsable)

    def setUp(self):
        self.hoy = date(2026, 10, 16)
        self.inicio, self.fin = date(2026, 7, 1), date(2026, 12, 31)
        reloj = patch('django.utils.timezone.localdate', return_value=self.hoy)
        reloj.start()
        self.addCleanup(reloj.stop)

    def datos(self, codigo='SIM-09', dia=date(2026, 9, 18), **detalle):
        base = dict(emergencia='sismo', participantes=18, accion_mejora='Señalizar la salida posterior.')
        return dict(tipo='SIMULACRO', codigo=codigo, fecha=dia, titulo='Simulacro de evacuación por sismo',
                    descripcion='Evacuación completa en tres minutos; una salida estaba sin señalizar.',
                    responsable=self.responsable, enlace=f'https://example.org/simulacros/{codigo.lower()}',
                    detalle=base | detalle)

    def simulacro(self, verificar=True, **datos):
        return registrar_evidencia(self.unidad, self.responsable, self.datos(**datos), verificar=verificar)

    # -- registro -------------------------------------------------------------------------

    def test_la_unidad_registra_un_simulacro_con_su_respaldo_donde_las_inspecciones(self):
        acciones = acciones_condiciones('seguridad', self.unidad, self.inicio, self.fin)
        self.assertEqual([a['label'] for a in acciones],
                         ['Registrar inspección y respaldo', 'Registrar simulacro o práctica de emergencia'])
        ruta = reverse('fuentes_metas_unidad', args=[self.unidad.slug])
        self.assertEqual(acciones[1]['url'], ruta + '?anio=2026&corte=B&tipo=SIMULACRO')

        self.client.force_login(self.responsable)
        pagina = self.client.get(acciones[1]['url'])
        self.assertContains(pagina, 'Emergencia ensayada')
        self.assertContains(pagina, 'Número de participantes')
        self.assertContains(pagina, 'no es una meta ni cambia la nota del informe')
        self.assertNotContains(pagina, 'Condiciones revisadas')

        respuesta = self.client.post(ruta, dict(
            anio=2026, corte='B', tipo='SIMULACRO', codigo='SIM-09', fecha='2026-09-18',
            titulo='Simulacro de evacuación por sismo',
            descripcion='Evacuación completa en tres minutos; una salida estaba sin señalizar.',
            emergencia='sismo', participantes='18', accion_mejora='Señalizar la salida posterior.',
            responsable=self.responsable.pk, verificar='on',
            archivo=SimpleUploadedFile('acta-simulacro.pdf', _acta_en_pdf(), 'application/pdf')))
        self.assertEqual(respuesta.status_code, 302, respuesta.context and respuesta.context['form'].errors)

        simulacro = EvidenciaGestionUnidad.objects.get(unidad=self.unidad, tipo='SIMULACRO')
        self.assertEqual(simulacro.estado, 'validado')
        self.assertEqual(simulacro.responsable, self.responsable)
        self.assertEqual(simulacro.detalle, {'emergencia': 'sismo', 'participantes': 18,
                                             'accion_mejora': 'Señalizar la salida posterior.'})
        self.assertTrue(simulacro.recurso.hash_sha256)
        self.assertTrue(simulacro.recurso.archivo.storage.exists(simulacro.recurso.archivo.name))
        # Deja rastro como cualquier evidencia de gestión.
        self.assertTrue(RegistroAuditoriaUnidad.objects.filter(
            unidad=self.unidad, entidad=simulacro._meta.label, objeto_id=str(simulacro.pk), accion='crear',
            usuario=self.responsable).exists())

        lista = self.client.get(respuesta.url)
        self.assertContains(lista, 'Simulacro guardado')
        self.assertContains(lista, 'Emergencia ensayada: Sismo')
        self.assertContains(lista, 'Participantes: 18')
        self.assertContains(lista, reverse('respaldo_meta_unidad', args=[self.unidad.slug, simulacro.pk]))
        self.assertEqual(self.client.get(
            reverse('respaldo_meta_unidad', args=[self.unidad.slug, simulacro.pk])).status_code, 200)

    def test_el_formulario_exige_emergencia_y_participantes_para_verificar(self):
        self.client.force_login(self.responsable)
        ruta = reverse('fuentes_metas_unidad', args=[self.unidad.slug])
        respuesta = self.client.post(ruta, dict(
            anio=2026, corte='B', tipo='SIMULACRO', codigo='SIM-INCOMPLETO', fecha='2026-09-18',
            titulo='Simulacro incompleto', descripcion='Sin datos del ejercicio.', responsable=self.responsable.pk,
            enlace='https://example.org/simulacros/incompleto', verificar='on'))
        self.assertEqual(respuesta.status_code, 200)
        errores = respuesta.context['form'].errors
        self.assertIn('emergencia', errores)
        self.assertIn('participantes', errores)
        self.assertFalse(EvidenciaGestionUnidad.objects.filter(tipo='SIMULACRO').exists())

    def test_un_simulacro_verificado_exige_su_detalle_y_su_respaldo(self):
        for clave, valor in (('emergencia', ''), ('emergencia', 'inundacion'), ('participantes', 0),
                             ('participantes', ''), ('participantes', True), ('accion_mejora', None)):
            with self.subTest(clave=clave, valor=valor), self.assertRaises(ValidationError):
                self.simulacro(**{clave: valor})
        datos = self.datos()
        datos['enlace'] = ''
        with self.assertRaisesMessage(ValidationError, 'Adjunta un archivo'):
            registrar_evidencia(self.unidad, self.responsable, datos, verificar=True)
        # La acción de mejora es opcional; un borrador se puede completar después.
        self.assertEqual(self.simulacro(accion_mejora='').estado, 'validado')
        self.assertEqual(self.simulacro(verificar=False, codigo='SIM-BORRADOR', emergencia='').estado, 'borrador')

    def test_solo_registra_quien_opera_los_reportes_de_la_unidad(self):
        ruta = reverse('fuentes_metas_unidad', args=[self.unidad.slug])
        self.client.force_login(self.ajeno)
        self.assertEqual(self.client.get(ruta, {'anio': 2026, 'corte': 'B', 'tipo': 'SIMULACRO'}).status_code, 403)
        self.assertEqual(self.client.get(ruta, {'anio': 2026, 'corte': 'B', 'tipo': 'INSPECCION'}).status_code, 403)

    def test_el_observatorio_no_registra_simulacros(self):
        acciones = acciones_condiciones('seguridad', self.observatorio, self.inicio, self.fin)
        self.assertFalse([a for a in acciones if 'SIMULACRO' in a['url']])
        self.client.force_login(self.responsable)
        ruta = reverse('fuentes_metas_unidad', args=[self.observatorio.slug])
        self.assertEqual(self.client.get(ruta, {'anio': 2026, 'corte': 'B', 'tipo': 'SIMULACRO'}).status_code, 403)

    def test_un_simulacro_rectificado_queda_anulado(self):
        simulacro = self.simulacro()
        self.client.force_login(self.responsable)
        respuesta = self.client.post(reverse('fuentes_metas_unidad', args=[self.unidad.slug]), dict(
            anio=2026, corte='B', tipo='SIMULACRO', accion='rectificar', evidencia=simulacro.pk,
            motivo='Se registró con la fecha equivocada.'))
        self.assertEqual(respuesta.status_code, 302)
        simulacro.refresh_from_db()
        self.assertEqual(simulacro.estado, 'anulado')

    # -- no va en el anexo ----------------------------------------------------------------

    def test_el_anexo_de_seguridad_no_presenta_los_simulacros(self):
        self.simulacro()
        anexo = _anexo(self.unidad)
        inicio, fin = tramo_del_documento(anexo)
        self.assertEqual((inicio, fin), (self.inicio, self.fin))
        titulos = [r.titulo for r in constructor_de(ANEXO)(contexto_del_anexo(anexo, inicio, fin))]
        self.assertEqual(len(titulos), 6)
        self.assertFalse([titulo for titulo in titulos if 'imulacro' in titulo])

    # -- no es una meta -------------------------------------------------------------------

    def test_el_simulacro_no_es_una_actividad_del_plan_ni_una_meta_del_anexo(self):
        self.assertNotIn('SIMULACRO', {a.codigo for a in ACTIVIDADES_PLAN})
        self.assertNotIn('gestion_simulacro', {a.contador for a in ACTIVIDADES_PLAN})
        self.assertEqual(metas_del_anexo(ANEXO), ('SEGURIDAD', 'INSPECCIONES'))

    def test_registrar_simulacros_no_altera_el_calculo_de_las_metas(self):
        # Una capacitación verificada, para que la comparación no sea entre ceros.
        registrar_evidencia(self.unidad, self.responsable, dict(
            tipo='CAPACITACION', codigo='CAP-09', fecha=date(2026, 9, 3), titulo='Capacitación de prueba',
            descripcion='Curso ficticio recibido por el personal.', responsable=self.responsable,
            enlace='https://example.org/capacitaciones/cap-09'), verificar=True)

        def medicion():
            """Las metas del catálogo de la unidad medidas como en el informe, y la nota que darían."""
            registros = registros_del_periodo(self.unidad, self.inicio, self.fin)
            metas = []
            for fila in filas_del_plan(self.unidad, {}, self.inicio, self.fin):
                fila = dict(fila, registrado=registros.get(fila['contador']) if fila['contador'] else None)
                lectura = evaluar_meta(fila, registros)
                metas.append((fila['codigo'], lectura['porcentaje'], lectura['estado'], lectura['exigible'],
                              lectura['pendiente']))
            exigibles = [porcentaje or 0 for _codigo, porcentaje, _estado, exigible, _pendiente in metas if exigible]
            nota = round(sum(exigibles) / len(exigibles), 2)
            cierre = calcular_cierre(_informe(self.unidad))
            gestion = registros_de_gestion(self.unidad, self.inicio, self.fin)
            propios = gestion.pop('gestion_simulacro'), gestion['fuentes_gestion'].pop('SIMULACRO', [])
            return (nota, metas, cierre['nota'], cierre['avance_metas'], cierre['catalogo'], gestion), propios

        antes, (contados, fuentes) = medicion()
        self.assertEqual((contados, fuentes), (0, []))
        porcentajes = {codigo: porcentaje for codigo, porcentaje, *_resto in antes[1]}
        self.assertEqual(porcentajes['CAPACITACION'], 100)
        self.assertIn('INSPECCIONES', porcentajes)
        self.assertNotIn('SIMULACRO', porcentajes)
        self.assertGreater(antes[0], 0)
        self.simulacro()
        self.simulacro(codigo='SIM-10', dia=date(2026, 10, 2), emergencia='incendio', participantes=7)
        anulado = self.simulacro(codigo='SIM-08', dia=date(2026, 8, 20))
        rectificar_evidencia(self.unidad, self.responsable, anulado.pk, 'Registro duplicado.')
        despues, (contados, fuentes) = medicion()
        self.assertEqual(contados, 2)
        self.assertEqual(len(fuentes), 2)
        self.assertEqual(despues, antes)
