"""Límites SQL, alcance y edición de catálogos que superan una página."""

from urllib.parse import parse_qs, urlparse
from django.test import TestCase
from django.db import connection
from django.urls import reverse
from apps.recursos.models.consumibles import Consumible
from apps.recursos.models.equipos import EquiposServicios
from apps.gestion_unidades.models.espacios import EspacioReservable
from apps.recursos.models.software import SoftwareDisponible
from apps.recursos.models.unidades import UnidadEquipo
from tests.integration import test_panel_gestion_unidad as fixtures


class CatalogosPaginadosTests(TestCase):
    databases = {'default', 'centros'}
    @classmethod
    def setUpTestData(cls):
        fixtures.PanelGestionUnidadTests.setUpTestData.__func__(cls)
        cls.modelos = EquiposServicios.objects.bulk_create(
            [
                EquiposServicios(codigo=f"CAT-{i:03}", nombre=f"Modelo catálogo {i:03}")
                for i in range(102)
            ]
        )
        cls.fisicos = UnidadEquipo.objects.bulk_create(
            [
                UnidadEquipo(
                    equipo=modelo, laboratorio=cls.unidad, codigo_unidad=f"FIS-{i:03}"
                )
                for i, modelo in enumerate(cls.modelos)
            ]
        )
        EspacioReservable.objects.bulk_create(
            [
                EspacioReservable(
                    unidad=cls.unidad,
                    codigo=f"ESP-{i:03}",
                    nombre=f"Espacio catálogo {i:03}",
                    capacidad=4,
                )
                for i in range(102)
            ]
        )
        SoftwareDisponible.objects.bulk_create(
            [
                SoftwareDisponible(
                    unidad=cls.unidad,
                    nombre=f"Software catálogo {i:03}",
                    licencias_totales=2,
                    licencias_disponibles=1,
                )
                for i in range(102)
            ]
        )
        Consumible.objects.bulk_create(
            [
                Consumible(
                    unidad=cls.unidad,
                    codigo=f"INS-{i:03}",
                    nombre=f"Insumo catálogo {i:03}",
                )
                for i in range(102)
            ]
        )
        cls.ajeno = UnidadEquipo.objects.create(
            equipo=cls.modelos[0],
            laboratorio=cls.otra_unidad,
            codigo_unidad="AJENO-CATALOGO",
        )

    def setUp(self):
        self.client.force_login(self.coordinador)
        self.buscar_url = reverse("gestion_recursos_buscar", args=[self.unidad.slug])

    def abrir(self, modo, pagina=1, **parametros):
        return self.client.get(
            self.url,
            {
                "view": "recursos",
                "modo_recursos": modo,
                "pagina_recursos": pagina,
                "fragment": "1",
                **parametros,
            },
        )

    def test_cuatro_catalogos_limitan_sql_y_ultima_pagina(self):
        for modo, clave in (
            ("activos", "equipos"),
            ("espacios", "espacios_gestion"),
            ("software", "software_gestion"),
            ("insumos", "consumibles"),
        ):
            with self.subTest(modo=modo):
                tamano, ultima_pagina, ultimo_total = (12, 9, 6) if modo in {'software', 'insumos'} else (50, 3, 2)
                primera = self.abrir(modo)
                segunda = self.abrir(modo, 2)
                ultima = self.abrir(modo, ultima_pagina)
                self.assertEqual(primera.status_code, 200)
                self.assertEqual(len(primera.context[clave]), tamano)
                self.assertEqual(len(segunda.context[clave]), tamano)
                self.assertEqual(len(ultima.context[clave]), ultimo_total)
                self.assertEqual(primera.context['recursos_tamano_pagina'], tamano)
                ids1 = {obj.pk for obj in primera.context[clave]}
                ids2 = {obj.pk for obj in segunda.context[clave]}
                self.assertFalse(ids1 & ids2)
                consulta_pagina = primera.context['recursos_modelos_pagina'] if modo == 'activos' else primera.context['recursos_pagina']
                sql, _ = consulta_pagina.object_list.query.sql_with_params()
                self.assertIn(f"LIMIT {tamano}", sql)
                self.assertEqual(primera.context["catalogos_equipos"], [])
                self.assertContains(primera, "data-resource-select=")
                self.assertNotContains(primera, "data-tabla-buscar")
                self.assertEqual(
                    self.abrir(modo, 999).context["recursos_pagina"].number, ultima_pagina
                )
                self.assertEqual(
                    self.abrir(modo, "invalida").context["recursos_pagina"].number, 1
                )

    def test_busqueda_fuera_de_pagina_y_navegacion_preservan_parametros(self):
        respuesta = self.abrir(
            "espacios", busqueda_recursos="101", estado_recursos="todos"
        )
        self.assertEqual(
            [e.nombre for e in respuesta.context["espacios_gestion"]],
            ["Espacio catálogo 101"],
        )
        respuesta = self.abrir(
            "software", modal="1", semana="2026-10-11", estado_recursos="todos"
        )
        query = parse_qs(urlparse(respuesta.context["recursos_siguiente"]).query)
        for clave, valor in {
            "pagina_recursos": "2",
            "modo_recursos": "software",
            "fragment": "1",
            "modal": "1",
            "semana": "2026-10-11",
            "estado_recursos": "todos",
        }.items():
            self.assertEqual(query[clave], [valor])
        self.assertContains(respuesta, "data-resources-query=")

    def test_lector_abre_edicion_fuera_de_pagina_y_recupera_equipo_inactivo(self):
        objetivo = self.fisicos[-1]
        respuesta = self.abrir("activos", editar_equipo=objetivo.pk)
        self.assertEqual(respuesta.context["recursos_pagina"].number, 3)
        self.assertIn(objetivo.pk, [obj.pk for obj in respuesta.context["equipos"]])
        objetivo.activa = False
        objetivo.save(update_fields=["activa"])
        respuesta = self.abrir("activos", editar_equipo=objetivo.pk)
        self.assertEqual(respuesta.context["recursos_estado"], "todos")
        self.assertIn(objetivo.pk, [obj.pk for obj in respuesta.context["equipos"]])
        parametros = parse_qs(respuesta.context["recursos_query"])
        self.assertEqual(parametros["pagina_recursos"], ["3"])
        self.assertEqual(parametros["estado_recursos"], ["todos"])
        self.assertNotIn("editar_equipo", parametros)
        respuesta = self.abrir("activos", editar_equipo=self.ajeno.pk)
        self.assertNotIn(
            self.ajeno.pk, [obj.pk for obj in respuesta.context["equipos"]]
        )

    def test_frontera_cincuenta_espacios_y_doce_tarjetas(self):
        EspacioReservable.objects.bulk_create(
            [
                EspacioReservable(
                    unidad=self.unidad,
                    nombre=f"Frontera espacio {i:03}",
                    codigo=f"FRON-{i:03}",
                    capacidad=4,
                )
                for i in range(50)
            ]
        )
        SoftwareDisponible.objects.bulk_create(
            [
                SoftwareDisponible(
                    unidad=self.unidad,
                    nombre=f"Frontera programa {i:03}",
                    licencias_totales=1,
                    licencias_disponibles=1,
                )
                for i in range(13)
            ]
        )
        espacios = self.abrir("espacios", busqueda_recursos="Frontera")
        programas = self.abrir("software", busqueda_recursos="Frontera")
        self.assertEqual(espacios.context["recursos_pagina"].paginator.num_pages, 1)
        self.assertEqual(programas.context["recursos_pagina"].paginator.num_pages, 2)
        self.assertEqual(
            len(
                self.abrir("software", 2, busqueda_recursos="Frontera").context[
                    "software_gestion"
                ]
            ),
            1,
        )
        self.assertFalse(espacios.context["recursos_siguiente"])
        self.assertTrue(programas.context["recursos_siguiente"])

    def test_cambio_de_estado_localiza_tarjeta_fuera_de_pagina_sin_abrir_editor(self):
        for modelo, modo, clave in ((SoftwareDisponible, 'software', 'software_gestion'),
                                   (Consumible, 'insumos', 'consumibles')):
            with self.subTest(modo=modo):
                recurso = modelo.objects.filter(unidad=self.unidad, nombre__contains='catálogo').order_by('nombre').last()
                recurso.activo = False
                recurso.save(update_fields=['activo'])
                respuesta = self.abrir(modo, 1, busqueda_recursos='catálogo', enfocar_recurso=recurso.pk)
                self.assertEqual(respuesta.status_code, 200)
                self.assertEqual(respuesta.context['recursos_pagina'].number, 9)
                self.assertIn(recurso.pk, [r.pk for r in respuesta.context[clave]])
                self.assertEqual(respuesta.context['recursos_estado'], 'todos')
                self.assertNotIn('enfocar_recurso', respuesta.context['recursos_query'])

    def test_crecer_catalogo_no_amplia_html_ni_consultas_de_primera_pagina(self):
        consultas = []

        def registrar(execute, sql, params, many, context):
            consultas.append(sql)
            return execute(sql, params, many, context)

        self.abrir("software")
        with connection.execute_wrapper(registrar):
            antes = self.abrir("software")
        total_antes = len(consultas)
        SoftwareDisponible.objects.bulk_create(
            [
                SoftwareDisponible(
                    unidad=self.unidad,
                    nombre=f"ZZ Programa adicional {i:03}",
                    licencias_totales=1,
                    licencias_disponibles=1,
                )
                for i in range(300)
            ]
        )
        consultas.clear()
        with connection.execute_wrapper(registrar):
            despues = self.abrir("software")
        self.assertGreater(total_antes, 0)
        self.assertEqual(len(consultas), total_antes)
        self.assertTrue(any("LIMIT" in sql for sql in consultas))
        self.assertLess(len(despues.content), len(antes.content) + 2000)
        self.assertEqual(len(despues.context["software_gestion"]), 12)
        self.assertEqual(despues.context["recursos_pagina"].paginator.count, 402)

    def test_disponibilidad_global_no_se_reduce_a_la_pagina(self):
        respuesta = self.abrir("activos", 3)
        valores = respuesta.context["analitica_activos"]["disponibilidad"]
        self.assertEqual([v["total"] for v in valores], [102, 102, 204])
        self.assertEqual([v["disponible"] for v in valores], [102, 102, 102])

    def test_selector_paginado_recupera_seleccion_fuera_de_pagina_y_nunca_ajena(self):
        primera = self.client.get(self.buscar_url, {"tipo": "modelos", "q": "catálogo"})
        ultima = self.client.get(
            self.buscar_url, {"tipo": "modelos", "q": "catálogo", "pagina": 3}
        )
        self.assertEqual(len(primera.json()["items"]), 50)
        self.assertEqual(len(ultima.json()["items"]), 2)
        self.assertEqual(primera.json()["total"], 102)
        seleccion = self.client.get(
            self.buscar_url,
            {"tipo": "equipos", "ids": f"{self.fisicos[-1].pk},{self.ajeno.pk}"},
        )
        self.assertEqual(
            [i["id"] for i in seleccion.json()["items"]], [self.fisicos[-1].pk]
        )
        self.assertIn("no-store", seleccion.headers["Cache-Control"])
        for valor in ("0", "x", "9" * 5000, ",".join(["1"] * 51)):
            self.assertEqual(
                self.client.get(
                    self.buscar_url, {"tipo": "equipos", "ids": valor}
                ).status_code,
                400,
            )
        self.assertEqual(
            self.client.get(
                self.buscar_url, {"tipo": "no-existe", "q": "hola"}
            ).status_code,
            400,
        )
        self.assertEqual(
            self.client.get(
                self.buscar_url, {"tipo": "modelos", "q": "\0"}
            ).status_code,
            400,
        )
        self.assertEqual(
            self.abrir("espacios", busqueda_recursos="\0").status_code, 400
        )

    def test_selector_software_cincuenta_etiquetas_sin_consultas_por_codigo(self):
        from django.test import RequestFactory
        from apps.gestion_unidades.presentation.catalogos_gestion import resultados_selector

        programas = SoftwareDisponible.objects.bulk_create(
            [
                SoftwareDisponible(
                    unidad=self.unidad,
                    nombre=f"N1 Programa {indice:03}",
                    codigo=f"COD-{indice:03}" if indice % 2 else "",
                    version=f"Versión {indice:03}",
                    licencias_totales=1,
                    licencias_disponibles=1,
                )
                for indice in range(50)
            ]
        )
        esperados = {
            programa.pk: f"{programa.nombre} · {programa.codigo or programa.version}"
            for programa in programas
        }
        parametros = (
            {"tipo": "software", "q": "N1 Programa"},
            {"tipo": "software", "ids": ",".join(str(p.pk) for p in programas)},
        )
        for valores in parametros:
            with self.subTest(modo="seleccion" if "ids" in valores else "busqueda"):
                solicitud = RequestFactory().get(self.buscar_url, valores)
                solicitud.user = self.coordinador
                sentencias = []

                def registrar(execute, sql, params, many, context):
                    sentencias.append(sql)
                    return execute(sql, params, many, context)

                with connection.execute_wrapper(registrar):
                    resultado = resultados_selector(solicitud, self.unidad)
                self.assertEqual(len(resultado["items"]), 50)
                self.assertEqual(resultado["total"], 50)
                self.assertEqual(
                    {item["id"]: item["text"] for item in resultado["items"]}, esperados
                )
                # COUNT del paginador y SELECT de sus 50 filas; nunca refresh_from_db.
                self.assertEqual(len(sentencias), 2, len(sentencias))

    def test_codigo_software_se_busca_en_selector_y_tabla(self):
        propio = SoftwareDisponible.objects.create(
            unidad=self.unidad,
            nombre="Programa identificable",
            codigo="SW-LOCAL-EXACTO",
            version="2026",
            licencias_totales=1,
            licencias_disponibles=1,
        )
        SoftwareDisponible.objects.create(
            unidad=self.otra_unidad,
            nombre="Programa ajeno",
            codigo="SW-AJENO-EXACTO",
            licencias_totales=1,
            licencias_disponibles=1,
        )
        respuesta = self.client.get(
            self.buscar_url, {"tipo": "software", "q": "SW-LOCAL-EXACTO"}
        )
        self.assertEqual(
            [fila["id"] for fila in respuesta.json()["items"]], [propio.pk]
        )
        self.assertEqual(
            respuesta.json()["items"][0]["text"],
            "Programa identificable · SW-LOCAL-EXACTO",
        )
        tabla = self.abrir("software", busqueda_recursos="SW-LOCAL-EXACTO")
        self.assertEqual(
            [fila.pk for fila in tabla.context["software_gestion"]], [propio.pk]
        )
        ajeno = self.client.get(
            self.buscar_url, {"tipo": "software", "q": "SW-AJENO-EXACTO"}
        )
        self.assertEqual(ajeno.json()["items"], [])
        self.assertEqual(
            list(
                self.abrir("software", busqueda_recursos="SW-AJENO-EXACTO").context[
                    "software_gestion"
                ]
            ),
            [],
        )

    def test_selector_denegado_a_staff_ajeno_y_cuenta_inactiva(self):
        self.usuario_ajeno.is_staff = True
        self.usuario_ajeno.save(update_fields=["is_staff"])
        self.client.force_login(self.usuario_ajeno)
        self.assertEqual(
            self.client.get(
                self.buscar_url, {"tipo": "modelos", "q": "catálogo"}
            ).status_code,
            403,
        )
        self.coordinador.is_active = False
        self.coordinador.save(update_fields=["is_active"])
        self.client.force_login(self.coordinador)
        self.assertIn(
            self.client.get(
                self.buscar_url, {"tipo": "modelos", "q": "catálogo"}
            ).status_code,
            (302, 403),
        )

    def test_no_borra_relaciones_si_el_componente_remoto_no_cargo(self):
        espacio = EspacioReservable.objects.get(unidad=self.unidad, codigo="ESP-101")
        espacio.equipos_asociados.add(self.fisicos[-1])
        url = reverse("gestion_operacion_accion", args=[self.unidad.slug])
        datos = {
            "modulo": "recursos",
            "entidad": "espacio",
            "registro_id": espacio.pk,
            "nombre": espacio.nombre,
            "capacidad": "4",
            "activo": "on",
            "catalogos_remotos": "1",
        }
        respuesta = self.client.post(url, datos)
        self.assertEqual(respuesta.status_code, 400)
        self.assertEqual(
            list(espacio.equipos_asociados.values_list("pk", flat=True)),
            [self.fisicos[-1].pk],
        )
        respuesta = self.client.post(
            url,
            {
                **datos,
                "catalogos_seleccion_cargada": "1",
                "equipos_asociados": [self.fisicos[-1].pk],
            },
        )
        self.assertEqual(respuesta.status_code, 200, respuesta.content)
        self.assertEqual(
            list(espacio.equipos_asociados.values_list("pk", flat=True)),
            [self.fisicos[-1].pk],
        )

    def test_guardar_opciones_fuera_de_pagina_y_rechazar_ids_ajenos_o_invalidos(self):
        espacio = EspacioReservable.objects.get(unidad=self.unidad, codigo="ESP-101")
        url = reverse("gestion_operacion_accion", args=[self.unidad.slug])
        datos = {
            "modulo": "recursos",
            "entidad": "espacio",
            "registro_id": espacio.pk,
            "nombre": espacio.nombre,
            "capacidad": "4",
            "activo": "on",
            "equipos_asociados": [self.fisicos[-1].pk],
        }
        respuesta = self.client.post(url, datos)
        self.assertEqual(respuesta.status_code, 200, respuesta.content)
        self.assertEqual(
            list(espacio.equipos_asociados.values_list("pk", flat=True)),
            [self.fisicos[-1].pk],
        )
        for invalido in (self.ajeno.pk, "no-numero", "9" * 30):
            respuesta = self.client.post(
                url, {**datos, "equipos_asociados": [invalido]}
            )
            self.assertEqual(respuesta.status_code, 400, respuesta.content)
            self.assertEqual(
                list(espacio.equipos_asociados.values_list("pk", flat=True)),
                [self.fisicos[-1].pk],
            )
