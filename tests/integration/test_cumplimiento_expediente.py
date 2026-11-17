"""Cumplimiento del expediente: quién entregó, quién no y qué se hace con eso.

La Dirección tiene que poder auditar sin abrir veinte consolas: por período,
qué unidad incumple y en qué. Y lo incumplido no puede quedarse en una cifra:
entra como hallazgo en la mejora continua de la unidad.
"""

from datetime import date, timedelta
from html.parser import HTMLParser
from urllib.parse import parse_qs, urlsplit

from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase
from django.utils import timezone
from django.urls import reverse

from apps.documentos.presentation.cumplimiento import DEPENDENCIAS_AUDITADAS, cumplimiento_de_unidad, cumplimiento_por_periodo, incumplimientos, pdf_de_cumplimiento, unidades_auditadas
from apps.documentos.presentation.expediente import construir_expediente, cortes_del_anio, del_periodo, periodo_vigente, resumen, validar_documento
from apps.documentos.presentation.expediente_catalogo import asegurar_catalogo
from apps.documentos.models.expediente import DocumentoExigido, DocumentoExpediente
from apps.directorio_unidades.models.core import Unidad
from tests.integration.utiles import abrir_entrega, identificar
from tests.integration.utiles import (pdf_legible_prueba, datos_correspondencia_revisada, cargar_documento_revisado, evaluar_documento_revisado)
from tests.integration.test_seguimiento_gobernanza import designar


PDF_FIRMADO = pdf_legible_prueba(firmado=True)


def enlaces_de(html):
    class Enlaces(HTMLParser):
        def __init__(self):
            super().__init__()
            self.enlaces = []

        def handle_starttag(self, tag, attrs):
            if tag == 'a':
                self.enlaces.append(dict(attrs))

    parser = Enlaces()
    parser.feed(html)
    return parser.enlaces


class BaseDeCumplimiento(TestCase):
    def firmar_y_cargar(self, url, documento, corte='A', revisar_anexos=True):
        """Carga un PDF firmado externo histórico y revisa sus anexos.

        Estos archivos existían antes del editor; generar un original nativo
        aquí crearía una preparación ajena al contrato que se está probando.
        """
        from apps.documentos.presentation.expediente import anexos_del, validar_anexo

        abrir_entrega(documento)
        self.client.post(url, {'anio': 2026, 'corte': corte, 'documento': documento.pk, 'accion': 'cargar',
                               'archivo': SimpleUploadedFile('firmado.pdf', PDF_FIRMADO),
                               **datos_correspondencia_revisada(documento)})
        documento.refresh_from_db()
        if revisar_anexos:
            for anexo in anexos_del(documento):
                validar_anexo(anexo, self.coordinador)

    @classmethod
    def setUpTestData(cls):
        asegurar_catalogo()
        cls.direccion = get_user_model().objects.create_superuser(
            'direccion-cumplimiento', 'direccion@ejemplo.ec', 'clave-segura')
        designar(cls.direccion)
        cls.coordinador = get_user_model().objects.create_user(
            'coordinador-cumplimiento', password='clave-segura')
        identificar(cls.coordinador, tipo_usuario='administrativo', carrera='')
        cls.laboratorio = Unidad.objects.create(
            nombre='Laboratorio auditado', slug='laboratorio-auditado', dependencia='laboratorios',
            descripcion='Unidad de prueba.', fecha_inicio=date(2024, 1, 1),
            administrador=cls.coordinador, activo=True)
        cls.planta = Unidad.objects.create(
            nombre='Planta auditada', slug='planta-auditada', dependencia='plantas_piloto',
            descripcion='Unidad de prueba.', fecha_inicio=date(2024, 1, 1),
            administrador=cls.coordinador, activo=True)


class TableroDeLaDireccionTests(BaseDeCumplimiento):
    """Una fila por unidad, las que incumplen primero."""

    def test_la_planificacion_viaja_sin_anexos_y_el_mantenimiento_va_con_el_informe(self):
        documentos = construir_expediente(self.laboratorio, 2026)
        self.assertFalse([d for d in documentos if d.exigido.anexo_de_id and d.exigido.anexo_de.codigo == 'PLANIFICACION'])
        anexo = next(d for d in documentos if d.exigido.codigo == 'EQUIPAMIENTO' and d.corte == 'B')
        self.client.force_login(self.direccion)
        respuesta = self.client.get(reverse('admin:reportes-cumplimiento-expediente'),
            {'anio': 2026, 'corte': 'B', 'unidad': self.laboratorio.slug})
        self.assertEqual(respuesta.status_code, 200)
        html = respuesta.content.decode()
        anexos = html.split('aria-label="Anexos y seguimiento"', 1)[1].split('</section>', 1)[0]
        self.assertNotIn('data-soporte-planificacion=', html)
        self.assertIn(f'data-avance-documento="{anexo.pk}"', anexos)
        self.assertNotIn('<form', anexos)

    def test_audita_las_cuatro_tipologias_y_deja_fuera_los_centros(self):
        self.assertEqual(
            set(DEPENDENCIAS_AUDITADAS),
            {'laboratorios', 'plantas_piloto', 'centro_experimental', 'observatorios'})
        centro = Unidad.objects.create(
            nombre='Centro I+D', slug='centro-id-prueba', dependencia='centros_id',
            descripcion='Otro ciclo.', fecha_inicio=date(2024, 1, 1), activo=True)

        auditadas = list(unidades_auditadas())

        self.assertIn(self.laboratorio, auditadas)
        self.assertIn(self.planta, auditadas)
        self.assertNotIn(centro, auditadas)

    def test_una_unidad_sin_entregar_nada_del_periodo_cerrado_incumple(self):
        fila = cumplimiento_de_unidad(self.laboratorio, 2026, 'A', hoy=date(2026, 9, 22))

        self.assertEqual(fila['semaforo'], 'incumple')
        self.assertGreater(fila['vencidos'], 0)
        self.assertEqual(fila['validados'], 0)
        self.assertTrue(fila['incumplimientos'])
        primero = fila['incumplimientos'][0]
        self.assertEqual(primero['estado'], 'vencido')
        self.assertGreater(primero['dias'], 0)

    def test_el_tablero_pone_primero_a_quien_incumple(self):
        filas, totales = cumplimiento_por_periodo(2026, 'A', hoy=date(2026, 9, 22))

        self.assertEqual(totales['unidades'], len(filas))
        # Las de esta prueba incumplen las dos; el tablero las pone delante.
        mias = [fila for fila in filas if fila['unidad'] in (self.laboratorio, self.planta)]
        self.assertEqual([fila['semaforo'] for fila in mias], ['incumple', 'incumple'])
        self.assertEqual(filas[0]['semaforo'], 'incumple')
        self.assertGreaterEqual(totales['incumplen'], 2)
        self.assertGreater(totales['vencidos'], 0)

    def test_quien_no_es_superusuario_solo_ve_lo_que_administra(self):
        ajena = Unidad.objects.create(
            nombre='Unidad ajena', slug='unidad-ajena-cumplimiento', dependencia='laboratorios',
            descripcion='De otra persona.', fecha_inicio=date(2024, 1, 1), activo=True)

        propias = list(unidades_auditadas(self.coordinador))

        self.assertIn(self.laboratorio, propias)
        self.assertNotIn(ajena, propias)

    def test_lo_que_cierra_el_periodo_no_se_reclama_antes_de_su_ventana(self):
        """La planificacion abre el periodo y ya venció; el cierre todavía no abre."""
        documentos = construir_expediente(self.laboratorio, 2026, date(2026, 9, 22))
        del_periodo_b = [d for d in documentos if d.corte == 'B']
        hoy = date(2026, 9, 22)

        faltantes = incumplimientos(del_periodo_b, hoy=hoy)

        reclamados = {fila['documento'].exigido.codigo for fila in faltantes}
        self.assertIn('PLANIFICACION', reclamados)
        self.assertNotIn('INFORME-SEMESTRAL', reclamados)
        informe = next(d for d in del_periodo_b if d.exigido.codigo == 'INFORME-SEMESTRAL')
        self.assertEqual(informe.semaforo(hoy), 'no_abierto')

    def test_el_consolidado_sale_en_pdf_con_el_marco_institucional(self):
        filas, totales = cumplimiento_por_periodo(2026, 'A', hoy=date(2026, 9, 22))

        contenido = pdf_de_cumplimiento(filas, totales, 2026, 'A')

        self.assertTrue(contenido.startswith(b'%PDF'))
        self.assertGreater(len(contenido), 3000)


class PaginaDeLaDireccionTests(BaseDeCumplimiento):
    """El tablero vive en la administración institucional."""

    def test_la_direccion_ve_el_tablero_con_su_semaforo(self):
        self.client.force_login(self.direccion)

        pagina = self.client.get(
            reverse('admin:reportes-cumplimiento-expediente'), {'anio': 2026, 'corte': 'A'})

        contenido = pagina.content.decode()
        self.assertEqual(pagina.status_code, 200)
        self.assertIn('Laboratorio auditado', contenido)
        self.assertIn('citt-cumplimiento__semaforo', contenido)
        self.assertIn('expedientes con faltantes', contenido)
        self.assertIn('Pendientes documentales', contenido)
        # La matriz con la que se decide: el plazo de cada documento, su evidencia y en qué paso va.
        self.assertIn('citt-matriz', contenido)
        self.assertIn('<th>Fechas</th>', contenido)
        self.assertIn('Plazo:', contenido)
        self.assertIn('Documentos permanentes de la unidad', contenido)
        self.assertIn('Documentos del año 2026', contenido)
        self.assertIn('citt-matriz__categoria', contenido)
        self.assertIn('<th>Avance</th>', contenido)
        self.assertIn('Anexos y seguimiento', contenido)
        self.assertIn('No suman obligaciones ni puntos independientes', contenido)

    def test_el_tablero_se_descarga_en_pdf(self):
        self.client.force_login(self.direccion)

        respuesta = self.client.get(
            reverse('admin:reportes-cumplimiento-expediente'),
            {'anio': 2026, 'corte': 'A', 'formato': 'pdf'})

        self.assertEqual(respuesta['Content-Type'], 'application/pdf')
        self.assertTrue(respuesta.content.startswith(b'%PDF'))

    def test_quien_no_puede_ver_el_expediente_no_entra(self):
        self.client.force_login(self.coordinador)

        respuesta = self.client.get(reverse('admin:reportes-cumplimiento-expediente'))

        self.assertIn(respuesta.status_code, (302, 403))


class ValidarDesdeLaConsolaTests(BaseDeCumplimiento):
    """Archivar no cierra nada: alguien tiene que dar por buena la entrega."""

    def documento(self, codigo, corte='A'):
        construir_expediente(self.laboratorio, 2026, date(2026, 9, 22))
        return next(
            d for d in construir_expediente(self.laboratorio, 2026, date(2026, 9, 22))
            if d.exigido.codigo == codigo and d.corte == corte)

    def test_no_se_valida_un_documento_sin_archivo_ni_un_anexo_suelto(self):
        from django.core.exceptions import ValidationError

        with self.assertRaises(ValidationError):
            validar_documento(self.documento('INFORME-SEMESTRAL'), self.coordinador)
        with self.assertRaises(ValidationError) as contexto:
            validar_documento(self.documento('PRACTICAS-FT02'), self.coordinador)
        self.assertIn('es un anexo', ' '.join(contexto.exception.messages))
    def test_la_consola_ofrece_enviar_y_reserva_observaciones_para_direccion(self):
        documento = self.documento('INFORME-SEMESTRAL')
        self.client.force_login(self.coordinador)
        url = reverse('gestion_expediente_unidad', args=[self.laboratorio.slug])

        self.firmar_y_cargar(url, documento)
        pagina = self.client.get(url, {'anio': 2026, 'corte': 'A', 'gestionar': documento.pk, 'fragment': '1'})

        contenido = pagina.content.decode()
        self.assertIn('value="validar"', contenido)
        self.assertNotIn('value="observar"', contenido)
        self.assertNotIn('Revisar PDF vigente', contenido)
        self.assertIn('Cargar y enviar a Dirección', contenido)
    def test_quien_administra_la_unidad_valida_lo_que_ella_produjo_y_cierra_sus_anexos(self):
        documento = self.documento('INFORME-SEMESTRAL')
        self.client.force_login(self.coordinador)
        url = reverse('gestion_expediente_unidad', args=[self.laboratorio.slug])
        self.firmar_y_cargar(url, documento)

        self.client.post(url, {'anio': 2026, 'documento': documento.pk, 'accion': 'validar'})

        documento.refresh_from_db()
        self.assertEqual(documento.estado, 'validado')
        self.assertEqual(documento.validado_por, self.coordinador)
        practicas = self.documento('PRACTICAS-FT02')
        self.assertEqual((practicas.estado, practicas.validado_por), ('validado', self.coordinador))
        # El anexo condicional que el plan no compromete no se presenta ni se cierra con la entrega.
        investigacion = self.documento('INVESTIGACION')
        self.assertEqual(investigacion.estado, 'no_aplica')
        self.assertIsNone(investigacion.validado_por)

    def test_el_borrador_heredado_sin_firma_ni_constancia_no_se_valida(self):
        from django.core.exceptions import ValidationError
        from unittest.mock import patch

        documento = self.documento('INFORME-SEMESTRAL')
        self.client.force_login(self.coordinador)
        url = reverse('gestion_expediente_unidad', args=[self.laboratorio.slug])
        abrir_entrega(documento)
        with patch('apps.documentos.presentation.aprobacion_en_linea.admite_aprobacion_en_linea', return_value=False):
            self.client.post(url, {'anio': 2026, 'documento': documento.pk, 'accion': 'generar'})
        documento.refresh_from_db()

        with self.assertRaises(ValidationError) as contexto:
            validar_documento(documento, self.coordinador)
        self.assertIn('firma', ' '.join(contexto.exception.messages))
    def test_observar_devuelve_el_documento_con_su_motivo(self):
        documento = self.documento('INFORME-SEMESTRAL')
        self.client.force_login(self.coordinador)
        url = reverse('gestion_expediente_unidad', args=[self.laboratorio.slug])
        self.firmar_y_cargar(url, documento)

        self.client.force_login(self.direccion)
        self.client.post(url, {'anio': 2026, 'documento': documento.pk, 'accion': 'observar',
                               'observacion': 'Falta la guía de la práctica de corte.',
                               'hasta_correccion': (timezone.now() + timedelta(days=3)).isoformat()})

        documento.refresh_from_db()
        self.assertEqual(documento.estado, 'observado')
        self.assertIn('corte', documento.observacion)
        # Lo observado cuenta como incumplimiento de la unidad.
        fila = cumplimiento_de_unidad(self.laboratorio, 2026, 'A', hoy=date(2026, 9, 22))
        self.assertGreater(fila['observados'], 0)
        self.assertEqual(fila['semaforo'], 'incumple')

    def test_validar_sube_el_cumplimiento_de_la_unidad(self):
        documento = self.documento('INFORME-SEMESTRAL')
        self.client.force_login(self.coordinador)
        url = reverse('gestion_expediente_unidad', args=[self.laboratorio.slug])
        antes = cumplimiento_de_unidad(self.laboratorio, 2026, 'A', hoy=date(2026, 9, 22))

        self.firmar_y_cargar(url, documento)
        self.client.post(url, {'anio': 2026, 'documento': documento.pk, 'accion': 'validar'})

        despues = cumplimiento_de_unidad(self.laboratorio, 2026, 'A', hoy=date(2026, 9, 22))
        self.assertEqual(despues['validados'], antes['validados'] + 1)
        self.assertEqual(despues['vencidos'], antes['vencidos'] - 1)


class MejoraContinuaTests(BaseDeCumplimiento):
    """El incumplimiento entra como hallazgo, sin que nadie lo transcriba."""

    def test_el_informe_recoge_lo_incumplido_en_su_apartado_de_mejora(self):
        from apps.documentos.presentation.expediente_redaccion import (
            _bloques_de_mejora_formal, incumplimientos_del_periodo,
        )

        documentos = construir_expediente(self.laboratorio, 2026, date(2026, 9, 22))
        # Las acciones de mejora van en la sección 8 del informe (documentos.0025), no en un anexo aparte.
        self.assertNotIn('ACCIONES-MEJORA', {d.exigido.codigo for d in documentos})
        informe = next(d for d in documentos if d.exigido.codigo == 'INFORME-SEMESTRAL' and d.corte == 'A')

        filas = incumplimientos_del_periodo(informe)

        self.assertTrue(filas)
        # Cada hallazgo trae qué documento, de qué período y por qué incumple.
        documento, periodo, estado, vencio, atraso, motivo = filas[0]
        self.assertTrue(documento)
        self.assertEqual(estado, 'Vencido')
        self.assertIn('plazo', motivo)
        # El informe los presenta tal cual, sin que nadie los transcriba.
        tabla = next(b for b in _bloques_de_mejora_formal(informe)
                     if b['titulo'] == 'Entregas del expediente fuera de plazo u observadas')
        self.assertEqual(tabla['filas'], filas)


class DocumentoEnviadoTests(BaseDeCumplimiento):
    """Validar es entregar: la fila lo dice y ofrece el documento final."""

    def entregar(self, codigo='INFORME-SEMESTRAL', corte='A'):
        documento = next(
            d for d in construir_expediente(self.laboratorio, 2026, date(2026, 9, 22))
            if d.exigido.codigo == codigo and d.corte == corte)
        url = reverse('gestion_expediente_unidad', args=[self.laboratorio.slug])
        self.firmar_y_cargar(url, documento, corte)
        self.client.post(url, {'anio': 2026, 'documento': documento.pk, 'accion': 'validar'})
        documento.refresh_from_db()
        return documento, url

    def test_la_fila_entregada_muestra_el_documento_final_y_quien_lo_envio(self):
        self.client.force_login(self.coordinador)
        documento, url = self.entregar()

        pagina = self.client.get(url, {'anio': 2026, 'corte': 'A'})

        contenido = pagina.content.decode()
        self.assertIn('data-estado-entrega="enviados"', contenido)
        self.assertIn('Enviado', contenido)
        self.assertIn(reverse('recurso_unidad', args=[documento.recurso_id]), contenido)
        enviado = next(a for a in enlaces_de(contenido)
            if a.get('href') == reverse('recurso_unidad', args=[documento.recurso_id]))
        self.assertIn('data-ver-pdf', enviado)
        self.assertNotIn('target', enviado)
        self.assertNotIn('data-pdf-directo', enviado)
        self.assertTrue(enviado.get('data-pdf-titulo'))
        self.assertIn('is-pdf', enviado.get('class', '').split())
        detalle = self.client.get(url, {'anio': 2026, 'corte': 'A', 'gestionar': documento.pk, 'fragment': '1'})
        self.assertContains(detalle, 'Documento enviado.')

    def test_las_acciones_permiten_preparar_o_cargar_el_documento_faltante(self):
        """Sin archivo, la tabla ofrece completar la entrega y no simula su envío."""
        self.client.force_login(self.coordinador)
        url = reverse('gestion_expediente_unidad', args=[self.laboratorio.slug])

        contenido = self.client.get(url, {'anio': 2026, 'corte': 'A'}).content.decode()

        for columna in ('Estado', 'Avance', 'Fechas', 'Observaciones', 'Acciones'):
            self.assertIn(f'data-columna="{columna}"', contenido)
        cargas = [a for a in enlaces_de(contenido) if 'is-cargar' in a.get('class', '').split()]
        self.assertTrue(cargas)
        self.assertTrue(all('data-entrega-abrir' in a for a in cargas))
        self.assertIn('data-estado-entrega="pendientes"', contenido)

    def test_la_ultima_columna_avisa_que_falta_validarlo_para_enviarlo(self):
        """Archivar no es enviar: la columna lo dice y ofrece ver el PDF."""
        documento = next(
            d for d in construir_expediente(self.laboratorio, 2026, date(2026, 9, 22))
            if d.exigido.codigo == 'INFORME-SEMESTRAL' and d.corte == 'A')
        self.client.force_login(self.coordinador)
        url = reverse('gestion_expediente_unidad', args=[self.laboratorio.slug])

        self.firmar_y_cargar(url, documento)
        contenido = self.client.get(url, {'anio': 2026, 'corte': 'A'}).content.decode()

        self.assertIn('Listo para enviar', contenido)
        borrador = next(a for a in enlaces_de(contenido)
            if parse_qs(urlsplit(a.get('href', '')).query).get('gestionar') == [str(documento.pk)]
            and parse_qs(urlsplit(a.get('href', '')).query).get('borrador') == ['1'])
        self.assertIn('data-ver-pdf', borrador)
        self.assertNotIn('target', borrador)
        self.assertNotIn('data-pdf-directo', borrador)
        self.assertTrue(borrador.get('data-pdf-titulo'))
        # Se abre con «Ver», como cualquier documento: no es un borrador que validar aparte.
        self.assertIn('is-pdf', borrador.get('class', '').split())
        self.assertTrue(any('is-cargar' in a.get('class', '').split() for a in enlaces_de(contenido)))
        self.assertNotIn('data-estado-entrega="enviados"', contenido)

    def test_lo_enviado_no_se_reemplaza(self):
        """Inmutable: ni botón ni acción. Solo la Dirección lo devuelve observado."""
        self.client.force_login(self.coordinador)
        documento, url = self.entregar()

        contenido = self.client.get(url, {'anio': 2026, 'corte': 'A'}).content.decode()
        self.assertNotIn('Reemplazar el documento enviado', contenido)
        self.assertNotIn('expediente__reemplazo', contenido)

        version_enviada = documento.version
        abrir_entrega(documento)
        respuesta = self.client.post(url, {'anio': 2026, 'documento': documento.pk, 'accion': 'generar'},
                                     follow=True)
        self.assertContains(respuesta, 'no se reemplaza')
        documento.refresh_from_db()
        self.assertEqual((documento.estado, documento.version), ('validado', version_enviada))
    def test_la_direccion_abre_lo_que_la_unidad_le_envio(self):
        self.client.force_login(self.coordinador)
        documento, _url = self.entregar()
        self.client.logout()
        self.client.force_login(self.direccion)

        pagina = self.client.get(
            reverse('admin:reportes-cumplimiento-expediente'), {'anio': 2026, 'corte': 'A'})

        contenido = pagina.content.decode()
        # La Dirección conserva el tablero y abre el documento en el visor.
        enviado = next(a for a in enlaces_de(contenido)
            if a.get('href') == reverse('recurso_unidad', args=[documento.recurso.pk]))
        self.assertIn('data-ver-pdf', enviado)
        self.assertNotIn('target', enviado)
        self.assertNotIn('data-pdf-directo', enviado)
        self.assertIn(reverse('recurso_unidad', args=[documento.recurso.pk]), contenido)

    def test_lo_entregado_sale_en_la_fila_de_la_unidad(self):
        self.client.force_login(self.coordinador)
        documento, _url = self.entregar()

        fila = cumplimiento_de_unidad(self.laboratorio, 2026, 'A', hoy=date(2026, 9, 22))

        self.assertIn(documento.pk, [f['documento'].pk for f in fila['matriz'] if f['enviado']])
        self.assertNotIn(documento.pk, [f['documento'].pk for f in fila['incumplimientos']])


class PeriodoDelExpedienteTests(BaseDeCumplimiento):
    """El expediente se lleva período a período; lo anterior queda a un clic."""

    def test_el_periodo_vigente_es_el_que_contiene_hoy(self):
        cortes = cortes_del_anio(2026)

        self.assertEqual(periodo_vigente(cortes, date(2026, 3, 1)), 'A')
        self.assertEqual(periodo_vigente(cortes, date(2026, 9, 22)), 'B')

    def test_entre_periodos_sigue_abierto_el_que_ya_empezo(self):
        """Al cerrar A todavía se entregan sus informes: no salta a B antes de tiempo."""
        cortes = {'A': (date(2026, 1, 1), date(2026, 6, 30)),
                  'B': (date(2026, 8, 17), date(2026, 12, 8))}

        self.assertEqual(periodo_vigente(cortes, date(2026, 7, 15)), 'A')
        self.assertEqual(periodo_vigente(cortes, date(2025, 12, 1)), 'A')

    def test_el_recorte_deja_lo_del_periodo_y_lo_anual(self):
        documentos = construir_expediente(self.laboratorio, 2026, date(2026, 9, 22))
        cortes = cortes_del_anio(2026)

        del_b = del_periodo(documentos, 'B', cortes)

        self.assertTrue(del_b)
        self.assertFalse([d for d in del_b if d.corte == 'A'])
        # Lo anual pertenece al año, así que se ve desde cualquiera de los dos.
        anuales = [d for d in documentos if not d.corte and not d.mes]
        self.assertTrue(anuales)
        for documento in anuales:
            self.assertIn(documento.pk, [d.pk for d in del_b])

    def test_la_pantalla_abre_en_el_periodo_vigente(self):
        self.client.force_login(self.coordinador)
        url = reverse('gestion_expediente_unidad', args=[self.laboratorio.slug])

        pagina = self.client.get(url, {'anio': 2026})

        self.assertEqual(pagina.context['corte'], periodo_vigente(cortes_del_anio(2026), timezone.localdate()))
        self.assertEqual([p['corte'] for p in pagina.context['periodos']], [pagina.context['corte']])

    def test_un_anio_pasado_se_lee_entero(self):
        self.client.force_login(self.coordinador)
        url = reverse('gestion_expediente_unidad', args=[self.laboratorio.slug])

        pagina = self.client.get(url, {'anio': 2025})

        self.assertEqual(pagina.context['corte'], '')
        self.assertEqual(pagina.context['etiqueta_periodo'], 'Año 2025')

    def test_el_historico_lista_los_periodos_con_lo_entregado(self):
        construir_expediente(self.laboratorio, 2026, date(2026, 9, 22))
        self.client.force_login(self.coordinador)
        url = reverse('gestion_expediente_unidad', args=[self.laboratorio.slug])

        pagina = self.client.get(url, {'anio': 2026, 'corte': 'B'})

        historico = pagina.context['historico']
        self.assertIn('2026-A', [fila['etiqueta'] for fila in historico])
        # El período abierto no se repite dentro de su propio histórico.
        self.assertNotIn('2026-B', [fila['etiqueta'] for fila in historico])
        self.assertContains(pagina, 'Histórico por período')

    def test_el_anexo_al_dia_se_abre_sin_marca_de_borrador(self):
        """El anexo que se consulta es el mismo formato que se archiva: sin marca de agua."""
        from io import BytesIO

        from pypdf import PdfReader

        self.client.force_login(self.coordinador)
        respuesta = self.client.get(reverse('gestion_expediente_unidad', args=[self.laboratorio.slug]), {
            'anio': 2026, 'corte': 'A', 'gestionar': 'INFORME-SEMESTRAL', 'anexo': 'REGISTRO-USO', 'borrador': '1'})
        self.assertEqual(respuesta.status_code, 200)
        cuerpo = (b''.join(respuesta.streaming_content) if getattr(respuesta, 'streaming', False)
                  else respuesta.content)
        texto = '\n'.join(pagina.extract_text() or '' for pagina in PdfReader(BytesIO(cuerpo)).pages)
        self.assertIn('REGISTROS DE USO', texto.upper())
        self.assertNotIn('BORRADOR', texto.upper())

    def test_el_anexo_al_dia_se_consulta_en_otro_rango_de_fechas_y_lleva_su_numero(self):
        """El visor ofrece el filtro de fechas; el anexo dice que es una consulta y conserva su número."""
        from io import BytesIO

        from pypdf import PdfReader

        self.client.force_login(self.coordinador)
        url = reverse('gestion_expediente_unidad', args=[self.laboratorio.slug])
        pagina = self.client.get(url, {'anio': 2026, 'corte': 'B'}).content.decode()
        cortes = cortes_del_anio(2026)
        enlace = next(a for a in enlaces_de(pagina) if 'anexo=REGISTRO-USO' in a.get('href', '')
                      and 'borrador=1' in a.get('href', ''))
        self.assertIn('anexo=REGISTRO-USO', enlace['data-pdf-rango'])
        self.assertEqual((enlace['data-pdf-desde'], enlace['data-pdf-hasta']),
                         (cortes['B'][0].isoformat(), cortes['B'][1].isoformat()))

        def texto(**fechas):
            respuesta = self.client.get(url, {'anio': 2026, 'corte': 'B', 'gestionar': 'INFORME-SEMESTRAL',
                                              'anexo': 'REGISTRO-USO', 'borrador': '1', **fechas})
            self.assertEqual(respuesta.status_code, 200)
            cuerpo = (b''.join(respuesta.streaming_content) if getattr(respuesta, 'streaming', False)
                      else respuesta.content)
            return ' '.join('\n'.join(p.extract_text() or '' for p in PdfReader(BytesIO(cuerpo)).pages).split())

        del_periodo = texto()
        # Sin fila guardada todavía, el anexo lleva el número que tendrá en el informe.
        self.assertIn('Anexo 1', del_periodo)
        self.assertIn('1.1 SESIONES DEL PERÍODO', del_periodo)
        self.assertNotIn('Consulta del', del_periodo)
        consulta = texto(desde='2026-09-01', hasta='2026-09-30')
        self.assertIn('Consulta del 01/09/2026 al 30/09/2026', consulta)
        # Un rango inválido o incompleto se ignora y se muestra el período.
        self.assertNotIn('Consulta del', texto(desde='2026-09-30', hasta='2026-09-01'))
        self.assertNotIn('Consulta del', texto(desde='ayer', hasta='2026-09-01'))

    def test_cada_documento_abre_su_informe_con_las_fechas_del_periodo(self):
        """Del documento al informe completo, ya acotado: no hay que volver a filtrar."""
        self.client.force_login(self.coordinador)
        url = reverse('gestion_expediente_unidad', args=[self.laboratorio.slug])
        cortes = cortes_del_anio(2026)

        pagina = self.client.get(url, {'anio': 2026, 'corte': 'A'})

        # El visor conserva la entrega, las consultas y el período elegidos.
        contenido = pagina.content.decode()
        self.assertIn('anexo=PRACTICAS-FT02&amp;borrador=1', contenido)
        self.assertIn('corte=A&amp;gestionar=INFORME-SEMESTRAL', contenido)
        enlaces = enlaces_de(contenido)
        anexo = next(a for a in enlaces
                     if parse_qs(urlsplit(a.get('href', '')).query).get('anexo') == ['PRACTICAS-FT02'])
        self.assertIn('data-ver-pdf', anexo)
        self.assertNotIn('target', anexo)
        self.assertNotIn('data-pdf-directo', anexo)
        self.assertEqual(parse_qs(urlsplit(anexo['href']).query)['corte'], ['A'])
        for consulta in pagina.context['consultas']:
            enlace = next(a for a in enlaces if a.get('href') == consulta['url'])
            query = parse_qs(urlsplit(enlace['href']).query)
            self.assertEqual(query['desde'], [str(cortes['A'][0])])
            self.assertEqual(query['hasta'], [str(cortes['A'][1])])
            self.assertIn('data-ver-pdf', enlace)
            self.assertNotIn('target', enlace)
            self.assertNotIn('data-pdf-directo', enlace)
            self.assertTrue(enlace.get('data-pdf-rango'))
            self.assertEqual(enlace.get('data-pdf-desde'), str(cortes['A'][0]))
            self.assertEqual(enlace.get('data-pdf-hasta'), str(cortes['A'][1]))

    def test_el_explorador_reune_los_respaldos_de_planificacion_y_cierre_en_una_tabla(self):
        """La tabla común conserva los dos padres y no duplica sus respaldos."""
        self.client.force_login(self.coordinador)
        url = reverse('gestion_expediente_unidad', args=[self.laboratorio.slug])

        pagina = self.client.get(url, {'anio': 2026, 'corte': 'A'})

        periodo = pagina.context['periodos'][0]
        self.assertEqual([e['nombre'] for e in periodo['entregas']], [
            'Planificación semestral del laboratorio',
            'Informe semestral de actividades y cumplimiento de la planificación'])
        codigos = {a.exigido.codigo for a in periodo['entregas'][1]['anexos']}
        # Un anexo por cada documento que pide la universidad (documentos.0027); la planificación, sin anexos.
        self.assertEqual(codigos, {'REGISTRO-USO', 'EQUIPAMIENTO', 'INVENTARIO-CORTE', 'FICHAS-TECNICAS',
                                   'PRACTICAS-FT02', 'GUIAS', 'PRACTICAS-FT03', 'INDUCCION-SEGURIDAD', 'DESECHOS',
                                   'INVESTIGACION', 'TRANSFERENCIA'})
        self.assertFalse({'PLAN-MANTENIMIENTO', 'INDICADORES-PLAN', 'PRESTAMOS-EQUIPOS', 'INSUMOS-CORTE',
                          'ACCIONES-MEJORA'} & codigos)
        plan = periodo['entregas'][0]
        self.assertEqual(plan['anexos'], [])
        self.assertEqual(plan['anexos_integrados'], [])
        self.assertEqual({d.exigido.codigo for d in pagina.context['de_la_unidad']},
                         {'RESOLUCION-CREACION', 'PROTOCOLO-BIOSEGURIDAD'})
        self.assertContains(pagina, '1. Documentos base de la unidad')
        self.assertContains(pagina, '2. Planificación y respaldo de actividades')
        self.assertContains(pagina, '3. Anexos y seguimiento')
        self.assertNotContains(pagina, 'data-soporte-planificacion=')
        self.assertContains(pagina, 'data-anexos-periodo="A"', count=1)
        self.assertContains(pagina, 'data-cierre-evidencias', count=1)
        self.assertNotContains(pagina, 'class="explorador__anexos"')
        self.assertContains(pagina, 'Validar y enviar', count=0)

    def test_abrir_un_documento_del_expediente_queda_en_la_auditoria(self):
        from apps.formacion.models.practicas import RegistroAuditoriaUnidad

        self.client.force_login(self.coordinador)
        url = reverse('gestion_expediente_unidad', args=[self.laboratorio.slug])
        documento = next(
            d for d in construir_expediente(self.laboratorio, 2026, date(2026, 9, 22))
            if d.exigido.codigo == 'INFORME-SEMESTRAL' and d.corte == 'A')
        self.firmar_y_cargar(url, documento)
        self.client.post(url, {'anio': 2026, 'documento': documento.pk, 'accion': 'validar'})
        documento.refresh_from_db()
        antes = RegistroAuditoriaUnidad.objects.filter(unidad=self.laboratorio, accion='consultar').count()

        self.client.get(reverse('recurso_unidad', args=[documento.recurso.pk]))
        self.client.get(reverse('recurso_unidad', args=[documento.recurso.pk]), {'download': '1'})

        registros = RegistroAuditoriaUnidad.objects.filter(unidad=self.laboratorio, accion='consultar')
        self.assertEqual(registros.count(), antes + 2)
        descripciones = ' '.join(registros.values_list('descripcion', flat=True))
        self.assertIn('Abrió Informe semestral', descripciones)
        self.assertIn('Descargó Informe semestral', descripciones)

    def test_la_direccion_y_la_unidad_cuentan_lo_mismo(self):
        """El tablero recorta el período igual que la pantalla de la unidad."""
        hoy = date(2026, 9, 22)
        fila = cumplimiento_de_unidad(self.laboratorio, 2026, 'A', hoy=hoy)
        documentos = construir_expediente(self.laboratorio, 2026, hoy)

        propios = del_periodo(documentos, 'A', cortes_del_anio(2026))

        self.assertEqual(fila['total'], resumen(propios, hoy)['total'])


class EvaluacionDeLaDireccionTests(BaseDeCumplimiento):
    """Un solo archivo recorre las cuatro carpetas; la Dirección lo califica de 0 a 100."""

    def informe_enviado(self, corte='A'):
        self.client.force_login(self.coordinador)
        url = reverse('gestion_expediente_unidad', args=[self.laboratorio.slug])
        documento = next(
            d for d in construir_expediente(self.laboratorio, 2026, date(2026, 9, 22))
            if d.exigido.codigo == 'INFORME-SEMESTRAL' and d.corte == corte)
        self.firmar_y_cargar(url, documento, corte)
        self.client.post(url, {'anio': 2026, 'documento': documento.pk, 'accion': 'validar'})
        documento.refresh_from_db()
        return documento, url

    def test_el_documento_recorre_las_carpetas_sin_duplicarse(self):
        from django.core.files.uploadedfile import SimpleUploadedFile

        hoy = date(2026, 9, 22)
        documentos = construir_expediente(self.laboratorio, 2026, hoy)
        informe_b = next(d for d in documentos if d.exigido.codigo == 'INFORME-SEMESTRAL' and d.corte == 'B')
        informe_a = next(d for d in documentos if d.exigido.codigo == 'INFORME-SEMESTRAL' and d.corte == 'A')

        # Todavía no se produjo y no venció: se planea.
        self.assertEqual(informe_b.etapa(hoy), 'planeacion')
        # Venció sin entregarse: cae en mejora continua aunque nadie lo evalúe.
        self.assertEqual(informe_a.etapa(hoy), 'mejora')
        # Con archivo, está en ejecución; enviado, en evaluación.
        from apps.documentos.presentation.expediente import anexos_del, validar_anexo
        cargar_documento_revisado(abrir_entrega(informe_a), SimpleUploadedFile('a.pdf', PDF_FIRMADO), self.coordinador)
        informe_a.refresh_from_db()
        self.assertEqual(informe_a.etapa(hoy), 'ejecucion')
        for anexo in anexos_del(informe_a):
            validar_anexo(anexo, self.coordinador)
        validar_documento(informe_a, self.coordinador)
        informe_a.refresh_from_db()
        self.assertEqual(informe_a.etapa(hoy), 'evaluacion')
        self.assertEqual(DocumentoExpediente.objects.filter(pk=informe_a.pk).count(), 1)

    def test_solo_la_direccion_evalua_y_bajo_el_minimo_exige_motivo(self):
        from django.core.exceptions import ValidationError

        documento, _url = self.informe_enviado()

        with self.assertRaises(ValidationError):
            evaluar_documento_revisado(documento, self.coordinador, 90)
        with self.assertRaises(ValidationError):
            evaluar_documento_revisado(documento, self.direccion, 120)
        with self.assertRaises(ValidationError):
            evaluar_documento_revisado(documento, self.direccion, 40, '')
        evaluar_documento_revisado(documento, self.direccion, 40, 'Faltan las evidencias de las prácticas.',
                          recomendaciones='Adjuntar FT03 con asistencia en cada práctica.')

        documento.refresh_from_db()
        self.assertEqual((documento.evaluacion, documento.cumple), (40, False))
        self.assertEqual(documento.etapa(date(2026, 9, 22)), 'mejora')
        self.assertEqual(documento.evaluado_por, self.direccion)

    def test_lo_que_cumple_queda_en_evaluacion_y_lo_que_no_es_hallazgo_de_mejora(self):

        documento, _url = self.informe_enviado()
        evaluar_documento_revisado(documento, self.direccion, 85, 'Bien sustentado.')
        documento.refresh_from_db()
        self.assertEqual(documento.etapa(date(2026, 9, 22)), 'evaluacion')
        fila = cumplimiento_de_unidad(self.laboratorio, 2026, 'A', hoy=date(2026, 9, 22))
        self.assertNotIn(documento.pk, [f['documento'].pk for f in fila['incumplimientos']])

        evaluar_documento_revisado(documento, self.direccion, 55, 'No compara el plan con lo realizado.',
                          recomendaciones='Comparar cada meta del plan con lo registrado.')
        fila = cumplimiento_de_unidad(self.laboratorio, 2026, 'A', hoy=date(2026, 9, 22))
        hallazgo = next(f for f in fila['incumplimientos'] if f['documento'].pk == documento.pk)
        self.assertIn('55', hallazgo['etiqueta'])
        self.assertIn('plan con lo realizado', hallazgo['motivo'])
        self.assertEqual(fila['semaforo'], 'incumple')
        self.assertGreater(fila['en_mejora'], 0)

    def test_la_unidad_no_ofrece_ni_admite_calificar_incluso_para_la_direccion(self):
        documento, url = self.informe_enviado()
        for usuario in (self.coordinador, self.direccion):
            self.client.force_login(usuario)
            pagina = self.client.get(url, {'anio': 2026, 'corte': 'A'})
            self.assertNotContains(pagina, 'value="evaluar"')
            self.assertNotContains(pagina, 'Guardar evaluación')
            for accion in ('evaluar', 'evaluar_rubrica'):
                respuesta = self.client.post(url, {
                    'anio': 2026, 'corte': 'A', 'documento': documento.pk,
                    'accion': accion, 'evaluacion': '92', 'evaluacion_observacion': 'Completo.',
                })
                self.assertEqual(respuesta.status_code, 403)
        documento.refresh_from_db()
        self.assertIsNone(documento.evaluacion)

        evaluar_documento_revisado(documento, self.direccion, 92, 'Completo.')
        documento.refresh_from_db()
        self.assertEqual(documento.evaluacion, 92)
        self.client.force_login(self.coordinador)
        pagina = self.client.get(url, {'anio': 2026, 'corte': 'A'})
        self.assertContains(pagina, 'Observaciones')
        self.assertRegex(pagina.content.decode(), r'Resultado:\s*92(?:[.,]0+)?\s*%')
        respuesta = self.client.get(url, {'anio': 2026, 'corte': 'A', 'gestionar': documento.pk,
                                          'vista': 'observaciones', 'fragment': '1'})
        # El resultado vive en su fila; las observaciones conservan el texto
        # atribuido de la revisión en el historial, sin ofrecer calificar.
        self.assertContains(respuesta, 'Historial')
        self.assertContains(respuesta, 'Completo.')
        self.assertContains(respuesta, self.direccion.username)
        self.assertNotContains(respuesta, 'data-rubrica')


class RevisionDeAnexosTests(BaseDeCumplimiento):
    """La unidad revisa cada anexo: puede salir vacío o con datos que no son."""

    def informe_firmado(self, codigo='INFORME-SEMESTRAL'):
        self.client.force_login(self.coordinador)
        url = reverse('gestion_expediente_unidad', args=[self.laboratorio.slug])
        documento = next(
            d for d in construir_expediente(self.laboratorio, 2026, date(2026, 9, 22))
            if d.exigido.codigo == codigo and d.corte == 'A')
        self.firmar_y_cargar(url, documento, revisar_anexos=False)
        return documento, url

    def test_planificacion_no_se_envia_con_anexos_sin_revisar(self):
        from django.core.exceptions import ValidationError

        # El catálogo distribuido no da anexos al plan; uno institucional también se revisa antes de enviar.
        DocumentoExigido.objects.create(codigo='SOPORTE-PLAN-PROPIO', nombre='Respaldo propio de la planificación',
            carpeta='planeacion', periodicidad='semestral', origen='sistema', fuente_reporte='asignaturas',
            plazo_regla='inicio', plazo_dias=15, orden=30,
            anexo_de=DocumentoExigido.objects.get(codigo='PLANIFICACION'))
        documento, _url = self.informe_firmado(codigo='PLANIFICACION')

        with self.assertRaises(ValidationError) as contexto:
            validar_documento(documento, self.coordinador)
        self.assertIn('Faltan por revisar y validar', ' '.join(contexto.exception.messages))
        documento.refresh_from_db()
        self.assertEqual(documento.estado, 'cargado')

    def test_cierre_envia_y_conserva_anexos_sin_marcas_manuales(self):
        from apps.documentos.presentation.expediente import anexos_del

        documento, url = self.informe_firmado()
        pagina = self.client.get(url, {'anio': 2026, 'corte': 'A'})
        self.assertContains(pagina, 'data-cierre-evidencias')
        self.assertNotContains(pagina, 'value="validar_anexo"')
        self.assertContains(pagina, 'Marcar un anexo como revisado no aumenta el resultado.')

        archivos = {a.pk: a.recurso_id for a in anexos_del(documento)}
        self.client.post(url, {'anio': 2026, 'corte': 'A', 'documento': documento.pk, 'accion': 'validar'})

        documento.refresh_from_db()
        self.assertEqual(documento.estado, 'validado')
        self.assertTrue(all(a.estado == 'validado' and a.validado_por == self.coordinador
                            for a in anexos_del(documento)))
        self.assertEqual({a.pk: a.recurso_id for a in anexos_del(documento)}, archivos)

    def test_actualizar_cierre_regenera_el_anexo_y_conserva_su_archivo_anterior(self):
        from apps.documentos.presentation.expediente import anexos_del, validar_anexo

        documento, url = self.informe_firmado()
        practicas = next(a for a in anexos_del(documento) if a.exigido.codigo == 'PRACTICAS-FT02')
        validar_anexo(practicas, self.coordinador)
        version = practicas.version
        anterior = practicas.recurso_id

        self.client.post(url, {'anio': 2026, 'corte': 'A', 'documento': documento.pk, 'accion': 'anexos'})

        practicas.refresh_from_db()
        self.assertEqual((practicas.estado, practicas.version), ('generado', version + 1))
        self.assertEqual(practicas.recurso.reemplaza_a_id, anterior)
        otro = next(a for a in anexos_del(documento) if a.exigido.codigo == 'REGISTRO-USO')
        self.assertEqual(otro.version, version + 1)

    def test_el_informe_en_pdf_enlaza_los_anexos_validados(self):
        from django.conf import settings
        from apps.documentos.presentation.expediente import anexos_del, validar_anexo
        from apps.documentos.presentation.expediente import tramo_del_documento
        from apps.documentos.presentation.expediente_redaccion import componer, obtener_redaccion

        documento, _url = self.informe_firmado()
        anexos = anexos_del(documento)
        validar_anexo(anexos[0], self.coordinador)

        inicio, fin = tramo_del_documento(documento)
        compuesto = componer(documento, obtener_redaccion(documento).contenido, inicio, fin)
        seccion = next(s for s in compuesto['secciones'] if s['codigo'] == 'anexos')
        items = seccion['bloques'][0]['items']

        # Un anexo que no aplica conserva su número y dice por qué, sin enlace: no tiene archivo que abrir.
        no_aplican = [i for i in items if ' · No aplica: ' in i['texto']]
        self.assertTrue(no_aplican)  # Sin registros de desechos ni plan que la comprometa, algo no aplica.
        self.assertEqual(len(no_aplican), len(anexos_del(documento, incluir_no_aplica=True)) - len(anexos))
        self.assertTrue(all('url' not in i for i in no_aplican))
        # Cada anexo que se presenta lleva su enlace.
        self.assertTrue(anexos and all(a.recurso_id for a in anexos))
        con_enlace = [i for i in items if i.get('url')]
        self.assertEqual(len(con_enlace), len(anexos))
        self.assertEqual(len(items), len(no_aplican) + len(con_enlace))
        self.assertTrue(con_enlace[0]['url'].startswith(settings.SITE_URL))
        self.assertIn(reverse('recurso_unidad', args=[anexos[0].recurso_id]), con_enlace[0]['url'])
        self.assertEqual({i['url'] for i in con_enlace}, {
            settings.SITE_URL.rstrip('/') + reverse('recurso_unidad', args=[a.recurso_id]) for a in anexos})


class MetasDelPeriodoTests(BaseDeCumplimiento):
    """El sistema dice si la meta se cumplió; la unidad no tiene que jurarlo."""

    def test_el_veredicto_compara_la_meta_con_lo_registrado(self):
        from apps.documentos.presentation.expediente_redaccion import veredicto_de_meta

        self.assertEqual(veredicto_de_meta({'meta': '≥ 6 por período', 'registrado': 7, 'codigo': 'PRACTICAS'}, {}), 'cumple')
        self.assertEqual(veredicto_de_meta({'meta': '6', 'registrado': 2, 'codigo': 'PRACTICAS'}, {}), 'no_cumple')
        self.assertEqual(veredicto_de_meta({'meta': 'según demanda', 'registrado': 2, 'codigo': 'SERVICIOS'}, {}), 'sin_medicion')
        self.assertEqual(veredicto_de_meta({'meta': '≥ 1', 'registrado': None, 'codigo': 'CAPACITACION'}, {}), 'sin_medicion')
        self.assertEqual(veredicto_de_meta(
            {'meta': '≥ 80 % de lo programado', 'registrado': 8, 'codigo': 'MANTENIMIENTO'},
            {'mantenimientos_criticos_programados': 10, 'mantenimientos_criticos_cumplidos': 8}), 'cumple')
        self.assertEqual(veredicto_de_meta(
            {'meta': '≥ 80 % de lo programado', 'registrado': 5, 'codigo': 'MANTENIMIENTO'},
            {'mantenimientos_criticos_programados': 10, 'mantenimientos_criticos_cumplidos': 5}), 'no_cumple')

    def test_el_expediente_muestra_las_metas_del_periodo_con_su_veredicto(self):
        from apps.documentos.presentation.expediente_redaccion import obtener_redaccion

        self.client.force_login(self.coordinador)
        url = reverse('gestion_expediente_unidad', args=[self.laboratorio.slug])
        documentos = construir_expediente(self.laboratorio, 2026, date(2026, 9, 22))
        plan = next(d for d in documentos if d.exigido.codigo == 'PLANIFICACION' and d.corte == 'A')
        redaccion = obtener_redaccion(plan)  # la planificación existe: hay metas que medir
        redaccion.contenido = {'actividades': {'catalogo': {'PRACTICAS': {'aplica': True, 'meta': '6'}}}}
        redaccion.save()

        pagina = self.client.get(url, {'anio': 2026, 'corte': 'A'})

        informe = next(e for e in pagina.context['periodos'][0]['entregas']
                       if e['documento'].exigido.codigo == 'INFORME-SEMESTRAL')
        self.assertTrue(informe['metas']['hay_plan'])
        self.assertGreater(informe['metas']['medibles'], 0)
        self.assertContains(pagina, 'Anexos y actividades')
        self.assertContains(pagina, 'data-anexos-periodo="A"', count=1)
        self.assertContains(pagina, 'data-cierre-evidencias', count=1)
        self.assertContains(pagina, 'data-indicador-anexo="PRACTICAS"')
        # Sin prácticas registradas, la meta institucional de seis no se cumple y el sistema lo dice.
        practicas = next(f for f in informe['metas']['filas'] if f['codigo'] == 'PRACTICAS')
        self.assertEqual(practicas['veredicto'], 'no_cumple')
        self.assertContains(pagina, 'No cumple')


class PeriodoPorDefectoDelCentroTests(BaseDeCumplimiento):
    def test_sin_fechas_todo_informe_sale_por_el_periodo_vigente(self):
        from apps.documentos.presentation.expediente import cortes_del_anio, periodo_vigente
        from apps.gestion_unidades.presentation.gestion_reportes import build_unit_report
        from django.test import RequestFactory

        hoy = timezone.localdate()
        cortes = cortes_del_anio(hoy.year)
        esperado = cortes[periodo_vigente(cortes, hoy)]
        for categoria in ('reservas', 'guias', 'finanzas'):
            peticion = RequestFactory().get('/', {'categoria_reporte': categoria})
            peticion.user = self.coordinador
            reporte = build_unit_report(peticion, self.laboratorio)
            self.assertEqual((reporte['start_date'], reporte['end_date']), esperado, categoria)
        # Con fechas, manda lo que se pidió.
        peticion = RequestFactory().get('/', {'categoria_reporte': 'reservas', 'desde': '2026-03-01', 'hasta': '2026-03-31'})
        peticion.user = self.coordinador
        reporte = build_unit_report(peticion, self.laboratorio)
        self.assertEqual((reporte['start_date'], reporte['end_date']), (date(2026, 3, 1), date(2026, 3, 31)))


class EvaluacionRobustaTests(BaseDeCumplimiento):
    """Fortalezas, debilidades y recomendaciones: la siguiente planificación las responde."""

    def enviado(self, codigo='INFORME-SEMESTRAL', corte='A'):
        self.client.force_login(self.coordinador)
        url = reverse('gestion_expediente_unidad', args=[self.laboratorio.slug])
        documento = next(
            d for d in construir_expediente(self.laboratorio, 2026, date(2026, 9, 22))
            if d.exigido.codigo == codigo and d.corte == corte)
        self.firmar_y_cargar(url, documento, corte)
        self.client.post(url, {'anio': 2026, 'documento': documento.pk, 'accion': 'validar'})
        documento.refresh_from_db()
        return documento, url

    def test_bajo_el_minimo_exige_recomendaciones(self):
        from django.core.exceptions import ValidationError

        documento, _url = self.enviado()

        with self.assertRaises(ValidationError) as contexto:
            evaluar_documento_revisado(documento, self.direccion, 50, debilidades='No sustenta las horas.')
        self.assertIn('recomendar', ' '.join(contexto.exception.messages))
        evaluar_documento_revisado(documento, self.direccion, 50, debilidades='No sustenta las horas.',
                          fortalezas='Registra todas las sesiones.',
                          recomendaciones='Adjuntar la bitácora de cada práctica.')
        documento.refresh_from_db()
        self.assertEqual(documento.evaluacion_recomendaciones, 'Adjuntar la bitácora de cada práctica.')
        fila = cumplimiento_de_unidad(self.laboratorio, 2026, 'A', hoy=date(2026, 9, 22))
        hallazgo = next(f for f in fila['incumplimientos'] if f['documento'].pk == documento.pk)
        self.assertIn('Recomendación: Adjuntar la bitácora', hallazgo['motivo'])

    def test_la_unidad_ve_la_evaluacion_completa_en_su_expediente(self):

        documento, url = self.enviado()
        evaluar_documento_revisado(documento, self.direccion, 88, 'Cumple.', fortalezas='Buen registro de uso.',
                          debilidades='Pocas guías nuevas.', recomendaciones='Actualizar dos guías en 2026-B.')

        pagina = self.client.get(url, {'anio': 2026, 'corte': 'A', 'gestionar': documento.pk, 'fragment': '1',
                                      'vista': 'observaciones'})

        self.assertContains(pagina, 'Buen registro de uso.')
        self.assertContains(pagina, 'Pocas guías nuevas.')
        self.assertContains(pagina, 'Historial')
        self.assertContains(pagina, 'Actualizar dos guías en 2026-B.')
        historial = pagina.context['observaciones_documentales']['historial']
        self.assertTrue(any(c['campo'] == 'evaluacion_recomendaciones'
            and c['texto'] == 'Actualizar dos guías en 2026-B.' for c in historial))
        self.assertNotContains(pagina, 'name="evaluacion_fortalezas"')

    def test_la_siguiente_planificacion_trae_lo_evaluado_y_la_direccion_lo_tiene_a_mano(self):
        from apps.documentos.presentation.expediente import evaluaciones_del_periodo_anterior, tramo_del_documento
        from apps.documentos.presentation.expediente_redaccion import componer, obtener_redaccion

        documento, url = self.enviado()
        evaluar_documento_revisado(documento, self.direccion, 60, debilidades='Sin evidencias de prácticas.',
                          recomendaciones='Cargar FT03 con asistencia en cada práctica.')

        previas = evaluaciones_del_periodo_anterior(self.laboratorio, 2026, 'B')
        self.assertEqual([p.pk for p in previas], [documento.pk])

        plan_b = next(
            d for d in construir_expediente(self.laboratorio, 2026, date(2026, 9, 22))
            if d.exigido.codigo == 'PLANIFICACION' and d.corte == 'B')
        inicio, fin = tramo_del_documento(plan_b)
        compuesto = componer(plan_b, obtener_redaccion(plan_b).contenido, inicio, fin)
        seccion = next(s for s in compuesto['secciones'] if s['codigo'] == 'mejora_previa')
        pares = dict(seccion['bloques'][0]['pares'])
        self.assertEqual(pares['Cumplimiento evaluado'], '60 %')
        self.assertIn('Cargar FT03', pares['Recomendaciones'])

        self.client.force_login(self.direccion)
        pagina = self.client.get(reverse('vista_previa_documento_expediente',
                                        args=[self.laboratorio.slug, plan_b.pk]))
        self.assertContains(pagina, 'EVALUACIÓN DEL PERÍODO ANTERIOR')
        self.assertContains(pagina, 'Cargar FT03 con asistencia')


class GeneracionExplicitaDeAnexosTests(BaseDeCumplimiento):
    """Consultar no genera archivos: una acción explícita produce los anexos."""

    def test_abrir_no_genera_y_el_post_produce_los_anexos(self):
        self.client.force_login(self.coordinador)
        url = reverse('gestion_expediente_unidad', args=[self.laboratorio.slug])
        antes = construir_expediente(self.laboratorio, 2026, date(2026, 9, 22))
        self.assertFalse([d for d in antes if d.exigido.es_anexo and d.recurso_id])

        pagina = self.client.get(url, {'anio': 2026, 'corte': 'A'})

        periodo = pagina.context['periodos'][0]
        for entrega in periodo['entregas']:
            self.assertEqual(entrega['anexos_listos'], 0)
            self.client.post(url, {'anio': 2026, 'corte': 'A',
                                  'documento': entrega['documento'].pk, 'accion': 'anexos'})
        pagina = self.client.get(url, {'anio': 2026, 'corte': 'A'})
        for entrega in pagina.context['periodos'][0]['entregas']:
            self.assertEqual(entrega['anexos_listos'], len(entrega['anexos']))
        self.assertContains(pagina, 'Ver documento')
        self.assertContains(pagina, 'data-ver-pdf')
        # La consulta no cambia la generación explícita ni sustituye los envíos.
        self.assertNotContains(pagina, 'data-pdf-directo')
        self.assertNotContains(pagina, 'Ver el informe completo')

    def test_el_informe_al_dia_y_las_consultas_se_abren_en_el_visor(self):
        self.client.force_login(self.coordinador)
        url = reverse('gestion_expediente_unidad', args=[self.laboratorio.slug])

        pagina = self.client.get(url, {'anio': 2026, 'corte': 'A'})

        pdf = reverse('gestion_reporte_unidad_pdf', args=[self.laboratorio.slug])
        self.assertContains(pagina, 'anexo=PRACTICAS-FT02&amp;borrador=1')
        self.assertContains(pagina, 'Informes de gestión')
        # Solo se ofrecen las consultas con registros de la unidad; la auditoría, siempre.
        consultas = pagina.content.decode().split('id="informes-gestion"', 1)[1].split('</section>', 1)[0]
        self.assertIn(f'{pdf}?categoria_reporte=auditoria', consultas)
        self.assertNotIn(f'{pdf}?categoria_reporte=aula', consultas)
        enlaces = [a for a in enlaces_de(pagina.content.decode())
            if a.get('href', '').startswith(pdf)]
        self.assertTrue(enlaces)
        for enlace in enlaces:
            self.assertIn('data-ver-pdf', enlace)
            self.assertNotIn('target', enlace)
            self.assertNotIn('data-pdf-directo', enlace)
        # Lo que es evidencia no se repite como consulta.
        self.assertNotIn('reservas', {c['codigo'] for c in pagina.context['consultas']})
        # Finanzas no se ofrece sin movimientos de la unidad.
        self.assertNotIn('finanzas', {c['codigo'] for c in pagina.context['consultas']})

    def test_las_consultas_van_visibles_en_la_tabla_de_anexos_del_periodo(self):
        """Con un período elegido son la última categoría de la tabla de anexos."""
        self.client.force_login(self.coordinador)
        url = reverse('gestion_expediente_unidad', args=[self.laboratorio.slug])
        html = self.client.get(url, {'anio': 2026, 'corte': 'A'}).content.decode()
        self.assertEqual(html.count('id="informes-gestion"'), 1)
        # Nada plegado: ni <details> ni sección aparte; van dentro de la tabla de anexos.
        self.assertNotIn('reportes-consultas-visibles', html)
        tabla = html.split('data-cierre-evidencias', 1)[1].split('</table>', 1)[0]
        categoria = tabla.split('id="informes-gestion"', 1)[1]
        self.assertIn('Consultas de gestión · no se entregan ni puntúan', categoria)
        self.assertIn('data-consulta-gestion', categoria)
        self.assertIn('categoria_reporte=auditoria', categoria)
        self.assertIn('data-pdf-rango', categoria)
        # Van después de los anexos del informe, no entre ellos.
        self.assertNotIn('data-meta-bloque', categoria)

    def test_actualizar_anexos_vuelve_a_producirlos_con_lo_registrado(self):
        self.client.force_login(self.coordinador)
        url = reverse('gestion_expediente_unidad', args=[self.laboratorio.slug])
        self.client.get(url, {'anio': 2026, 'corte': 'A'})
        informe = next(
            d for d in construir_expediente(self.laboratorio, 2026, date(2026, 9, 22))
            if d.exigido.codigo == 'INFORME-SEMESTRAL' and d.corte == 'A')
        practicas = next(
            d for d in construir_expediente(self.laboratorio, 2026, date(2026, 9, 22))
            if d.exigido.codigo == 'PRACTICAS-FT02' and d.corte == 'A')
        self.assertEqual(practicas.version, 0)
        self.client.post(url, {'anio': 2026, 'corte': 'A', 'documento': informe.pk, 'accion': 'anexos'})
        practicas.refresh_from_db()
        self.assertEqual(practicas.version, 1)

        self.client.post(url, {'anio': 2026, 'corte': 'A', 'documento': informe.pk, 'accion': 'anexos'})

        practicas.refresh_from_db()
        self.assertEqual(practicas.version, 2)
