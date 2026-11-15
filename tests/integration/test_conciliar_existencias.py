"""Lo que no existe no se muestra ni se cuenta: la conciliación separa existencias de referencias en cada unidad."""
import json
from datetime import date, time, timedelta
from decimal import Decimal
from io import StringIO

from django.contrib.auth import get_user_model
from django.core.management import call_command
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from apps.directorio_unidades.models.core import Unidad
from apps.formacion.models.practicas import RegistroAuditoriaUnidad
from apps.gestion_unidades.models.espacios import EspacioReservable
from apps.gestion_unidades.models.fichas_area import ElementoFichaArea, FichaArea
from apps.recursos.management.catalogos.existencias import VERSION
from apps.recursos.models.equipos import EquiposServicios
from apps.recursos.models.unidades import UnidadEquipo
from apps.recursos.presentation.verificacion_equipos import verificar_existencia
from apps.reservas.models.reservas import Reserva

FABLAB = 'laboratorio-fabricacion-digital-prototipado'


def ejecutar(*argumentos):
    salida = StringIO()
    call_command('conciliar_existencias', *argumentos, stdout=salida)
    return salida.getvalue()


class Base(TestCase):
    def unidad(self, slug, nombre):
        return Unidad.objects.create(nombre=nombre, slug=slug, dependencia='laboratorios', descripcion='.',
                                     fecha_inicio=date(2026, 1, 1))

    def area(self, unidad, codigo, **datos):
        area = EspacioReservable.objects.create(unidad=unidad, codigo=codigo, nombre=datos.pop('nombre', codigo),
                                                capacidad=6, **datos)
        FichaArea.objects.create(espacio=area, publicada=True)
        return area

    def equipo(self, unidad, area, codigo, nombre, nivel='basico', cantidad=1, **datos):
        modelo = EquiposServicios.objects.create(codigo=f'M-{codigo}', nombre=nombre)
        unidades = []
        for indice in range(1, cantidad + 1):
            fisica = UnidadEquipo.objects.create(codigo_unidad=f'{codigo}-{indice:02d}', equipo=modelo, laboratorio=unidad,
                                                 **datos)
            area.equipos_asociados.add(fisica)
            unidades.append(fisica)
        ElementoFichaArea.objects.create(ficha=area.ficha, tipo='equipo', nombre=nombre, nivel=nivel,
                                         cantidad=str(cantidad), registrado=unidades[0])
        return unidades


class SinInventarioPatrimonialTests(Base):
    """Una unidad cuyas existencias solo vienen de las fichas: lo básico se queda, lo demás es referencia."""

    @classmethod
    def setUpTestData(cls):
        cls.u = Base.unidad(cls, 'lab-conciliacion-qa', 'Laboratorio de conciliación QA')
        cls.trabajo = Base.area(cls, cls.u, 'QA-TRABAJO')
        cls.avanzada = Base.area(cls, cls.u, 'QA-AVANZADA')
        cls.basico = Base.equipo(cls, cls.u, cls.trabajo, 'QA-BAS', 'Multímetro digital', cantidad=2)
        cls.alta = Base.equipo(cls, cls.u, cls.trabajo, 'QA-ALT', 'Osciloscopio de alta gama', nivel='alta',
                               estado_unidad='no_disponible')
        cls.verificar = Base.equipo(cls, cls.u, cls.trabajo, 'QA-PV', 'Cámara térmica (por verificar)')
        cls.sin_habilitar = Base.equipo(cls, cls.u, cls.trabajo, 'QA-ND', 'Fuente de laboratorio', estado_unidad='no_disponible')
        cls.verificado = Base.equipo(cls, cls.u, cls.avanzada, 'QA-VER', 'Espectrómetro', nivel='alta',
                                     existencia_verificada=True)
        cls.solo_alta = Base.equipo(cls, cls.u, cls.trabajo, 'QA-SOLO', 'Robot colaborativo', nivel='alta')
        cls.vacia = Base.area(cls, cls.u, 'QA-VACIA')
        Base.equipo(cls, cls.u, cls.vacia, 'QA-VAC', 'Sistema de captura de movimiento', nivel='alta')
        # Una unidad compartida que es de otra unidad no se toca.
        otra = Base.unidad(cls, 'lab-dueno-qa', 'Laboratorio dueño QA')
        modelo = EquiposServicios.objects.create(codigo='M-AJENO', nombre='Brazo robótico ajeno')
        cls.ajeno = UnidadEquipo.objects.create(codigo_unidad='AJENO-01', equipo=modelo, laboratorio=otra,
                                                estado_unidad='no_disponible')
        cls.ajeno.laboratorios.add(cls.u)
        cls.trabajo.equipos_asociados.add(cls.ajeno)

    def activos(self):
        return set(UnidadEquipo.objects.filter(activa=True).values_list('codigo_unidad', flat=True))

    def test_la_simulacion_no_guarda_nada(self):
        antes = self.activos(), RegistroAuditoriaUnidad.objects.count()
        salida = ejecutar('--unidad', self.u.slug)
        self.assertIn('Simulación (nada se guardó)', salida)
        self.assertIn('5 equipos pasan a referencia', salida)
        self.assertEqual((self.activos(), RegistroAuditoriaUnidad.objects.count()), antes)

    def test_lo_basico_y_lo_verificado_existen_y_lo_demas_pasa_a_referencia(self):
        ejecutar('--unidad', self.u.slug, '--aplicar')
        self.assertEqual(self.activos() & {e.codigo_unidad for e in UnidadEquipo.objects.filter(laboratorio=self.u)},
                         {'QA-BAS-01', 'QA-BAS-02', 'QA-VER-01'})
        alta = UnidadEquipo.objects.get(codigo_unidad='QA-ALT-01')
        self.assertIn('alta capacidad', alta.observaciones)
        self.assertIn('por verificar', UnidadEquipo.objects.get(codigo_unidad='QA-PV-01').observaciones)
        self.assertIn('nunca se habilitó', UnidadEquipo.objects.get(codigo_unidad='QA-ND-01').observaciones)
        # La ficha conserva la descripción como dotación propuesta; lo que existe sigue como dotación.
        propuestas = set(ElementoFichaArea.objects.filter(solo_referencia=True).values_list('nombre', flat=True))
        self.assertIn('Osciloscopio de alta gama', propuestas)
        self.assertNotIn('Multímetro digital', propuestas)
        # El área que se quedó sin nada existente se oculta; las demás siguen.
        self.vacia.refresh_from_db()
        self.trabajo.refresh_from_db()
        self.assertEqual((self.vacia.activo, self.vacia.reservable, self.trabajo.activo), (False, False, True))
        self.ajeno.refresh_from_db()
        self.assertTrue(self.ajeno.activa)
        registro = RegistroAuditoriaUnidad.objects.get(unidad=self.u, descripcion__startswith=f'{VERSION}:')
        self.assertEqual(len(registro.datos_nuevos['equipos']), 5)

    def test_repetir_no_cambia_nada_y_revertir_lo_devuelve_todo(self):
        ejecutar('--unidad', self.u.slug, '--aplicar')
        self.assertIn('nada que cambiar', ejecutar('--unidad', self.u.slug, '--aplicar'))
        self.assertIn('equipos vuelven a existir', ejecutar('--unidad', self.u.slug, '--revertir', '--aplicar'))
        self.assertTrue(UnidadEquipo.objects.filter(laboratorio=self.u).exclude(activa=True).count() == 0)
        self.assertNotIn('Referencia:', UnidadEquipo.objects.get(codigo_unidad='QA-ALT-01').observaciones)
        self.assertFalse(ElementoFichaArea.objects.filter(solo_referencia=True).exists())
        self.vacia.refresh_from_db()
        self.assertTrue(self.vacia.activo)
        # Revertir dos veces no hace nada más.
        self.assertIn('nada que cambiar', ejecutar('--unidad', self.u.slug, '--revertir', '--aplicar'))

    def test_la_sincronizacion_de_fichas_no_vuelve_a_crear_lo_que_paso_a_referencia(self):
        ejecutar('--unidad', self.u.slug, '--aplicar')
        antes = UnidadEquipo.objects.filter(laboratorio=self.u).count()
        call_command('sincronizar_equipamiento_areas', '--unidad', self.u.slug, stdout=StringIO())
        self.assertEqual(UnidadEquipo.objects.filter(laboratorio=self.u).count(), antes)
        self.assertEqual(UnidadEquipo.objects.get(codigo_unidad='QA-ALT-01').activa, False)

    def test_un_equipo_nuevo_de_alta_capacidad_en_la_ficha_queda_como_propuesta(self):
        nuevo = ElementoFichaArea.objects.create(ficha=self.trabajo.ficha, tipo='equipo', nombre='Cortadora láser de fibra',
                                                 nivel='alta', cantidad='1')
        basico = ElementoFichaArea.objects.create(ficha=self.trabajo.ficha, tipo='equipo', nombre='Soldador de estaño',
                                                  nivel='basico', cantidad='2')
        call_command('sincronizar_equipamiento_areas', '--unidad', self.u.slug, stdout=StringIO())
        nuevo.refresh_from_db()
        basico.refresh_from_db()
        self.assertEqual((nuevo.solo_referencia, nuevo.registrado_id), (True, None))
        self.assertEqual(UnidadEquipo.objects.filter(equipo=basico.registrado.equipo, activa=True).count(), 2)

    def test_verificar_una_referencia_la_vuelve_a_existir(self):
        ejecutar('--unidad', self.u.slug, '--aplicar')
        alta = UnidadEquipo.objects.get(codigo_unidad='QA-ALT-01')
        verificar_existencia(alta, get_user_model().objects.create_user('verifica-qa'), nota='Conteo físico')
        alta.refresh_from_db()
        self.assertTrue(alta.activa)
        self.assertFalse(ElementoFichaArea.objects.get(registrado=alta).solo_referencia)

    def test_avisa_de_las_reservas_que_piden_algo_que_ya_no_existe(self):
        alta = self.alta[0]
        Reserva.objects.create(
            laboratorio=self.u, usuario=get_user_model().objects.create_user('solicita-qa'), fecha=timezone.localdate() + timedelta(days=3),
            hora_inicio=time(9), hora_fin=time(10), horas_seleccionadas='[9]', proposito='Docencia', equipo_codigo=alta.codigo_unidad,
            equipo_nombre=alta.equipo.nombre, unidades_seleccionadas=json.dumps([{'id': alta.pk}]), estado='pendiente')
        self.assertIn('pide un equipo o un área que ya no existe', ejecutar('--unidad', self.u.slug))


class ConInventarioPatrimonialTests(Base):
    """Con el reporte de bodega importado, existe lo que figura en él o lo que el responsable declaró."""

    @classmethod
    def setUpTestData(cls):
        Unidad.objects.filter(slug=FABLAB).update(slug='fablab-historico-qa')
        cls.u = Base.unidad(cls, FABLAB, 'FabLab QA')
        cls.diseno = Base.area(cls, cls.u, 'FAB-EST-DISENO', nombre='Diseño')
        cls.escaneo = Base.area(cls, cls.u, 'FAB-AREA-SCAN3D', nombre='Escaneo')
        cls.robotica = Base.area(cls, cls.u, 'FAB-AREA-ROBOTICA', nombre='Robótica hospedada')
        cls.sala = Base.area(cls, cls.u, 'FAB-SALA-CAP', nombre='Sala')
        Base.equipo(cls, cls.u, cls.diseno, 'FAB-WS', 'Estación de trabajo', codigo_bien='40530521',
                    valor_contable=Decimal('9367'))
        Base.equipo(cls, cls.u, cls.diseno, 'FAB-LAP', 'Portátil de préstamo', cantidad=3)
        Base.equipo(cls, cls.u, cls.diseno, 'FAB-DEC', 'Impresora declarada',
                    existencia_nota='Cantidad declarada por el responsable el 2026-10-21; pendiente placa.')
        Base.equipo(cls, cls.u, cls.diseno, 'FAB-DEMO', 'Equipo de ejemplo', codigo_bien='99009003')
        Base.equipo(cls, cls.u, cls.escaneo, 'FAB-SCAN', 'Escáner 3D', codigo_bien='40095898', valor_contable=Decimal('2820'))
        Base.equipo(cls, cls.u, cls.robotica, 'FAB-ROB', 'Robot móvil', codigo_bien='40000001', valor_contable=Decimal('100'))
        Base.equipo(cls, cls.u, cls.sala, 'FAB-KIT', 'Kits de taller', cantidad=2)

    def test_existe_lo_patrimonial_y_lo_declarado_y_se_ordenan_las_areas(self):
        ejecutar('--aplicar', '--unidad', FABLAB)
        existentes = set(UnidadEquipo.objects.filter(laboratorio=self.u, activa=True).values_list('codigo_unidad', flat=True))
        self.assertEqual(existentes, {'FAB-WS-01', 'FAB-DEC-01', 'FAB-SCAN-01'})
        self.assertIn('no figura en el inventario patrimonial',
                      UnidadEquipo.objects.get(codigo_unidad='FAB-LAP-01').observaciones)
        self.assertIn('no pertenece a la unidad', UnidadEquipo.objects.get(codigo_unidad='FAB-ROB-01').observaciones)
        areas = {area.codigo: area for area in EspacioReservable.objects.filter(unidad=self.u)}
        # El escaneo se integra en el diseño, con su equipo; la robótica es de otra unidad; la sala quedó vacía.
        self.assertEqual(areas['FAB-AREA-SCAN3D'].integrada_en, areas['FAB-EST-DISENO'])
        self.assertTrue(areas['FAB-EST-DISENO'].equipos_asociados.filter(codigo_unidad='FAB-SCAN-01').exists())
        self.assertEqual(areas['FAB-EST-DISENO'].nombre, 'Diseño, digitalización 3D y CAD/CAM')
        self.assertEqual({codigo for codigo, area in areas.items() if area.activo}, {'FAB-EST-DISENO'})
        # Lo que la unidad describe en la ficha ya no se completa con equipos inventados.
        antes = UnidadEquipo.objects.filter(laboratorio=self.u).count()
        call_command('sincronizar_equipamiento_areas', '--unidad', FABLAB, stdout=StringIO())
        self.assertEqual(UnidadEquipo.objects.filter(laboratorio=self.u).count(), antes)


class ElVisorSoloMuestraLoQueExisteTests(Base):
    @classmethod
    def setUpTestData(cls):
        cls.gestor = get_user_model().objects.create_user('gestor-visor-qa', password='clave')
        cls.u = Base.unidad(cls, 'lab-visor-qa', 'Laboratorio del visor QA')
        cls.u.administrador = cls.gestor
        cls.u.save(update_fields=['administrador'])
        cls.area = Base.area(cls, cls.u, 'VIS-AREA')
        cls.existe = Base.equipo(cls, cls.u, cls.area, 'VIS-OK', 'Microscopio óptico')[0]
        cls.referencia = Base.equipo(cls, cls.u, cls.area, 'VIS-REF', 'Microscopio confocal', nivel='alta')[0]
        cls.propuesta = ElementoFichaArea.objects.create(ficha=cls.area.ficha, tipo='equipo', nombre='Citómetro de flujo',
                                                         nivel='alta', solo_referencia=True)
        cls.inactiva = Base.area(cls, cls.u, 'VIS-INACTIVA', nombre='Área que no existe', activo=False)
        ejecutar('--aplicar', '--unidad', cls.u.slug)

    def botones(self):
        carpetas = self.client.get(self.u.get_absolute_url()).context['aula']['carpetas']
        return [boton for carpeta in carpetas for grupo in carpeta.get('grupos', []) for boton in grupo['botones']]

    def test_ni_el_publico_ni_quien_gestiona_ven_referencias_en_el_visor(self):
        for usuario in (None, self.gestor):
            with self.subTest(gestor=usuario is not None):
                if usuario:
                    self.client.force_login(usuario)
                urls = {boton.get('url') for boton in self.botones()}
                self.assertIn(reverse('ficha_equipo_publica', args=[self.u.slug, self.existe.codigo_unidad]), urls)
                self.assertNotIn(reverse('ficha_equipo_publica', args=[self.u.slug, self.referencia.codigo_unidad]), urls)
                self.assertNotIn(reverse('ficha_equipo_referencia', args=[self.u.slug, self.propuesta.pk]), urls)
                self.assertNotIn(reverse('area_unidad', args=[self.u.slug, self.inactiva.codigo]), urls)
                self.assertIn(reverse('area_unidad', args=[self.u.slug, self.area.codigo]), urls)

    def test_la_pagina_del_area_y_la_ficha_de_referencia_no_muestran_lo_que_no_existe(self):
        pagina = self.client.get(reverse('area_unidad', args=[self.u.slug, self.area.codigo]))
        self.assertContains(pagina, 'Microscopio óptico')
        self.assertNotContains(pagina, 'Microscopio confocal')
        self.assertNotContains(pagina, 'Citómetro de flujo')
        self.assertEqual(self.client.get(reverse('ficha_equipo_referencia', args=[self.u.slug, self.propuesta.pk])).status_code, 404)
        self.client.force_login(self.gestor)
        self.assertEqual(self.client.get(reverse('ficha_equipo_referencia', args=[self.u.slug, self.propuesta.pk])).status_code, 200)


class LoQueNoExisteNoSeOperaNiSeCuentaTests(Base):
    """Una referencia no se ofrece al reservar ni como equipo de un programa o de un insumo, ni se presta."""

    @classmethod
    def setUpTestData(cls):
        from apps.recursos.models.consumibles import Consumible, ConsumiblePorEquipo
        from apps.recursos.models.software import SoftwareDisponible

        cls.u = Base.unidad(cls, 'lab-operaciones-qa', 'Laboratorio de operaciones QA')
        cls.area = Base.area(cls, cls.u, 'OPE-AREA')
        cls.existe = Base.equipo(cls, cls.u, cls.area, 'OPE-OK', 'Computador de diseño')[0]
        cls.referencia = Base.equipo(cls, cls.u, cls.area, 'OPE-REF', 'Estación de render', nivel='alta')[0]
        cls.programa = SoftwareDisponible.objects.create(unidad=cls.u, nombre='Programa QA', activo=True)
        cls.programa.equipos_instalados.add(cls.existe, cls.referencia)
        cls.insumo = Consumible.objects.create(unidad=cls.u, codigo='OPE-INS', nombre='Filamento QA', activo=True)
        ConsumiblePorEquipo.objects.create(equipo=cls.referencia.equipo, consumible=cls.insumo)
        ejecutar('--aplicar', '--unidad', cls.u.slug)

    def test_areas_y_programas_cuentan_solo_lo_que_existe(self):
        area = EspacioReservable.objects.get(pk=self.area.pk)
        self.assertEqual(area.equipos_existentes, [self.existe])
        self.assertEqual(area.equipos_existentes_ids_csv, str(self.existe.pk))
        # El formulario de gestión conserva el vínculo con la referencia, para no perderlo al guardar.
        self.assertIn(str(self.referencia.pk), area.equipos_asociados_ids_csv)
        self.assertNotIn('Estación de render', self.programa.equipos_instalados_resumen)
        self.assertEqual(self.programa.equipos_existentes_ids_csv, str(self.existe.pk))

    def test_la_api_publica_y_la_pagina_de_insumos_no_muestran_referencias(self):
        datos = self.client.get(reverse('obtener_unidades_equipo', args=[self.referencia.equipo_id])).json()
        self.assertEqual(datos.get('unidades', []), [])
        pagina = self.client.get(reverse('insumos_unidad', args=[self.u.slug]))
        self.assertContains(pagina, 'Filamento QA')
        self.assertNotContains(pagina, 'Estación de render')

    def test_no_se_presta_ni_se_repara_una_referencia(self):
        from django.core.exceptions import ValidationError

        from apps.gestion_unidades.presentation.gestion import _equipo_existente_bloqueado

        with self.assertRaisesMessage(ValidationError, 'no existe en la unidad'):
            _equipo_existente_bloqueado(self.u, self.referencia.pk)
        self.assertEqual(_equipo_existente_bloqueado(self.u, self.existe.pk), self.existe)


class UnaUnidadSinInventarioNoLoRecibeDeSusFichasTests(Base):
    def test_la_sincronizacion_deja_sus_fichas_como_dotacion_propuesta(self):
        u = self.unidad('planta-proyectada-qa', 'Planta proyectada QA')
        area = self.area(u, 'PRO-AREA')
        elemento = ElementoFichaArea.objects.create(ficha=area.ficha, tipo='equipo', nombre='Tostadora de café',
                                                    nivel='basico', cantidad='1')
        call_command('sincronizar_equipamiento_areas', '--unidad', u.slug, stdout=StringIO())
        elemento.refresh_from_db()
        self.assertEqual((elemento.solo_referencia, elemento.registrado_id), (True, None))
        self.assertFalse(UnidadEquipo.objects.filter(laboratorio=u).exists())
