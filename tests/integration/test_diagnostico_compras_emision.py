"""La revisión posterior evalúa la propuesta enviada y sus fuentes conservadas."""
from io import BytesIO
from uuid import uuid4

from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.urls import reverse
from openpyxl import load_workbook
from pypdf import PdfReader

from apps.directorio_unidades.models.core import Unidad
from apps.documentos.models.constancias import ConstanciaDocumento
from apps.documentos.models.expediente import DocumentoElaborado
from apps.documentos.presentation.aprobacion_en_linea import decidir_documento_qr, enviar_documento_qr
from apps.documentos.presentation.conformidad_planes import analizar_conformidad
from apps.documentos.presentation.contenido_emitido import contenido_pac_enviado
from apps.documentos.presentation.expediente import generar_documento, tramo_del_documento
from apps.documentos.presentation.pac_universitario import preparar_pac
from apps.gestion_unidades.models.espacios import EspacioReservable
from apps.recursos.models.equipos import EquiposServicios
from apps.recursos.models.unidades import UnidadEquipo
from tests.integration.test_seguimiento_gobernanza import designar
from tests.integration.test_expediente_redaccion import BaseDeRedaccion
from tests.integration.utiles import abrir_entrega
from types import SimpleNamespace


class DiagnosticoComprasEmisionTests(BaseDeRedaccion):
    def setUp(self):
        self.director = get_user_model().objects.create_superuser('direccion-diagnostico-congelado', password=None,
            first_name='Dirección', last_name='del diagnóstico')
        designar(self.director)
        self.area = EspacioReservable.objects.get(unidad=self.unidad, codigo='RED-A1')
        self.area.equipos_asociados.add(self.unidad_equipo)
        self.documento_pac = abrir_entrega(self.documento('PLAN-COMPRAS-ANUAL', corte=''))
        contenido = preparar_pac(dict(compras=[dict(area_id=str(self.area.pk), area_nombre=self.area.nombre,
            tipo_necesidad='reposicion', clase_bien='equipos', item='Sustituto del equipo de red documentado', cantidad='1',
            costo_unitario='100.00', justificacion='Renovar la prestación identificada con respaldo del inventario.',
            mes_compra='3', equipos_referencia=[str(self.unidad_equipo.pk)],
            equipo_referencia=f'{self.unidad_equipo.codigo_unidad} · {self.unidad_equipo.equipo.nombre}',
            clasificacion_pac='por_definir')],
            justificacion_uso_existente='La unidad programará el aprovechamiento del inventario operativo y del recurso que lo sustituye.',
            acciones_cumplimiento=[dict(accion='Publicar la programación del área de redes y realizar sus prácticas',
                responsable='Coordinación de la unidad', plazo='2027-03-31',
                resultado='Conservar metas, responsables y meses; registrar ejecución real y participantes.')],
            firma_nombre=self.coordinador.get_full_name(),
            firma_cargo='Responsable de la unidad'), unidad=self.unidad)
        self.redaccion = DocumentoElaborado.objects.create(documento=self.documento_pac, version=1, contenido=contenido)
        self.otra = Unidad.objects.create(nombre='Unidad receptora del activo', slug='unidad-receptora-diagnostico',
            dependencia='laboratorios', fecha_inicio=self.unidad.fecha_inicio)

    def emitir(self):
        generar_documento(self.documento_pac, self.coordinador)
        self.documento_pac.refresh_from_db()
        return ConstanciaDocumento.objects.get(token=self.documento_pac.verificacion_qr)

    def enviar(self, constancia):
        enviar_documento_qr(self.documento_pac, self.coordinador,
            token=constancia.token, version=constancia.version)
        self.documento_pac.refresh_from_db()
        constancia.refresh_from_db()

    def exportado(self):
        self.client.force_login(self.coordinador)
        ruta = reverse('exportar_pac_unidad', args=[self.unidad.slug, self.documento_pac.pk])
        respuesta = self.client.get(ruta)
        self.assertEqual(respuesta.status_code, 200)
        libro = load_workbook(BytesIO(respuesta.content), data_only=False)
        try:
            return {hoja.title: list(hoja.values) for hoja in libro.worksheets}
        finally:
            libro.close()

    def test_generacion_revalida_las_areas_actuales_antes_de_crear_el_pdf(self):
        EspacioReservable.objects.filter(pk=self.area.pk).update(activo=False)
        with self.assertRaisesMessage(ValidationError, 'área seleccionada no está activa'):
            generar_documento(self.documento_pac, self.coordinador)
        self.documento_pac.refresh_from_db()
        self.assertIsNone(self.documento_pac.recurso_id)
        self.assertFalse(ConstanciaDocumento.objects.filter(documento=self.documento_pac).exists())

    def test_envio_revalida_fuentes_vivas_aunque_el_diagnostico_ya_este_preparado(self):
        constancia = self.emitir()
        EspacioReservable.objects.filter(pk=self.area.pk).update(activo=False)
        with self.assertRaisesMessage(ValidationError, 'área seleccionada no está activa'):
            self.enviar(constancia)
        EspacioReservable.objects.filter(pk=self.area.pk).update(activo=True)
        UnidadEquipo.objects.filter(pk=self.unidad_equipo.pk).update(laboratorio=self.otra)
        self.unidad_equipo.laboratorios.clear()
        with self.assertRaisesMessage(ValidationError, 'alguno no pertenece a esta unidad'):
            self.enviar(constancia)
        constancia.refresh_from_db()
        self.assertIsNone(constancia.enviado_en)
        self.documento_pac.refresh_from_db()
        self.assertEqual(self.documento_pac.estado, 'generado')

    def test_conformidad_y_exportacion_preservan_el_diagnostico_despues_de_retiro_y_transferencia(self):
        constancia = self.emitir()
        self.enviar(constancia)
        congelado = contenido_pac_enviado(self.documento_pac)
        self.assertEqual(congelado['pac_version'], 2)
        self.assertIn('diagnostico_compras_fuentes', congelado)
        libro_inicial = self.exportado()
        with self.documento_pac.recurso.archivo.open('rb') as archivo:
            original = archivo.read()
        identidades = (self.documento_pac.version, self.documento_pac.recurso_id,
                       self.documento_pac.recurso.hash_sha256)
        EspacioReservable.objects.filter(pk=self.area.pk).update(nombre='Área actual retirada', activo=False)
        UnidadEquipo.objects.filter(pk=self.unidad_equipo.pk).update(laboratorio=self.otra, estado_unidad='dañado')
        self.unidad_equipo.laboratorios.clear()
        EquiposServicios.objects.filter(pk=self.unidad_equipo.equipo_id).update(nombre='Nombre actual modificado')
        # Una redacción mutable posterior tampoco sustituye la entrega QR.
        DocumentoElaborado.objects.filter(pk=self.redaccion.pk).update(contenido={})
        inicio, fin = tramo_del_documento(self.documento_pac)
        hallazgos, _ = analizar_conformidad(self.documento_pac, SimpleNamespace(inicio=inicio, fin=fin))
        self.assertFalse([h for h in hallazgos if h['severidad'] == 'bloqueo'])
        decidir_documento_qr(self.documento_pac, self.director, token=constancia.token,
            version=constancia.version, decision='aprobar')
        constancia.refresh_from_db()
        self.assertIsNotNone(constancia.aprobado_en)
        self.assertEqual(contenido_pac_enviado(self.documento_pac), congelado)
        self.assertEqual(self.exportado(), libro_inicial)
        self.documento_pac.refresh_from_db()
        self.assertEqual((self.documento_pac.version, self.documento_pac.recurso_id,
                          self.documento_pac.recurso.hash_sha256), identidades)
        with self.documento_pac.recurso.archivo.open('rb') as archivo:
            self.assertEqual(archivo.read(), original)
        with constancia.archivo_aprobado.open('rb') as archivo:
            aprobado = PdfReader(BytesIO(archivo.read()))
        texto = '\n'.join(p.extract_text() or '' for p in aprobado.pages)
        self.assertIn('Área de racks', texto)
        self.assertIn('Switch de núcleo', texto)
        self.assertNotIn('Nombre actual modificado', texto)
        self.assertNotIn('Área actual retirada', texto)

    def test_un_token_distinto_no_habilita_relajar_la_pertenencia_actual(self):
        constancia = self.emitir()
        self.enviar(constancia)
        EspacioReservable.objects.filter(pk=self.area.pk).update(activo=False)
        self.documento_pac.verificacion_qr = uuid4()
        self.assertIsNone(contenido_pac_enviado(self.documento_pac))
        inicio, fin = tramo_del_documento(self.documento_pac)
        hallazgos, _ = analizar_conformidad(self.documento_pac, SimpleNamespace(inicio=inicio, fin=fin))
        self.assertTrue(any(h['regla'] == 'pac_area_ajena' and h['severidad'] == 'bloqueo' for h in hallazgos))
