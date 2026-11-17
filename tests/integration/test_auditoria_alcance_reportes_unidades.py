"""Alcance de reportes y emisión desde la vista previa de las cuatro tipologías."""
from copy import deepcopy
from datetime import date
from pathlib import Path
from tempfile import TemporaryDirectory

from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.files.base import ContentFile
from django.test import TestCase, override_settings
from django.urls import reverse

from apps.directorio_unidades.models.core import Unidad
from apps.documentos.models.expediente import DocumentoElaborado, DocumentoExigido, DocumentoExpediente
from apps.documentos.presentation.expediente_catalogo import asegurar_catalogo
from apps.documentos.presentation.expediente_redaccion import componer, obtener_redaccion
from apps.recursos.models.recursos import CarpetaRecurso, Recurso
from tests.integration.test_seguimiento_gobernanza import designar
from tests.integration.utiles import abrir_entrega, identificar, pdf_legible_prueba


class BaseAlcanceReportes(TestCase):
    @classmethod
    def setUpTestData(cls):
        asegurar_catalogo()
        cls.unidades, cls.usuarios, cls.documentos = {}, {}, {}
        for tipo in ('laboratorios', 'plantas_piloto', 'centro_experimental', 'observatorios'):
            usuario = get_user_model().objects.create_user('alcance-' + tipo, password=None)
            identificar(usuario, tipo_usuario='administrativo', carrera='')
            unidad = Unidad.objects.create(nombre='Unidad de alcance ' + tipo, slug='alcance-' + tipo,
                dependencia=tipo, fecha_inicio=date(2026, 1, 1), administrador=usuario, activo=True)
            cls.unidades[tipo], cls.usuarios[tipo] = unidad, usuario
            cls.documentos[tipo] = DocumentoExpediente.objects.create(unidad=unidad,
                exigido=DocumentoExigido.objects.get(codigo='PLANIFICACION'), anio=2026, corte='B')
        cls.direccion = get_user_model().objects.create_superuser('direccion-alcance-reportes', password=None)
        designar(cls.direccion)

    def setUp(self):
        self.media = self.enterContext(TemporaryDirectory(prefix='citt-auditoria-alcance-'))
        self.enterContext(override_settings(MEDIA_ROOT=self.media))

    def consultas(self, unidad, **extras):
        datos = {'categoria_reporte': 'reservas', 'desde': '2026-08-17', 'hasta': '2026-10-17', **extras}
        for nombre, formato in (('gestion_reporte_unidad', ''), ('gestion_reporte_unidad_pdf', ''),
                                ('gestion_reporte_unidad_xlsx', ''), ('gestion_reporte_unidad', 'csv')):
            yield reverse(nombre, args=[unidad.slug]), dict(datos, **({'formato': formato} if formato else {}))


class AlcanceReportesCuatroTiposTests(BaseAlcanceReportes):
    def test_las_cuatro_unidades_consultan_su_reporte_y_ninguna_exporta_los_de_otra(self):
        for tipo, usuario in self.usuarios.items():
            self.client.force_login(usuario)
            propia = self.unidades[tipo]
            self.assertEqual(self.client.get(reverse('gestion_reporte_unidad', args=[propia.slug])).status_code, 200)
            for otro_tipo, ajena in self.unidades.items():
                if otro_tipo == tipo:
                    continue
                for ruta, datos in self.consultas(ajena):
                    with self.subTest(usuario=tipo, ajena=otro_tipo, ruta=ruta, formato=datos.get('formato')):
                        self.assertEqual(self.client.get(ruta, datos).status_code, 403)

    def test_categoria_inexistente_o_de_otro_perfil_no_se_convierte_en_reporte_de_reservas(self):
        for tipo, unidad in self.unidades.items():
            self.client.force_login(self.usuarios[tipo])
            categorias = ['inexistente']
            if tipo == 'observatorios':
                categorias += ['planificaciones', 'desechos', 'guias']
            if tipo == 'laboratorios':
                categorias += ['datos-observatorio', 'control-calidad', 'ensayos']
            for categoria in categorias:
                for ruta, datos in self.consultas(unidad, categoria_reporte=categoria):
                    with self.subTest(tipo=tipo, categoria=categoria, ruta=ruta):
                        self.assertEqual(self.client.get(ruta, datos).status_code, 400)

    def test_fechas_imposibles_no_producen_exportaciones_en_ningun_tipo(self):
        for tipo, unidad in self.unidades.items():
            self.client.force_login(self.usuarios[tipo])
            for ruta, datos in self.consultas(unidad, desde='2026-02-31'):
                with self.subTest(tipo=tipo, ruta=ruta):
                    self.assertEqual(self.client.get(ruta, datos).status_code, 400)

    def test_documento_id_ajeno_no_abre_editor_vista_previa_pdf_ni_historial(self):
        for tipo, unidad in self.unidades.items():
            self.client.force_login(self.usuarios[tipo])
            ajeno = next(d for otro, d in self.documentos.items() if otro != tipo)
            for nombre in ('redactar_documento_expediente', 'vista_previa_documento_expediente',
                           'pdf_borrador_documento_expediente'):
                with self.subTest(tipo=tipo, vista=nombre):
                    self.assertEqual(self.client.get(reverse(nombre, args=[unidad.slug, ajeno.pk])).status_code, 404)
            ruta = reverse('gestion_expediente_unidad', args=[unidad.slug])
            self.assertEqual(self.client.get(ruta, {'anio': 2026, 'corte': 'B',
                'gestionar': ajeno.pk, 'archivo': 1}).status_code, 404)

    def test_recurso_de_cada_expediente_exige_acceso_a_su_unidad(self):
        for tipo, unidad in self.unidades.items():
            carpeta = CarpetaRecurso.objects.create(unidad=unidad, nombre='Expediente interno',
                visibilidad='interna', del_expediente=True)
            recurso = Recurso(unidad=unidad, carpeta=carpeta, nombre='Documento de ' + tipo,
                visibilidad='interna', descargar=True)
            recurso.archivo.save(tipo + '.pdf', ContentFile(pdf_legible_prueba('Respaldo de ' + tipo)))
            documento = self.documentos[tipo]
            documento.recurso, documento.estado, documento.version = recurso, 'cargado', 1
            documento.save(update_fields=['recurso', 'estado', 'version'])
            ruta = reverse('recurso_unidad', args=[recurso.pk])
            self.client.force_login(self.usuarios[tipo])
            respuesta = self.client.get(ruta, {'download': '1'})
            self.assertEqual(respuesta.status_code, 200)
            self.assertEqual(b''.join(respuesta.streaming_content), Path(recurso.archivo.path).read_bytes())
            for otro, usuario in self.usuarios.items():
                if otro != tipo:
                    self.client.force_login(usuario)
                    with self.subTest(tipo=tipo, usuario=otro):
                        self.assertEqual(self.client.get(ruta).status_code, 404)
            self.client.logout()
            self.assertEqual(self.client.get(ruta).status_code, 404)

    def test_administrador_no_amplia_el_selector_para_leer_documento_de_otra_unidad(self):
        self.client.force_login(self.direccion)
        ruta = reverse('admin:reportes-cumplimiento-expediente')
        for tipo, unidad in self.unidades.items():
            ajeno = next(d for otro, d in self.documentos.items() if otro != tipo)
            for selector in ('archivos', 'revisar', 'plazos'):
                with self.subTest(tipo=tipo, selector=selector):
                    respuesta = self.client.get(ruta, {'anio': 2026, 'corte': 'B',
                        'unidad': unidad.slug, selector: ajeno.pk})
                    self.assertEqual(respuesta.status_code, 400)

    def test_editor_y_pdf_compuesto_conservan_nombre_y_referencia_interna_de_cada_perfil(self):
        prefijos = {'laboratorios': 'LAB', 'plantas_piloto': 'PP',
                    'centro_experimental': 'CE', 'observatorios': 'OBS'}
        for tipo, documento in self.documentos.items():
            self.client.force_login(self.usuarios[tipo])
            compuesto = componer(documento, {}, date(2026, 8, 17), date(2026, 12, 8))
            with self.subTest(tipo=tipo):
                self.assertEqual(compuesto['titulo'], documento.nombre_documental)
                self.assertEqual(compuesto['codigo_etiqueta'], 'Referencia interna')
                self.assertEqual(compuesto['codigo_formato'], 'SLCID-' + prefijos[tipo] + '-PLAN')
                respuesta = self.client.get(reverse('redactar_documento_expediente',
                    args=[documento.unidad.slug, documento.pk]))
                self.assertContains(respuesta, documento.nombre_documental)
                self.assertContains(respuesta, 'Referencia interna: SLCID-' + prefijos[tipo] + '-PLAN')


class EmisionDesdeVistaPreviaTests(BaseAlcanceReportes):
    """Ejercita emisión real sin reenviar ni sustituir los campos del editor."""
    def compra_guardada(self, tipo='laboratorios'):
        unidad, usuario = self.unidades[tipo], self.usuarios[tipo]
        documento = DocumentoExpediente.objects.create(unidad=unidad,
            exigido=DocumentoExigido.objects.get(codigo='PLAN-COMPRAS-ANUAL'), anio=2026, corte='')
        abrir_entrega(documento)
        redaccion = obtener_redaccion(documento)
        redaccion.contenido = {'capacidad': '<p>La capacidad instalada cubre el siguiente período.</p>',
            'sin_compras_justificacion': '<p>Los activos están operativos y con existencias suficientes.</p>',
            'firma_nombre': 'Coordinación de ' + tipo, 'firma_cargo': 'Coordinación de la unidad'}
        redaccion.version, redaccion.actualizado_por = 3, usuario
        redaccion.save()
        self.client.force_login(usuario)
        return documento, redaccion

    def test_boton_de_vista_previa_genera_el_contenido_guardado_de_los_cuatro_tipos(self):
        for tipo in self.unidades:
            documento, redaccion = self.compra_guardada(tipo)
            anterior = deepcopy(redaccion.contenido)
            ruta = reverse('redactar_documento_expediente', args=[documento.unidad.slug, documento.pk])
            pagina = self.client.get(reverse('vista_previa_documento_expediente',
                args=[documento.unidad.slug, documento.pk]))
            with self.subTest(tipo=tipo):
                self.assertContains(pagina, 'name="version_base" value="3"')
                self.assertContains(pagina, 'name="accion" value="generar_guardado"')
                respuesta = self.client.post(ruta, {'accion': 'generar_guardado', 'version_base': '3'})
                self.assertRedirects(respuesta, reverse('gestion_expediente_unidad', args=[documento.unidad.slug])
                    + '?anio=2026&corte=', fetch_redirect_response=False)
                documento.refresh_from_db()
                redaccion.refresh_from_db()
                self.assertEqual((documento.estado, documento.version), ('generado', 1))
                # Emitir conserva lo escrito y fija las fuentes técnicas para
                # que una transferencia o reparación posterior no reescriba el PDF.
                self.assertEqual(redaccion.version, 3)
                for clave, valor in anterior.items():
                    self.assertEqual(redaccion.contenido[clave], valor)
                from apps.documentos.presentation.pac_universitario import preparar_pac
                esperado = preparar_pac(anterior, unidad=documento.unidad)
                self.assertEqual(set(redaccion.contenido) - set(esperado),
                    {'diagnostico_compras_fuentes', 'inversion_gestion_fuentes'})
                self.assertEqual(redaccion.contenido['diagnostico_compras_fuentes']['unidad'], documento.unidad_id)
                self.assertEqual(redaccion.contenido['inversion_gestion_fuentes']['unidad'], documento.unidad_id)
                self.assertTrue(Path(documento.recurso.archivo.path).read_bytes().startswith(b'%PDF'))

    def test_vista_obsoleta_no_emite_archivo_ni_sobrescribe_la_redaccion(self):
        documento, redaccion = self.compra_guardada()
        anteriores = (deepcopy(redaccion.contenido), redaccion.version)
        recursos, archivos = Recurso.objects.count(), set(Path(settings.MEDIA_ROOT).rglob('*'))
        respuesta = self.client.post(reverse('redactar_documento_expediente',
            args=[documento.unidad.slug, documento.pk]), {'accion': 'generar_guardado', 'version_base': '2'},
            HTTP_X_REQUESTED_WITH='XMLHttpRequest')
        self.assertEqual(respuesta.status_code, 409)
        documento.refresh_from_db()
        redaccion.refresh_from_db()
        self.assertEqual((redaccion.contenido, redaccion.version), anteriores)
        self.assertEqual((documento.recurso_id, documento.version), (None, 0))
        self.assertEqual(Recurso.objects.count(), recursos)
        self.assertEqual(set(Path(settings.MEDIA_ROOT).rglob('*')), archivos)

    def test_validado_no_ofrece_ni_acepta_otra_emision_desde_vista_previa(self):
        documento, redaccion = self.compra_guardada()
        documento.estado = 'validado'
        documento.save(update_fields=['estado'])
        pagina = self.client.get(reverse('vista_previa_documento_expediente',
            args=[documento.unidad.slug, documento.pk]))
        self.assertNotContains(pagina, 'name="accion" value="generar_guardado"')
        respuesta = self.client.post(reverse('redactar_documento_expediente',
            args=[documento.unidad.slug, documento.pk]), {'accion': 'generar_guardado', 'version_base': '3'},
            HTTP_X_REQUESTED_WITH='XMLHttpRequest')
        self.assertEqual(respuesta.status_code, 409)
        self.assertFalse(DocumentoElaborado.objects.filter(documento=documento).exclude(version=redaccion.version).exists())
