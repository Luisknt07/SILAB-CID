"""Perfiles institucionales, salida publica y PDF usan una identidad coherente."""

from dataclasses import FrozenInstanceError
from datetime import datetime, timezone
from io import BytesIO
from pathlib import Path
import subprocess
import sys
import re
from pypdf import PdfReader

from django.contrib import admin
from django.contrib.auth.models import AnonymousUser
from django.template.loader import render_to_string
from django.test import RequestFactory, SimpleTestCase, override_settings
from django.utils.translation import override

from apps.core.checks import identidad_configurada
from apps.core.identidad import identidades
from apps.core.presentation.identidad import identidad_actual, identidad_publica, logo_institucional
from config.identidad import configuracion_identidad
from apps.gestion_unidades.presentation.gestion_reportes import render_unit_report_pdf
from apps.laboratorios.operacion.presentation.maquetas_pdf import render_maqueta_pdf


def contenido_pdf(datos):
    """Lee las páginas; fuentes e imágenes pueden usar otros filtros PDF."""
    lector = PdfReader(BytesIO(datos))
    return b'\n'.join(pagina.get_contents().get_data() for pagina in lector.pages)


class IdentidadProductoTests(SimpleTestCase):
    def test_cuentas_personalizadas_no_heredan_marca_o_soporte_upec(self):
        plantillas = ('password_change', 'password_set', 'password_reset',
                      'password_reset_done', 'password_reset_from_key',
                      'password_reset_from_key_done')
        for correo in ('ayuda@example.test', ''):
            producto, institucion = configuracion_identidad({
                'INSTITUTION_PROFILE': 'custom', 'INSTITUTION_NAME': 'Instituto Regional',
                'INSTITUTION_CODE': 'IR', 'INSTITUTION_EMAIL': correo,
                'SYSTEM_SHORT_NAME': 'Laboratorios & Ensayos',
            })
            with override_settings(PRODUCT_IDENTITY=producto, INSTITUTION_IDENTITY=institucion):
                request = RequestFactory().get('/')
                request.user = AnonymousUser()
                for idioma in ('es', 'en'):
                    with override(idioma):
                        for nombre in plantillas:
                            with self.subTest(correo=correo, idioma=idioma, plantilla=nombre):
                                html = render_to_string(f'account/{nombre}.html', request=request)
                                titulo = re.search(r'<title>(.*?)</title>', html, re.S)[1]
                                self.assertIn('Laboratorios &amp; Ensayos', titulo)
                                self.assertIn('IR', titulo)
                                self.assertNotIn('UPEC', html)
                                self.assertNotIn('upec.edu.ec', html)
                                if nombre in ('password_reset', 'password_reset_done'):
                                    self.assertEqual(f'mailto:{correo}' in html if correo else 'mailto:' in html,
                                                     bool(correo))
                                self.assertNotIn(' ? ', titulo)

    def test_perfil_upec_conserva_identidad_y_no_proyecta_secretos(self):
        producto, institucion = configuracion_identidad({'DB_PASSWORD': 'no-publicar'})
        p, i = identidades(producto, institucion)
        self.assertEqual(p.codigo, 'SLCID')
        self.assertEqual(i.siglas, 'UPEC')
        self.assertEqual(i.logo, 'img/logo_upec.png')
        self.assertNotIn('no-publicar', repr((p, i)))
        with self.assertRaises(FrozenInstanceError):
            i.nombre = 'Cambio'

    @override('es')
    def test_tres_instituciones_personalizadas_no_heredan_datos_upec(self):
        for nombre, siglas in [('Instituto Técnico', 'IT'), ('Centro de Ensayos', 'CE'), ('Universidad Regional', 'UR')]:
            with self.subTest(institucion=siglas):
                producto, institucion = configuracion_identidad({
                    'INSTITUTION_PROFILE': 'custom', 'INSTITUTION_NAME': nombre,
                    'INSTITUTION_CODE': siglas,
                })
                with override_settings(PRODUCT_IDENTITY=producto, INSTITUTION_IDENTITY=institucion):
                    self.assertEqual(identidad_configurada(None), [])
                    self.assertIsNone(logo_institucional())
                    self.assertEqual(identidad_actual()[1].correo, '')
                    request = RequestFactory().get('/')
                    request.user = AnonymousUser()
                    html = render_to_string('portal/components/navegacion/encabezado_institucional.html', identidad_publica(), request=request)
                    self.assertIn(siglas, html)
                    self.assertNotIn('UPEC', html)
                    self.assertNotIn('/static/"', html)
                    self.assertEqual(str(admin.site.site_title), f'Administración {siglas}')

    def test_titulos_admin_siguen_el_idioma_activo_sin_retener_el_anterior(self):
        producto, institucion = configuracion_identidad({
            'INSTITUTION_PROFILE': 'custom', 'INSTITUTION_NAME': 'Instituto Regional',
            'INSTITUTION_CODE': 'IR', 'SYSTEM_SHORT_NAME': 'Portal Regional',
        })
        # Se reutiliza la misma referencia diferida: ni el idioma de una
        # solicitud anterior ni su evaluación deben quedar fijados en el sitio.
        titulo, cabecera = admin.site.site_title, admin.site.site_header
        with override_settings(PRODUCT_IDENTITY=producto, INSTITUTION_IDENTITY=institucion):
            for idioma, administracion in [('en', 'Administration'), ('es', 'Administración'),
                                            ('en', 'Administration')]:
                with self.subTest(idioma=idioma), override(idioma):
                    self.assertEqual(str(titulo), f'{administracion} IR')
                    self.assertEqual(str(cabecera), f'{administracion} · Portal Regional')
                    self.assertNotIn('UPEC', str(titulo))
                    self.assertNotIn('UPEC', str(cabecera))

    def test_configuracion_invalida_y_secretos_desconocidos_se_rechazan(self):
        producto, institucion = configuracion_identidad({})
        for cambio in ({'nombre': ''}, {'nombre': '<script>ataque</script>'},
                       {'nombre': 'Cabecera\r\ninyectada'}, {'correo': 'invalido'},
                       {'password': 'secreto'}, {'logo': '../secreto.png'},
                       {'logo': 'https://privado/logo.png'}, {'logo': 'C:\\privado.png'},
                       {'logo': 'img/logo.svg'}):
            with self.subTest(cambio=cambio):
                with override_settings(PRODUCT_IDENTITY=producto, INSTITUTION_IDENTITY={**institucion, **cambio}):
                    self.assertEqual([e.id for e in identidad_configurada(None)], ['slcid.E001'])
        with self.assertRaises(ValueError):
            configuracion_identidad({'INSTITUTION_PROFILE': '../privado'})

    def test_pdf_reporte_y_maqueta_sin_logo_usan_la_institucion_actual(self):
        producto, institucion = configuracion_identidad({
            'INSTITUTION_PROFILE': 'custom', 'INSTITUTION_NAME': 'Centro Regional',
            'INSTITUTION_CODE': 'CR', 'SYSTEM_SHORT_NAME': 'Laboratorios Regionales',
        })
        with override_settings(PRODUCT_IDENTITY=producto, INSTITUTION_IDENTITY=institucion):
            reporte = {'scope_label': 'Laboratorio de Ensayos', 'category_label': 'Recursos',
                       'filter_summary': [('Selección', 'Todos')], 'is_generic': True,
                       'generated_at': datetime(2026, 9, 16, tzinfo=timezone.utc),
                       'start_date': datetime(2026, 9, 1), 'end_date': datetime(2026, 9, 30),
                       'dataset': {'headers': ['Equipo'], 'rows': [['Equipo A']], 'cards': []}}
            pdf = render_unit_report_pdf(reporte)
            self.assertIn(b'/Author (Centro Regional)', pdf)
            texto = contenido_pdf(pdf)
            # El marco institucional identifica al despliegue: institución arriba, producto al pie.
            self.assertIn(b'CENTRO REGIONAL', texto)
            self.assertIn(b'CR', texto)
            self.assertIn(b'SLCID', texto)
            self.assertNotIn(b'UPEC', texto)
            html = '<div class="unit-report"><header class="unit-report__masthead"><div class="unit-report__brandmark"></div><div class="unit-report__identity"><span>Laboratorios Regionales</span><h1>Recursos</h1></div><div class="unit-report__meta"></div></header><section><h2>Equipo A</h2></section></div>'
            maqueta = render_maqueta_pdf(f'<html><head><title>Recursos</title></head><body><main>{html}<footer class="unit-report__footer">Centro Regional</footer></main></body></html>', 'acta_entrega')
            self.assertIn(b'/Author (Centro Regional)', maqueta)
            self.assertNotIn(b'UPEC', contenido_pdf(maqueta))

    def test_identidad_pura_no_importa_django_ni_verticales(self):
        codigo = "import sys; from apps.core.identidad import IdentidadProducto; assert not any(n == 'django' or n.startswith('webcitt') for n in sys.modules); print('OK')"
        resultado = subprocess.run([sys.executable, '-c', codigo], cwd=Path(__file__).resolve().parents[2], capture_output=True, text=True, check=True)
        self.assertEqual(resultado.stdout.strip(), 'OK')

    def test_producto_del_negocio_no_oculta_identidad_en_cabecera_y_aula(self):
        request = RequestFactory().get('/')
        request.user = AnonymousUser()
        contexto = {'producto': {'nombre': 'Queso fresco', 'codigo': 'LAC-PRD-QF'},
                    'institucion': 'Institucion del solicitante'}
        for plantilla in ('portal/components/navegacion/encabezado_institucional.html',
                          'portal/pages/unidades/aula/producto.html'):
            with self.subTest(plantilla=plantilla):
                html = render_to_string(plantilla, contexto, request=request)
                self.assertIn('Sistema de Laboratorios y Centros I+D', html)
                if plantilla.endswith('producto.html'):
                    self.assertIn('Queso fresco', html)
        self.assertEqual(set(identidad_publica()), {
            'identidad_producto', 'identidad_institucion', 'paleta_institucional',
        })
