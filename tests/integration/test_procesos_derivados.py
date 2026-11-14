"""Todas las familias con un proceso de referencia y cada producto con un proceso de partida.

Los procesos de referencia cuadran su balance y controlan al menos un peligro de
inocuidad (PCC). Los demás productos parten del proceso más cercano de su
familia, marcados «derivado, por validar»; una nueva carga no pisa lo que el
usuario haya editado y quitar un proceso libera su código.
"""
from decimal import Decimal

from django.core.management import call_command
from django.test import TestCase
from django.urls import reverse

from apps.plantas_piloto.operacion.presentation.derivacion_procesos import derivar_procesos
from apps.plantas_piloto.operacion.presentation.procesos import balance_de_masa, datos_de_receta
from apps.integraciones.management.commands.cargar_laboratorios_institucionales import LABORATORIOS
from apps.plantas_piloto.operacion.models.produccion import FamiliaProducto, Producto, Receta
from apps.gestion_unidades.models.fichas import FichaContenido
from apps.directorio_unidades.models.core import Unidad

PLANTAS = ('lacteos', 'carnicos', 'hortofruticola', 'almidones', 'panificacion')

# Nombres de catálogo que ya tienen su producto específico con proceso («Chorizo» es el
# «Chorizo parrillero») y lo que las plantas no pueden fabricar con sus equipos.
SIN_PROCESO_PROPIO = {
    'Chorizo', 'Jamón', 'Salchicha', 'Pulpa de mora', 'Néctares', 'Encurtidos', 'Aceites esenciales',
    'Almidón de papa', 'Almidón pregelatinizado', 'Pan artesanal', 'Pan de molde', 'Mazada', 'Suero en polvo',
}


class ProcesosDeLasPlantasTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        for planta in PLANTAS:
            call_command('cargar_laboratorios_institucionales', laboratorio=planta)
        cls.plantas = list(Unidad.objects.filter(dependencia='plantas_piloto', recetas__isnull=False).distinct())

    def test_cada_familia_tiene_un_proceso_de_referencia(self):
        self.assertEqual(len(self.plantas), 5)
        for familia in FamiliaProducto.objects.filter(unidad__in=self.plantas):
            with self.subTest(familia=familia.codigo):
                self.assertTrue(Receta.objects.filter(familia=familia, origen='referencia').exists())

    def test_los_procesos_de_referencia_cuadran_y_controlan_la_inocuidad(self):
        for receta in Receta.objects.filter(unidad__in=self.plantas, origen='referencia'):
            with self.subTest(receta=receta.codigo):
                self.assertTrue(receta.etapas.filter(punto_critico=True).exists())
                balance = balance_de_masa(datos_de_receta(receta))
                self.assertFalse([fila['orden'] for fila in balance['filas'] if fila['exceso']])
                if receta.producto.unidad_medida in ('kg', 'litro'):
                    por_balance = Decimal(balance['producto_por_balance'].replace(',', '.'))
                    diferencia = abs(por_balance - receta.rendimiento_esperado) / receta.rendimiento_esperado
                    self.assertLess(diferencia, Decimal('0.05'), f'{por_balance} frente a {receta.rendimiento_esperado}')

    def test_cada_producto_terminado_tiene_un_proceso_de_partida(self):
        sin_proceso = set(
            Producto.objects.filter(unidad__in=self.plantas, tipo='terminado', activo=True, publico=True)
            .exclude(recetas__isnull=False)
            .values_list('nombre', flat=True)
        )
        self.assertEqual(sin_proceso, SIN_PROCESO_PROPIO)
        self.assertGreaterEqual(Receta.objects.filter(unidad__in=self.plantas, origen='derivado').count(), 50)

    def test_el_derivado_copia_el_proceso_y_avisa_que_falta_validarlo(self):
        derivado = Receta.objects.get(producto__nombre='Queso maduro')
        base = Receta.objects.get(codigo='LAC-REC-SEMIMADURO-100')
        self.assertEqual(derivado.origen, 'derivado')
        self.assertEqual(derivado.derivado_de, base)
        self.assertEqual(derivado.familia, derivado.producto.familia)
        for relacion in ('etapas', 'insumos'):
            self.assertEqual(getattr(derivado, relacion).count(), getattr(base, relacion).count())
        self.assertEqual(
            list(derivado.etapas.filter(punto_critico=True).values_list('orden', flat=True)),
            list(base.etapas.filter(punto_critico=True).values_list('orden', flat=True)),
        )
        self.assertIn('por validar', derivado.nombre_publico)
        ficha = self.client.get(reverse('ficha_proceso_publica', args=[derivado.unidad.slug, derivado.pk]))
        self.assertContains(ficha, 'derivado, por validar')
        self.assertContains(ficha, 'Proceso derivado de')

    def test_una_nueva_carga_no_pisa_el_derivado_editado(self):
        derivado = Receta.objects.get(producto__nombre='Arequipe')
        etapa = derivado.etapas.order_by('orden').first()
        etapa.duracion_min = 99
        etapa.save(update_fields=['duracion_min'])
        antes = Receta.objects.filter(unidad=derivado.unidad).count()
        lacteos = LABORATORIOS['lacteos']
        self.assertEqual(derivar_procesos(derivado.unidad, lacteos['plantillas_derivadas'], lacteos['sin_derivar']), [])
        call_command('cargar_laboratorios_institucionales', laboratorio='lacteos')
        etapa.refresh_from_db()
        self.assertEqual(etapa.duracion_min, 99)
        self.assertEqual(Receta.objects.filter(unidad=derivado.unidad).count(), antes)

    def test_quitar_un_proceso_archiva_su_ficha_y_libera_el_codigo(self):
        derivado = Receta.objects.get(producto__nombre='Paletas')
        codigo, unidad = derivado.codigo, derivado.unidad
        ficha = FichaContenido.objects.get(codigo=codigo)
        derivado.delete()
        ficha.refresh_from_db()
        self.assertEqual(ficha.estado, 'archivada')
        self.assertIn('-RETIRADA-', ficha.codigo)
        # Vuelve a derivarse con el mismo código, sin chocar con la ficha anterior.
        call_command('cargar_laboratorios_institucionales', laboratorio='lacteos')
        self.assertTrue(Receta.objects.filter(codigo=codigo, unidad=unidad, origen='derivado').exists())
