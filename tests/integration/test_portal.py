from django.contrib.staticfiles import finders
from django.test import TestCase
from django.urls import reverse


class PortalInformativoTests(TestCase):
    paginas = (
        (
            'quienes_somos',
            'portal/pages/quienes_somos/quienes_somos.html',
            'quienes',
            'Quiénes somos',
        ),
        (
            'centros_id',
            'centros_id/portada.html',
            'centros',
            'Centros I+D',
        ),
        (
            'laboratorios_unidades',
            'portal/pages/unidades/catalogo_unidades.html',
            'laboratorios',
            'Laboratorios y Unidades Experimentales',
        ),
        (
            'servicios_portal',
            'portal/pages/servicios/servicios.html',
            'servicios',
            'Servicios',
        ),
        (
            'normativa',
            'portal/pages/normativa/normativa.html',
            'normativa',
            'Normativa',
        ),
        (
            'noticias',
            'portal/pages/noticias/noticias.html',
            'noticias',
            'Noticias',
        ),
    )

    def test_paginas_informativas_usan_plantilla_y_contexto_propios(self):
        for route_name, template_name, page_key, page_title in self.paginas:
            with self.subTest(route_name=route_name):
                response = self.client.get(reverse(route_name))

                self.assertEqual(response.status_code, 200)
                self.assertTemplateUsed(response, template_name)
                self.assertTemplateUsed(response, 'portal/layouts/base.html')
                self.assertEqual(response.context['page_key'], page_key)
                self.assertEqual(response.context['page_title'], page_title)

    def test_paginas_cargan_la_cascada_institucional_completa(self):
        inicio = self.client.get(reverse('home')).content.decode()
        hublab = self.client.get(reverse('hublab')).content.decode()
        quienes = self.client.get(reverse('quienes_somos')).content.decode()
        servicios = self.client.get(reverse('servicios_portal')).content.decode()
        centros = self.client.get(reverse('centros_id')).content.decode()

        for contenido in (inicio, hublab, quienes, servicios, centros):
            self.assertIn('portal/css/portal.css', contenido)

    def test_cabecera_institucional_es_compartida_y_tiene_un_activo(self):
        rutas = (
            'home',
            'quienes_somos',
            'centros_id',
            'laboratorios_unidades',
            'servicios_portal',
            'normativa',
            'noticias',
            'hublab',
        )

        for route_name in rutas:
            with self.subTest(route_name=route_name):
                response = self.client.get(reverse(route_name))
                contenido = response.content.decode()
                inicio_cabecera = contenido.index('<header class="home-top"')
                fin_cabecera = contenido.index('</header>', inicio_cabecera)
                cabecera = contenido[inicio_cabecera:fin_cabecera]

                self.assertEqual(response.status_code, 200)
                self.assertTemplateUsed(
                    response,
                    'portal/components/navegacion/encabezado_institucional.html',
                )
                self.assertEqual(cabecera.count('class="active"'), 1)
                self.assertEqual(contenido.count('id="homeTop"'), 1)
                self.assertEqual(contenido.count('id="homeMenu"'), 1)

    def test_quienes_somos_se_compone_de_secciones_reutilizables(self):
        response = self.client.get(reverse('quienes_somos'))
        secciones = (
            'portal/pages/quienes_somos/secciones/portada.html',
            'portal/pages/quienes_somos/secciones/proposito.html',
            'portal/components/unidades_conectadas.html',
            'portal/pages/quienes_somos/secciones/pilares_sistema.html',
            'portal/pages/quienes_somos/secciones/historia.html',
            'portal/components/ecosistema_industrial.html',
            'portal/pages/quienes_somos/secciones/innovacion.html',
            'portal/pages/quienes_somos/secciones/equipo_institucional.html',
            'portal/pages/quienes_somos/secciones/multimedia.html',
            'portal/components/experiencias_interactivas.html',
            'portal/pages/quienes_somos/secciones/contacto.html',
        )

        for template_name in secciones:
            self.assertTemplateUsed(response, template_name)

        contenido_quienes = response.content.decode()
        contenido_inicio = self.client.get(reverse('home')).content.decode()
        self.assertIn(
            'class="industry-ecosystem moved-industry-source"',
            contenido_quienes,
        )
        self.assertIn('class="industry-ecosystem"', contenido_inicio)
        self.assertNotIn(
            'class="industry-ecosystem moved-industry-source"',
            contenido_inicio,
        )

    def test_sistema_visual_institucional_se_carga_desde_la_base(self):
        response = self.client.get(reverse('home'))
        contenido = response.content.decode()

        self.assertIn('portal/css/core/tokens.css', contenido)
        self.assertIn('portal/css/core/foundation.css', contenido)
        self.assertIn('portal/css/components/botones.css', contenido)
        self.assertNotIn('base_typography.css', contenido)
        self.assertIn('upec-button--outline', contenido)
        self.assertIn('upec-button--primary', contenido)

        for static_path in (
            'portal/css/core/tokens.css',
            'portal/css/core/foundation.css',
            'portal/css/components/botones.css',
            'portal/css/components/encabezado_institucional.css',
            'portal/js/components/encabezado_institucional.js',
        ):
            self.assertIsNotNone(finders.find(static_path))

    def test_paginas_principales_usan_portada_tecnologica_sin_barra_antigua(self):
        for route_name in (
            'centros_id',
            'laboratorios_unidades',
            'normativa',
            'noticias',
        ):
            with self.subTest(route_name=route_name):
                response = self.client.get(reverse(route_name))
                contenido = response.content.decode()

                self.assertEqual(response.status_code, 200)
                self.assertIn('class="institutional-page', contenido)
                self.assertIn('institutional-hero', contenido)
                if route_name == 'centros_id':
                    # Centros I+D tiene su portada independiente y acceso
                    # directo a su catálogo, sin heredar el menú de unidades.
                    self.assertTemplateUsed(response, 'centros_id/portada.html')
                    self.assertIn('href="#centros"', contenido)
                    self.assertIn('<section id="centros" data-vista="list"', contenido)
                else:
                    self.assertIn('institutional-local-nav', contenido)
                self.assertNotIn('navbar fixed-top', contenido)
                self.assertNotIn('portal-side', contenido)
                self.assertEqual(contenido.count('id="homeTop"'), 1)

    def test_laboratorios_integra_catalogo_y_conserva_los_cuatro_accesos(self):
        response = self.client.get(reverse('laboratorios_unidades'))
        contenido = response.content.decode()

        self.assertTemplateUsed(
            response,
            'portal/pages/unidades/catalogo/filtros_y_listado.html',
        )
        self.assertIn('id="catalogo-unidades"', contenido)
        self.assertIn('class="lab-catalog-filters"', contenido)
        self.assertIn('data-catalog-grid', contenido)
        for route_name in (
            'hublab',
            'observatorios',
            'centros-experimentales',
            'plantas-piloto',
        ):
            self.assertIn(f'href="{reverse(route_name)}"', contenido)
