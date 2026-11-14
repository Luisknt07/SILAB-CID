"""Seguimiento sin entregas duplicadas y con el mismo alcance en las salidas."""
from datetime import date, datetime, time, timedelta
from io import BytesIO
from tempfile import TemporaryDirectory
from zipfile import ZipFile

from django.contrib.auth import get_user_model
from django.core.files.base import ContentFile
from django.test import TestCase, override_settings
from django.urls import reverse
from django.utils import timezone
from openpyxl import load_workbook
from pypdf import PdfReader

from apps.directorio_unidades.models.core import Unidad
from apps.documentos.models.expediente import DocumentoElaborado, DocumentoExigido, DocumentoExpediente
from apps.documentos.models.mejora import AccionMejora, InformeMejora, SeguimientoMejora
from apps.gestion_unidades.presentation.reportes_seguimiento_documental import reporte_mejora, reporte_retiros
from apps.recursos.models.equipos import EquiposServicios
from apps.recursos.models.mantenimiento import EventoCicloVidaEquipo
from apps.recursos.models.recursos import Recurso
from apps.recursos.models.unidades import UnidadEquipo
from tests.integration.utiles import identificar, pdf_legible_prueba


def instante(dia):
    return timezone.make_aware(datetime.combine(dia, time(10)))


class ReportesSeguimientoDocumentalTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.hasta = timezone.localdate() - timedelta(days=2)
        cls.desde = cls.hasta - timedelta(days=20)
        cls.usuario = get_user_model().objects.create_user('seguimiento-reportes-qa', first_name='Responsable')
        identificar(cls.usuario, tipo_usuario='administrativo', carrera='')
        cls.unidades, cls.equipos, cls.informes, cls.acciones = {}, {}, {}, {}
        tipo = EquiposServicios.objects.create(codigo='SEG-REPORTES-QA', nombre='Equipo de seguimiento')
        for numero, base in enumerate(('laboratorios', 'plantas_piloto', 'centro_experimental', 'observatorios'), 1):
            unidad = Unidad.objects.create(nombre=f'Unidad seguimiento {base}', slug=f'seguimiento-qa-{base}',
                dependencia=base, fecha_inicio=date(2020, 1, 1), administrador=cls.usuario, activo=True)
            cls.unidades[base] = unidad
            equipo = UnidadEquipo.objects.create(equipo=tipo, laboratorio=unidad, codigo_unidad=f'RQA-{numero}')
            UnidadEquipo.objects.filter(pk=equipo.pk).update(fecha_baja=cls.desde,
                motivo_baja='vida_util', observacion_baja=f'REFERENCIA-RETIRO-{numero}',
                activa=False, estado_unidad='no_disponible')
            equipo.refresh_from_db()
            cls.equipos[base] = equipo
            EventoCicloVidaEquipo.objects.create(equipo=equipo, unidad=unidad, tipo='baja',
                usuario=cls.usuario, fecha=instante(cls.desde),
                descripcion=f'Retiro/sustitución: HECHO-RETIRO-{numero}',
                evidencia=f'equipos/ciclo_vida/respaldo-{numero}.pdf')
            recurso = Recurso.objects.create(unidad=unidad, nombre=f'Informe de mejora {numero}')
            informe = InformeMejora.objects.create(unidad=unidad, recurso=recurso, anio=cls.desde.year,
                corte='A' if cls.desde.month < 7 else 'B', decision='continuidad',
                decidido_en=instante(cls.desde), decidido_por=cls.usuario,
                motivo=f'DECISION-QA-{numero}')
            cls.informes[base] = informe
            accion = AccionMejora.objects.create(informe=informe, descripcion=f'ACCION-QA-{numero}',
                responsable=cls.usuario, vence_el=cls.desde - timedelta(days=3), creada_por=cls.usuario)
            AccionMejora.objects.filter(pk=accion.pk).update(creada_en=instante(cls.desde - timedelta(days=30)))
            accion.refresh_from_db()
            cls.acciones[base] = accion

    def test_retiro_filtra_listado_hechos_y_cadena_sin_traer_otra_unidad(self):
        unidad = self.unidades['laboratorios']
        datos = reporte_retiros(unidad, self.desde, self.hasta, 'sin_reemplazo', 'RQA-1')
        self.assertEqual(len(datos['rows']), 1)
        self.assertIn('REFERENCIA-RETIRO-1', str(datos['rows']))
        self.assertIn('HECHO-RETIRO-1', str(datos['tablas']))
        self.assertNotIn('HECHO-RETIRO-2', str(datos))
        vacio = reporte_retiros(unidad, self.desde, self.hasta, 'con_reemplazo', 'RQA-1')
        self.assertFalse(vacio['rows'])
        self.assertTrue(all(not tabla['rows'] for tabla in vacio['tablas']))

    def test_retiro_anterior_sin_sustituto_permanece_y_evento_futuro_no_se_exporta(self):
        equipo = self.equipos['laboratorios']
        UnidadEquipo.objects.filter(pk=equipo.pk).update(fecha_baja=self.desde - timedelta(days=50))
        EventoCicloVidaEquipo.objects.create(equipo=equipo, unidad=self.unidades['laboratorios'],
            tipo='actualizacion', usuario=self.usuario, fecha=instante(self.hasta + timedelta(days=1)),
            descripcion='Retiro/sustitución: EVENTO-FUERA-DEL-CORTE')
        datos = reporte_retiros(self.unidades['laboratorios'], self.desde, self.hasta)
        self.assertTrue(datos['rows'])
        self.assertNotIn('EVENTO-FUERA-DEL-CORTE', str(datos['tablas']))

    def test_activo_transferido_solo_expone_eventos_propios_sin_identidad_actual_ni_busqueda_ajena(self):
        origen = self.unidades['laboratorios']
        destino = self.unidades['plantas_piloto']
        equipo = self.equipos['laboratorios']
        privado = EquiposServicios.objects.create(codigo='TIPO-PRIVADO-Y', nombre='NOMBRE-PRIVADO-DESTINO')
        UnidadEquipo.objects.filter(pk=equipo.pk).update(laboratorio=destino, equipo=privado,
            codigo_unidad='CODIGO-PRIVADO-DESTINO', codigo_bien='BIEN-PRIVADO-Y',
            observacion_baja='JUSTIFICACION-PRIVADA-DESTINO',
            reemplazado_por=self.equipos['plantas_piloto'])
        EventoCicloVidaEquipo.objects.create(equipo=equipo, unidad=destino, tipo='actualizacion',
            usuario=self.usuario, fecha=instante(self.hasta),
            descripcion='Retiro/sustitución: EVENTO-PRIVADO-DESTINO')
        datos = reporte_retiros(origen, self.desde, self.hasta, 'historial', 'HECHO-RETIRO-1')
        self.assertEqual(len(datos['rows']), 1)
        self.assertEqual(datos['rows'][0][0], f'Activo histórico ID {equipo.pk}')
        self.assertIn('HECHO-RETIRO-1', str(datos['tablas']))
        for privado in ('NOMBRE-PRIVADO-DESTINO', 'CODIGO-PRIVADO-DESTINO', 'BIEN-PRIVADO-Y',
                        'JUSTIFICACION-PRIVADA-DESTINO', 'EVENTO-PRIVADO-DESTINO'):
            self.assertNotIn(privado, str(datos))
            filtrado = reporte_retiros(origen, self.desde, self.hasta, search=privado)
            self.assertFalse(filtrado['rows'])
            self.assertTrue(all(not tabla['rows'] for tabla in filtrado['tablas']))
        cadenas = next(t for t in datos['tablas'] if t['titulo'].startswith('Relaciones'))
        self.assertFalse(cadenas['rows'])

    def test_accion_anterior_cerrada_despues_sigue_vencida_al_corte(self):
        accion = self.acciones['laboratorios']
        AccionMejora.objects.filter(pk=accion.pk).update(cerrada_en=instante(self.hasta + timedelta(days=1)))
        avance = SeguimientoMejora.objects.create(accion=accion, detalle='CIERRE-FUTURO-EXCLUIDO',
                                                 cierre=True, creado_por=self.usuario)
        SeguimientoMejora.objects.filter(pk=avance.pk).update(creado_en=instante(self.hasta + timedelta(days=1)))
        datos = reporte_mejora(self.unidades['laboratorios'], self.desde, self.hasta, 'vencida', 'ACCION-QA-1')
        self.assertEqual(len(datos['rows']), 1)
        self.assertIn('vencida al corte', datos['rows'][0][4])
        self.assertIn('Cierre actual:', datos['rows'][0][5])
        self.assertNotIn('CIERRE-FUTURO-EXCLUIDO', str(datos['tablas']))
        self.assertNotIn('ACCION-QA-2', str(datos))

    def test_cierre_no_se_presume_sin_seguimiento_y_todos_los_detalles_respetan_filtros(self):
        accion = self.acciones['laboratorios']
        AccionMejora.objects.filter(pk=accion.pk).update(cerrada_en=instante(self.hasta))
        datos = reporte_mejora(self.unidades['laboratorios'], self.desde, self.hasta, 'sin_cierre_verificado')
        self.assertEqual(len(datos['rows']), 1)
        self.assertFalse(reporte_mejora(self.unidades['laboratorios'], self.desde, self.hasta, 'cerrada')['rows'])
        avance = SeguimientoMejora.objects.create(accion=accion, detalle='SEGUIMIENTO-CIERRE-REGISTRADO',
            cierre=True, creado_por=self.usuario)
        SeguimientoMejora.objects.filter(pk=avance.pk).update(creado_en=instante(self.hasta))
        datos = reporte_mejora(self.unidades['laboratorios'], self.desde, self.hasta, 'cerrada', 'SEGUIMIENTO-CIERRE')
        self.assertEqual(len(datos['rows']), 1)
        self.assertIn('Cierre formal con seguimiento registrado', datos['rows'][0][4])
        self.assertIn('Seguimiento marcado como cierre', str(datos['tablas']))
        self.assertNotIn('Cierre verificado registrado', str(datos))
        self.assertNotIn('circuito competente', str(datos))
        vacio = reporte_mejora(self.unidades['laboratorios'], self.desde, self.hasta, 'cerrada', 'INEXISTENTE')
        self.assertFalse(vacio['rows'])
        self.assertTrue(all(not tabla['rows'] for tabla in vacio['tablas']))

    def test_mejora_no_enlaza_documento_de_origen_ajeno_a_la_unidad(self):
        privado = Recurso.objects.create(unidad=self.unidades['plantas_piloto'], nombre='ORIGEN-PRIVADO-Y')
        InformeMejora.objects.filter(pk=self.informes['laboratorios'].pk).update(recurso=privado)
        datos = reporte_mejora(self.unidades['laboratorios'], self.desde, self.hasta)
        self.assertIn('Documento de origen de otra unidad; no se enlaza', str(datos['tablas']))
        self.assertNotIn('ORIGEN-PRIVADO-Y', str(datos))
        self.assertNotIn(reverse('recurso_unidad', args=[privado.pk]), str(datos))

    def test_respaldo_solo_se_enlaza_si_es_propio_activo_vigente_y_tiene_archivo(self):
        unidad = self.unidades['laboratorios']
        datos = reporte_mejora(unidad, self.desde, self.hasta)
        self.assertIn('Sin archivo de origen registrado', str(datos['tablas']))
        carpeta = self.enterContext(TemporaryDirectory(prefix='citt-seguimiento-respaldo-'))
        self.enterContext(override_settings(MEDIA_ROOT=carpeta))
        recurso = Recurso.objects.create(unidad=unidad, nombre='Origen propio con archivo',
            archivo=ContentFile(pdf_legible_prueba('Informe de origen para prueba aislada.'), name='origen-qa.pdf'))
        InformeMejora.objects.filter(pk=self.informes['laboratorios'].pk).update(recurso=recurso)
        enlace = reverse('recurso_unidad', args=[recurso.pk])
        self.assertIn(enlace, str(reporte_mejora(unidad, self.desde, self.hasta)['tablas']))
        Recurso.objects.filter(pk=recurso.pk).update(activo=False)
        datos = reporte_mejora(unidad, self.desde, self.hasta)
        self.assertNotIn(enlace, str(datos['tablas']))
        self.assertIn('Documento de origen inactivo u obsoleto', str(datos['tablas']))
        Recurso.objects.filter(pk=recurso.pk).update(activo=True, estado='obsoleto')
        self.assertNotIn(enlace, str(reporte_mejora(unidad, self.desde, self.hasta)['tablas']))

    def test_editor_cumplida_no_es_cierre_verificado_y_no_reconstruye_redaccion_futura(self):
        unidad = self.unidades['laboratorios']
        exigido, _ = DocumentoExigido.objects.get_or_create(codigo='INFORME-SEMESTRAL',
            defaults=dict(nombre='Informe semestral', periodicidad='semestral', fuente_reporte='informe'))
        documento = DocumentoExpediente.objects.create(unidad=unidad, exigido=exigido,
            anio=self.hasta.year, corte='A' if self.hasta.month < 7 else 'B')
        redaccion = DocumentoElaborado.objects.create(documento=documento, version=2, contenido=dict(acciones=[
            dict(hallazgo='HALLAZGO-DECLARADO', accion='ACCION-EDITOR', responsable='Responsable declarado',
                 plazo=self.hasta.isoformat(), estado='cumplida'), 'FILA-JSON-INVALIDA']))
        DocumentoElaborado.objects.filter(pk=redaccion.pk).update(actualizado_en=instante(self.hasta))
        datos = reporte_mejora(unidad, self.desde, self.hasta, 'declarada', 'ACCION-EDITOR')
        self.assertEqual(len(datos['rows']), 1)
        self.assertIn('sin cierre verificado', datos['rows'][0][5])
        self.assertIn('HALLAZGO-DECLARADO', str(datos['tablas']))
        DocumentoElaborado.objects.filter(pk=redaccion.pk).update(actualizado_en=instante(self.hasta + timedelta(days=1)))
        self.assertFalse(reporte_mejora(unidad, self.desde, self.hasta, 'declarada')['rows'])

    def test_cuatro_perfiles_conservan_los_mismos_datos_en_html_pdf_excel_y_word(self):
        self.client.force_login(self.usuario)
        for numero, (base, unidad) in enumerate(self.unidades.items(), 1):
            for categoria, marca in (('retiros', f'RQA-{numero}'), ('mejora', f'ACCION-QA-{numero}')):
                filtros = dict(categoria_reporte=categoria, desde=self.desde.isoformat(), hasta=self.hasta.isoformat())
                for formato in ('html', 'pdf', 'xlsx', 'docx'):
                    with self.subTest(base=base, categoria=categoria, formato=formato):
                        consulta = dict(filtros)
                        if formato != 'html':
                            consulta['formato'] = formato
                        respuesta = self.client.get(reverse('gestion_reporte_unidad', args=[unidad.slug]), consulta)
                        self.assertEqual(respuesta.status_code, 200)
                        if formato == 'pdf':
                            contenido = ' '.join(p.extract_text() for p in PdfReader(BytesIO(respuesta.content)).pages)
                        elif formato == 'xlsx':
                            libro = load_workbook(BytesIO(respuesta.content), data_only=True)
                            contenido = str([fila for hoja in libro for fila in hoja.values])
                        elif formato == 'docx':
                            with ZipFile(BytesIO(respuesta.content)) as paquete:
                                contenido = paquete.read('word/document.xml').decode('utf-8')
                        else:
                            contenido = respuesta.content.decode('utf-8')
                        self.assertIn(marca, contenido)
