"""Documentación pública visible sin activar servicios o acceso operativo."""

from datetime import date
from pathlib import Path
from tempfile import TemporaryDirectory
from types import SimpleNamespace
from unittest.mock import patch

from django.contrib.auth.models import AnonymousUser
from django.template.loader import render_to_string
from django.test import SimpleTestCase, TestCase, override_settings
from django.urls import reverse

from apps.plantas_piloto.operacion.presentation.secciones_plantas import MAPA_LABORATORIO
from apps.recursos.models.recursos import CarpetaRecurso, Recurso
from apps.gestion_unidades.models.operaciones import ConfiguracionOperativaUnidad
from apps.directorio_unidades.models.core import Unidad


class DocumentacionPublicaPlantillaTests(SimpleTestCase):
    def contexto(self, *, habilitadas=False, gestor=False, oferta=False):
        secciones = {}
        for indice, clave in enumerate(
            (
                "reservar",
                "servicios",
                "agenda",
                "requisitos",
                "mis_guias",
                "reglamento",
                "visitas",
            ),
            1,
        ):
            carpeta = SimpleNamespace(
                pk=100 + indice,
                nombre="Documento público " + clave,
                total_recursos=1,
                recursos_publicos=[],
                subcarpetas_publicas=[],
            )
            secciones[clave] = {
                "numero": MAPA_LABORATORIO.numero(clave),
                "titulo": MAPA_LABORATORIO.secciones[MAPA_LABORATORIO.numero(clave)][
                    "titulo"
                ],
                "oculta": False,
                "total_personalizado": 1,
                "carpetas_personalizadas": [carpeta],
            }
        return {
            "unidad": SimpleNamespace(slug="documentacion-qa", pk=1),
            "secciones_planta": secciones,
            "herramientas_reserva_habilitadas": habilitadas,
            "puede_gestionar_unidad": gestor,
            "oferta_visitas": {"acepta": oferta},
            "reglamento_data": {"activo": True},
            "tiene_sesiones_programadas": False,
            "request": SimpleNamespace(user=AnonymousUser()),
            "ediciones": (),
        }

    def renderizar(self, **opciones):
        return render_to_string(
            "portal/pages/unidades/detalle/reservas_secciones.html",
            self.contexto(**opciones),
        )

    def test_las_siete_secciones_muestran_documentos_sin_operaciones_activas(self):
        html = self.renderizar()
        for clave in (
            "reservar",
            "servicios",
            "agenda",
            "requisitos",
            "mis_guias",
            "reglamento",
            "visitas",
        ):
            self.assertIn("Documento público " + clave, html)
        for identificador in (
            "reservar-unidad",
            "mis-reservas",
            "catalogo-servicios",
            "agenda-disponibilidad",
            "requisitos-acceso",
            "guias-practica",
            "reglamento-unidad",
            "visitas-unidad",
        ):
            self.assertNotIn('data-id="' + identificador + '"', html)

    def test_habilitar_operacion_conserva_herramientas_preexistentes(self):
        html = self.renderizar(habilitadas=True)
        for identificador in (
            "reservar-unidad",
            "mis-reservas",
            "catalogo-servicios",
            "agenda-disponibilidad",
            "requisitos-acceso",
            "guias-practica",
            "reglamento-unidad",
        ):
            self.assertIn('data-id="' + identificador + '"', html)

    def test_documento_publico_de_visitas_no_habilita_el_boton_operativo(self):
        html = self.renderizar(habilitadas=True, oferta=True)
        self.assertIn("Documento público visitas", html)
        self.assertNotIn('data-id="visitas-unidad"', html)
        self.assertIn(
            'data-id="visitas-unidad"',
            self.renderizar(habilitadas=True, gestor=True, oferta=True),
        )
        self.assertNotIn(
            'data-id="visitas-unidad"',
            self.renderizar(habilitadas=True, gestor=True, oferta=False),
        )

    def test_ocultar_seccion_sigue_retirando_sus_documentos(self):
        contexto = self.contexto()
        contexto["secciones_planta"]["visitas"]["oculta"] = True
        html = render_to_string(
            "portal/pages/unidades/detalle/reservas_secciones.html", contexto
        )
        self.assertNotIn("Documento público visitas", html)
        self.assertIn("Documento público agenda", html)

    def test_no_se_muestran_secciones_vacias_con_operacion_desactivada(self):
        contexto = self.contexto()
        for seccion in contexto["secciones_planta"].values():
            seccion["carpetas_personalizadas"] = []
            seccion["total_personalizado"] = 0
        html = render_to_string(
            "portal/pages/unidades/detalle/reservas_secciones.html", contexto
        )
        self.assertNotIn('class="unit-folder', html)

    def test_contadores_reflejan_solo_documentos_y_acciones_visibles(self):
        html = self.renderizar()
        self.assertEqual(html.count("</strong><b>1</b>"), 7)
        contexto = self.contexto(habilitadas=True)
        contexto["tiene_sesiones_programadas"] = True
        html = render_to_string(
            "portal/pages/unidades/detalle/reservas_secciones.html", contexto
        )
        self.assertIn("Mis guías de práctica</strong><b>3</b>", html)
        self.assertIn("Reservar el laboratorio</strong><b>3</b>", html)
        self.assertIn("Visitas y uso del laboratorio</strong><b>1</b>", html)


class DocumentacionPublicaFichaTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.unidad = Unidad.objects.create(
            slug="laboratorio-logistica-comercio-internacional",
            nombre="Laboratorio documental de logística",
            dependencia="laboratorios",
            descripcion="Documentación docente",
            fecha_inicio=date(2026, 1, 1),
        )
        cls.modulo = cls.unidad.modulos_contenido.get(clave="reservas-servicios")
        configuracion, _ = ConfiguracionOperativaUnidad.objects.get_or_create(
            unidad=cls.unidad
        )
        configuracion.reservas_equipos = False
        configuracion.reservas_espacios = False
        configuracion.solicitudes_servicio = False
        configuracion.acepta_visitas = False
        configuracion.save(
            update_fields=[
                "reservas_equipos",
                "reservas_espacios",
                "solicitudes_servicio",
                "acepta_visitas",
            ]
        )
        cls.configuracion = configuracion
        for numero in ("5.1", "5.2", "5.3", "5.4", "5.5", "5.6", "5.7"):
            carpeta = CarpetaRecurso.objects.create(
                unidad=cls.unidad,
                modulo_config=cls.modulo,
                nombre="Documentos " + numero,
                seccion_planta=numero,
                activa=True,
                visibilidad="publica",
            )
            Recurso.objects.create(
                unidad=cls.unidad,
                carpeta=carpeta,
                nombre="Guía pública " + numero,
                url="https://www.upec.edu.ec/",
                activo=True,
                seguridad_verificada=True,
                visibilidad="publica",
            )
        cls.interno = Recurso.objects.create(
            unidad=cls.unidad,
            carpeta=carpeta,
            nombre="Expediente privado sensible",
            url="https://www.upec.edu.ec/",
            activo=True,
            seguridad_verificada=True,
            visibilidad="interna",
        )
        Recurso.objects.create(
            unidad=cls.unidad,
            carpeta=carpeta,
            nombre="Archivo sin revisión de seguridad",
            url="https://www.upec.edu.ec/",
            activo=True,
            seguridad_verificada=False,
            visibilidad="publica",
        )

    def test_ficha_completa_muestra_guias_conservando_bloqueos_y_privacidad(self):
        with patch("apps.gestion_unidades.presentation.detalle._registrar_visita"):
            respuesta = self.client.get(self.unidad.get_absolute_url())
        self.assertEqual(respuesta.status_code, 200)
        for numero in ("5.1", "5.2", "5.3", "5.4", "5.5", "5.6", "5.7"):
            self.assertContains(respuesta, "Guía pública " + numero)
        self.assertNotContains(respuesta, "Expediente privado sensible")
        self.assertNotContains(respuesta, "Archivo sin revisión de seguridad")
        for identificador in (
            "reservar-unidad",
            "mis-reservas",
            "catalogo-servicios",
            "agenda-disponibilidad",
            "visitas-unidad",
        ):
            self.assertNotContains(respuesta, 'data-id="' + identificador + '"')
        self.configuracion.refresh_from_db()
        self.assertFalse(self.configuracion.reservas_equipos)
        self.assertFalse(self.configuracion.reservas_espacios)
        self.assertFalse(self.configuracion.solicitudes_servicio)
        self.assertFalse(self.configuracion.acepta_visitas)
        self.assertEqual(
            self.client.get(
                reverse("recurso_unidad", args=[self.interno.pk])
            ).status_code,
            404,
        )

    def test_la_ficha_no_abre_adjuntos_y_el_visor_abre_solo_el_elegido(self):
        carpeta = self.unidad.carpetas.get(seccion_planta="5.7")
        with TemporaryDirectory() as temporal, override_settings(MEDIA_ROOT=temporal):
            base = Path(temporal) / "documentos-qa"
            base.mkdir()
            (base / "elegido.html").write_text(
                "<p>Documento elegido de prueba</p>", encoding="utf-8"
            )
            (base / "segundo.html").write_text(
                "<p>Otro documento de prueba</p>", encoding="utf-8"
            )
            elegida, _ = Recurso.objects.bulk_create(
                [
                    Recurso(
                        unidad=self.unidad,
                        carpeta=carpeta,
                        nombre="Documento elegido",
                        archivo="documentos-qa/elegido.html",
                        seguridad_verificada=True,
                        visibilidad="publica",
                    ),
                    Recurso(
                        unidad=self.unidad,
                        carpeta=carpeta,
                        nombre="Documento segundo",
                        archivo="documentos-qa/segundo.html",
                        seguridad_verificada=True,
                        visibilidad="publica",
                    ),
                ]
            )
            abiertos = []
            abrir_original = Path.open

            def abrir(ruta, *args, **kwargs):
                abiertos.append(ruta)
                return abrir_original(ruta, *args, **kwargs)

            with (
                patch("pathlib.Path.open", new=abrir),
                patch("apps.gestion_unidades.presentation.detalle._registrar_visita"),
            ):
                respuesta = self.client.get(self.unidad.get_absolute_url())
                self.assertContains(respuesta, "Documento elegido")
                self.assertContains(respuesta, "Documento segundo")
                self.assertEqual(abiertos, [])
                respuesta = self.client.get(
                    reverse("recurso_unidad", args=[elegida.pk])
                )
                self.assertEqual(respuesta.status_code, 200)
                self.assertEqual(
                    b"".join(respuesta.streaming_content),
                    b"<p>Documento elegido de prueba</p>",
                )
                # El cliente cierra la respuesta al agotar streaming_content,
                # desconectando close_old_connections durante ese cierre.
                # Cerrarla una segunda vez rompe la transacción del TestCase.
                self.assertTrue(respuesta.closed)
                self.assertEqual(abiertos, [(base / "elegido.html").resolve()])

    def test_titulo_del_recorrido_utiliza_laboratorio_en_lugar_de_planta(self):
        # El GET conserva los context processors institucionales del portal;
        # sólo la existencia de un recorrido se sustituye por un fixture local.
        with (
            patch("apps.gestion_unidades.presentation.detalle._registrar_visita"),
            patch(
                "apps.gestion_unidades.presentation.detalle.interior_de_la_planta",
                return_value={"total": 1, "plano_y_video": True},
            ),
        ):
            respuesta = self.client.get(self.unidad.get_absolute_url())
        self.assertContains(
            respuesta,
            'data-id="planta-interior" data-section-title="El laboratorio por dentro"',
        )
        self.assertNotContains(respuesta, 'data-section-title="La planta por dentro"')
