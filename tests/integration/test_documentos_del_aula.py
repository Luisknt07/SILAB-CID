"""Cada página del aula se ve y se baja como documento, no como captura.

El «Imprimir / Guardar como PDF» del navegador escribía la dirección y la fecha
en los bordes, cortaba las tablas donde caía y no sabía nada del formato
institucional. Ahora la página es su propia vista previa y el mismo contexto que
la pinta arma el PDF: primero se ve, después se baja, y lo revisado es
exactamente lo descargado.

Dentro del visor de la unidad, además, la barra deja de repetir la navegación
que ya está a la derecha.
"""

from datetime import date
from pathlib import Path

from django.conf import settings
from django.contrib.auth import get_user_model
from django.urls import reverse

from apps.plantas_piloto.operacion.models.produccion import Receta
from apps.formacion.models.aula import SimulacionGuardada
from apps.directorio_unidades.models.core import Unidad
from tests.integration.test_produccion_planta import BasePlantaProduce

from django.template.loader import get_template

AULA = Path(get_template('portal/pages/unidades/aula/includes/visor_pdf_modal.html').origin.name).parents[1]


def unidad_vacia(slug):
    """Una unidad recién creada: sin recetas, sin productos y sin equipos."""
    return Unidad.objects.create(
        nombre=slug.replace('-', ' ').capitalize(),
        slug=slug,
        dependencia='laboratorios',
        descripcion='Unidad recién abierta, todavía sin contenido cargado.',
        fecha_inicio=date(2026, 1, 1),
    )


class LasPaginasDelAulaSeBajanComoDocumentoTests(BasePlantaProduce):
    def paginas(self):
        receta = self.receta_queso
        return [
            ('ficha', reverse('ficha_proceso_publica', args=[self.unidad.slug, receta.pk]), {}),
            ('producto', reverse('ficha_producto_publica', args=[self.unidad.slug, receta.producto_id]), {}),
            ('documentacion', reverse('documentacion_proceso', args=[self.unidad.slug, receta.pk]), {}),
            ('indice_materiales', reverse('materiales_insumos', args=[self.unidad.slug]), {}),
            ('indice_metodos', reverse('metodos_tiempos', args=[self.unidad.slug]), {}),
            (
                'indice_documentacion',
                reverse('ruta_saber_documentacion', args=[self.unidad.slug]),
                {},
            ),
            ('balance', reverse('simulador_balance', args=[self.unidad.slug]), {'receta': receta.pk}),
            ('linea', reverse('simulador_linea', args=[self.unidad.slug]), {'receta': receta.pk}),
            ('materiales', reverse('simulador_materiales', args=[self.unidad.slug]), {'receta': receta.pk}),
            ('protocolos', reverse('protocolos_control', args=[self.unidad.slug]), {}),
            ('produccion', reverse('produccion_publica', args=[self.unidad.slug]), {}),
            ('corridas_lotes', reverse('corridas_lotes_publicos', args=[self.unidad.slug]), {}),
            ('calidad', reverse('calidad_publica', args=[self.unidad.slug]), {}),
            ('areas', reverse('areas_equipos', args=[self.unidad.slug]), {}),
        ]

    def test_cada_pagina_ofrece_ver_el_documento_y_descargarlo(self):
        for clave, url, parametros in self.paginas():
            with self.subTest(pagina=clave):
                pagina = self.client.get(url, parametros)
                self.assertEqual(pagina.status_code, 200)
                self.assertContains(pagina, 'Ver el documento')
                self.assertContains(pagina, 'Descargar documento')
                self.assertContains(pagina, 'data-descargar-pdf')
                self.assertContains(pagina, 'formato=pdf')
                self.assertContains(pagina, 'data-ver-pdf')
                self.assertContains(pagina, 'data-aula-pdf-modal')
                self.assertNotContains(
                    pagina, 'target="_blank" rel="noopener">Ver el documento',
                )

    def test_la_vista_previa_la_dibuja_la_plataforma_y_no_el_navegador(self):
        """El complemento de PDF del navegador no muestra nada en un telefono.

        La vista previa dibuja el documento con el mismo visor que ya usa la
        consola de la unidad, asi que se ve en pantallas pequenas y se amplia
        con los dedos.
        """
        pagina = self.client.get(*self.paginas()[0][1:])
        contenido = pagina.content.decode()
        self.assertIn('portal/js/components/visor_pdf.js', contenido)
        self.assertIn('<div class="aula-pdf-modal__visor" data-visor-pdf', contenido)
        # Ya no se delega el dibujo a un marco del navegador.
        self.assertNotIn('<iframe title="Vista previa del documento PDF"', contenido)
        # La descarga sigue a mano por si el visor no llegara a cargar.
        self.assertIn('data-descargar-pdf', contenido)
        # Un comentario de plantilla mal cerrado se imprimiria sobre el documento.
        self.assertNotIn('El documento se dibuja con el visor', contenido)

    def test_la_consola_de_la_unidad_usa_el_mismo_visor(self):
        """Un solo visor para toda la plataforma, no una copia por pantalla."""
        from django.contrib.staticfiles import finders

        componente = 'portal/js/components/visor_pdf.js'
        self.assertIsNotNone(finders.find(componente))
        self.assertIsNotNone(finders.find('portal/css/components/visor_pdf.css'))
        plantillas = (
            AULA / 'includes' / 'visor_pdf_modal.html',
            Path(get_template('portal/pages/unidades/detalle/detalle_unidad.html').origin.name),
        )
        for plantilla in plantillas:
            with self.subTest(plantilla=plantilla.name):
                self.assertIn(componente, plantilla.read_text(encoding='utf-8'))

    def test_el_visor_lee_el_documento_como_los_reportes(self):
        """Hoja blanca sobre lienzo neutro y el ancho de la hoja del reporte.

        Si el fondo toma el verde de la paleta, la hoja se confunde con él y
        el documento deja de leerse como el papel que es.
        """
        from django.contrib.staticfiles import finders

        hoja = Path(finders.find('portal/css/components/visor_pdf.css')).read_text(encoding='utf-8')
        modal = (AULA / 'includes' / 'visor_pdf_modal.html').read_text(encoding='utf-8')
        estilo_modal = 'portal/css/components/visor_pdf_modal.css'
        self.assertIn(estilo_modal, modal)
        ruta_estilo_modal = finders.find(estilo_modal)
        self.assertIsNotNone(ruta_estilo_modal)
        panel = Path(ruta_estilo_modal).read_text(encoding='utf-8')

        self.assertIn('--visor-lienzo', hoja)
        self.assertIn('background: var(--visor-lienzo', hoja)
        # El lienzo del documento no se tiñe con la paleta institucional.
        self.assertNotIn('.pdf-viewer-layout {\n    display: flex;\n    flex: 1 1 auto;\n'
                         '    width: 100%;\n    min-height: 0;\n'
                         '    background: var(--institucion-fondo', hoja)
        # El mismo ancho que la hoja del reporte operativo. El estilo compartido
        # se carga desde la plantilla para poder reutilizarlo y almacenarlo en caché.
        self.assertIn('width: min(1480px, 100%)', panel)
        self.assertIn('max-height: calc(100vh - 28px)', panel)
        self.assertIn('background: #f4f5f5', panel)

    def test_el_documento_se_abre_para_revisarlo_antes_de_bajarlo(self):
        for clave, url, parametros in self.paginas():
            with self.subTest(pagina=clave):
                respuesta = self.client.get(url, {**parametros, 'formato': 'pdf'})
                self.assertEqual(respuesta.status_code, 200)
                self.assertEqual(respuesta['Content-Type'], 'application/pdf')
                # «inline» es lo que abre el visor del navegador en vez de bajarlo.
                self.assertTrue(respuesta['Content-Disposition'].startswith('inline;'))
                self.assertTrue(respuesta.content.startswith(b'%PDF'))

    def test_y_despues_se_baja_el_mismo_documento(self):
        for clave, url, parametros in self.paginas():
            with self.subTest(pagina=clave):
                respuesta = self.client.get(url, {**parametros, 'formato': 'pdf', 'descargar': '1'})
                self.assertTrue(respuesta['Content-Disposition'].startswith('attachment;'))
                self.assertIn('.pdf', respuesta['Content-Disposition'])
                self.assertTrue(respuesta.content.startswith(b'%PDF'))

    def test_el_documento_lleva_texto_y_el_logo_no_es_una_foto_de_la_pantalla(self):
        respuesta = self.client.get(
            reverse('ficha_proceso_publica', args=[self.unidad.slug, self.receta_queso.pk]),
            {'formato': 'pdf'},
        )

        contenido = respuesta.content
        # Una captura viaja como una sola imagen; este PDF lleva fuentes.
        self.assertIn(b'/Font', contenido)
        # El logo va como imagen propia, con su máscara de transparencia.
        self.assertIn(b'/SMask', contenido)

    def test_ninguna_pagina_del_aula_manda_a_imprimir_el_navegador(self):
        sospechosas = [
            ruta.name for ruta in (Path(settings.BASE_DIR) / 'apps').rglob('*.html')
            if '/templates/portal/pages/unidades/aula/' in ruta.as_posix()
            if 'window.print()' in ruta.read_text(encoding='utf-8')
        ]
        self.assertEqual(sospechosas, [], f'todavía imprimen con el navegador: {sospechosas}')

    def test_una_unidad_sin_procesos_no_finge_tener_documentos(self):
        laboratorio = unidad_vacia('laboratorio-sin-procesos')

        respuesta = self.client.get(
            reverse('protocolos_control', args=[laboratorio.slug]), {'formato': 'pdf'}
        )

        self.assertEqual(respuesta.status_code, 404)


class DentroDelVisorNoSeRepiteLaNavegacionTests(BasePlantaProduce):
    def test_solo_el_regreso_se_marca_para_esconderse(self):
        pagina = self.client.get(
            reverse('simulador_balance', args=[self.unidad.slug]), {'receta': self.receta_queso.pk}
        )

        cuerpo = pagina.content.decode()
        self.assertIn('class="es-navegacion"', cuerpo)
        # Solo el regreso pertenece al marco; las acciones del proceso quedan visibles.
        self.assertIn('accion-proceso is-active', cuerpo)
        self.assertNotIn('class="es-navegacion" href="?', cuerpo)

    def test_la_hoja_de_estilo_esconde_esa_navegacion_cuando_va_incrustada(self):
        hoja = (
            Path(settings.BASE_DIR) / 'apps' / 'gestion_unidades' / 'static' / 'portal' / 'css' / 'pages' / 'unidades' / 'reporte_gestion.css'
        ).read_text(encoding='utf-8')

        self.assertIn('.esta-incrustado .unit-report__toolbar .es-navegacion { display: none; }', hoja)
        self.assertNotIn('.esta-incrustado .unit-report__toolbar .accion-proceso { display: none; }', hoja)


class LoQueProduceViveEnLaSeccionCuatroUnoTests(BasePlantaProduce):
    def test_el_catalogo_no_se_repite_en_la_portada_de_produccion(self):
        pagina = self.client.get(self.unidad.get_absolute_url())

        cuerpo = pagina.content.decode()
        self.assertEqual(pagina.status_code, 200)
        self.assertNotIn('unit-panel--operations" aria-label="Lo que produce', cuerpo)
        portada = cuerpo.split('data-portada-modulo="produccion-lotes"')[1].split('</template>', 1)[0]
        self.assertNotIn('<h3>Lo que produce</h3>', portada)
        self.assertIn('Lo que produce la planta', portada)
        self.assertNotIn('Queso fresco', portada)

        catalogo = self.client.get(reverse('produccion_publica', args=[self.unidad.slug]))
        self.assertContains(catalogo, 'Queso fresco')
        self.assertContains(catalogo, '$6,50 / kg')

    def test_una_unidad_sin_productos_no_estrena_el_bloque(self):
        laboratorio = unidad_vacia('laboratorio-sin-productos')

        pagina = self.client.get(laboratorio.get_absolute_url())

        self.assertEqual(pagina.status_code, 200)
        self.assertNotContains(pagina, '<h3>Lo que produce</h3>')


class LosDocumentosDelEstudianteTests(BasePlantaProduce):
    def setUp(self):
        super().setUp()
        self.estudiante = get_user_model().objects.create_user(
            username='estudiante.documentos',
            email='estudiante.documentos@upec.edu.ec',
            password='clave-segura-pruebas',
        )
        self.client.force_login(self.estudiante)

    def test_mis_ejercicios_y_mis_simulaciones_tambien_se_bajan(self):
        SimulacionGuardada.objects.create(
            unidad=self.unidad,
            autor=self.estudiante,
            simulador='balance',
            receta=Receta.objects.filter(unidad=self.unidad, activa=True).first(),
            nombre='Una corrida guardada',
            parametros={'receta': str(self.receta_queso.pk), 'cantidad': '100'},
        )
        for nombre in ('mis_ejercicios', 'mis_simulaciones'):
            with self.subTest(pagina=nombre):
                url = reverse(nombre, args=[self.unidad.slug])
                pagina = self.client.get(url)
                self.assertContains(pagina, 'Ver el documento')

                pdf = self.client.get(url, {'formato': 'pdf', 'descargar': '1'})
                self.assertEqual(pdf['Content-Type'], 'application/pdf')
                self.assertTrue(pdf.content.startswith(b'%PDF'))
