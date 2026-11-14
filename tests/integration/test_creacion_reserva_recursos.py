import json
from datetime import date, datetime, time
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.http import QueryDict
from django.test import TestCase
from django.utils.datastructures import MultiValueDict

from apps.reservas.presentation.creacion_recursos import normalizar_ids_post, resolver_catalogos_solicitud, resolver_recursos_fisicos
from apps.reservas.presentation.creacion_servicio import preparar_solicitud
from apps.gestion_unidades.models.operaciones import ConfiguracionOperativaUnidad
from apps.recursos.models.consumibles import Consumible
from apps.recursos.models.equipos import EquiposServicios
from apps.laboratorios.operacion.models.fablab import FablabService
from apps.directorio_unidades.models.core import Unidad
from apps.recursos.models.unidades import UnidadEquipo


def post_recursos(**cambios):
    post = QueryDict("", mutable=True)
    post.update(
        {
            "unidades_seleccionadas": "[]",
            "consumibles_seleccionados": "[]",
            "alcance_espacio": "",
        }
    )
    for nombre, valor in cambios.items():
        if isinstance(valor, list):
            post.setlist(nombre, valor)
        else:
            post[nombre] = valor
    return post


class CreacionReservaRecursosTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.usuario = get_user_model().objects.create_user(
            username="seleccion.directa",
            email="seleccion.directa@upec.edu.ec",
            password="prueba-segura",
        )
        cls.unidad = Unidad.objects.create(
            nombre="Laboratorio para selección",
            descripcion="Prueba directa de recursos.",
            fecha_inicio=date(2026, 1, 1),
            dependencia="laboratorios",
            slug="laboratorio-seleccion-directa",
        )
        cls.unidad_ajena = Unidad.objects.create(
            nombre="Laboratorio ajeno",
            descripcion="Control de aislamiento.",
            fecha_inicio=date(2026, 1, 1),
            dependencia="laboratorios",
            slug="laboratorio-seleccion-ajena",
        )
        cls.configuracion = ConfiguracionOperativaUnidad.objects.get(unidad=cls.unidad)
        cls.equipo = EquiposServicios.objects.create(
            codigo="EQ-DIRECTO-01",
            nombre="Equipo directo",
        )
        cls.recurso = UnidadEquipo.objects.create(
            codigo_unidad="REC-DIRECTO-01",
            equipo=cls.equipo,
            laboratorio=cls.unidad,
            estado_unidad="disponible",
            activa=True,
        )
        cls.recurso_ajeno = UnidadEquipo.objects.create(
            codigo_unidad="REC-AJENO-01",
            equipo=cls.equipo,
            laboratorio=cls.unidad_ajena,
            estado_unidad="disponible",
            activa=True,
        )
        cls.consumible = Consumible.objects.create(
            unidad=cls.unidad,
            codigo="CON-DIRECTO-01",
            nombre="Consumible directo",
            unidad_medida="kg",
            stock_total=Decimal("5"),
        )
        cls.servicio = FablabService.objects.create(
            code="SER-DIRECTO-01",
            nombre="Servicio directo",
            unidad=cls.unidad,
            activo=True,
            publico=True,
        )
        cls.servicio_ajeno = FablabService.objects.create(
            code="SER-AJENO-01",
            nombre="Servicio ajeno",
            unidad=cls.unidad_ajena,
            activo=True,
            publico=True,
        )

    def test_resuelve_equipo_solo_dentro_de_la_unidad(self):
        post = post_recursos(
            unidades_seleccionadas=json.dumps([{"id": self.recurso.pk}]),
        )

        seleccion = resolver_recursos_fisicos(
            post,
            unidad=self.unidad,
            configuracion=self.configuracion,
            tipo_solicitud="recursos",
            modalidad_servicio="",
            proposito_codigo="investigacion_innovacion",
            incluye_espacio_solicitado=False,
            requisitos_especiales="",
        )

        self.assertEqual([item["id"] for item in seleccion.recursos], [self.recurso.pk])
        self.assertEqual(seleccion.equipos, [self.equipo])
        self.assertTrue(seleccion.requiere_espacio)
        self.assertEqual(seleccion.alcance_espacio, "espacio_unico")
        self.assertTrue(seleccion.solicito_equipo)

    def test_rechaza_equipo_de_otra_unidad(self):
        post = post_recursos(
            unidades_seleccionadas=json.dumps([{"id": self.recurso_ajeno.pk}]),
        )

        with self.assertRaisesMessage(ValueError, "ya no están disponibles"):
            resolver_recursos_fisicos(
                post,
                unidad=self.unidad,
                configuracion=self.configuracion,
                tipo_solicitud="recursos",
                modalidad_servicio="",
                proposito_codigo="investigacion_innovacion",
                incluye_espacio_solicitado=False,
                requisitos_especiales="",
            )

    def test_resuelve_consumible_y_servicio_sin_peticion_http(self):
        post = post_recursos(
            consumibles_seleccionados=json.dumps(
                [{"id": self.consumible.pk, "cantidad": "1.5"}]
            ),
            servicios_solicitados=[str(self.servicio.pk)],
        )

        seleccion = resolver_catalogos_solicitud(
            post,
            MultiValueDict(),
            unidad=self.unidad,
            tipo_solicitud="servicio",
            modalidad_servicio="diseno_completo",
            equipos=[],
            receta_proceso=None,
            espacios=[],
        )

        self.assertEqual(seleccion.consumibles[0][0], self.consumible)
        self.assertEqual(seleccion.consumibles[0][1], Decimal("1.5"))
        self.assertEqual(seleccion.servicios, [self.servicio])

    def test_rechaza_servicio_de_otra_unidad(self):
        post = post_recursos(servicios_solicitados=[str(self.servicio_ajeno.pk)])

        with self.assertRaisesMessage(ValueError, "no pertenece a esta unidad"):
            resolver_catalogos_solicitud(
                post,
                MultiValueDict(),
                unidad=self.unidad,
                tipo_solicitud="servicio",
                modalidad_servicio="diseno_completo",
                equipos=[],
                receta_proceso=None,
                espacios=[],
            )

    def test_rechaza_ids_repetidos_en_campos_multivalor(self):
        post = post_recursos(espacios_solicitados=["8", "8"])

        with self.assertRaisesMessage(ValueError, "dos veces"):
            normalizar_ids_post(post, "espacios_solicitados")

    def test_prepara_reserva_de_recursos_sin_escribir_expediente(self):
        post = post_recursos(
            unidades_seleccionadas=json.dumps([{"id": self.recurso.pk}]),
        )
        recursos = resolver_recursos_fisicos(
            post,
            unidad=self.unidad,
            configuracion=self.configuracion,
            tipo_solicitud="recursos",
            modalidad_servicio="",
            proposito_codigo="investigacion_innovacion",
            incluye_espacio_solicitado=False,
            requisitos_especiales="",
        )

        preparacion = preparar_solicitud(
            post,
            usuario=self.usuario,
            unidad=self.unidad,
            configuracion=self.configuracion,
            tipo_solicitud="recursos",
            modalidad_servicio="",
            metodo_pago="",
            cotizacion_aceptada=False,
            provision_consumibles="ninguno",
            incluye_espacio_solicitado=False,
            requiere_espacio=recursos.requiere_espacio,
            recursos=recursos.recursos,
            equipos=recursos.equipos,
            software=recursos.software,
            espacios=recursos.espacios,
            servicios=[],
            consumibles=[],
            fecha_inicio=datetime(2026, 10, 20, 9),
            hora_fin=time(11),
            duracion=2,
            sesiones_programa=1,
            receta_proceso=None,
            factor_proceso=None,
        )

        self.assertTrue(preparacion.incluye_espacio)
        self.assertIsNone(preparacion.trabajo_servicio)
        self.assertEqual(preparacion.modalidad_servicio, "")
        self.assertIn("total", preparacion.cotizacion)

    def test_rechaza_recursos_en_servicio_sin_diseno_asistido(self):
        post = post_recursos()

        with self.assertRaisesMessage(ValueError, "recursos complementarios"):
            preparar_solicitud(
                post,
                usuario=self.usuario,
                unidad=self.unidad,
                configuracion=self.configuracion,
                tipo_solicitud="servicio",
                modalidad_servicio="diseno_completo",
                metodo_pago="",
                cotizacion_aceptada=False,
                provision_consumibles="ninguno",
                incluye_espacio_solicitado=True,
                requiere_espacio=False,
                recursos=[],
                equipos=[],
                software=[],
                espacios=[],
                servicios=[self.servicio],
                consumibles=[],
                fecha_inicio=datetime(2026, 10, 20, 9),
                hora_fin=time(11),
                duracion=2,
                sesiones_programa=1,
                receta_proceso=None,
                factor_proceso=None,
            )
