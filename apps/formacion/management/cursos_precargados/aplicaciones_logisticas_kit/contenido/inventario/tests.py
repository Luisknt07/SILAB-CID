"""Pruebas de reglas logísticas, permisos, CSV y consultas MCP sin necesitar IA."""

from decimal import Decimal
from io import StringIO
from pathlib import Path
import sqlite3
import tempfile
import uuid
from unittest.mock import patch
from django.contrib.auth import get_user_model
from django.core.exceptions import PermissionDenied, ValidationError
from django.core.management import call_command
from django.db import IntegrityError
from django.test import Client, SimpleTestCase, TestCase
from inventario.management.commands.preparar_demo import preparar_grupos
from inventario.models import Movimiento, Producto
from inventario.services import importar_productos, registrar_movimiento
from mcp_consultas import leer_existencias


class InventarioTests(TestCase):
    def setUp(self):
        consulta, operacion = preparar_grupos()
        self.operador = get_user_model().objects.create_user(
            username="operador", password="Prueba-larga-2026"
        )
        self.operador.groups.add(operacion)
        self.lector = get_user_model().objects.create_user(
            username="lector", password="Otra-prueba-larga-2026"
        )
        self.lector.groups.add(consulta)
        self.producto = Producto.objects.create(
            codigo="PR-01",
            nombre="Producto ficticio",
            unidad="KG",
            minimo=Decimal("5.00"),
        )

    def mover(self, cantidad, tipo="E", usuario=None, **kwargs):
        return registrar_movimiento(
            usuario=usuario or self.operador,
            producto_id=self.producto.pk,
            tipo=tipo,
            cantidad=cantidad,
            motivo="Práctica",
            **kwargs,
        )

    def test_entradas_salidas_decimales_y_ledger_coherente(self):
        self.mover("12.50")
        self.mover("3.25", "S")
        self.producto.refresh_from_db()
        self.assertEqual(self.producto.existencia, Decimal("9.25"))
        self.assertEqual(Movimiento.objects.count(), 2)
        self.assertEqual(Movimiento.objects.first().usuario, self.operador)

    def test_no_salida_superior_ni_cantidad_invalida(self):
        self.mover("4.00")
        for valor in [
            "4.01",
            "0",
            "-1",
            "NaN",
            "Infinity",
            "1.234",
            "1,5",
            "10000000000",
        ]:
            with self.subTest(valor=valor), self.assertRaises(ValidationError):
                self.mover(valor, "S")
        self.producto.refresh_from_db()
        self.assertEqual(self.producto.existencia, Decimal("4.00"))
        self.assertEqual(Movimiento.objects.count(), 1)

    def test_stock_se_revierte_si_falla_historial(self):
        self.mover("10.00")
        with patch.object(
            Movimiento, "save", side_effect=IntegrityError("fallo simulado")
        ):
            with self.assertRaises(IntegrityError):
                self.mover("2.00", "S")
        self.producto.refresh_from_db()
        self.assertEqual(self.producto.existencia, Decimal("10.00"))
        self.assertEqual(Movimiento.objects.count(), 1)

    def test_doble_envio_no_duplica_y_reuso_distinto_falla(self):
        clave = uuid.uuid4()
        primero = self.mover("10.00", clave=clave)
        segundo = self.mover("10.00", clave=clave)
        self.assertEqual(primero.pk, segundo.pk)
        with self.assertRaises(ValidationError):
            self.mover("11.00", clave=clave)
        self.producto.refresh_from_db()
        self.assertEqual(self.producto.existencia, Decimal("10.00"))
        self.assertEqual(Movimiento.objects.count(), 1)

    def test_servicio_rechaza_usuario_lector_y_tipo_invalido(self):
        with self.assertRaises(PermissionDenied):
            self.mover("1.00", usuario=self.lector)
        with self.assertRaises(ValidationError):
            self.mover("1.00", tipo="X")
        self.assertEqual(Movimiento.objects.count(), 0)

    def test_modelo_rechaza_texto_con_html(self):
        producto = Producto(
            codigo="PR-02", nombre="<script>alert(1)</script>", unidad="UN", minimo=0
        )
        with self.assertRaises(ValidationError):
            producto.full_clean()
        with self.assertRaises(ValidationError):
            registrar_movimiento(
                usuario=self.operador,
                producto_id=self.producto.pk,
                tipo="E",
                cantidad="1.00",
                motivo="<img src=x>",
            )
        self.assertEqual(Movimiento.objects.count(), 0)

    def test_csv_valido_crea_catalogo_con_stock_cero(self):
        datos = (
            Path(__file__).resolve().parents[1] / "datos/productos_validos.csv"
        ).read_bytes()
        self.assertEqual(importar_productos(usuario=self.operador, contenido=datos), 4)
        self.assertTrue(
            all(
                p.existencia == 0 for p in Producto.objects.exclude(pk=self.producto.pk)
            )
        )
        self.assertFalse(Movimiento.objects.exists())

    def test_csv_invalido_no_deja_filas_parciales(self):
        datos = (
            Path(__file__).resolve().parents[1] / "datos/productos_invalidos.csv"
        ).read_bytes()
        with self.assertRaises(ValidationError) as error:
            importar_productos(usuario=self.operador, contenido=datos)
        self.assertIn("Fila", " ".join(error.exception.messages))
        self.assertEqual(Producto.objects.count(), 1)

    def test_csv_duplicado_existente_no_actualiza_ni_importa_parcial(self):
        datos = b"codigo,nombre,unidad,minimo\nPR-02,Valido,UN,0\nPR-01,Cambio,UN,2\n"
        with self.assertRaises(ValidationError):
            importar_productos(usuario=self.operador, contenido=datos)
        self.producto.refresh_from_db()
        self.assertEqual(self.producto.nombre, "Producto ficticio")
        self.assertEqual(Producto.objects.count(), 1)

    def test_csv_limites_codificacion_y_cabecera(self):
        for datos in [
            b"codigo;nombre;unidad;minimo\n",
            b"\xff\xfe",
            b"x" * 1_048_577,
            b"codigo,nombre,unidad,minimo\n",
            b"codigo,nombre,unidad,minimo\nPR-02,Mal,UN\n",
        ]:
            with self.subTest(size=len(datos)), self.assertRaises(ValidationError):
                importar_productos(usuario=self.operador, contenido=datos)
        self.assertEqual(Producto.objects.count(), 1)

    def test_web_autenticacion_permisos_y_exportacion_segura(self):
        self.assertEqual(self.client.get("/").status_code, 302)
        self.client.force_login(self.lector)
        self.assertEqual(self.client.get("/").status_code, 200)
        for ruta in ["/productos/nuevo/", "/movimientos/nuevo/", "/importar/"]:
            self.assertEqual(self.client.get(ruta).status_code, 403)
        self.assertEqual(
            self.client.post(
                "/movimientos/nuevo/",
                {
                    "producto": self.producto.pk,
                    "tipo": "E",
                    "cantidad": "9",
                    "motivo": "Sin permiso",
                    "clave": uuid.uuid4(),
                },
            ).status_code,
            403,
        )
        self.assertFalse(Movimiento.objects.exists())
        self.producto.nombre = "=1+1"
        self.producto.save(update_fields=["nombre"])
        contenido = self.client.get("/exportar/").content.decode("utf-8-sig")
        self.assertIn("'=1+1", contenido)
        self.assertIn("existencia", contenido)

    def test_web_operacion_y_validacion_backend(self):
        self.client.force_login(self.operador)
        self.mover("2.00")
        datos = {
            "producto": self.producto.pk,
            "tipo": "S",
            "cantidad": "3.00",
            "motivo": "Prueba",
            "clave": uuid.uuid4(),
        }
        respuesta = self.client.post("/movimientos/nuevo/", datos)
        self.assertContains(respuesta, "Stock insuficiente")
        self.producto.refresh_from_db()
        self.assertEqual(self.producto.existencia, Decimal("2.00"))
        datos["cantidad"] = "1.00"
        self.assertEqual(
            self.client.post("/movimientos/nuevo/", datos).status_code, 302
        )
        self.assertContains(self.client.get("/movimientos/"), "Prueba")

    def test_csrf_requerido_para_escritura(self):
        cliente = Client(enforce_csrf_checks=True)
        cliente.force_login(self.operador)
        self.assertEqual(
            cliente.post(
                "/productos/nuevo/",
                {"codigo": "PR-03", "nombre": "Otro", "unidad": "UN", "minimo": "0"},
            ).status_code,
            403,
        )
        self.assertFalse(Producto.objects.filter(codigo="PR-03").exists())

    def test_demo_idempotente_saldos_y_minimos(self):
        call_command("preparar_demo", stdout=StringIO())
        conteo = Movimiento.objects.count()
        call_command("preparar_demo", stdout=StringIO())
        self.assertEqual(Movimiento.objects.count(), conteo)
        esperados = {
            "AD-001": "17.00",
            "AD-002": "20.00",
            "AD-003": "9.25",
            "AD-004": "4.00",
        }
        for codigo, cantidad in esperados.items():
            self.assertEqual(
                Producto.objects.get(codigo=codigo).existencia, Decimal(cantidad)
            )
        self.assertTrue(Producto.objects.get(codigo="AD-002").bajo_minimo)
        self.assertFalse(Producto.objects.get(codigo="AD-003").bajo_minimo)


class ConsultasMCPTests(SimpleTestCase):
    def test_lectura_acotada_no_modifica_base_y_rechaza_codigo_inyectado(self):
        with tempfile.TemporaryDirectory() as carpeta:
            ruta = Path(carpeta) / "docente.sqlite3"
            con = sqlite3.connect(ruta)
            con.execute(
                "CREATE TABLE inventario_producto (codigo TEXT,nombre TEXT,unidad TEXT,existencia DECIMAL,minimo DECIMAL)"
            )
            con.executemany(
                "INSERT INTO inventario_producto VALUES (?,?,?,?,?)",
                [
                    ("AD-001", "Caja", "UN", 17, 10),
                    ("AD-002", "Etiqueta", "UN", 20, 30),
                ],
            )
            con.commit()
            con.close()
            original = ruta.read_bytes()
            self.assertEqual(len(leer_existencias(ruta=ruta)["productos"]), 2)
            bajos = leer_existencias(ruta=ruta, solo_bajos=True)["productos"]
            self.assertEqual([p["codigo"] for p in bajos], ["AD-002"])
            self.assertEqual(
                leer_existencias(ruta=ruta, codigo="AD-001")["productos"][0][
                    "existencia"
                ],
                "17.00",
            )
            with self.assertRaises(ValueError):
                leer_existencias(ruta=ruta, codigo="' OR 1=1 --")
            self.assertEqual(original, ruta.read_bytes())
