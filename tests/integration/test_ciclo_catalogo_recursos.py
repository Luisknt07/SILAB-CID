"""Las referencias no cuentan como existencias
sólo recepción completa una compra."""
from datetime import date
from decimal import Decimal
from copy import deepcopy
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError, PermissionDenied
from django.test import TestCase
from django.urls import reverse
from apps.directorio_unidades.models.core import Unidad
from apps.documentos.models.expediente import DocumentoExigido, DocumentoExpediente, DocumentoElaborado
from apps.documentos.presentation.compras_resumen import resumen_compras
from apps.documentos.presentation.diagnostico_existencias import inventario_por_clase
from apps.recursos.models import EquiposServicios, UnidadEquipo, SoftwareDisponible, Consumible, EntradaInventario
from apps.recursos.presentation.ciclo_catalogo import solicitar, transicionar, eliminar_referencia
from apps.gestion_unidades.presentation.activacion import alternar_equipo, alternar_software, alternar_insumo


class CicloCatalogoTests(TestCase):
    databases = {'default', 'centros'}

    @classmethod
    def setUpTestData(cls):
        cls.admin = get_user_model().objects.create_superuser('direccion-ciclo', 'ciclo@example.org', 'clave')
        cls.gestor = get_user_model().objects.create_user('gestor-ciclo', password='clave')
        cls.ajeno = get_user_model().objects.create_user('ajeno-ciclo', password='clave')
        cls.unidad = Unidad.objects.create(nombre='Catálogo real', slug='catalogo-real', dependencia='laboratorios',
            fecha_inicio=date(2020, 1, 1), administrador=cls.gestor)
        cls.exigido = DocumentoExigido.objects.create(codigo='CICLO-COMPRAS', nombre='Plan de compras',
            fuente_reporte='compras', periodicidad='anual')
        cls.documento = DocumentoExpediente.objects.create(unidad=cls.unidad, exigido=cls.exigido, anio=2026)
        cls.modelo = EquiposServicios.objects.create(codigo='CICLO-MODELO', nombre='Equipo de referencia')

    def recurso(self, tipo):
        if tipo == 'equipo':
            return UnidadEquipo.objects.create(equipo=self.modelo, laboratorio=self.unidad,
                codigo_unidad='CICLO-FISICA', activa=False, estado_unidad='dañado')
        if tipo == 'software':
            return SoftwareDisponible.objects.create(unidad=self.unidad, nombre='Software referencia',
                activo=False, licencias_totales=0, licencias_disponibles=0)
        return Consumible.objects.create(unidad=self.unidad, codigo='CICLO-INS', nombre='Material referencia',
            clasificacion='material', activo=False, stock_total=0, unidad_medida='u')

    def pedir(self, tipo, recurso):
        return solicitar(self.unidad, tipo, recurso, dict(anio=2026,
            cantidad=Decimal('1') if tipo == 'equipo' else Decimal('3'), costo_unitario=Decimal('10'),
            mes_compra='2', justificacion='Dotación requerida para el proceso del área.'), self.gestor)

    def test_ciclo_tres_recursos_plan_informe_excel_y_recepcion_sin_doble_ingreso(self):
        for tipo in ('equipo', 'software', 'consumible'):
            with self.subTest(tipo=tipo):
                recurso = self.recurso(tipo)
                solicitud = self.pedir(tipo, recurso)
                recurso.refresh_from_db()
                self.assertFalse(getattr(recurso, 'activa', getattr(recurso, 'activo', False)))
                contenido = DocumentoElaborado.objects.get(documento=self.documento).contenido
                self.assertIn(str(solicitud.necesidad), {f['id_necesidad'] for f in contenido['compras']})
                self.assertGreater(resumen_compras(contenido)['total_general'], 0)
                with self.assertRaises(PermissionDenied):
                    transicionar(solicitud, 'aprobar', '', self.gestor, tipo)
                with self.assertRaises(ValidationError):
                    transicionar(solicitud, 'recibir', 'Acta anticipada', self.admin, tipo)
                solicitud = transicionar(solicitud, 'aprobar', '', self.admin, tipo)
                recurso.refresh_from_db()
                self.assertFalse(getattr(recurso, 'activa', getattr(recurso, 'activo', False)))
                with self.assertRaises(ValidationError):
                    {'equipo': alternar_equipo, 'software': alternar_software, 'consumible': alternar_insumo}[tipo](recurso)
                solicitud = transicionar(solicitud, 'comprar', 'Factura-2027', self.admin, tipo)
                solicitud = transicionar(solicitud, 'recibir', 'Acta-2027', self.gestor, tipo)
                transicionar(solicitud, 'recibir', 'Acta-2027', self.gestor, tipo)
                recurso.refresh_from_db()
                self.assertTrue(getattr(recurso, 'activa', getattr(recurso, 'activo', False)))
                if tipo == 'consumible':
                    self.assertEqual(recurso.stock_total, 3)
                    self.assertEqual(EntradaInventario.objects.filter(consumible=recurso).count(), 1)
                elif tipo == 'software':
                    self.assertEqual((recurso.licencias_totales, recurso.licencias_disponibles), (3, 3))
                else:
                    self.assertTrue(recurso.existencia_verificada)

    def test_no_permite_solicitudes_duplicadas_ni_habilitar_con_necesidad_modificada(self):
        recurso = self.recurso('equipo')
        solicitud = self.pedir('equipo', recurso)
        with self.assertRaises(ValidationError):
            self.pedir('equipo', recurso)
        solicitud = transicionar(solicitud, 'aprobar', '', self.admin, 'equipo')
        redaccion = DocumentoElaborado.objects.get(documento=self.documento)
        contenido = deepcopy(redaccion.contenido)
        contenido['compras'][0]['cantidad'] = '2'
        redaccion.contenido = contenido
        redaccion.save()
        with self.assertRaises(ValidationError):
            transicionar(solicitud, 'comprar', 'Factura', self.admin, 'equipo')
        solicitud = transicionar(solicitud, 'revisar', '', self.admin, 'equipo')
        self.assertEqual(solicitud.estado, 'solicitada')

    def test_material_se_puede_volver_a_solicitar_sin_perder_el_ingreso_anterior(self):
        material = self.recurso('consumible')
        primera = self.pedir('consumible', material)
        primera = transicionar(primera, 'aprobar', '', self.admin, 'consumible')
        primera = transicionar(primera, 'comprar', 'Factura', self.admin, 'consumible')
        transicionar(primera, 'recibir', 'Acta', self.gestor, 'consumible')
        EntradaInventario.objects.create(consumible=material, unidad=self.unidad,
            tipo='salida', motivo='consumo_practica', cantidad=3, usuario=self.gestor)
        material.refresh_from_db()
        alternar_insumo(material)
        segunda = self.pedir('consumible', material)
        self.assertNotEqual(primera.pk, segunda.pk)
        self.assertEqual(EntradaInventario.objects.filter(consumible=material).count(), 2)

    def test_solicitud_se_exporta_al_informe_y_excel_desde_la_misma_fila(self):
        from io import BytesIO
        from openpyxl import load_workbook
        from apps.documentos.presentation.pac_universitario import render_pac_xlsx
        from apps.documentos.presentation.compras_resumen import bloques_resumen_compras
        self.pedir('software', self.recurso('software'))
        contenido = DocumentoElaborado.objects.get(documento=self.documento).contenido
        self.assertEqual(contenido['pac_version'], 2)
        self.assertIn('Software referencia', str(bloques_resumen_compras(contenido)))
        libro = load_workbook(BytesIO(render_pac_xlsx(contenido, self.unidad.nombre, 2027)), data_only=True)
        self.addCleanup(libro.close)
        filas = [fila for hoja in libro for fila in hoja.values]
        self.assertTrue(any('Software referencia' in fila for fila in filas))

    def test_inactivos_fuera_del_inventario_del_informe_y_de_instalaciones(self):
        equipo = self.recurso('equipo')
        self.recurso('software')
        self.recurso('consumible')
        grupos = inventario_por_clase(self.unidad, [equipo], {}, {}, {}, {})
        self.assertTrue(all(not grupo['filas'] for grupo in grupos))

    def test_eliminar_solo_referencias_sin_historia(self):
        recurso = self.recurso('consumible')
        with self.assertRaises(ValidationError):
            eliminar_referencia(recurso, 'otro')
        eliminar_referencia(recurso, recurso.codigo)
        self.assertFalse(Consumible.objects.filter(pk=recurso.pk).exists())
        software = self.recurso('software')
        self.pedir('software', software)
        with self.assertRaises(ValidationError):
            eliminar_referencia(software, software.codigo or str(software.pk))

    def test_vistas_seguras_sin_mutaciones_get_y_acciones_dentro_de_unidad(self):
        recurso = self.recurso('software')
        url = reverse('ciclo_recurso_unidad', args=[self.unidad.slug, 'software', recurso.pk])
        self.client.force_login(self.ajeno)
        self.assertEqual(self.client.get(url).status_code, 403)
        self.client.force_login(self.gestor)
        self.assertContains(self.client.get(url), 'Añadir necesidad al plan anual')
        self.assertFalse(DocumentoElaborado.objects.exists())
        respuesta = self.client.post(url, dict(accion='solicitar', anio=2026, cantidad=2,
            costo_unitario=10, mes_compra='4', area_id='unidad', justificacion='Requiere licencias para el área.'))
        self.assertEqual(respuesta.status_code, 302)
        self.assertContains(self.client.get(reverse('adquisiciones_unidad', args=[self.unidad.slug])), 'Software referencia')

    def test_eliminacion_http_protege_historial_y_deja_auditoria(self):
        recurso = self.recurso('consumible')
        pk = recurso.pk
        self.client.force_login(self.gestor)
        url = reverse('ciclo_recurso_unidad', args=[self.unidad.slug, 'consumible', pk])
        self.assertEqual(self.client.post(url, {'accion': 'eliminar', 'confirmacion': recurso.codigo}).status_code, 302)
        self.assertFalse(Consumible.objects.filter(pk=pk).exists())
        from apps.formacion.models.practicas import RegistroAuditoriaUnidad
        self.assertTrue(RegistroAuditoriaUnidad.objects.filter(unidad=self.unidad, accion='eliminar', objeto_id=str(pk)).exists())

    def test_referencia_inactiva_se_previsualiza_por_gestor_y_no_por_publico(self):
        equipo = self.recurso('equipo')
        software = self.recurso('software')
        material = self.recurso('consumible')
        ficha = reverse('ficha_equipo_publica', args=[self.unidad.slug, equipo.codigo_unidad])
        sw = reverse('software_unidad', args=[self.unidad.slug])
        ins = reverse('insumos_unidad', args=[self.unidad.slug])
        self.assertEqual(self.client.get(ficha).status_code, 404)
        self.assertNotContains(self.client.get(sw), software.nombre)
        self.assertNotContains(self.client.get(ins), material.nombre)
        self.client.force_login(self.gestor)
        self.assertEqual(self.client.get(ficha).status_code, 200)
        self.assertContains(self.client.get(sw), software.nombre)
        self.assertContains(self.client.get(ins), material.nombre)

    def test_funciona_en_las_cuatro_tipologias_sin_datos_particulares_del_fablab(self):
        for tipo_unidad in ('laboratorios', 'plantas_piloto', 'centros_experimentales', 'observatorios'):
            self.unidad.dependencia = tipo_unidad
            self.unidad.save(update_fields=['dependencia'])
            recurso = SoftwareDisponible.objects.create(unidad=self.unidad, nombre='Referencia '+tipo_unidad, activo=False)
            solicitud = self.pedir('software', recurso)
            self.assertEqual(solicitud.unidad_id, self.unidad.pk)
