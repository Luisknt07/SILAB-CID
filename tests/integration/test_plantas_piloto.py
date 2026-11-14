"""Las otras cuatro plantas piloto: la misma estructura, sus propios procesos.

Cárnicos, panificación, hortofrutícola y almidones se cargan con la misma
definición que la planta de lácteos: equipos, espacios, insumos con su plazo de
reposición, servicios, procesos con etapas y puntos críticos, planes de
calidad, requisitos de acceso, visitas, asignatura y cuentas. Lo que cambia son
los procesos, no el modelo: cada receta tiene que derivar su selección sin que
falte nada, y cada plan de calidad tiene que medir algo con un límite.
"""

from decimal import Decimal

from django.contrib.auth import get_user_model
from django.core.management import call_command
from django.test import TestCase
from django.urls import reverse

from apps.plantas_piloto.operacion.management.plantas.taxonomia import PRODUCTOS_TAXONOMIA, TAXONOMIA_FAMILIAS
from apps.plantas_piloto.operacion.presentation.secciones_plantas import PESTANAS_PLANTA, SECCIONES_PLANTA

from apps.reservas.presentation.proceso import seleccion_por_proceso
from apps.recursos.models.unidades import AliasCodigoUnidadEquipo, UnidadEquipo
from apps.recursos.models.consumibles import Consumible
from apps.gestion_unidades.models.espacios import EspacioReservable, ResponsableUnidad
from apps.plantas_piloto.operacion.models.produccion import FamiliaProducto, Producto, Receta
from apps.laboratorios.operacion.models.fablab import FablabService
from apps.gestion_unidades.models.fichas import FichaContenido
from apps.plantas_piloto.operacion.models.calidad import ParametroCalidad, PlanCalidad
from apps.reservas.models.seguridad import RequisitoAcceso
from apps.directorio_unidades.models.core import Unidad

CLAVE_OPERATIVA = 'Planta-Piloto-2026'


class PlantaCargada:
    """Corre el cargador de una planta y deja sus objetos a mano.

    Es una mezcla y no un `TestCase`: sin la planta concreta no hay nada que
    cargar, y el corredor no debe intentar ejecutar la base por su cuenta.
    """

    planta = ''
    slug = ''
    nombre = ''
    prefijo = ''

    @classmethod
    def setUpTestData(cls):
        call_command(
            'cargar_laboratorios_institucionales',
            laboratorio=cls.planta,
            password=CLAVE_OPERATIVA,
        )
        cls.unidad = Unidad.objects.get(slug=cls.slug)
        cls.configuracion = cls.unidad.configuracion_operativa
        cls.recetas = list(Receta.objects.filter(unidad=cls.unidad).order_by('codigo'))

    def test_la_planta_queda_operativa_con_su_catalogo(self):
        self.assertEqual(self.unidad.nombre, self.nombre)
        self.assertEqual(self.unidad.dependencia, 'plantas_piloto')
        self.assertEqual(self.unidad.clasificacion_funcional, 'planta_piloto')
        self.assertTrue(self.configuracion.registra_produccion)
        self.assertEqual(self.configuracion.unidad_de_trabajo, 'lotes')
        self.assertTrue(self.configuracion.acepta_visitas)
        self.assertGreaterEqual(
            UnidadEquipo.objects.filter(laboratorio=self.unidad, activa=True).count(), 6,
        )
        self.assertGreaterEqual(EspacioReservable.objects.filter(unidad=self.unidad).count(), 4)
        self.assertGreaterEqual(Consumible.objects.filter(unidad=self.unidad).count(), 10)
        self.assertGreaterEqual(Producto.objects.filter(unidad=self.unidad).count(), 4)
        self.assertGreaterEqual(len(self.recetas), 3)
        self.assertGreaterEqual(ResponsableUnidad.objects.filter(unidad=self.unidad).count(), 2)
        # La planta tiene su línea de proceso y un área que un grupo puede recorrer.
        espacios = EspacioReservable.objects.filter(unidad=self.unidad)
        self.assertTrue(espacios.filter(tipo='linea').exists())
        self.assertTrue(espacios.filter(visitable=True).exists())
        # Todo lo suyo lleva su prefijo.
        for codigo in Consumible.objects.filter(unidad=self.unidad).values_list('codigo', flat=True):
            self.assertTrue(codigo.startswith(f'{self.prefijo}-'), codigo)

    def test_usa_la_taxonomia_maestra_y_codigos_canonicos(self):
        self.assertEqual(
            list(FamiliaProducto.objects.filter(unidad=self.unidad).values_list('nombre', flat=True)),
            list(TAXONOMIA_FAMILIAS[self.prefijo]),
        )
        self.assertFalse(Producto.objects.filter(unidad=self.unidad, familia__isnull=True).exists())
        self.assertFalse(Receta.objects.filter(unidad=self.unidad, familia__isnull=True).exists())
        esperados = {
            nombre
            for productos in PRODUCTOS_TAXONOMIA[self.prefijo].values()
            for nombre, _unidad_medida in productos
        }
        actuales = set(Producto.objects.filter(unidad=self.unidad).values_list('nombre', flat=True))
        self.assertTrue(esperados.issubset(actuales), esperados - actuales)
        self.assertFalse(
            PlanCalidad.objects.filter(unidad=self.unidad, producto__isnull=False, familia__isnull=True).exists()
        )
        equipos = UnidadEquipo.objects.filter(laboratorio=self.unidad, activa=True)
        self.assertTrue(all('-EQP-' in codigo for codigo in equipos.values_list('codigo_unidad', flat=True)))
        equipo = equipos.order_by('codigo_unidad').first()
        alias = AliasCodigoUnidadEquipo.objects.get(unidad_equipo=equipo)
        self.assertIn('-UNIT-', alias.codigo)
        actual = self.client.get(reverse('ficha_equipo_publica', args=[self.unidad.slug, equipo.codigo_unidad]))
        self.assertEqual(actual.status_code, 200)
        self.assertContains(actual, equipo.codigo_unidad)
        anterior = self.client.get(reverse('ficha_equipo_publica', args=[self.unidad.slug, alias.codigo]))
        self.assertEqual(anterior.status_code, 301)
        self.assertIn(equipo.codigo_unidad, anterior['Location'])
        # Cada área tiene su página; ahí cada equipo muestra su código y lleva a su ficha.
        area = EspacioReservable.objects.filter(unidad=self.unidad, activo=True, equipos_asociados=equipo).first()
        pagina_area = self.client.get(reverse('area_unidad', args=[self.unidad.slug, area.codigo]))
        self.assertContains(pagina_area, equipo.codigo_unidad)
        self.assertContains(pagina_area, reverse('ficha_equipo_publica', args=[self.unidad.slug, equipo.codigo_unidad]))

    def test_las_fichas_y_calidad_comparten_la_familia(self):
        familias_con_proceso = FamiliaProducto.objects.filter(unidad=self.unidad, recetas__isnull=False).distinct()
        familia = familias_con_proceso.order_by('orden').first()
        respuesta = self.client.get(
            reverse('calidad_publica', args=[self.unidad.slug]) + f'?familia={familia.codigo}'
        )
        self.assertEqual(respuesta.status_code, 200)
        self.assertEqual(respuesta.context['familia_activa'], familia)
        self.assertTrue(all(
            item['receta'].familia_id == familia.pk for item in respuesta.context['calidad']['protocolos']
        ))
        planes_publicados = [item['plan'] for item in respuesta.context['calidad']['publicada']['planes']]
        self.assertTrue(any(plan.familia_id is None for plan in planes_publicados))
        self.assertTrue(all(plan.familia_id in (None, familia.pk) for plan in planes_publicados))
        transversales = self.client.get(
            reverse('calidad_publica', args=[self.unidad.slug]) + '?transversales=1'
        )
        self.assertEqual(transversales.status_code, 200)
        self.assertTrue(transversales.context['solo_transversales'])
        self.assertTrue(all(
            item['plan'].familia_id is None
            for item in transversales.context['calidad']['publicada']['planes']
        ))
        fichas = FichaContenido.objects.filter(unidad=self.unidad)
        fichas_equipo = fichas.filter(tipo='equipo')
        self.assertTrue(fichas_equipo.filter(estado='en_revision', visibilidad='publica').exists())
        self.assertFalse(fichas_equipo.filter(estado='publicada').exists())
        self.assertTrue(all(ficha.completitud < 100 for ficha in fichas_equipo))
        self.assertTrue(fichas.filter(tipo='producto', familia__isnull=False).exists())
        self.assertTrue(fichas.filter(tipo='proceso', familia__isnull=False).exists())
        self.assertTrue(fichas.filter(tipo='pcc', familia__isnull=False).exists())
        self.assertTrue(fichas.filter(tipo='especificacion', familia__isnull=False).exists())
        self.assertTrue(fichas.filter(tipo='simulador').exists())
        self.assertTrue(all(0 <= ficha.completitud <= 100 for ficha in fichas))

    def test_el_mapa_canonico_conserva_las_seis_pestanas_y_las_34_secciones(self):
        self.assertEqual(len(PESTANAS_PLANTA), 6)
        self.assertEqual(len(SECCIONES_PLANTA), 34)
        self.assertEqual(list(SECCIONES_PLANTA), [
            *(f'1.{numero}' for numero in range(1, 7)),
            *(f'2.{numero}' for numero in range(1, 7)),
            *(f'3.{numero}' for numero in range(1, 5)),
            *(f'4.{numero}' for numero in range(1, 7)),
            *(f'5.{numero}' for numero in range(1, 6)),
            *(f'6.{numero}' for numero in range(1, 8)),
        ])
        self.assertEqual(SECCIONES_PLANTA['2.6']['titulo'], 'Guías de práctica')
        self.assertEqual(SECCIONES_PLANTA['5.1']['titulo'], 'Protocolos de control')

    def test_sus_cuentas_operativas_existen_con_produccion(self):
        Usuario = get_user_model()
        coordinacion = Usuario.objects.get(username=f'coordinacion.{self.planta}')
        laboratorista = Usuario.objects.get(username=f'laboratorista.{self.planta}')
        for persona in (coordinacion, laboratorista):
            vinculo = ResponsableUnidad.objects.get(unidad=self.unidad, usuario=persona)
            self.assertTrue(vinculo.activo)
        vinculo = ResponsableUnidad.objects.get(unidad=self.unidad, usuario=coordinacion)
        self.assertTrue(vinculo.permisos_operativos.get('produccion'))
        self.assertTrue(vinculo.permisos_operativos.get('reservas'))
        self.assertTrue(vinculo.permisos_operativos.get('inventario'))

    def test_cada_proceso_deriva_su_seleccion_sin_que_falte_nada(self):
        for receta in self.recetas:
            with self.subTest(receta=receta.codigo):
                seleccion = seleccion_por_proceso(receta, Decimal('1'))
                self.assertEqual(seleccion['faltantes'], [], seleccion['faltantes'])
                self.assertTrue(seleccion['espacios'], 'el proceso no ocupa ningún área')
                self.assertTrue(seleccion['equipos'], 'el proceso no usa ningún equipo')
                self.assertTrue(seleccion['insumos'], 'el proceso no consume ningún insumo')
                self.assertTrue(seleccion['sesion']['horas'], 'la corrida no ocupa ninguna hora')
                # Una corrida base rinde lo que la receta declara.
                self.assertGreater(Decimal(receta.rendimiento_esperado), 0)
                # Al menos un PCC de inocuidad, y además controles de calidad (PC).
                self.assertGreaterEqual(receta.etapas.filter(punto_critico=True).count(), 1)
                self.assertGreaterEqual(receta.etapas.filter(punto_control=True).count(), 1)
                # Las materias primas base (la carne y la grasa de un embutido) suman la corrida base.
                bases = [
                    insumo for insumo in receta.insumos.all() if insumo.forma_parte == 'base'
                ]
                self.assertTrue(bases, receta.codigo)
                self.assertEqual(sum(insumo.cantidad for insumo in bases), receta.cantidad_base, receta.codigo)

    def test_sus_planes_de_calidad_miden_con_limites_reales(self):
        planes = list(PlanCalidad.objects.filter(unidad=self.unidad))
        self.assertGreaterEqual(len(planes), 4)
        momentos = {plan.momento for plan in planes}
        self.assertIn('recepcion', momentos)
        self.assertIn('liberacion', momentos)
        parametros = ParametroCalidad.objects.filter(plan__unidad=self.unidad)
        self.assertGreaterEqual(parametros.count(), 12)
        for parametro in parametros:
            with self.subTest(parametro=parametro.nombre):
                self.assertNotEqual(parametro.limite_texto, 'sin límite')
        # Al menos un parámetro vigila una etapa crítica de un proceso.
        self.assertTrue(parametros.filter(etapa__isnull=False).exists())

    def test_ofrece_la_visita_guiada_y_exige_sus_requisitos(self):
        visita = FablabService.objects.filter(unidad=self.unidad, tipo_servicio='visita').first()
        self.assertIsNotNone(visita, 'la planta no publica su visita técnica')
        self.assertEqual(Decimal(visita.tarifa_base), Decimal('0'))
        requisitos = RequisitoAcceso.objects.filter(unidad=self.unidad, activo=True)
        self.assertGreaterEqual(requisitos.count(), 6)
        self.assertTrue(
            any('visitante' in (requisito.aplica_a or []) for requisito in requisitos),
            'ningún requisito aplica al visitante',
        )

    def test_la_ficha_publica_muestra_sus_procesos(self):
        pagina = self.client.get(self.unidad.get_absolute_url())
        self.assertEqual(pagina.status_code, 200)
        self.assertContains(pagina, self.nombre)
        self.assertContains(pagina, self.recetas[0].nombre_publico)
        self.assertContains(pagina, 'Sistemas de producción')
        self.assertEqual(
            pagina.content.decode().count('data-id="ficha-proceso-'),
            len(self.recetas),
        )
        catalogo = self.client.get(reverse('produccion_publica', args=[self.unidad.slug]))
        for familia, referencias in PRODUCTOS_TAXONOMIA[self.prefijo].items():
            self.assertContains(pagina, familia)
            self.assertContains(pagina, f'<optgroup label="{familia}">')
            for nombre, _unidad_medida in referencias:
                with self.subTest(producto=nombre):
                    producto = Producto.objects.get(unidad=self.unidad, nombre=nombre)
                    self.assertContains(pagina, f'data-producto="{nombre}"')
                    if not Receta.objects.filter(unidad=self.unidad, producto=producto).exists():
                        self.assertContains(pagina, f'data-id="ficha-producto-{producto.pk}"')
                    self.assertContains(catalogo, nombre)
                    self.assertContains(
                        catalogo,
                        reverse('ficha_producto_publica', args=[self.unidad.slug, producto.pk]),
                    )

    def test_la_carga_es_idempotente(self):
        antes = (
            Producto.objects.filter(unidad=self.unidad).count(),
            Receta.objects.filter(unidad=self.unidad).count(),
            Consumible.objects.filter(unidad=self.unidad).count(),
            PlanCalidad.objects.filter(unidad=self.unidad).count(),
            ParametroCalidad.objects.filter(plan__unidad=self.unidad).count(),
            UnidadEquipo.objects.filter(laboratorio=self.unidad).count(),
        )
        call_command('cargar_laboratorios_institucionales', laboratorio=self.planta)
        despues = (
            Producto.objects.filter(unidad=self.unidad).count(),
            Receta.objects.filter(unidad=self.unidad).count(),
            Consumible.objects.filter(unidad=self.unidad).count(),
            PlanCalidad.objects.filter(unidad=self.unidad).count(),
            ParametroCalidad.objects.filter(plan__unidad=self.unidad).count(),
            UnidadEquipo.objects.filter(laboratorio=self.unidad).count(),
        )
        self.assertEqual(antes, despues)


class PlantaDeCarnicosTests(PlantaCargada, TestCase):
    planta = 'carnicos'
    slug = 'planta-piloto-carnicos'
    nombre = 'Planta Piloto de Cárnicos'
    prefijo = 'CAR'


class PlantaDePanificacionTests(PlantaCargada, TestCase):
    planta = 'panificacion'
    slug = 'planta-piloto-cereales'
    nombre = 'Planta Piloto de Panificación'
    prefijo = 'PAN'


class PlantaHortofruticolaTests(PlantaCargada, TestCase):
    planta = 'hortofruticola'
    slug = 'planta-piloto-frutas-vegetales'
    nombre = 'Planta Piloto Hortofrutícola'
    prefijo = 'HOR'


class PlantaDeAlmidonesTests(PlantaCargada, TestCase):
    planta = 'almidones'
    slug = 'planta-extraccion-almidon-biotecnologia'
    nombre = 'Planta Piloto de Almidones y Derivados'
    prefijo = 'ALM'


class LasCuatroPlantasTests(TestCase):
    """Lo que vale para las cuatro juntas, sin repetir la carga en cada prueba."""

    @classmethod
    def setUpTestData(cls):
        for planta in ('carnicos', 'panificacion', 'hortofruticola', 'almidones', 'lacteos'):
            call_command('cargar_laboratorios_institucionales', laboratorio=planta)

    def test_las_cinco_plantas_conviven_sin_pisarse_los_codigos(self):
        plantas = Unidad.objects.filter(dependencia='plantas_piloto')
        self.assertGreaterEqual(plantas.count(), 4)
        prefijos = {'CAR': 0, 'PAN': 0, 'HOR': 0, 'ALM': 0}
        for producto in Producto.objects.filter(unidad__dependencia='plantas_piloto'):
            prefijo = producto.codigo.split('-')[0]
            if prefijo in prefijos:
                prefijos[prefijo] += 1
        for prefijo, cantidad in prefijos.items():
            self.assertGreaterEqual(cantidad, 4, f'{prefijo}: solo {cantidad} productos')
        # Ningún código de producto se repite entre plantas.
        codigos = list(
            Producto.objects.filter(unidad__dependencia='plantas_piloto').values_list('codigo', flat=True)
        )
        self.assertEqual(len(codigos), len(set(codigos)))
        self.assertEqual(FamiliaProducto.objects.filter(unidad__in=plantas).count(), 31)
        for unidad in plantas:
            prefijo = unidad.familias_producto.order_by('orden').first().codigo.split('-F', 1)[0]
            self.assertEqual(
                list(unidad.familias_producto.values_list('nombre', flat=True)),
                list(TAXONOMIA_FAMILIAS[prefijo]),
            )
            self.assertFalse(Producto.objects.filter(unidad=unidad, familia__isnull=True).exists())
            self.assertFalse(Receta.objects.filter(unidad=unidad, familia__isnull=True).exists())

    def test_cada_planta_declara_el_plazo_de_reposicion_de_su_materia_prima(self):
        for slug in (
            'planta-piloto-carnicos', 'planta-piloto-cereales',
            'planta-piloto-frutas-vegetales', 'planta-extraccion-almidon-biotecnologia',
        ):
            with self.subTest(planta=slug):
                unidad = Unidad.objects.get(slug=slug)
                con_plazo = Consumible.objects.filter(unidad=unidad, plazo_reposicion_dias__gt=0)
                self.assertGreaterEqual(con_plazo.count(), 3)
                self.assertTrue(
                    Consumible.objects.filter(unidad=unidad).exclude(proveedor_referencia='').exists(),
                    'ningún insumo dice de dónde llega',
                )

    def test_catalogo_muestra_identidad_responsable_y_cifras_reales(self):
        response = self.client.get(reverse('plantas-piloto'))

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context['paginator'].count, 5)
        self.assertContains(response, 'Ing. Marcela Ortega')
        self.assertContains(response, 'Producción por lotes')
        self.assertContains(response, '/static/img/default_project.jpg')
        self.assertNotContains(response, 'lab-unit-card__views')
        self.assertNotContains(response, 'Por asignar')
        self.assertNotContains(response, 'Por registrar')

        lacteos = next(
            unidad
            for unidad in response.context['unidades']
            if unidad.slug == 'planta-piloto-lacteos'
        )
        self.assertEqual(lacteos.catalogo_etiqueta, 'Lácteos')
        self.assertEqual(lacteos.total_productos_catalogo, 20)
        # Once procesos de referencia y cuatro derivados, por validar.
        self.assertEqual(lacteos.total_procesos_catalogo, 15)
        self.assertEqual(lacteos.total_equipos_catalogo, 19)
        self.assertEqual(len(lacteos.catalogo_familias_principales), 3)

    def test_filtros_especificos_consultan_el_nucleo_de_cada_planta(self):
        def slugs(**filtros):
            response = self.client.get(reverse('plantas-piloto'), filtros)
            self.assertEqual(response.status_code, 200)
            return {unidad.slug for unidad in response.context['unidades']}

        self.assertEqual(
            slugs(familia_producto='LAC-F01'),
            {'planta-piloto-lacteos'},
        )
        self.assertEqual(
            slugs(tecnologia='fermentacion'),
            {'planta-piloto-lacteos', 'planta-piloto-cereales'},
        )
        self.assertEqual(
            slugs(tecnologia='envasado_vacio_map'),
            {'planta-piloto-carnicos', 'planta-piloto-frutas-vegetales'},
        )
        self.assertEqual(
            slugs(servicio='desarrollo_producto'),
            {'planta-piloto-carnicos'},
        )
        self.assertEqual(len(slugs(servicio='maquila_academica')), 5)
        self.assertEqual(slugs(tecnologia='destilacion'), set())
        self.assertEqual(slugs(modo_operacion='lotes'), {
            'planta-piloto-lacteos', 'planta-piloto-carnicos',
            'planta-piloto-frutas-vegetales', 'planta-extraccion-almidon-biotecnologia',
            'planta-piloto-cereales',
        })
        self.assertEqual(
            slugs(busqueda='despulpadora'),
            {'planta-piloto-frutas-vegetales'},
        )

        Unidad.objects.filter(slug='planta-piloto-carnicos').update(
            estado_catalogo='disponible',
        )
        Unidad.objects.filter(slug='planta-piloto-frutas-vegetales').update(
            estado_catalogo='mantenimiento',
        )
        self.assertEqual(
            slugs(disponibilidad='disponible'),
            {'planta-piloto-carnicos'},
        )
        self.assertEqual(
            slugs(disponibilidad='mantenimiento'),
            {'planta-piloto-frutas-vegetales'},
        )

class LasDefinicionesNoSePisanTests(TestCase):
    """Lo que se revisa sin tocar la base: los códigos y los nombres son de una sola unidad.

    `CategoriaEquipo.nombre` es único en toda la plataforma, así que dos plantas
    no pueden llamar «Empaque» a su categoría aunque cada una use su propio
    código. Lo mismo vale para los códigos de equipo, insumo, área, software,
    producto, receta y servicio: el cargador los busca por código, sin filtrar
    por unidad.
    """

    @staticmethod
    def _catalogo():
        from apps.integraciones.management.commands.cargar_laboratorios_institucionales import LABORATORIOS

        return LABORATORIOS

    def test_ninguna_categoria_de_equipo_repite_nombre_con_otro_codigo(self):
        por_nombre = {}
        for definicion in self._catalogo().values():
            for equipo in definicion['equipos']:
                por_nombre.setdefault(equipo['categoria'], set()).add(equipo['categoria_codigo'])
        repetidos = {nombre: codigos for nombre, codigos in por_nombre.items() if len(codigos) > 1}
        self.assertEqual(repetidos, {}, f'categorías con el mismo nombre y distinto código: {repetidos}')

    def test_ningun_codigo_pertenece_a_dos_unidades(self):
        duenos = {}
        for clave, definicion in self._catalogo().items():
            codigos = [item['codigo'] for item in definicion['equipos']]
            codigos += [codigo for item in definicion['equipos'] for codigo in item['unidades']]
            for lista in ('consumibles', 'espacios', 'software', 'productos', 'recetas', 'acceso'):
                codigos += [item['codigo'] for item in definicion.get(lista, [])]
            codigos += [item['code'] for item in definicion.get('servicios', [])]
            codigos += [item['codigo'] for item in definicion.get('calidad', [])]
            for codigo in codigos:
                duenos.setdefault(codigo, set()).add(clave)
        compartidos = {codigo: unidades for codigo, unidades in duenos.items() if len(unidades) > 1}
        self.assertEqual(compartidos, {}, f'códigos en más de una unidad: {compartidos}')

    def test_cada_planta_lleva_su_prefijo_en_todo_lo_suyo(self):
        for clave in ('carnicos', 'panificacion', 'hortofruticola', 'almidones', 'lacteos'):
            definicion = self._catalogo()[clave]
            prefijo = definicion['prefijo']
            with self.subTest(planta=clave):
                for lista in ('equipos', 'consumibles', 'espacios', 'software', 'productos', 'recetas'):
                    for item in definicion.get(lista, []):
                        self.assertTrue(
                            item['codigo'].startswith(f'{prefijo}-'),
                            f'{clave}: «{item["codigo"]}» no empieza con «{prefijo}-»',
                        )
