"""Un solo registro de retiro se consulta en ficha, PDF y mantenimiento."""
from contextlib import ExitStack
from datetime import date, datetime
from io import BytesIO
from types import SimpleNamespace
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.test import SimpleTestCase, TestCase
from django.urls import reverse
from django.utils import timezone
from openpyxl import load_workbook
from pypdf import PdfReader

from apps.directorio_unidades.models.core import Unidad
from apps.recursos.models.equipos import EquiposServicios
from apps.recursos.models.mantenimiento import EventoCicloVidaEquipo
from apps.recursos.models.unidades import UnidadEquipo
from apps.recursos.presentation.ficha_equipo import (
    AVISO_RETIRO, registros_baja_y_sustitucion, resumen_baja_y_sustitucion,
)
from apps.recursos.presentation.ficha_equipo_pdf import render_ficha_equipo_pdf
from tests.integration.utiles import identificar


class RegistroRetiroLecturaTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.usuario = get_user_model().objects.create_user('retiro-reportes', first_name='Ana')
        identificar(cls.usuario, tipo_usuario='administrativo', carrera='')
        cls.unidad = Unidad.objects.create(nombre='Laboratorio de retiros', slug='retiros-reportes',
            dependencia='laboratorios', fecha_inicio=date(2020, 1, 1), administrador=cls.usuario)
        cls.tipo = EquiposServicios.objects.create(codigo='TIPO-RETIRO-QA', nombre='Impresora de retiro')
        cls.viejo = UnidadEquipo.objects.create(codigo_unidad='RET-ANTERIOR', equipo=cls.tipo,
                                                laboratorio=cls.unidad)
        cls.nuevo = UnidadEquipo.objects.create(codigo_unidad='RET-NUEVO', equipo=cls.tipo,
                                                laboratorio=cls.unidad)
        # Un registro histórico puede preceder al flujo guiado de retiro.
        UnidadEquipo.objects.filter(pk=cls.viejo.pk).update(fecha_baja=timezone.localdate(),
            motivo_baja='dano_irreparable', observacion_baja='INFORME-TEC-RET-01; pieza no reparable.',
            reemplazado_por=cls.nuevo, activa=False, estado_unidad='no_disponible')
        cls.viejo.refresh_from_db()
        cls.evento = EventoCicloVidaEquipo.objects.create(equipo=cls.viejo, unidad=cls.unidad,
            tipo='baja', usuario=cls.usuario, evidencia='equipos/ciclo_vida/respaldo-retiro.pdf',
            descripcion='Retiro/sustitución: daño irreparable. ' + AVISO_RETIRO)

    def test_lote_incluye_reemplazo_historia_y_respaldo_sin_escribir_ni_n_mas_uno(self):
        antes = EventoCicloVidaEquipo.objects.count()
        with self.assertNumQueries(2):
            registros = registros_baja_y_sustitucion([self.viejo, self.nuevo])
            self.assertEqual(registros[self.viejo.pk]['reemplazo'].equipo.nombre, self.tipo.nombre)
            self.assertEqual(registros[self.nuevo.pk]['reemplazados'][0].codigo_unidad, 'RET-ANTERIOR')
            self.assertEqual(registros[self.viejo.pk]['ultimo']['usuario'].pk, self.usuario.pk)
        self.assertEqual(registros[self.viejo.pk]['ultimo']['respaldo'], 'respaldo-retiro.pdf')
        self.assertIn('INFORME-TEC-RET-01', resumen_baja_y_sustitucion(registros[self.viejo.pk]))
        self.assertEqual(EventoCicloVidaEquipo.objects.count(), antes)

    def test_rectificaciones_de_retiro_se_conservan_sin_mezclar_otras_actualizaciones(self):
        EventoCicloVidaEquipo.objects.create(equipo=self.viejo, tipo='actualizacion',
            usuario=self.usuario, descripcion='Retiro/sustitución: referencia rectificada.')
        EventoCicloVidaEquipo.objects.create(equipo=self.viejo, tipo='actualizacion',
            usuario=self.usuario, descripcion='Firmware actualizado; no es un retiro.')
        registro = registros_baja_y_sustitucion([self.viejo])[self.viejo.pk]
        self.assertEqual(len(registro['historial']), 2)
        self.assertIn('referencia rectificada', registro['ultimo']['descripcion'])
        self.assertFalse(registro['ultimo']['respaldo'])
        self.assertEqual(registro['historial'][1]['respaldo'], 'respaldo-retiro.pdf')

    def test_pdf_especifico_usa_permisos_existentes_y_no_crea_entregas(self):
        self.client.force_login(self.usuario)
        antes = EventoCicloVidaEquipo.objects.count()
        respuesta = self.client.get(reverse('ficha_equipo_unidad_pdf',
            args=[self.unidad.slug, self.viejo.pk]), {'documento': 'baja'})
        self.assertEqual(respuesta.status_code, 200)
        self.assertIn('registro-retiro-RET-ANTERIOR.pdf', respuesta['Content-Disposition'])
        texto = ' '.join(p.extract_text() for p in PdfReader(BytesIO(respuesta.content)).pages)
        self.assertIn('INFORME-TEC-RET-01', texto)
        self.assertIn('respaldo-retiro.pdf', texto)
        self.assertIn(AVISO_RETIRO, texto)
        self.assertEqual(EventoCicloVidaEquipo.objects.count(), antes)
        ajeno = get_user_model().objects.create_user('ajeno-retiro-reportes')
        self.client.force_login(ajeno)
        self.assertEqual(self.client.get(reverse('ficha_equipo_unidad_pdf',
            args=[self.unidad.slug, self.viejo.pk]), {'documento': 'baja'}).status_code, 403)

    def test_mantenimiento_conserva_dieciseis_columnas_y_expone_retiro_sustitucion(self):
        from apps.recursos.presentation.reportes_mantenimiento import reporte_mantenimiento

        with patch('apps.recursos.presentation.reportes_mantenimiento.es_laboratorio', return_value=False):
            headers, rows, _cards, _choices = reporte_mantenimiento(
                self.unidad, date(timezone.localdate().year, 1, 1), timezone.localdate())
        self.assertEqual(len(headers), 16)
        fila = next(f for f in rows if f[0].startswith('RET-ANTERIOR'))
        situacion = fila[headers.index('Situación')]
        for esperado in ('INFORME-TEC-RET-01', 'RET-NUEVO', 'respaldo-retiro.pdf', 'Ana', AVISO_RETIRO):
            self.assertIn(esperado, situacion)
        sustituto = next(f for f in rows if f[0].startswith('RET-NUEVO'))
        self.assertIn('Sin novedades registradas', sustituto[headers.index('Situación')])
        self.assertIn('Sustituye a: RET-ANTERIOR', sustituto[headers.index('Situación')])


class RetiroExportacionesSinBDTests(SimpleTestCase):
    def ficha(self):
        actor = SimpleNamespace(get_full_name=lambda: 'Ana Técnica', get_username=lambda: 'ana')
        reemplazo = SimpleNamespace(codigo_unidad='RET-NUEVO', equipo=SimpleNamespace(nombre='Equipo nuevo'))
        registro = dict(fecha=date(2026, 10, 10), estado='Retirado de operación',
            motivo='Daño irreparable', justificacion='INFORME-TEC-01: diagnóstico y destino documentados.',
            reemplazo=reemplazo, reemplazados=[], tiene_registro=True, aviso=AVISO_RETIRO,
            origen='Inventario actual e historial del activo.', historial=[dict(
                fecha=timezone.make_aware(datetime(2026, 10, 12, 10)), usuario=actor,
                descripcion='Retiro/sustitución: daño irreparable; respaldo técnico registrado.',
                respaldo='informe-tecnico-01.pdf')])
        registro['ultimo'] = registro['historial'][0]
        equipo = SimpleNamespace(codigo_unidad='RET-ANTERIOR', codigo_bien='BIEN-001',
            numero_serie='SERIE-001', custodio='Custodio QA', ubicacion_especifica='Área de fabricación',
            ubicacion_bodega='', fecha_adquisicion=date(2021, 1, 1), valor_referencial=0,
            get_criticidad_display=lambda: 'Crítico', get_estado_unidad_display=lambda: 'No disponible')
        return dict(equipo=equipo, tipo=SimpleNamespace(nombre='Equipo anterior', marca='Marca QA', modelo='QA'),
            etiqueta='Retirado de operación', motivos=['Retiro registrado.'], retiro=registro,
            contenido=dict(categoria='Fabricación digital', espacios=[]),
            vida=dict(anios=8, fin_previsto=date(2029, 1, 1), consumida=70,
                      motivo_texto='Retiro anticipado', horas_acumuladas=20, horas_limite=100),
            garantia=dict(vigente=False, fin=None, cobertura=''),
            uso=dict(sesiones=1, horas=2, usuarios=3), piezas=[], planes=[], fichas=[])

    def identidad(self):
        pila = ExitStack()
        identidad = (SimpleNamespace(codigo='QA'),
            SimpleNamespace(nombre='Universidad QA', siglas='UQA', paleta={}))
        for modulo in ('apps.recursos.presentation.ficha_equipo_pdf',
                       'apps.gestion_unidades.presentation.gestion_reportes',
                       'apps.core.presentation.pdf_institucional'):
            pila.enter_context(patch(modulo + '.identidad_actual', return_value=identidad))
        pila.enter_context(patch('apps.core.presentation.pdf_institucional.logo_institucional', return_value=None))
        return pila

    def test_ficha_y_pdf_especifico_conservan_datos_y_advierten_el_alcance(self):
        with self.identidad():
            for especifico in (False, True):
                contenido = render_ficha_equipo_pdf(SimpleNamespace(nombre='FabLab QA'), self.ficha(),
                                                    solo_retiro=especifico)
                texto = ' '.join(p.extract_text() for p in PdfReader(BytesIO(contenido)).pages)
                for esperado in ('INFORME-TEC-01', 'RET-NUEVO', 'informe-tecnico-01.pdf', 'Ana Técnica', AVISO_RETIRO):
                    self.assertIn(esperado, texto)
                self.assertIn('Historial de retiro y sustitución', texto)

    def test_pdf_sin_retiro_no_inventa_acta_ni_autor(self):
        ficha = self.ficha()
        ficha['retiro'] = dict(tiene_registro=False)
        with self.identidad():
            contenido = render_ficha_equipo_pdf(SimpleNamespace(nombre='FabLab QA'), ficha, solo_retiro=True)
        texto = ' '.join(p.extract_text() for p in PdfReader(BytesIO(contenido)).pages)
        self.assertIn('Sin retiro operativo ni sustitución registrados', texto)
        self.assertNotIn('Ana Técnica', texto)
        self.assertNotIn('INFORME-TEC-01', texto)

    def test_pdf_y_excel_reutilizan_el_bloque_sin_anadir_columnas_y_con_ajuste_de_texto(self):
        from apps.gestion_unidades.presentation.gestion_reportes import render_unit_report_pdf
        from apps.gestion_unidades.presentation.reportes_excel import render_unit_report_xlsx

        resumen = resumen_baja_y_sustitucion(self.ficha()['retiro'])
        headers = ['Equipo'] + [f'Dato {i}' for i in range(14)] + ['Situación']
        reporte = dict(unit=SimpleNamespace(slug='fablab-qa', nombre='FabLab QA'), category='mantenimiento',
            category_label='Mantenimiento', scope_label='FabLab QA', is_generic=True,
            generated_at=timezone.now(), start_date=date(2026, 8, 17), end_date=date(2026, 12, 8),
            filter_summary=[], metrics={}, dataset=dict(headers=headers, rows=[['RET-ANTERIOR'] + ['—'] * 14 + [resumen]],
                                            cards=[], notes=[], tablas=[], supporting_documents=[]))
        with self.identidad():
            contenido = render_unit_report_pdf(reporte)
        texto = ' '.join(' '.join(p.extract_text() for p in PdfReader(BytesIO(contenido)).pages).split())
        for esperado in ('INFORME-TEC-01', 'RET-NUEVO', 'informe-tecnico-01.pdf', 'Ana Técnica'):
            self.assertIn(esperado, texto)
        libro = load_workbook(BytesIO(render_unit_report_xlsx(reporte)))
        hoja = libro.worksheets[1]
        self.assertEqual(hoja.max_column, 16)
        self.assertEqual(hoja['P3'].value, resumen)
        self.assertTrue(hoja['P3'].alignment.wrap_text)
