"""La ficha del activo: qué es, qué contiene, cómo se usa y qué le ha pasado.

Relaciona el seguimiento de mantenimiento con el equipo real del inventario:
sus características y accesorios, el espacio desde el que se reserva, su nivel
de uso, la vida útil por tiempo y por horas, la ficha de estado de cada
intervención y la línea de trazabilidad desde que entró al laboratorio.
"""

from datetime import date, time, timedelta

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from apps.recursos.presentation.ficha_equipo import ficha_equipo, fichas_de_estado, garantia_del_equipo, linea_de_trazabilidad, origenes_de_la_ficha, piezas_del_equipo, uso_del_equipo, vida_util
from apps.recursos.models.equipos import CategoriaEquipo, EquiposServicios, PiezaEquipo
from apps.recursos.models.consumibles import Consumible, ConsumiblePorEquipo
from apps.gestion_unidades.models.espacios import EspacioReservable
from apps.recursos.models.mantenimiento import IncidenciaEquipo, MantenimientoEquipo, PlanMantenimientoEquipo, RepuestoMantenimiento
from apps.reservas.models.reservas import Reserva
from apps.recursos.models.software import SoftwareDisponible
from apps.directorio_unidades.models.core import Unidad
from apps.recursos.models.unidades import UnidadEquipo
from tests.integration.utiles import identificar


class BaseDeFicha(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.hoy = timezone.localdate()
        cls.coordinador = get_user_model().objects.create_user(
            'coordinador-ficha', password='clave-segura', first_name='Ana', last_name='Coordinadora')
        identificar(cls.coordinador, tipo_usuario='administrativo', carrera='')
        cls.unidad = Unidad.objects.create(
            nombre='Laboratorio de fichas', slug='laboratorio-fichas', dependencia='laboratorios',
            descripcion='Laboratorio de prueba.', fecha_inicio=date(2019, 1, 1), administrador=cls.coordinador)
        categoria = CategoriaEquipo.objects.create(nombre='Impresión 3D de ficha')
        cls.tipo = EquiposServicios.objects.create(
            codigo='FICHA-IMP', nombre='Impresora 3D FDM', marca='Prusa', modelo='XL',
            vida_util_referencia_anios=8, vida_util_horas=100,
            caracteristicas_publicas='Volumen 360 mm. Cinco cabezales.')
        cls.tipo.categorias.add(categoria)
        cls.equipo = UnidadEquipo.objects.create(
            codigo_unidad='FIC-IMP-01', equipo=cls.tipo, laboratorio=cls.unidad, estado_unidad='disponible',
            criticidad='critico', fecha_adquisicion=cls.hoy - timedelta(days=365 * 4),
            valor_referencial=4200, numero_serie='SN-0042')

    def reserva(self, dias, horas=3, estado='completada'):
        return Reserva.objects.create(
            laboratorio=self.unidad, usuario=self.coordinador, equipo_nombre=self.tipo.nombre,
            unidades_seleccionadas=f'[{{"codigo": "{self.equipo.codigo_unidad}", "nombre": "x"}}]',
            fecha=self.hoy - timedelta(days=dias), hora_inicio=time(9, 0), hora_fin=time(9 + horas, 0),
            estado=estado, proposito_codigo='docencia_practica', titulo_solicitud='Práctica',
            numero_participantes=10)

    def orden(self, dias, costo=None, resultado='Sin novedades.', estado='completado'):
        return MantenimientoEquipo.objects.create(
            equipo=self.equipo, unidad=self.unidad, tipo='preventivo', estado=estado,
            titulo='Mantenimiento preventivo', fecha_programada=timezone.now() - timedelta(days=dias),
            fecha_inicio=timezone.now() - timedelta(days=dias),
            fecha_fin=timezone.now() - timedelta(days=dias) + timedelta(hours=4) if estado == 'completado' else None,
            responsable=self.coordinador, costo=costo,
            resultado=resultado if estado == 'completado' else '')


class VidaUtilYUsoTests(BaseDeFicha):
    def test_la_vida_util_se_hereda_del_tipo_cuando_el_activo_no_la_define(self):
        # El activo no declara años propios: usa la referencia institucional del tipo.
        self.assertEqual(self.equipo.vida_util_anios, 0)
        self.assertEqual(self.equipo.vida_util_efectiva, 8)
        self.assertEqual(self.equipo.vida_util_por_horas, 100)
        self.assertEqual(self.equipo.fin_vida_util.year, self.equipo.fecha_adquisicion.year + 8)

        self.equipo.vida_util_anios = 5
        self.assertEqual(self.equipo.vida_util_efectiva, 5)

    def test_la_vida_util_se_cumple_por_tiempo_o_por_uso_lo_que_ocurra_primero(self):
        # Cuatro de ocho años: la mitad por tiempo, nada por uso.
        por_tiempo = vida_util(self.equipo, 0, self.hoy)
        self.assertEqual(por_tiempo['motivo'], 'tiempo')
        self.assertAlmostEqual(por_tiempo['por_tiempo'], 50, delta=1)
        self.assertEqual(por_tiempo['por_uso'], 0)
        self.assertFalse(por_tiempo['alerta'])

        # Con 90 de las 100 horas de vida, manda el uso.
        por_uso = vida_util(self.equipo, 90, self.hoy)
        self.assertEqual(por_uso['motivo'], 'uso')
        self.assertEqual(por_uso['consumida'], 90)
        self.assertTrue(por_uso['alerta'])
        self.assertFalse(por_uso['cumplida'])
        self.assertTrue(vida_util(self.equipo, 120, self.hoy)['cumplida'])

    def test_una_baja_por_dano_cierra_el_ciclo_antes_de_tiempo(self):
        self.equipo.fecha_baja = self.hoy
        self.equipo.motivo_baja = 'dano_irreparable'

        ciclo = vida_util(self.equipo, 10, self.hoy)

        self.assertEqual(ciclo['motivo'], 'dano')
        self.assertEqual(ciclo['motivo_texto'], 'Baja anticipada por daño irreparable')

    def test_el_uso_cuenta_las_sesiones_horas_y_usuarios_del_activo(self):
        self.reserva(10)
        self.reserva(40)
        self.reserva(70, estado='cancelada')

        uso = uso_del_equipo(self.equipo, self.hoy)

        self.assertEqual(uso['sesiones'], 2)
        self.assertEqual(uso['horas'], 6.0)
        self.assertEqual(uso['usuarios'], 1)
        self.assertEqual(uso['horas_acumuladas'], 6.0)
        self.assertEqual(len(uso['serie']), 12)
        self.assertEqual(sum(mes['sesiones'] for mes in uso['serie']), 2)


class FichasYTrazabilidadTests(BaseDeFicha):
    def test_cada_intervencion_deja_su_ficha_de_estado_con_repuestos_y_costo(self):
        orden = self.orden(30, costo=120, resultado='Cambio de hotend y nivelación.')
        RepuestoMantenimiento.objects.create(
            mantenimiento=orden, descripcion='Hotend completo', cantidad=1, costo_unitario=85,
            procedencia='compra')
        RepuestoMantenimiento.objects.create(
            mantenimiento=orden, descripcion='Boquilla', cantidad=2, costo_unitario=18,
            procedencia='inventario')

        fichas = fichas_de_estado(self.equipo)

        self.assertEqual(len(fichas), 1)
        ficha = fichas[0]
        self.assertEqual(ficha['orden'].resultado, 'Cambio de hotend y nivelación.')
        self.assertEqual(len(ficha['repuestos']), 2)
        self.assertEqual(ficha['costo_repuestos'], 121)
        self.assertEqual(ficha['costo_total'], 241)
        self.assertEqual(ficha['horas_detenido'], 4.0)

    def test_la_trazabilidad_reune_registro_incidencias_y_mantenimientos(self):
        IncidenciaEquipo.objects.create(
            equipo=self.equipo, unidad=self.unidad, titulo='Atasco de extrusor', tipo='falla',
            prioridad='alta', estado='abierta', descripcion='Se detuvo.', detiene_operacion=True,
            reportada_por=self.coordinador)
        self.orden(15, costo=40)

        hitos = linea_de_trazabilidad(self.equipo)

        titulos = ' | '.join(hito['titulo'] for hito in hitos)
        self.assertIn('Registro inicial', titulos)
        self.assertIn('Incidencia: Atasco de extrusor', titulos)
        self.assertIn('Mantenimiento preventivo', titulos)
        # Del hecho más reciente al más antiguo.
        self.assertEqual(hitos, sorted(hitos, key=lambda hito: hito['fecha'], reverse=True))
        self.assertEqual(next(h['tono'] for h in hitos if h['titulo'].startswith('Incidencia')), 'critico')


class PaginaDeLaFichaTests(BaseDeFicha):
    def test_la_ficha_reune_inventario_uso_mantenimiento_y_trazabilidad(self):
        espacio = EspacioReservable.objects.create(
            unidad=self.unidad, codigo='FIC-A1', nombre='Área de impresión', tipo='area', capacidad=10)
        espacio.equipos_asociados.add(self.equipo)
        software = SoftwareDisponible.objects.create(
            unidad=self.unidad, nombre='PrusaSlicer', codigo='PS', version='2.9', tipo_acceso='instalacion')
        software.equipos_instalados.add(self.equipo)
        consumible = Consumible.objects.create(
            unidad=self.unidad, codigo='BOQ-04', nombre='Boquilla 0,4 mm', clasificacion='insumo',
            unidad_medida='unidad', stock_total=8)
        ConsumiblePorEquipo.objects.create(consumible=consumible, equipo=self.tipo, cantidad=1)
        PlanMantenimientoEquipo.objects.create(
            equipo=self.equipo, nombre='Calibración trimestral', tipo='preventivo', frecuencia_dias=90,
            fecha_inicio=self.hoy, proxima_ejecucion=self.hoy + timedelta(days=30))
        self.orden(20, costo=50)
        self.reserva(5)

        ficha = ficha_equipo(self.equipo, self.hoy)

        self.assertEqual(ficha['contenido']['espacios'], [espacio])
        self.assertEqual(ficha['contenido']['software'], [software])
        self.assertEqual(ficha['contenido']['insumos'], [consumible])
        self.assertEqual(len(ficha['planes']), 1)
        self.assertEqual(ficha['uso']['sesiones'], 1)
        self.assertEqual(ficha['costo_total'], 50)
        self.assertEqual(ficha['semaforo'], 'al_dia')
        self.assertTrue(ficha['trazabilidad'])

    def test_la_pagina_muestra_la_ficha_y_se_abre_desde_el_seguimiento(self):
        self.orden(20, costo=50, resultado='Limpieza general y cambio de boquilla.')
        self.reserva(5)
        self.client.force_login(self.coordinador)
        ruta = reverse('ficha_equipo_unidad', args=[self.unidad.slug, self.equipo.pk])

        pagina = self.client.get(ruta)

        self.assertContains(pagina, 'FIC-IMP-01')
        self.assertContains(pagina, 'Volumen 360 mm. Cinco cabezales.')
        self.assertContains(pagina, 'Cuánta vida le queda')
        self.assertContains(pagina, 'Cuánto se usa')
        self.assertContains(pagina, 'Qué se hizo en cada intervención')
        self.assertContains(pagina, 'Limpieza general y cambio de boquilla.')
        self.assertContains(pagina, 'Todo lo que le ha pasado')
        panel = self.client.get(reverse('gestion_unidad', args=[self.unidad.slug]), {'view': 'mantenimiento'})
        self.assertContains(panel, ruta)

    def test_quien_no_gestiona_la_unidad_no_abre_la_ficha(self):
        ajeno = get_user_model().objects.create_user('ajeno-ficha', password='clave-segura')
        identificar(ajeno, tipo_usuario='estudiante')
        self.client.force_login(ajeno)

        respuesta = self.client.get(reverse('ficha_equipo_unidad', args=[self.unidad.slug, self.equipo.pk]))

        self.assertEqual(respuesta.status_code, 403)

    def test_un_equipo_de_otra_unidad_no_se_abre_desde_esta(self):
        otra = Unidad.objects.create(
            nombre='Otro laboratorio', slug='otro-laboratorio-ficha', dependencia='laboratorios',
            descripcion='Otro.', fecha_inicio=date(2024, 1, 1), administrador=self.coordinador)
        ajeno = UnidadEquipo.objects.create(
            codigo_unidad='OTRO-01', equipo=self.tipo, laboratorio=otra, estado_unidad='disponible')
        self.client.force_login(self.coordinador)

        respuesta = self.client.get(reverse('ficha_equipo_unidad', args=[self.unidad.slug, ajeno.pk]))

        self.assertEqual(respuesta.status_code, 404)


class PiezasGarantiaYEjecutorTests(BaseDeFicha):
    """Las piezas no son insumos, la garantía se declara y se sabe quién ejecuta."""

    def piezas(self):
        boquilla = PiezaEquipo.objects.create(
            equipo=self.tipo, nombre='Boquilla 0,4 mm', clase='componente', cantidad=5,
            critica=True, vida_util_horas=600, repuesto_disponible=True,
            descripcion='Por donde sale el filamento fundido.',
            recomendacion='Limpiar en frío; no rayar la punta con metal.')
        PiezaEquipo.objects.create(
            equipo=self.tipo, nombre='Cama de impresión', clase='componente', critica=True,
            descripcion='Superficie donde se adhiere la primera capa.')
        PiezaEquipo.objects.create(
            equipo=self.tipo, nombre='Espátula', clase='accesorio',
            descripcion='Para retirar la pieza terminada.')
        PiezaEquipo.objects.create(
            equipo=self.tipo, nombre='Regulador de energía', clase='proteccion', critica=True,
            recomendacion='Conectar siempre por el regulador: un corte daña la placa.')
        PiezaEquipo.objects.create(
            equipo=self.tipo, nombre='Juego de llaves Allen', clase='herramienta')
        return boquilla

    def test_las_piezas_se_agrupan_por_clase_y_no_se_mezclan_con_los_insumos(self):
        self.piezas()
        filamento = Consumible.objects.create(
            unidad=self.unidad, codigo='FIL-PLA', nombre='Filamento PLA 1,75 mm',
            clasificacion='insumo', unidad_medida='kg', stock_total=6)
        ConsumiblePorEquipo.objects.create(consumible=filamento, equipo=self.tipo, cantidad=1)

        ficha = ficha_equipo(self.equipo, self.hoy)

        clases = [clase for clase, _etiqueta, _filas in ficha['piezas']]
        self.assertEqual(clases, ['componente', 'accesorio', 'proteccion', 'herramienta'])
        nombres = [fila['pieza'].nombre
                   for _c, _e, filas in ficha['piezas'] for fila in filas]
        self.assertIn('Boquilla 0,4 mm', nombres)
        self.assertIn('Regulador de energía', nombres)
        # El filamento se gasta en el trabajo: es insumo, nunca pieza.
        self.assertNotIn('Filamento PLA 1,75 mm', nombres)
        self.assertEqual(ficha['contenido']['insumos'], [filamento])

    def test_la_pieza_reemplazada_queda_registrada_en_el_activo(self):
        boquilla = self.piezas()
        orden = self.orden(30, costo=18, resultado='Se cambió la boquilla obstruida.')
        RepuestoMantenimiento.objects.create(
            mantenimiento=orden, pieza=boquilla, descripcion='Boquilla 0,4 mm de latón',
            cantidad=1, costo_unitario=18, procedencia='inventario')

        grupos = dict((clase, filas) for clase, _etiqueta, filas in piezas_del_equipo(self.equipo))

        fila = next(f for f in grupos['componente'] if f['pieza'] == boquilla)
        self.assertEqual(len(fila['cambios']), 1)
        self.assertEqual(fila['ultimo_cambio'], orden.fecha_programada)
        cama = next(f for f in grupos['componente'] if f['pieza'].nombre == 'Cama de impresión')
        self.assertEqual(cama['cambios'], [])

    def test_la_garantia_dice_hasta_cuando_responde_el_proveedor_y_que_cubre(self):
        self.equipo.fecha_adquisicion = self.hoy - timedelta(days=200)
        self.equipo.garantia_meses = 24
        self.equipo.garantia_cobertura = 'Piezas, mano de obra y visita del técnico del proveedor.'
        self.equipo.garantia_contacto = 'Distribuidora Andina · soporte@ejemplo.ec'
        self.equipo.save()

        garantia = garantia_del_equipo(self.equipo, self.hoy)

        self.assertTrue(garantia['vigente'])
        self.assertEqual(garantia['meses'], 24)
        self.assertGreater(garantia['dias_restantes'], 400)
        self.assertIn('mano de obra', garantia['cobertura'])

    def test_un_equipo_fuera_de_plazo_queda_sin_garantia_vigente(self):
        self.equipo.fecha_adquisicion = self.hoy - timedelta(days=365 * 4)
        self.equipo.garantia_meses = 12
        self.equipo.save()

        garantia = garantia_del_equipo(self.equipo, self.hoy)

        self.assertFalse(garantia['vigente'])
        self.assertIsNone(garantia['dias_restantes'])
        self.assertLess(garantia['fin'], self.hoy)

    def test_sin_fecha_de_adquisicion_no_se_inventa_una_garantia(self):
        sin_fecha = UnidadEquipo.objects.create(
            codigo_unidad='FIC-IMP-02', equipo=self.tipo, laboratorio=self.unidad,
            estado_unidad='disponible', garantia_meses=12)

        self.assertIsNone(garantia_del_equipo(sin_fecha, self.hoy)['fin'])

    def test_la_ficha_declara_quien_ejecuta_cada_mantenimiento(self):
        PlanMantenimientoEquipo.objects.create(
            equipo=self.equipo, nombre='Limpieza y calibración mensual', tipo='preventivo',
            frecuencia_dias=30, ejecutor='interno', fecha_inicio=self.hoy,
            proxima_ejecucion=self.hoy + timedelta(days=10))
        externa = self.orden(12, costo=95, resultado='Cambio de placa madre.')
        externa.ejecutor = 'externo'
        externa.proveedor = 'Servicio técnico autorizado'
        externa.save()
        self.client.force_login(self.coordinador)

        pagina = self.client.get(
            reverse('ficha_equipo_unidad', args=[self.unidad.slug, self.equipo.pk]))

        self.assertContains(pagina, 'Personal de la unidad')
        self.assertContains(pagina, 'Técnico especializado externo')

    def test_la_ficha_usa_la_misma_fotografia_del_catalogo_de_reservas(self):
        # Sin foto propia ni de catálogo no hay imagen (se muestra el ícono), ni la de otro equipo.
        self.assertEqual(ficha_equipo(self.equipo, self.hoy)['contenido']['imagen'], '')
        self.tipo.imagen_catalogo = 'img/catalogo/fablab/equipos/impresora-3d-fdm.png'
        self.tipo.save(update_fields=['imagen_catalogo'])
        self.equipo.refresh_from_db()
        ficha = ficha_equipo(self.equipo, self.hoy)

        self.assertEqual(ficha['contenido']['imagen'], self.tipo.imagen_publica_url)
        self.assertTrue(ficha['contenido']['imagen'])


class FichaEnPdfTests(BaseDeFicha):
    """La ficha se archiva y se entrega igual que los planes de mantenimiento."""

    def test_la_ficha_se_descarga_en_pdf_con_el_marco_institucional(self):
        PiezaEquipo.objects.create(
            equipo=self.tipo, nombre='Extrusor', clase='componente', critica=True)
        PlanMantenimientoEquipo.objects.create(
            equipo=self.equipo, nombre='Calibración trimestral', tipo='preventivo',
            frecuencia_dias=90, ejecutor='interno', fecha_inicio=self.hoy,
            proxima_ejecucion=self.hoy + timedelta(days=30))
        self.orden(20, costo=50, resultado='Limpieza general.')
        self.client.force_login(self.coordinador)

        respuesta = self.client.get(
            reverse('ficha_equipo_unidad_pdf', args=[self.unidad.slug, self.equipo.pk]))

        self.assertEqual(respuesta.status_code, 200)
        self.assertEqual(respuesta['Content-Type'], 'application/pdf')
        self.assertIn('ficha-FIC-IMP-01.pdf', respuesta['Content-Disposition'])
        self.assertTrue(respuesta.content.startswith(b'%PDF'))

    def test_la_pagina_ofrece_la_descarga_del_pdf(self):
        self.client.force_login(self.coordinador)
        ruta_pdf = reverse('ficha_equipo_unidad_pdf', args=[self.unidad.slug, self.equipo.pk])

        pagina = self.client.get(
            reverse('ficha_equipo_unidad', args=[self.unidad.slug, self.equipo.pk]))

        self.assertContains(pagina, ruta_pdf)

    def test_quien_no_gestiona_la_unidad_tampoco_descarga_el_pdf(self):
        ajeno = get_user_model().objects.create_user('ajeno-pdf-ficha', password='clave-segura')
        identificar(ajeno, tipo_usuario='estudiante')
        self.client.force_login(ajeno)

        respuesta = self.client.get(
            reverse('ficha_equipo_unidad_pdf', args=[self.unidad.slug, self.equipo.pk]))

        self.assertEqual(respuesta.status_code, 403)

    def test_la_tabla_del_seguimiento_identifica_el_equipo_con_nombre_y_foto(self):
        self.client.force_login(self.coordinador)

        panel = self.client.get(
            reverse('gestion_unidad', args=[self.unidad.slug]), {'view': 'mantenimiento'})

        self.assertContains(panel, 'Impresora 3D FDM')
        self.assertContains(panel, 'class="mant-equipo"')
        self.assertContains(panel, self.tipo.imagen_publica_url)


class OrigenDelDatoTests(BaseDeFicha):
    """La ficha dice de dónde sale cada bloque y por dónde se corrige."""

    def test_cada_bloque_declara_su_origen(self):
        origenes = origenes_de_la_ficha(self.unidad, self.equipo, self.coordinador)

        self.assertEqual(
            sorted(origenes),
            ['activo', 'insumos', 'mantenimiento', 'piezas', 'tipo', 'trazabilidad', 'uso', 'vida'])
        for clave, origen in origenes.items():
            self.assertTrue(str(origen['texto']).strip(), clave)
        # Lo que se calcula solo no se edita a mano en ninguna pantalla.
        self.assertEqual(origenes['trazabilidad']['url'], '')

    def test_quien_administra_recibe_la_pantalla_de_su_vertical(self):
        administrador = get_user_model().objects.create_superuser(
            'super-ficha', 'super@ejemplo.ec', 'clave-segura')

        origenes = origenes_de_la_ficha(self.unidad, self.equipo, administrador)

        self.assertEqual(origenes['activo']['url'],
                         reverse('admin:laboratorios_unidadequipo_change', args=[self.equipo.pk]))
        self.assertEqual(origenes['tipo']['url'],
                         reverse('admin:laboratorios_equiposservicios_change', args=[self.tipo.pk]))
        self.assertIn(str(self.tipo.pk), origenes['piezas']['url'])
        self.assertIn('view=mantenimiento', origenes['mantenimiento']['url'])

    def test_sin_permiso_no_se_ofrece_una_pantalla_que_no_se_puede_abrir(self):
        origenes = origenes_de_la_ficha(self.unidad, self.equipo, self.coordinador)

        self.assertEqual(origenes['activo']['url'], '')
        self.assertEqual(origenes['tipo']['url'], '')
        # El seguimiento de la unidad sí es suyo: siempre se ofrece.
        self.assertTrue(origenes['mantenimiento']['url'])

    def test_la_pagina_explica_de_donde_sale_la_informacion(self):
        self.client.force_login(self.coordinador)

        pagina = self.client.get(
            reverse('ficha_equipo_unidad', args=[self.unidad.slug, self.equipo.pk]))

        self.assertContains(pagina, 'ficha__origen')
        self.assertContains(pagina, 'la ficha técnica del equipo en el catálogo')
        self.assertContains(pagina, 'No se escribe a mano.')


class VisorDeLaFichaTests(BaseDeFicha):
    """El PDF se mira dentro de la página y se descarga desde el visor."""

    def test_la_ficha_se_abre_en_el_visor_de_la_plataforma(self):
        self.client.force_login(self.coordinador)
        ruta_pdf = reverse('ficha_equipo_unidad_pdf', args=[self.unidad.slug, self.equipo.pk])

        pagina = self.client.get(
            reverse('ficha_equipo_unidad', args=[self.unidad.slug, self.equipo.pk]))

        self.assertContains(pagina, 'data-ver-pdf')
        self.assertContains(pagina, f'data-pdf-descarga="{ruta_pdf}"')
        # El mismo visor del aula y del expediente, con su botón de descarga.
        self.assertContains(pagina, 'data-aula-pdf-modal')
        self.assertContains(pagina, 'data-descargar-pdf')
        self.assertContains(pagina, 'components/visor_pdf.js')
