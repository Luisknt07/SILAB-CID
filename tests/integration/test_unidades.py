from datetime import date

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from apps.recursos.models.equipos import EquiposServicios
from apps.recursos.models.recursos import ModuloUnidad
from apps.directorio_unidades.models.core import Unidad
from apps.recursos.models.unidades import UnidadEquipo


class UnidadAdminTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.admin_user = get_user_model().objects.create_superuser(
            username='admin-pruebas',
            email='admin-pruebas@upec.edu.ec',
            password='clave-segura-pruebas',
        )
        cls.unidades = [
            Unidad.objects.create(
                nombre=f'Unidad administrable {dependencia}',
                descripcion='Contenido editable desde el administrador.',
                fecha_inicio=date(2026, 7, indice),
                slug=f'unidad-administrable-{dependencia}',
                dependencia=dependencia,
                area_conocimiento='otro',
            )
            for indice, dependencia in enumerate(
                ('laboratorios', 'observatorios', 'centro_experimental', 'plantas_piloto'),
                start=1,
            )
        ]

    def test_formulario_de_edicion_abre_para_las_cuatro_unidades(self):
        self.client.force_login(self.admin_user)

        for unidad in self.unidades:
            with self.subTest(dependencia=unidad.dependencia):
                response = self.client.get(
                    reverse('admin:directorio_unidades_unidad_change', args=(unidad.pk,))
                )

                self.assertEqual(response.status_code, 200)
                self.assertContains(response, unidad.nombre)
                self.assertContains(response, 'Módulos de contenido')
                self.assertNotContains(response, 'Presentación pública')
                self.assertContains(response, 'Reglamento de uso')

    def test_cada_tipo_recibe_modulos_activos_y_especificos(self):
        esperados = {
            'laboratorios': 'Docencia y capacitación',
            'observatorios': 'Datos y monitoreo',
            'centro_experimental': 'Áreas y sistemas productivos',
            'plantas_piloto': 'Procesos y protocolos',
        }

        for unidad in self.unidades:
            with self.subTest(dependencia=unidad.dependencia):
                modulos = unidad.modulos_contenido.all()
                # Los observatorios tienen cinco: el monitoreo va con los datos.
                cuantos = 5 if unidad.dependencia == 'observatorios' else 6
                self.assertEqual(modulos.count(), cuantos)
                self.assertEqual(modulos.filter(activo=True).count(), cuantos)
                self.assertTrue(modulos.filter(nombre=esperados[unidad.dependencia]).exists())

    def test_modulo_desactivado_no_aparece_en_el_detalle(self):
        unidad = self.unidades[1]
        modulo = unidad.modulos_contenido.get(clave='datos-indicadores')
        modulo.activo = False
        modulo.save(update_fields=['activo'])

        response = self.client.get(unidad.get_absolute_url())

        self.assertEqual(response.status_code, 200)
        self.assertNotContains(response, 'Datos y monitoreo')
        self.assertContains(response, 'Información general')

    def test_administrador_independiente_permite_crear_modulos(self):
        self.client.force_login(self.admin_user)
        response = self.client.get(reverse('admin:recursos_modulounidad_add'))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Módulo de contenido')

    def test_modulo_personalizado_genera_clave_y_puede_eliminarse(self):
        unidad = self.unidades[0]
        modulo = ModuloUnidad.objects.create(
            unidad=unidad,
            nombre='Servicios especializados',
            orden=7,
        )

        self.assertEqual(modulo.clave, 'servicios-especializados')
        self.assertTrue(modulo.activo)
        modulo.delete()
        self.assertFalse(ModuloUnidad.objects.filter(pk=modulo.pk).exists())

    def test_herramientas_de_reserva_solo_se_activan_en_el_modulo_asignado(self):
        unidad = self.unidades[0]
        informacion = unidad.modulos_contenido.get(clave='informacion-general')
        gestion = unidad.modulos_contenido.get(clave='reservas-servicios')

        informacion.mostrar_herramientas_reserva = True
        informacion.save()
        gestion.mostrar_herramientas_reserva = False
        gestion.save()

        informacion.refresh_from_db()
        gestion.refresh_from_db()
        self.assertFalse(informacion.mostrar_herramientas_reserva)
        self.assertTrue(gestion.mostrar_herramientas_reserva)
        self.assertEqual(
            unidad.modulos_contenido.filter(mostrar_herramientas_reserva=True).count(),
            1,
        )

    def test_detalle_no_incluye_presentacion_de_la_unidad(self):
        unidad = self.unidades[0]

        response = self.client.get(unidad.get_absolute_url())

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'data-id="video-institucional"')
        self.assertContains(response, 'unitRegulationData')
        self.assertNotContains(response, 'Presentación de la unidad')
        self.assertNotContains(response, 'unitPresentationData')
        self.assertNotIn('presentacion_data', response.context)

    def test_video_propio_reemplaza_el_institucional_solo_en_su_unidad(self):
        unidad = self.unidades[-1]
        unidad.video_unidad = 'https://youtu.be/abc123XYZ_9'
        unidad.save(update_fields=['video_unidad'])

        response = self.client.get(unidad.get_absolute_url())

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'data-initial-video-id="abc123XYZ_9"')
        self.assertContains(response, 'Video de la unidad')
        self.assertEqual(unidad.video_unidad_youtube_id, 'abc123XYZ_9')

    def test_al_ocultar_el_primer_modulo_el_siguiente_queda_activo(self):
        unidad = self.unidades[1]
        unidad.modulos_contenido.filter(clave='informacion-general').update(activo=False)
        # El público no ve las pestañas vacías del observatorio; quien gestiona sí, en su orden.
        self.client.force_login(self.admin_user)

        response = self.client.get(unidad.get_absolute_url())

        self.assertContains(
            response,
            'class="nav-link active" href="javascript:void(0);" role="tab" aria-selected="true" aria-current="page" data-modulo="datos-indicadores"',
        )

    def test_detalle_incluye_equipo_asignado_por_relacion_principal(self):
        unidad = self.unidades[0]
        equipo = EquiposServicios.objects.create(
            codigo="EQ-PRINCIPAL-TEST",
            nombre="Equipo principal de prueba",
        )
        UnidadEquipo.objects.create(
            codigo_unidad="EQ-PRINCIPAL-TEST-01",
            equipo=equipo,
            laboratorio=unidad,
        )

        response = self.client.get(unidad.get_absolute_url())

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context["total_equipos"], 1)
        self.assertEqual(response.context["total_unidades_equipo"], 1)
        self.assertQuerySetEqual(response.context["equipos_servicios"], [equipo])

    def test_configuracion_operativa_controla_acciones_publicas(self):
        unidad = self.unidades[0]
        configuracion = unidad.configuracion_operativa
        configuracion.solicitudes_servicio = False
        configuracion.reservas_equipos = False
        configuracion.reservas_espacios = False
        configuracion.save(
            update_fields=[
                "solicitudes_servicio",
                "reservas_equipos",
                "reservas_espacios",
            ]
        )

        response = self.client.get(unidad.get_absolute_url())

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context["configuracion_operativa"], configuracion)
        self.assertNotContains(response, "Solicitar servicio")
        self.assertNotContains(response, "Reservar equipos")
        self.assertNotContains(response, "Reservar la unidad")

    def test_detalle_publico_no_expone_gestion_ni_reportes_operativos(self):
        unidad = self.unidades[0]

        response = self.client.get(unidad.get_absolute_url())

        self.assertEqual(response.status_code, 200)
        self.assertNotContains(response, "Operaci\u00f3n y acceso")
        self.assertNotContains(response, "Gestionar unidad")
        self.assertNotContains(response, "Solicitar servicio")
        self.assertNotContains(response, "Control operativo")
        self.assertNotContains(response, "Estado de la unidad")
        self.assertNotIn("tablero_operativo", response.context)
        self.assertNotIn("resumen_usuario", response.context)

    def test_detalle_publico_no_muestra_panel_de_categorias_de_equipos(self):
        unidad = self.unidades[0]

        response = self.client.get(unidad.get_absolute_url())

        self.assertEqual(response.status_code, 200)
        self.assertNotContains(response, "Categorías de equipos")
        self.assertNotIn("categorias_equipo", response.context)

    def test_mis_reservas_usa_calendario_con_detalle_integrado(self):
        unidad = self.unidades[0]

        response = self.client.get(unidad.get_absolute_url())

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'class="modal fade reservation-modal reservation-history-modal"')
        self.assertContains(response, 'class="modal-dialog reservation-history-modal__dialog"')
        self.assertContains(response, 'id="misReservasMesDias"')
        self.assertContains(response, 'id="misReservasListado"')
        self.assertContains(response, 'data-reservations-list')
        self.assertContains(response, 'id="misReservasSemanaCuerpo"')
        self.assertNotContains(response, 'id="detalleReservaModal"')
        self.assertNotContains(response, 'id="confirmacionModal"')
        # El marcador de version evita que el navegador conserve el modal
        # anterior en cache. Se valida que exista, no un valor literal que
        # obligue a editar la prueba en cada publicacion de estaticos.
        self.assertRegex(
            response.content.decode(),
            r"modal_mis_reservas\.js[^\"]*\?v=[0-9A-Za-z._-]+",
        )

    def test_reserva_respeta_capacidades_desactivadas(self):
        unidad = self.unidades[2]
        configuracion = unidad.configuracion_operativa
        configuracion.solicitudes_servicio = False
        configuracion.reservas_equipos = False
        configuracion.reservas_espacios = False
        configuracion.seguimiento = False
        configuracion.consumibles = False
        configuracion.save()

        response = self.client.get(unidad.get_absolute_url())

        self.assertNotContains(response, "Solicitar servicio")
        self.assertNotContains(response, "Programar reserva")
        self.assertNotContains(response, "Ver seguimiento")
        self.assertNotContains(response, "Materiales y consumibles")


class CatalogoUnidadesTests(TestCase):
    catalogos = (
        ('hublab', 'laboratorios', 'Laboratorios'),
        ('observatorios', 'observatorios', 'Observatorios'),
        ('centros-experimentales', 'centro_experimental', 'Centros Experimentales'),
        ('plantas-piloto', 'plantas_piloto', 'Plantas Piloto'),
    )

    @classmethod
    def setUpTestData(cls):
        cls.unidades = {}
        for indice, (_, dependencia, _) in enumerate(cls.catalogos, start=1):
            cls.unidades[dependencia] = Unidad.objects.create(
                nombre=f'Unidad {dependencia}',
                descripcion=f'Descripción de prueba {dependencia}',
                fecha_inicio=date(2026, 1, indice),
                slug=f'unidad-{dependencia}',
                dependencia=dependencia,
                area_conocimiento='otro',
            )

    def test_cada_catalogo_muestra_solo_su_dependencia(self):
        for route_name, dependencia, titulo in self.catalogos:
            with self.subTest(route_name=route_name):
                response = self.client.get(reverse(route_name))

                self.assertEqual(response.status_code, 200)
                self.assertTemplateUsed(
                    response,
                    'portal/pages/unidades/catalogo_unidades.html',
                )
                self.assertEqual(response.context['catalogo_titulo'], titulo)
                self.assertQuerySetEqual(
                    response.context['unidades'],
                    [self.unidades[dependencia]],
                )

    def test_page_size_invalido_recupera_el_valor_predeterminado(self):
        response = self.client.get(reverse('hublab'), {'page_size': 'invalido'})

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context['page_size'], 8)

    def test_planta_sin_contenido_usa_portada_y_estado_en_construccion(self):
        response = self.client.get(reverse('plantas-piloto'))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'En construcción')
        self.assertContains(response, '/static/img/default_project.jpg')
        self.assertNotContains(response, 'lab-unit-card__views')

    def test_los_cuatro_catalogos_paginan_despues_de_ocho_unidades(self):
        for route_name, dependencia, _ in self.catalogos:
            Unidad.objects.bulk_create([
                Unidad(
                    nombre=f'Unidad adicional {dependencia} {indice}',
                    descripcion='Unidad creada para comprobar la paginación.',
                    fecha_inicio=date(2026, 2, indice),
                    slug=f'unidad-adicional-{dependencia}-{indice}',
                    dependencia=dependencia,
                    area_conocimiento='otro',
                )
                for indice in range(1, 9)
            ])

            with self.subTest(route_name=route_name):
                response = self.client.get(reverse(route_name))

                self.assertEqual(response.status_code, 200)
                self.assertEqual(response.context['page_size'], 8)
                self.assertEqual(response.context['paginator'].count, 9)
                self.assertEqual(response.context['paginator'].num_pages, 2)
                self.assertEqual(len(response.context['unidades']), 8)
                self.assertContains(response, 'Página <b>1</b> de <b>2</b>')

            Unidad.objects.filter(
                dependencia=dependencia,
                slug__startswith=f'unidad-adicional-{dependencia}-',
            ).delete()

    def test_experiencia_interactiva_aparece_solo_en_observatorios(self):
        observatorios = self.client.get(reverse('observatorios'))

        self.assertEqual(observatorios.status_code, 200)
        self.assertContains(observatorios, 'data-observatory-experience')
        self.assertContains(observatorios, 'data-obs-step="5"')
        self.assertContains(observatorios, 'data-open-resource', count=6)
        self.assertContains(observatorios, 'data-obs-resource-dialog')
        self.assertContains(observatorios, '<details class="observatory-experience"')
        self.assertContains(observatorios, '<summary class="obs-experience__toggle">')
        self.assertContains(observatorios, 'data-obs-library-content')
        self.assertContains(observatorios, 'mapas-territoriales.webp')
        self.assertContains(observatorios, 'documentacion-metodologias.webp')
        self.assertContains(observatorios, '¿Qué es un observatorio UPEC?')
        self.assertContains(observatorios, 'Información confiable y actualizada')
        # Sin video ajeno ni cifras escritas a mano: una guía para leer un observatorio.
        self.assertContains(observatorios, 'Cómo leer un observatorio')
        self.assertNotContains(observatorios, 'img/video/fablab.mp4')
        self.assertNotContains(observatorios, '68 indicadores')
        self.assertContains(observatorios, 'data-obs-coverflow')
        self.assertContains(observatorios, 'data-coverflow-prev')
        self.assertContains(observatorios, 'data-coverflow-next')

        for route_name in ('hublab', 'centros-experimentales', 'plantas-piloto'):
            with self.subTest(route_name=route_name):
                response = self.client.get(reverse(route_name))
                self.assertNotContains(response, 'data-observatory-experience')

    def test_plantas_piloto_incluye_experiencia_interactiva_estandarizada(self):
        response = self.client.get(reverse('plantas-piloto'))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'id="experiencia-plantas-piloto"')
        self.assertContains(response, 'data-unit-experience')
        self.assertContains(response, 'data-obs-step="5"')
        self.assertContains(response, 'data-open-resource', count=5)
        self.assertContains(response, 'data-obs-resource-dialog')
        self.assertContains(response, 'data-obs-coverflow')
        self.assertContains(response, '<video')
        self.assertContains(response, 'Planta piloto de cárnicos')
        self.assertContains(response, 'Planta piloto de lácteos')
        self.assertContains(response, 'Planta piloto de panificación')
        self.assertContains(response, 'Planta piloto de cervezas y almidones')
        self.assertContains(response, 'Planta piloto de frutas y vegetales')

    def test_centros_experimentales_incluye_experiencia_interactiva_estandarizada(self):
        response = self.client.get(reverse('centros-experimentales'))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'id="experiencia-centros-experimentales"')
        self.assertContains(response, 'data-unit-experience')
        self.assertContains(response, 'data-obs-step="5"')
        self.assertContains(response, 'data-open-resource', count=6)
        self.assertContains(response, 'data-obs-resource-dialog')
        self.assertContains(response, 'data-obs-coverflow')
        self.assertContains(response, '<video')
        self.assertContains(response, 'Centro Experimental Alonzo Tadeo')
        self.assertContains(response, 'Centro Experimental San Francisco')
        self.assertContains(response, 'Más de 20 hectáreas')
        self.assertContains(response, 'Más de 40 hectáreas')
        self.assertContains(response, 'Galpones de gallinas')
        self.assertContains(response, 'Ganado lechero y plantas piloto')

    def test_page_size_se_limita_a_cien(self):
        response = self.client.get(reverse('hublab'), {'page_size': '5000'})

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context['page_size'], 100)

    def test_cada_dependencia_abre_su_detalle(self):
        for unidad in self.unidades.values():
            with self.subTest(dependencia=unidad.dependencia):
                response = self.client.get(unidad.get_absolute_url())

                self.assertEqual(response.status_code, 200)
                self.assertTemplateUsed(response, 'portal/pages/unidades/detalle/detalle_unidad.html')
                self.assertEqual(response.context['unidad'], unidad)
                self.assertContains(response, 'class="project-detail-page"')
                self.assertContains(response, 'class="project-detail-hero"')
                self.assertContains(response, 'project-detail-workspace')
                self.assertNotContains(response, 'project-detail-heading-row')
