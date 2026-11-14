"""Paleta cerrada, continuidad de marca y publicacion con cuatro instituciones."""

from unittest.mock import patch
from datetime import datetime, timezone

from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.db import DatabaseError, connection
from django.db.migrations.executor import MigrationExecutor
from django.template.loader import render_to_string
from django.test import TestCase, override_settings
from django.urls import reverse

from apps.core.identidad import identidades
from apps.core.paleta import CLAVES_PALETA, PALETA_SUGERIDA, contraste, validar_paleta
from apps.core.plantillas_marca import PLANTILLAS, catalogo_plantillas
from apps.configuracion_institucional.paleta import GRUPO_DE_ESTILO, GRUPOS_SOLO_VISUALIZADOR
from apps.core.presentation.identidad import identidad_de_despliegue, identidad_publica
from apps.core.presentation.presentacion_institucional import con_presentacion_institucional
from config.paleta import configuracion_paleta
from apps.configuracion_institucional.models import RevisionPresentacion
from apps.configuracion_institucional.paleta import PaletaField
from apps.configuracion_institucional.selectors import identidad_de_revision, identidad_publicada
from apps.configuracion_institucional.services import guardar_borrador, publicar_revision
from apps.gestion_unidades.presentation.gestion_reportes import render_unit_report_pdf
from tests.integration.test_identidad_producto import contenido_pdf


PALETAS = (
    {},
    dict(zip(CLAVES_PALETA, ('#163a63', '#0b1728', '#aad3fa', '#14253b', '#f0f4f8'))),
    dict(zip(CLAVES_PALETA, ('#493263', '#22152d', '#e5b8f4', '#281e30', '#f8f4fa'))),
    dict(zip(CLAVES_PALETA, ('#533d26', '#241a10', '#efcf88', '#302515', '#faf7f1'))),
)


class PaletaInstitucionalTests(TestCase):
    def setUp(self):
        self.autor = get_user_model().objects.create_superuser('paleta.admin')
        self.datos = dict(nombre_producto='Sistema de ensayos', nombre_corto_producto='Ensayos',
                          nombre_institucion='Institucion QA')

    def borrador(self, paleta):
        return guardar_borrador(RevisionPresentacion(**self.datos, paleta=paleta), self.autor)

    def test_cuatro_instituciones_y_dto_inmutable(self):
        for numero, paleta in enumerate(PALETAS):
            with self.subTest(institucion=numero), override_settings(
                PRODUCT_IDENTITY={'nombre': 'Sistema QA', 'nombre_corto': 'QA', 'codigo': 'SLCID'},
                INSTITUTION_IDENTITY={'nombre': f'Institucion QA {numero}', 'siglas': f'QA{numero}'},
            ):
                producto, institucion = identidad_de_despliegue()
                revision = guardar_borrador(RevisionPresentacion(
                    **{**self.datos, 'nombre_institucion': institucion.nombre}, paleta=paleta,
                ), self.autor)
                _, identidad = identidad_de_revision(revision, producto, institucion)
                self.assertIsInstance(identidad.paleta, tuple)
                self.assertEqual(dict(identidad.paleta), paleta)
                self.assertEqual(identidad.siglas, institucion.siglas)
                self.assertEqual(identidad.nombre, institucion.nombre)

    def test_las_combinaciones_listas_se_publican_sin_retoques(self):
        """Quien elige una plantilla no deberia toparse con un rechazo.

        Cada combinacion que ofrece el editor pasa por las mismas reglas de
        contraste que exige publicar, incluido su degradado.
        """
        claves = {plantilla.clave for plantilla in PLANTILLAS}
        self.assertEqual(len(claves), len(PLANTILLAS))
        anterior = None
        for plantilla in PLANTILLAS:
            with self.subTest(plantilla=plantilla.clave):
                guardada = dict(validar_paleta(plantilla.paleta))
                for clave in CLAVES_PALETA:
                    self.assertEqual(guardada[clave], plantilla.paleta[clave])
                revision = self.borrador(plantilla.paleta)
                anterior = publicar_revision(revision.pk, self.autor, base_esperada=anterior).pk
                html = self.client.get('/').content.decode()
                self.assertIn(f"--institucion-primario: {plantilla.paleta['primario']}", html)
                self.assertIn(f"--institucion-acento: {plantilla.paleta['acento']}", html)

    def test_el_editor_ofrece_las_combinaciones_y_la_opcion_de_crear(self):
        formulario = PaletaField().widget.render('paleta', {}, {'id': 'id_paleta'})
        for plantilla in catalogo_plantillas():
            with self.subTest(plantilla=plantilla['clave']):
                self.assertIn(f'data-palette-template="{plantilla["clave"]}"', formulario)
                self.assertIn(plantilla['nombre'], formulario)
        # La quinta tarjeta deja definir una combinacion propia.
        self.assertIn('data-palette-template=""', formulario)
        # Las secciones de la vista previa se ven todas, sin pestanas.
        self.assertNotIn('data-preview-tab', formulario)
        for seccion in ('barra', 'portada', 'catalogo', 'contenidos', 'formularios', 'bandas'):
            self.assertIn(f'data-pantalla="{seccion}"', formulario)

    def test_la_paleta_sugerida_es_la_de_la_institucion_instalada(self):
        """Lo que propone el formulario y la tarjeta «Verde institucional» no
        pueden separarse: serian dos verdes distintos llamados igual."""
        verde = next(p for p in PLANTILLAS if p.clave == 'verde')
        for clave in CLAVES_PALETA:
            with self.subTest(color=clave):
                self.assertEqual(PALETA_SUGERIDA[clave], verde.paleta[clave])
        self.assertEqual(PALETA_SUGERIDA['primario'], '#006633')
        self.assertEqual(PALETA_SUGERIDA['acento'], '#ffce00')

    def test_ningun_color_queda_sin_forma_de_configurarse(self):
        """Un control escondido y sin pieza que lo abra seria inalcanzable.

        El formulario oculta los grupos que se configuran pulsando el
        visualizador. Cada uno de esos campos necesita, entonces, una pieza que
        lo declare; los que no tienen pieza deben seguir a la vista.
        """
        import re

        formulario = PaletaField().widget.render('paleta', {}, {'id': 'id_paleta'})
        declarados = set()
        for grupo in re.findall(r'data-editable="([^"]+)"', formulario):
            declarados.update(grupo.split())

        for clave in CLAVES_PALETA:
            with self.subTest(color=clave):
                oculto = 'colores' in GRUPOS_SOLO_VISUALIZADOR
                self.assertTrue(clave in declarados or not oculto,
                                f'{clave} no se ve en el formulario y ninguna pieza lo abre')
        for clave, grupo in GRUPO_DE_ESTILO.items():
            with self.subTest(estilo=clave):
                if grupo not in GRUPOS_SOLO_VISUALIZADOR:
                    continue
                self.assertIn(clave, declarados,
                              f'{clave} esta oculto y ninguna pieza del visualizador lo abre')
        # El degradado principal tampoco puede quedarse sin pieza.
        self.assertIn('degradado_primario', declarados)

    def test_las_tres_plantillas_piden_la_misma_version_del_editor(self):
        """Una version olvidada deja al navegador con el editor anterior.

        Las pantallas que cargan la hoja y el guion del editor deben pedir la
        misma version; si una se queda atras, quien la abra ve controles
        nuevos gobernados por codigo viejo.
        """
        import re
        from pathlib import Path

        from django.conf import settings

        raiz = Path(settings.BASE_DIR) / 'apps' / 'configuracion_institucional' / 'templates'
        versiones = set()
        for plantilla in raiz.rglob('*.html'):
            texto = plantilla.read_text(encoding='utf-8')
            versiones.update(re.findall(r"paleta_editor\.(?:css|js)' %\}\?v=([\w.-]+)", texto))
        self.assertTrue(versiones)
        self.assertEqual(len(versiones), 1, f'Versiones distintas del editor: {sorted(versiones)}')

    def test_rechaza_css_inyeccion_claves_y_estructuras(self):
        for valor in (None, [], 'red', {'primario': '#123456'},
                      {**PALETA_SUGERIDA, 'extra': '#123456'},
                      {**PALETA_SUGERIDA, 'primario': '#123456;display:none'},
                      {**PALETA_SUGERIDA, 'oscuro': '</style><script>'},
                      {**PALETA_SUGERIDA, 'texto': 123}):
            with self.subTest(valor=valor), self.assertRaises(ValueError):
                validar_paleta(valor)

    def test_contraste_conocido_y_rechazo_de_cada_par(self):
        self.assertAlmostEqual(contraste('#ffffff', '#000000'), 21)
        self.assertAlmostEqual(contraste('#000000', '#ffffff'), 21)
        for clave, color in (('primario', '#ffffff'), ('oscuro', '#ffffff'),
                             ('acento', PALETA_SUGERIDA['texto']),
                             ('fondo', PALETA_SUGERIDA['texto'])):
            with self.subTest(clave=clave), self.assertRaises(ValidationError):
                self.borrador({**PALETA_SUGERIDA, clave: color})
        with self.assertRaises(ValueError):
            validar_paleta({**PALETA_SUGERIDA, 'acento': '#888888',
                            'oscuro': '#493263', 'texto': '#000000'})
        # Las tarjetas y campos mantienen superficie blanca aunque cambie el fondo.
        with self.assertRaises(ValueError):
            validar_paleta(dict(zip(CLAVES_PALETA, (
                '#000000', '#000000', '#767676', '#ffffff', '#000000',
            ))))

    def test_entorno_rechaza_duplicados_y_normaliza_hex(self):
        self.assertEqual(configuracion_paleta({}), {})
        for contenido in ('[]', '{"primario":"#123456","primario":"#123456"}',
                          'x' * 5001, '{'):
            with self.subTest(contenido=contenido[:20]), self.assertRaises(ValueError):
                configuracion_paleta({'INSTITUTION_PALETTE_JSON': contenido})
        mayusculas = {k: v.upper() for k, v in PALETA_SUGERIDA.items()}
        self.assertEqual(dict(validar_paleta(mayusculas)), PALETA_SUGERIDA)
        with self.assertRaises(ValueError):
            identidades({'nombre': 'X', 'nombre_corto': 'X', 'codigo': 'X'},
                        {'nombre': 'X', 'siglas': 'X', 'paleta': []})

    def test_diseno_original_y_borrador_no_activan_css(self):
        # Una version anterior omite la columna: PostgreSQL mantiene el default.
        state = MigrationExecutor(connection).loader.project_state([
            ('configuracion_institucional', '0004_revisionpoliticacalendario_and_more'),
        ])
        anterior = state.apps.get_model('configuracion_institucional', 'RevisionPresentacion')
        producto, institucion = identidad_de_despliegue()
        legacy = anterior.objects.create(**self.datos, producto_codigo=producto.codigo,
                                         institucion_codigo=institucion.siglas,
                                         estado='borrador', autor_id=self.autor.pk)
        self.assertEqual(RevisionPresentacion.objects.get(pk=legacy.pk).paleta, {})
        self.assertNotContains(self.client.get('/'), 'id="paleta-institucional"')
        self.borrador(PALETAS[1])
        self.assertNotContains(self.client.get('/'), 'id="paleta-institucional"')

    def test_publicacion_comparte_portal_admin_y_correo(self):
        publicar_revision(self.borrador(PALETAS[1]).pk, self.autor, base_esperada=None)
        self.assertContains(self.client.get('/'), '--institucion-primario: #163a63;')
        self.client.force_login(self.autor)
        self.assertContains(self.client.get('/admin/'), '--institucion-primario: #163a63;')
        with con_presentacion_institucional():
            html = render_to_string('emails/reservas/_comprobante_contenido.html', identidad_publica())
        self.assertIn('background:#163a63;', html)
        self.assertIn('solid #aad3fa;', html)

    def test_restaurar_paleta_crea_historia_y_vacio_restaura_diseno(self):
        primera = publicar_revision(self.borrador({}).pk, self.autor, base_esperada=None)
        segunda = publicar_revision(self.borrador(PALETAS[1]).pk, self.autor, base_esperada=primera.pk)
        tercera = publicar_revision(primera.pk, self.autor, base_esperada=segunda.pk)
        self.assertEqual(tercera.paleta, {})
        segunda.refresh_from_db()
        self.assertEqual(segunda.paleta, PALETAS[1])
        self.assertNotContains(self.client.get('/'), 'id="paleta-institucional"')

    def test_fallo_proveedor_conserva_identidad_completa(self):
        base = identidad_de_despliegue()
        with patch('apps.configuracion_institucional.selectors.PublicacionInstitucional.objects.select_related',
                   side_effect=DatabaseError), self.assertLogs('apps.configuracion_institucional.selectors'):
            self.assertEqual(identidad_publicada(base), base)

    def test_formulario_colores_completo_invalido_y_desactivado(self):
        campo = PaletaField()
        self.assertEqual(campo.clean([True, *PALETA_SUGERIDA.values()]), PALETA_SUGERIDA)
        self.assertEqual(campo.clean([False, *PALETA_SUGERIDA.values()]), {})
        with self.assertRaises(ValidationError):
            campo.clean([True, '#123456'])
        self.client.force_login(self.autor)
        url = reverse('admin:configuracion_institucional_revisionpresentacion_add')
        alta = self.client.get(url)
        self.assertContains(alta, 'type="color"', count=5)
        self.assertNotContains(alta, 'var clean_input_types')
        respuesta = self.client.post(url, {**self.datos, 'paleta_0': 'on', 'paleta_1': '#ffffff'})
        self.assertEqual(respuesta.status_code, 200)
        self.assertIn('paleta', respuesta.context['adminform'].form.errors)
        self.assertFalse(RevisionPresentacion.objects.exists())

    def test_revision_y_preview_no_confunden_paleta_vigente_con_propuesta(self):
        primera = publicar_revision(self.borrador(PALETAS[1]).pk, self.autor, base_esperada=None)
        propuesta = self.borrador(PALETAS[2])
        self.client.force_login(self.autor)
        respuesta = self.client.get(reverse('admin:configuracion_institucional_revisionpresentacion_publicar',
                                           args=[propuesta.pk]))
        self.assertEqual(respuesta.context['paleta_propuesta'], PALETAS[2])
        self.assertContains(respuesta, '--institucion-primario: #163a63;')
        self.assertContains(respuesta, 'background:#493263')
        self.assertEqual(primera.paleta, PALETAS[1])

    def test_pdf_nuevo_comparte_marca_publicada_y_conserva_datos(self):
        publicar_revision(self.borrador(PALETAS[1]).pk, self.autor, base_esperada=None)
        reporte = {'scope_label': 'Laboratorio QA', 'category_label': 'Recursos',
                   'filter_summary': [('Seleccion', 'Todos')], 'is_generic': True,
                   'generated_at': datetime(2026, 9, 17, tzinfo=timezone.utc),
                   'start_date': datetime(2026, 9, 1), 'end_date': datetime(2026, 9, 30),
                   'dataset': {'headers': ['Equipo'], 'rows': [['Equipo QA']], 'cards': []}}
        with con_presentacion_institucional():
            pdf = render_unit_report_pdf(reporte)
        self.assertIn(b'/Author (Institucion QA)', pdf)
        streams = contenido_pdf(pdf)
        self.assertIn(b'Equipo QA', streams)
        # Color principal efectivo en las instrucciones PDF, no solo en configuracion.
        self.assertIn(b'.086275 .227451 .388235 rg', streams)
