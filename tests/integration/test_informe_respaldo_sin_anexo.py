"""El informe semestral lista el respaldo de las dos metas sin anexo: capacitación y difusión.

La unidad registra esas evidencias con su archivo y la meta se evalúa; el informe trae, después de la
tabla de cumplimiento, una tabla con cada registro del período, su verificación y el enlace al respaldo.
"""

from copy import deepcopy
from datetime import date
from io import BytesIO
from unittest.mock import patch

from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import override_settings
from django.urls import reverse
from pypdf import PdfReader

from apps.documentos.models.constancias import ConstanciaDocumento
from apps.documentos.models.expediente import DocumentoElaborado
from apps.documentos.models.medicion import EvidenciaGestionUnidad
from apps.documentos.presentation.aprobacion_en_linea import (
    decidir_documento_qr, enviar_documento_qr, generar_y_enviar_qr,
)
from apps.documentos.presentation.expediente import generar_documento, tramo_del_documento
from apps.documentos.presentation.expediente_redaccion import (
    FUENTES_FINANCIAMIENTO, componer, pdf_del_documento, secciones_de,
)
from apps.documentos.presentation.medicion_metas import rectificar_evidencia, registrar_evidencia
from tests.integration.test_expediente_redaccion import PLAN_COMPLETO, BaseDeRedaccion
from tests.integration.test_seguimiento_gobernanza import designar
from tests.integration.utiles import abrir_entrega, pdf_legible_prueba

TITULO = 'Respaldo de las actividades sin anexo'
CABECERA = ['Actividad', 'Fecha', 'Descripción', 'Responsable', 'Verificación', 'Respaldo']
SIN_REGISTROS = 'Sin registros en el período'


def _archivo(nombre):
    """Un PDF ficticio con texto suficiente para que el registro lo acepte como respaldo legible."""
    return SimpleUploadedFile(
        f'{nombre}.pdf', pdf_legible_prueba(f'Respaldo ficticio {nombre}: asistencia, contenidos y resultado de la '
                                            'actividad de prueba.'), content_type='application/pdf')


def _texto(pdf):
    """El texto del PDF en una sola línea, para buscar frases que la celda parte en renglones."""
    return ' '.join(' '.join(pagina.extract_text() or '' for pagina in PdfReader(BytesIO(pdf)).pages).split())


def _enlaces(pdf):
    return {str(anotacion.get_object().get('/A', {}).get('/URI', ''))
            for pagina in PdfReader(BytesIO(pdf)).pages for anotacion in pagina.get('/Annots', [])}


@override_settings(MEDICION_METAS_HABILITADA=True)
class RespaldoSinAnexoTests(BaseDeRedaccion):
    def setUp(self):
        self.informe = self.documento('INFORME-SEMESTRAL')
        self.inicio, self.fin = tramo_del_documento(self.informe)
        self.contenido = {'resumen_ejecutivo': '<p>Semestre de prueba.</p>', 'logros': '<ul><li>Logro</li></ul>',
                          'firma_nombre': 'Ana Coordinadora', 'firma_cargo': 'Responsable'}

    def planificar(self, contenido=PLAN_COMPLETO):
        plan = self.documento('PLANIFICACION')
        DocumentoElaborado.objects.update_or_create(documento=plan, defaults={'contenido': deepcopy(contenido)})
        return plan

    def evidencia(self, tipo, codigo, dia, titulo, descripcion, *, verificar=True, archivo=False):
        datos = dict(tipo=tipo, codigo=codigo, fecha=dia, titulo=titulo, descripcion=descripcion,
                     responsable=self.coordinador)
        if not archivo:
            datos['enlace'] = f'https://example.org/respaldo/{codigo.lower()}'
        return registrar_evidencia(self.unidad, self.coordinador, datos, verificar=verificar,
                                   archivo=_archivo(codigo) if archivo else None)

    def bloques(self):
        compuesto = componer(self.informe, self.contenido, self.inicio, self.fin)
        return next(s for s in compuesto['secciones'] if s['codigo'] == 'cumplimiento')['bloques']

    def respaldo(self):
        return next((b for b in self.bloques() if b.get('titulo') == TITULO), None)

    def pdf(self):
        redaccion = DocumentoElaborado(documento=self.informe, contenido=self.contenido)
        return pdf_del_documento(self.informe, redaccion, self.inicio, self.fin, estricto=False)

    def test_el_informe_lista_cada_registro_con_fecha_descripcion_verificacion_y_enlace(self):
        self.planificar()
        taller = self.evidencia('CAPACITACION', 'CAP-01', date(2026, 4, 15), 'Taller ficticio de cableado',
                                'Ocho horas con constancia de asistencia.', archivo=True)
        self.evidencia('DIFUSION', 'DIF-01', date(2026, 5, 20), 'Boletín ficticio de servicios',
                       'Publicado en la cartelera de la facultad.', verificar=False)
        anulada = self.evidencia('DIFUSION', 'DIF-02', date(2026, 5, 21), 'Afiche retirado', 'Se anuló por error.')
        rectificar_evidencia(self.unidad, self.coordinador, anulada.pk, 'Registro duplicado de prueba.')
        self.evidencia('CAPACITACION', 'CAP-09', date(2026, 9, 10), 'Curso del otro semestre',
                       'Pertenece al período siguiente.')

        bloques = self.bloques()
        tabla = bloques[-1]
        # Va al final del apartado de cumplimiento, después de su tabla y de lo que falta para cumplir.
        self.assertEqual([b.get('titulo') for b in bloques][1], 'Planificado frente a realizado')
        self.assertEqual((tabla['tipo'], tabla['titulo'], tabla['cabecera']), ('tabla', TITULO, CABECERA))
        archivo = settings.SITE_URL.rstrip('/') + reverse('recurso_unidad', args=[taller.recurso_id])
        self.assertEqual(tabla['filas'], [
            ['Capacitación', '15/04/2026',
             'Taller ficticio de cableado (CAP-01)\nOcho horas con constancia de asistencia.',
             'Ana Coordinadora', 'Evidencia verificada', {'texto': 'Abrir', 'url': archivo}],
            ['Difusión', '20/05/2026',
             'Boletín ficticio de servicios (DIF-01)\nPublicado en la cartelera de la facultad.',
             'Ana Coordinadora', 'Borrador', {'texto': 'Abrir', 'url': 'https://example.org/respaldo/dif-01'}],
        ])

        pdf = self.pdf()
        texto = _texto(pdf)
        self.assertIn(TITULO, texto)
        for esperado in ('15/04/2026', 'Taller ficticio de cableado (CAP-01)',
                         'Ocho horas con constancia de asistencia.', '20/05/2026',
                         'Boletín ficticio de servicios (DIF-01)', 'Publicado en la cartelera de la facultad.'):
            self.assertIn(esperado, texto)
        # La anulada y la del otro semestre no salen.
        for ausente in ('Afiche retirado', 'Curso del otro semestre'):
            self.assertNotIn(ausente, texto)
        # El enlace abre el archivo de la capacitación y la publicación de la difusión desde el PDF.
        self.assertLessEqual({archivo, 'https://example.org/respaldo/dif-01'}, _enlaces(pdf))

    def test_una_evidencia_validada_que_la_meta_no_conto_queda_como_verificacion_pendiente(self):
        self.planificar()
        # Una fila escrita sin la operación auditada no acredita la meta: el informe no la da por verificada.
        EvidenciaGestionUnidad.objects.create(
            unidad=self.unidad, tipo='CAPACITACION', codigo='CAP-SQL', fecha=date(2026, 4, 2),
            titulo='Charla importada', descripcion='Fila sin operación auditada.', responsable=self.coordinador,
            creado_por=self.coordinador, enlace='https://example.org/respaldo/cap-sql', estado='validado')
        fila = self.respaldo()['filas'][0]
        self.assertEqual((fila[0], fila[4]), ('Capacitación', 'Verificación pendiente'))

    def test_la_meta_comprometida_sin_registros_lo_dice_en_su_fila(self):
        self.planificar()
        self.assertEqual(self.respaldo()['filas'], [
            ['Capacitación', '—', SIN_REGISTROS, '—', '—', '—'],
            ['Difusión', '—', SIN_REGISTROS, '—', '—', '—'],
        ])
        self.evidencia('DIFUSION', 'DIF-01', date(2026, 5, 20), 'Feria ficticia', 'Stand de la unidad.')
        filas = self.respaldo()['filas']
        self.assertEqual(filas[0], ['Capacitación', '—', SIN_REGISTROS, '—', '—', '—'])
        self.assertEqual(filas[1][:2], ['Difusión', '20/05/2026'])
        texto = _texto(self.pdf())
        self.assertIn(SIN_REGISTROS, texto)
        self.assertIn('Feria ficticia (DIF-01)', texto)

    def test_sin_esas_metas_ni_registros_la_tabla_no_aparece(self):
        # Sin planificación redactada.
        self.assertIsNone(self.respaldo())
        self.assertNotIn(TITULO, _texto(self.pdf()))
        # Con un plan anterior a los mínimos por tipo, que no compromete ninguna de las dos.
        self.planificar({'actividades': {'catalogo': {
            'USO': {'aplica': True, 'meta': '100 %', 'meses': [3, 4], 'responsable': 'Ana Coordinadora'}}}})
        self.assertNotIn('Capacitación del personal de la unidad',
                         [f[0] for f in self.bloques()[1]['filas']])
        self.assertIsNone(self.respaldo())
        self.assertNotIn(TITULO, _texto(self.pdf()))

    def test_un_registro_sale_aunque_el_plan_no_comprometa_la_meta(self):
        self.evidencia('DIFUSION', 'DIF-01', date(2026, 5, 20), 'Feria ficticia', 'Stand de la unidad.')
        bloques = self.bloques()
        # Sin plan, el apartado dice que no hay con qué comparar y aun así muestra el respaldo registrado.
        self.assertEqual([b['tipo'] for b in bloques], ['vacio', 'tabla'])
        self.assertEqual([f[:2] for f in bloques[1]['filas']], [['Difusión', '20/05/2026']])
        self.assertIn('Feria ficticia (DIF-01)', _texto(self.pdf()))

    def test_la_vista_previa_muestra_la_tabla_con_el_enlace(self):
        self.planificar()
        self.evidencia('DIFUSION', 'DIF-01', date(2026, 5, 20), 'Feria ficticia', 'Stand de la unidad.')
        DocumentoElaborado.objects.create(documento=self.informe, contenido=self.contenido)
        self.client.force_login(self.coordinador)
        respuesta = self.client.get(reverse('vista_previa_documento_expediente',
                                            args=[self.unidad.slug, self.informe.pk]))
        self.assertContains(respuesta, TITULO)
        self.assertContains(respuesta, '<a href="https://example.org/respaldo/dif-01" target="_blank" '
                                       'rel="noopener">Abrir</a>', html=True)
        self.assertNotContains(respuesta, "{&#x27;texto&#x27;")

    def test_la_unidad_registra_la_difusion_con_su_archivo_y_el_informe_la_enlaza(self):
        self.planificar()
        self.client.force_login(self.coordinador)
        ruta = (reverse('fuentes_metas_unidad', args=[self.unidad.slug])
                + f'?anio={self.informe.anio}&corte={self.informe.corte}&tipo=DIFUSION')
        self.assertContains(self.client.get(ruta), 'Subir respaldo (PDF o imagen)')
        respuesta = self.client.post(ruta, dict(
            codigo='DIF-PANTALLA', fecha='2026-05-20', titulo='Programa de radio ficticio',
            descripcion='Entrevista sobre los servicios de la unidad.', responsable=self.coordinador.pk,
            verificar='on', archivo=_archivo('difusion')))
        self.assertEqual(respuesta.status_code, 302)
        evidencia = EvidenciaGestionUnidad.objects.get(unidad=self.unidad, codigo='DIF-PANTALLA')
        self.assertEqual((evidencia.tipo, evidencia.estado, bool(evidencia.recurso_id)), ('DIFUSION', 'validado', True))
        fila = next(f for f in self.respaldo()['filas'] if f[0] == 'Difusión')
        self.assertEqual(fila[4:], ['Evidencia verificada', {
            'texto': 'Abrir',
            'url': settings.SITE_URL.rstrip('/') + reverse('recurso_unidad', args=[evidencia.recurso_id])}])


@override_settings(MEDICION_METAS_HABILITADA=True)
class InformeEnviadoConservaSuRespaldoTests(BaseDeRedaccion):
    def setUp(self):
        self.director = get_user_model().objects.create_superuser(
            'direccion-respaldo-sin-anexo', password=None, first_name='Dirección', last_name='de prueba')
        designar(self.director)
        self.coordinador.profile.cedula = '0400000001'
        self.coordinador.profile.save(update_fields=['cedula'])
        self.director.profile.cedula = '0400000002'
        self.director.profile.save(update_fields=['cedula'])
        plan = abrir_entrega(self.documento('PLANIFICACION'))
        contenido_plan = deepcopy(PLAN_COMPLETO)
        contenido_plan.update(recursos_periodo_version=1, revision_recursos='revisado',
                              cobertura_recursos='<p>Los recursos disponibles cubren las actividades.</p>')
        contenido_plan['inversion'][0]['fuente'] = FUENTES_FINANCIAMIENTO[0][0]
        DocumentoElaborado.objects.create(documento=plan, contenido=contenido_plan)
        generar_y_enviar_qr(plan, self.coordinador)
        decidir_documento_qr(plan, self.director, token=plan.verificacion_qr, version=plan.version,
                             decision='aprobar')
        self.informe = abrir_entrega(self.documento('INFORME-SEMESTRAL'))
        self.inicio, self.fin = tramo_del_documento(self.informe)

    def registrar(self, tipo, codigo, dia, titulo):
        return registrar_evidencia(self.unidad, self.coordinador, dict(
            tipo=tipo, codigo=codigo, fecha=dia, titulo=titulo, descripcion='Registro ficticio de prueba.',
            responsable=self.coordinador, enlace=f'https://example.org/respaldo/{codigo.lower()}'), verificar=True)

    def test_el_informe_enviado_no_cambia_cuando_se_registra_otra_evidencia(self):
        from apps.documentos.presentation.validacion_pdf import _representar_aprobada, copia_para_recurso

        self.registrar('CAPACITACION', 'CAP-01', date(2026, 4, 15), 'Taller ficticio inicial')
        contenido = {c.clave: '<p>Resultados y evidencias del semestre para revisión.</p>'
                     for s in secciones_de('informe', self.unidad) for c in s.campos if c.requerido}
        redaccion = DocumentoElaborado.objects.create(documento=self.informe, contenido=contenido)
        generar_documento(self.informe, self.coordinador)
        self.informe.refresh_from_db()
        constancia = ConstanciaDocumento.objects.select_related('documento', 'recurso').get(
            documento=self.informe, version=self.informe.version)
        enviar_documento_qr(self.informe, self.coordinador, token=constancia.token, version=constancia.version)
        self.informe.refresh_from_db()
        self.assertEqual(self.informe.estado, 'validado')
        with constancia.recurso.archivo.open('rb') as archivo:
            enviado = archivo.read()
        self.assertIn('Taller ficticio inicial (CAP-01)', _texto(enviado))
        self.assertIn('https://example.org/respaldo/cap-01', _enlaces(enviado))

        # Después del envío la unidad registra una difusión del mismo período.
        self.registrar('DIFUSION', 'DIF-TARDE', date(2026, 5, 20), 'Feria ficticia posterior')
        constancia.refresh_from_db()
        with constancia.recurso.archivo.open('rb') as archivo:
            self.assertEqual(archivo.read(), enviado)
        # Lo que se consulta y la copia aprobada salen del contenido conservado, no de los registros de hoy.
        with patch('apps.documentos.presentation.expediente_redaccion.componer',
                   side_effect=AssertionError('El informe enviado no se vuelve a componer.')):
            consultado = copia_para_recurso(constancia.recurso)
            decidir_documento_qr(self.informe, self.director, token=constancia.token,
                                 version=constancia.version, decision='aprobar')
            constancia.refresh_from_db()
            aprobado = _representar_aprobada(enviado, constancia)
        for copia in (consultado, aprobado):
            texto = _texto(copia)
            self.assertIn('Taller ficticio inicial (CAP-01)', texto)
            self.assertNotIn('Feria ficticia posterior', texto)
            self.assertIn('https://example.org/respaldo/cap-01', _enlaces(copia))
        with constancia.recurso.archivo.open('rb') as archivo:
            self.assertEqual(archivo.read(), enviado)
        # El informe al día sí la trae: es lo que vería un borrador nuevo, no el archivo conservado.
        al_dia = _texto(pdf_del_documento(self.informe, redaccion, self.inicio, self.fin, estricto=False))
        self.assertIn('Feria ficticia posterior (DIF-TARDE)', al_dia)
