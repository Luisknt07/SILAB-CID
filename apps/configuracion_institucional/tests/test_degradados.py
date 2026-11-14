"""Pegado HEX, degradado cerrado, contraste y continuidad de publicaciones."""
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.test import TestCase
from django.urls import reverse

from apps.core.paleta import CLAVE_DEGRADADO, PALETA_SUGERIDA, normalizar_hex, validar_paleta, variables_degradado
from apps.configuracion_institucional.models import RevisionPresentacion
from apps.configuracion_institucional.paleta import PaletaField
from apps.configuracion_institucional.services import guardar_borrador, publicar_revision
from config.paleta import configuracion_paleta
import json
from datetime import datetime, timezone
from django.template.loader import render_to_string
from apps.core.presentation.identidad import identidad_publica
from apps.core.presentation.presentacion_institucional import con_presentacion_institucional
from apps.gestion_unidades.presentation.gestion_reportes import render_unit_report_pdf


class PaletaDegradadosTests(TestCase):
    def setUp(self):
        self.autor = get_user_model().objects.create_superuser('degradado.qa')
        self.datos = {'nombre_producto': 'Sistema QA', 'nombre_corto_producto': 'QA',
                      'nombre_institucion': 'Institucion QA'}
        self.paleta = {**PALETA_SUGERIDA, 'primario': '#082b22'}

    def test_hex_pegado_con_o_sin_hash_y_espacios(self):
        for entrada in ('082b22', '#082B22', '  #082b22\n', '&#x20;082b22&#32;'):
            self.assertEqual(normalizar_hex(entrada), '#082b22')
        for entrada in ('rgb(8,43,34)', '#082b22;', '#abc', '#082b22ff', None, '0'*33):
            with self.subTest(entrada=entrada), self.assertRaises(ValueError):
                normalizar_hex(entrada)

    def test_degradado_canonico_y_posiciones_idempotentes(self):
        valor = 'linear-gradient(-225deg, #082B22 0%, #064e3b 50%, #071525 100%)'
        paleta = dict(validar_paleta({**self.paleta, CLAVE_DEGRADADO: valor}))
        self.assertEqual(paleta[CLAVE_DEGRADADO], 'linear-gradient(135deg in srgb, #082b22 0%, #064e3b 50%, #071525 100%)')
        self.assertEqual(dict(validar_paleta(paleta)), paleta)

    def test_ejemplo_usuario_resuelve_variables_sin_dependencias_futuras(self):
        entrada = 'linear-gradient(\n135deg,\u00a0var(--unit-green-800),\u00a0var(--unit-green-600)) &#x20;'
        salida = dict(validar_paleta({**self.paleta, CLAVE_DEGRADADO: entrada}))[CLAVE_DEGRADADO]
        variables = variables_degradado(self.paleta)
        self.assertEqual(salida, f"linear-gradient(135deg in srgb, {variables['--unit-green-800']}, #082b22)")
        self.assertNotIn('var(', salida)

    def test_rechaza_codigo_urls_variables_externas_y_sintaxis_invalida(self):
        validos = '#082b22, #064e3b'
        for valor in (f'linear-gradient(135deg, {validos});display:none',
                      f'linear-gradient(135deg, {validos})</style>',
                      'linear-gradient(135deg, url(https://ejemplo.test), #082b22)',
                      'linear-gradient(135deg, var(--externo), #082b22)',
                      'linear-gradient(135deg, var(--unit-green-800, #000000), #082b22)',
                      'radial-gradient(#082b22, #064e3b)',
                      f'linear-gradient(361deg, {validos})',
                      'linear-gradient(135deg, #082b22 70%, #064e3b 20%)',
                      'linear-gradient(135deg, #082b22, #064e3b 101%)',
                      'linear-gradient(135deg, ' + ', '.join(['#082b22']*6) + ')', None):
            with self.subTest(valor=valor), self.assertRaises(ValueError):
                validar_paleta({**self.paleta, CLAVE_DEGRADADO: valor})

    def test_contraste_incluye_cada_parada_intermedia(self):
        for parada in ('#ffffff', '#318566', '#f2bd3f'):
            with self.subTest(parada=parada), self.assertRaises(ValueError):
                validar_paleta({**self.paleta, CLAVE_DEGRADADO: f'linear-gradient(135deg, #082b22, {parada} 50%, #071525)'})

    def test_formulario_sin_js_acepta_hex_y_degradado_o_desactivacion(self):
        campo = PaletaField()
        valores = [c.lstrip('#') for c in self.paleta.values()]
        salida = campo.clean([True, *valores, 'linear-gradient(135deg, #082b22, #064e3b)'])
        self.assertEqual(salida['primario'], '#082b22')
        self.assertIn(CLAVE_DEGRADADO, salida)
        self.assertEqual(campo.clean([False, *valores, 'url(x)']), {})
        with self.assertRaises(ValidationError):
            campo.clean([True, *valores, 'url(x)'])

    def test_post_admin_guarda_normaliza_y_previsualiza_sin_publicar(self):
        self.client.force_login(self.autor)
        valores = {f'paleta_{i}': c.lstrip('#') for i, c in enumerate(self.paleta.values(), 1)}
        respuesta = self.client.post(reverse('admin:configuracion_institucional_revisionpresentacion_add'),
            {**self.datos, **valores, 'paleta_0': 'on',
             'paleta_6': 'linear-gradient(135deg, var(--unit-green-800), var(--unit-green-600))'})
        self.assertEqual(respuesta.status_code, 302)
        revision = RevisionPresentacion.objects.get()
        self.assertEqual(revision.paleta['primario'], '#082b22')
        self.assertNotIn('var(', revision.paleta[CLAVE_DEGRADADO])
        self.assertNotContains(self.client.get('/'), 'id="paleta-institucional"')
        preview = self.client.get(reverse('admin:configuracion_institucional_revisionpresentacion_publicar', args=[revision.pk]))
        self.assertIn(revision.paleta[CLAVE_DEGRADADO], preview.content.decode())

    def test_historial_y_restauracion_conservan_degradado(self):
        primera = publicar_revision(guardar_borrador(RevisionPresentacion(**self.datos,
            paleta={**self.paleta, CLAVE_DEGRADADO: 'linear-gradient(135deg, #082b22, #064e3b)'}), self.autor).pk,
            self.autor, base_esperada=None)
        segunda = publicar_revision(guardar_borrador(RevisionPresentacion(**self.datos,
            paleta=self.paleta), self.autor).pk, self.autor, base_esperada=primera.pk)
        self.assertNotContains(self.client.get('/'), '135deg in srgb')
        tercera = publicar_revision(primera.pk, self.autor, base_esperada=segunda.pk)
        self.assertEqual(tercera.paleta, primera.paleta)
        html = self.client.get('/').content.decode()
        self.assertIn('--institucion-degradado-primario: linear-gradient(135deg in srgb', html)
        # Sin elegir alcance el degradado llega a las bandas y no a los botones.
        self.assertIn('--institucion-degradado-bandas: linear-gradient(135deg in srgb', html)
        self.assertIn('--institucion-degradado-botones: none', html)
        self.assertIn('background-image: var(--institucion-degradado-bandas)', html)

    def test_alcance_separa_bandas_de_botones_sin_tocar_el_degradado(self):
        """Elegir botones retira el degradado de las bandas y al reves."""
        base = {**self.paleta, CLAVE_DEGRADADO: 'linear-gradient(135deg, #082b22, #064e3b)'}
        esperado = {
            'botones': ('none', 'linear-gradient(135deg in srgb'),
            'bandas': ('linear-gradient(135deg in srgb', 'none'),
            'ambos': ('linear-gradient(135deg in srgb', 'linear-gradient(135deg in srgb'),
        }
        anterior = None
        for alcance, (bandas, botones) in esperado.items():
            with self.subTest(alcance=alcance):
                revision = guardar_borrador(RevisionPresentacion(
                    **self.datos, paleta={**base, 'degradado_alcance': alcance}), self.autor)
                anterior = publicar_revision(revision.pk, self.autor, base_esperada=anterior).pk
                html = self.client.get('/').content.decode()
                self.assertIn(f'--institucion-degradado-bandas: {bandas}', html)
                self.assertIn(f'--institucion-degradado-botones: {botones}', html)
                # El degradado publicado no cambia: solo cambia donde se aplica.
                self.assertIn('--institucion-degradado-primario: linear-gradient(135deg in srgb', html)

    def test_botones_y_barra_tienen_color_propio_e_independiente(self):
        """Elegir color de boton o de barra no altera los colores base."""
        publicar_revision(guardar_borrador(RevisionPresentacion(**self.datos, paleta={
            **self.paleta, 'boton_principal': '#7a3bbf', 'boton_acento': '#0f8a8a',
            'barra_color': '#3d2a6b', 'color_secundario': '#f4f1fb'}), self.autor).pk,
            self.autor, base_esperada=None)
        html = self.client.get('/').content.decode()
        for variable, valor in (('--institucion-boton-principal', '#7a3bbf'),
                                ('--institucion-boton-acento', '#0f8a8a'),
                                ('--institucion-barra', '#3d2a6b'),
                                ('--institucion-superficie', '#f4f1fb')):
            with self.subTest(variable=variable):
                self.assertIn(f'{variable}: {valor}', html)
        # El color principal declarado no cambia por elegir uno de boton.
        self.assertIn(f"--institucion-primario: {self.paleta['primario']}", html)
        # El texto del boton se decide por legibilidad sobre cada color: blanco
        # sobre el morado oscuro y tinta oscura sobre el turquesa claro.
        self.assertIn('--institucion-boton-principal-texto: #ffffff', html)
        self.assertIn(f"--institucion-boton-acento-texto: {self.paleta['texto']}", html)

    def test_sin_eleccion_los_botones_y_la_barra_heredan_el_color_base(self):
        publicar_revision(guardar_borrador(RevisionPresentacion(
            **self.datos, paleta=self.paleta), self.autor).pk, self.autor, base_esperada=None)
        html = self.client.get('/').content.decode()
        self.assertIn(f"--institucion-boton-principal: {self.paleta['primario']}", html)
        self.assertIn(f"--institucion-boton-acento: {self.paleta['acento']}", html)
        self.assertIn(f"--institucion-barra: {self.paleta['primario']}", html)

    def test_el_fondo_de_paneles_es_propio_y_vacio_conserva_el_blanco(self):
        """El color secundario pinta tarjetas y paneles, no las bandas."""
        anterior = publicar_revision(guardar_borrador(RevisionPresentacion(
            **self.datos, paleta=self.paleta), self.autor).pk, self.autor, base_esperada=None).pk
        self.assertIn('--institucion-superficie: #ffffff', self.client.get('/').content.decode())
        publicar_revision(guardar_borrador(RevisionPresentacion(**self.datos, paleta={
            **self.paleta, 'color_secundario': '#eef3f8'}), self.autor).pk, self.autor, base_esperada=anterior)
        html = self.client.get('/').content.decode()
        self.assertIn('--institucion-superficie: #eef3f8', html)
        # Elegir el fondo de los paneles no altera ningun color base.
        self.assertIn(f"--institucion-primario: {self.paleta['primario']}", html)
        self.assertIn(f"--institucion-fondo: {self.paleta['fondo']}", html)

    def test_un_fondo_de_paneles_sin_contraste_se_rechaza(self):
        with self.assertRaises(ValidationError):
            guardar_borrador(RevisionPresentacion(**self.datos, paleta={
                **self.paleta, 'color_secundario': '#123456'}), self.autor)

    def test_el_panel_de_contenidos_tiene_color_propio_por_nivel(self):
        """Modulo, carpeta y archivo elegido se pintan por separado."""
        anterior = publicar_revision(guardar_borrador(RevisionPresentacion(
            **self.datos, paleta=self.paleta), self.autor).pk, self.autor, base_esperada=None).pk
        # Vacios, cada nivel sigue al boton que le corresponde.
        html = self.client.get('/').content.decode()
        self.assertIn(f"--institucion-panel-modulo: {self.paleta['primario']}", html)
        self.assertIn(f"--institucion-panel-carpeta: {self.paleta['acento']}", html)
        self.assertIn(f"--institucion-panel-seleccion: {self.paleta['acento']}", html)

        publicar_revision(guardar_borrador(RevisionPresentacion(**self.datos, paleta={
            **self.paleta, 'panel_modulo': '#1f3a93', 'panel_carpeta': '#c0392b',
            'panel_seleccion': '#dff0d8'}), self.autor).pk, self.autor, base_esperada=anterior)
        html = self.client.get('/').content.decode()
        for variable, valor in (('--institucion-panel-modulo', '#1f3a93'),
                                ('--institucion-panel-carpeta', '#c0392b'),
                                ('--institucion-panel-seleccion', '#dff0d8')):
            with self.subTest(variable=variable):
                self.assertIn(f'{variable}: {valor}', html)
        # La tinta de cada nivel se decide por legibilidad sobre su color.
        self.assertIn('--institucion-panel-modulo-texto: #ffffff', html)
        self.assertIn(f"--institucion-panel-seleccion-texto: {self.paleta['texto']}", html)
        # Elegirlos no altera los colores base ni los botones.
        self.assertIn(f"--institucion-primario: {self.paleta['primario']}", html)
        self.assertIn(f"--institucion-boton-acento: {self.paleta['acento']}", html)

    def test_las_filas_del_panel_y_su_degradado_son_propios(self):
        """Las filas del modulo y de la carpeta abierta llevan su fondo.

        Sin elegir nada, la variable ni se declara y el panel conserva el verde
        suave derivado del color principal.
        """
        anterior = publicar_revision(guardar_borrador(RevisionPresentacion(
            **self.datos, paleta=self.paleta), self.autor).pk, self.autor, base_esperada=None).pk
        html = self.client.get('/').content.decode()
        self.assertNotIn('--institucion-panel-modulo-fondo', html)
        self.assertNotIn('--institucion-panel-imagen', html)

        publicar_revision(guardar_borrador(RevisionPresentacion(**self.datos, paleta={
            **self.paleta, 'panel_modulo_fondo': '#fdf2f2', 'panel_carpeta_fondo': '#eef6ff',
            'panel_degradado': 'linear-gradient(135deg, #00381c, #004d26)'}),
            self.autor).pk, self.autor, base_esperada=anterior)
        html = self.client.get('/').content.decode()
        self.assertIn('--institucion-panel-modulo-fondo: #fdf2f2', html)
        self.assertIn('--institucion-panel-carpeta-fondo: #eef6ff', html)
        self.assertIn('--institucion-panel-imagen: linear-gradient(135deg in srgb', html)
        # Sobre el degradado va tinta blanca: su validacion la garantiza legible.
        self.assertIn('--institucion-panel-modulo-texto: #ffffff', html)
        self.assertIn('--institucion-panel-seleccion-texto: #ffffff', html)

    def test_un_fondo_de_fila_sin_contraste_se_rechaza(self):
        with self.assertRaises(ValidationError):
            guardar_borrador(RevisionPresentacion(**self.datos, paleta={
                **self.paleta, 'panel_carpeta_fondo': '#123456'}), self.autor)

    def test_los_botones_admiten_su_propio_degradado(self):
        """Sin el, los botones dependen del alcance del degradado principal."""
        base = {**self.paleta, CLAVE_DEGRADADO: 'linear-gradient(135deg, #082b22, #064e3b)'}
        anterior = publicar_revision(guardar_borrador(RevisionPresentacion(
            **self.datos, paleta=base), self.autor).pk, self.autor, base_esperada=None).pk
        self.assertIn('--institucion-degradado-botones: none', self.client.get('/').content.decode())

        publicar_revision(guardar_borrador(RevisionPresentacion(**self.datos, paleta={
            **base, 'boton_degradado': 'linear-gradient(90deg, #00381c, #004d26)'}),
            self.autor).pk, self.autor, base_esperada=anterior)
        html = self.client.get('/').content.decode()
        self.assertIn('--institucion-degradado-botones: linear-gradient(90deg in srgb', html)
        # Las bandas conservan el suyo: son degradados independientes.
        self.assertIn('--institucion-degradado-bandas: linear-gradient(135deg in srgb', html)
        # Sobre el degradado va tinta blanca en los dos papeles de boton.
        self.assertIn('--institucion-boton-principal-texto: #ffffff', html)
        self.assertIn('--institucion-boton-acento-texto: #ffffff', html)

    def test_la_barra_admite_su_propio_degradado(self):
        publicar_revision(guardar_borrador(RevisionPresentacion(**self.datos, paleta={
            **self.paleta, 'barra_degradado': 'linear-gradient(90deg, #082b22, #064e3b)'}),
            self.autor).pk, self.autor, base_esperada=None)
        html = self.client.get('/').content.decode()
        self.assertIn('--institucion-barra-imagen: linear-gradient(90deg in srgb', html)
        self.assertIn('background-image: var(--institucion-barra-imagen)', html)

    def test_alcance_invalido_se_rechaza_al_guardar(self):
        with self.assertRaises(ValidationError):
            guardar_borrador(RevisionPresentacion(**self.datos, paleta={
                **self.paleta, CLAVE_DEGRADADO: 'linear-gradient(135deg, #082b22, #064e3b)',
                'degradado_alcance': 'todas'}), self.autor)

    def test_configuracion_entorno_aplica_mismo_contrato(self):
        datos = {**self.paleta, CLAVE_DEGRADADO: 'linear-gradient(135deg, #082b22, #064e3b)'}
        resultado = configuracion_paleta({'INSTITUTION_PALETTE_JSON': json.dumps(datos)})
        self.assertEqual(resultado, dict(validar_paleta(datos)))

    def test_degradado_no_rompe_pdf_ni_correo_que_usan_colores_solidos(self):
        publicar_revision(guardar_borrador(RevisionPresentacion(**self.datos,
            paleta={**self.paleta, CLAVE_DEGRADADO: 'linear-gradient(135deg, #082b22, #064e3b)'}), self.autor).pk,
            self.autor, base_esperada=None)
        reporte = {'scope_label': 'Unidad QA', 'category_label': 'Equipos',
                   'filter_summary': [], 'is_generic': True,
                   'generated_at': datetime(2026, 9, 17, tzinfo=timezone.utc),
                   'start_date': datetime(2026, 9, 1), 'end_date': datetime(2026, 9, 30),
                   'dataset': {'headers': ['Equipo'], 'rows': [['Equipo QA']], 'cards': []}}
        with con_presentacion_institucional():
            pdf = render_unit_report_pdf(reporte)
            correo = render_to_string('emails/reservas/_comprobante_contenido.html', identidad_publica())
        self.assertTrue(pdf.startswith(b'%PDF'))
        self.assertIn(b'/Author (Institucion QA)', pdf)
        self.assertIn('background:#082b22;', correo)
        self.assertNotIn('linear-gradient(', correo)
