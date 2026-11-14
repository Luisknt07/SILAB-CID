"""La preparación técnica distingue declaración, existencia, stock y propuesta."""
from datetime import date
from io import StringIO
from types import SimpleNamespace
from unittest.mock import patch

from django.core.management import call_command
from django.db.models import Q
from django.test import TestCase

from apps.directorio_unidades.models.core import Unidad
from apps.gestion_unidades.models.espacios import EspacioReservable
from apps.gestion_unidades.models.fichas_area import ElementoFichaArea, FichaArea
from apps.recursos.management.catalogos.fablab_2026 import DECLARADOS, SLUG
from apps.recursos.models.consumibles import Consumible, ConsumiblePorEquipo, EntradaInventario
from apps.recursos.models.equipos import CategoriaEquipo, EquiposServicios
from apps.recursos.models.software import SoftwareDisponible
from apps.recursos.models.unidades import UnidadEquipo


class PrepararFabLabTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        # El comando se limita al slug solicitado; aislar la fixture de cualquier
        # unidad histórica sembrada por migraciones sin tocar su identidad.
        Unidad.objects.filter(slug=SLUG).update(slug='fablab-historico-prueba')
        cls.unidad = Unidad.objects.create(nombre='FabLab QA técnico', slug=SLUG,
            dependencia='laboratorios', fecha_inicio=date(2026, 1, 1))
        cls.area = EspacioReservable.objects.create(unidad=cls.unidad, codigo='FAB-AREA-IMP3D',
            nombre='Manufactura aditiva', capacidad=6)
        cls.otra = Unidad.objects.create(nombre='Otra unidad QA', slug='fablab-no-es-otra-qa', dependencia='laboratorios',
                                        fecha_inicio=date(2026, 1, 1))
        cls.pla = Consumible.objects.create(unidad=cls.unidad, codigo='FAB-QA-PLA', nombre='Filamento PLA negro 1,75 mm',
            unidad_medida='g', stock_total=1250, familia='Filamentos')
        cls.grueso = Consumible.objects.create(unidad=cls.unidad, codigo='FAB-QA-PLA285', nombre='Filamento PLA 2,85 mm',
            unidad_medida='g', stock_total=800)

    def aplicar(self):
        call_command('preparar_fablab_2026', aplicar=True, stdout=StringIO())

    def test_simulacion_no_crea_registros_ni_altera_stock(self):
        antes = (UnidadEquipo.objects.count(), EquiposServicios.objects.count(), SoftwareDisponible.objects.count(),
                 Consumible.objects.count(), ElementoFichaArea.objects.count())
        call_command('preparar_fablab_2026', stdout=StringIO())
        despues = (UnidadEquipo.objects.count(), EquiposServicios.objects.count(), SoftwareDisponible.objects.count(),
                   Consumible.objects.count(), ElementoFichaArea.objects.count())
        self.assertEqual(antes, despues)
        self.pla.refresh_from_db()
        self.assertEqual(self.pla.stock_total, 1250)

    def test_cantidades_declaradas_idempotentes_y_sin_habilitar(self):
        self.aplicar()
        primero = list(UnidadEquipo.objects.filter(laboratorio=self.unidad).values_list('pk', flat=True))
        self.aplicar()
        self.assertEqual(primero, list(UnidadEquipo.objects.filter(laboratorio=self.unidad).values_list('pk', flat=True)))
        self.assertEqual(len(primero), 12)
        for dato in DECLARADOS:
            with self.subTest(modelo=dato['modelo']):
                activos = UnidadEquipo.objects.filter(laboratorio=self.unidad, equipo__modelo=dato['modelo'])
                self.assertEqual(activos.count(), 4)
                self.assertFalse(activos.exclude(estado_unidad='no_disponible').exists())
                self.assertFalse(activos.filter(existencia_verificada=True).exists())
                self.assertFalse(activos.exclude(numero_serie__isnull=True).exclude(numero_serie='').exists())
                self.assertEqual(activos.filter(espacios_asociados=self.area).count(), 4)
        self.assertFalse(UnidadEquipo.objects.filter(laboratorio=self.otra).exists())

    def test_repeticion_conserva_estado_serie_e_inactivacion_del_responsable(self):
        self.aplicar()
        activo = UnidadEquipo.objects.filter(laboratorio=self.unidad).first()
        activo.estado_unidad, activo.numero_serie, activo.activa = 'mantenimiento', 'SERIE-REAL-QA', False
        activo.save()
        self.aplicar()
        activo.refresh_from_db()
        self.assertEqual((activo.estado_unidad, activo.numero_serie, activo.activa), ('mantenimiento', 'SERIE-REAL-QA', False))
        self.assertEqual(UnidadEquipo.objects.filter(laboratorio=self.unidad).count(), 12)

    def test_propuestas_no_fabrican_existencias_licencias_ni_instalaciones(self):
        self.aplicar()
        self.assertTrue(ElementoFichaArea.objects.filter(ficha__espacio__unidad=self.unidad, solo_referencia=True).exists())
        self.assertFalse(EntradaInventario.objects.filter(unidad=self.unidad).exists())
        nuevos = Consumible.objects.filter(unidad=self.unidad, codigo__startswith='FAB-REF-MAT-')
        self.assertTrue(nuevos.exists())
        self.assertFalse(nuevos.exclude(stock_total=0).exists())
        software = SoftwareDisponible.objects.filter(unidad=self.unidad)
        self.assertFalse(software.exclude(licencias_totales=0, licencias_disponibles=0, activo=False).exists())
        self.assertFalse(software.filter(equipos_instalados__isnull=False).exists())
        self.assertFalse(ConsumiblePorEquipo.objects.filter(consumible=self.grueso).exists())
        self.assertEqual(ConsumiblePorEquipo.objects.filter(consumible=self.pla).count(), 3)

    def test_sincronizacion_ignora_toda_dotacion_marcada_como_propuesta(self):
        ficha = FichaArea.objects.create(espacio=self.area)
        for tipo, nombre in [('equipo', 'Máquina futura QA'), ('insumo', 'Material futuro QA'), ('software', 'Programa futuro QA')]:
            ElementoFichaArea.objects.create(ficha=ficha, tipo=tipo, nombre=nombre, cantidad='4', solo_referencia=True)
        antes = (UnidadEquipo.objects.count(), EquiposServicios.objects.count(), Consumible.objects.count(), SoftwareDisponible.objects.count())
        call_command('sincronizar_equipamiento_areas', unidad=[SLUG], stdout=StringIO())
        self.assertEqual(antes, (UnidadEquipo.objects.count(), EquiposServicios.objects.count(), Consumible.objects.count(), SoftwareDisponible.objects.count()))

    def test_pf001_p_se_contrasta_como_x1_sin_agregar_otro_activo(self):
        modelo = EquiposServicios.objects.create(codigo='FAB-QA-X1', nombre='Impresora genérica', marca='Bambulab', modelo='PF001 - P')
        activo = UnidadEquipo.objects.create(codigo_unidad='FAB-QA-X1-01', equipo=modelo, laboratorio=self.unidad)
        self.aplicar()
        modelo.refresh_from_db()
        self.assertEqual(modelo.modelo, 'X1-Carbon')
        self.assertEqual(modelo.especificaciones['Volumen nominal'], '256 × 256 × 256 mm')
        self.assertEqual(modelo.unidades.get().pk, activo.pk)

    def test_modelo_de_otra_unidad_no_se_modifica_por_coincidencia(self):
        modelo = EquiposServicios.objects.create(codigo='OTRO-H2C-QA', nombre='H2C ajena', marca='Bambu Lab', modelo='H2C')
        UnidadEquipo.objects.create(codigo_unidad='OTRO-H2C-QA-01', equipo=modelo, laboratorio=self.otra)
        self.aplicar()
        modelo.refresh_from_db()
        self.assertEqual(modelo.nombre, 'H2C ajena')
        self.assertEqual(modelo.especificaciones, {})

    def test_modelo_compartido_por_m2m_se_reutiliza_sin_duplicar_cuatro_activos(self):
        modelo = EquiposServicios.objects.create(codigo='COMPARTIDO-H2C-QA', nombre='H2C compartida', marca='Bambu Lab', modelo='H2C')
        originales = []
        for indice in range(4):
            activo = UnidadEquipo.objects.create(codigo_unidad=f'COMP-H2C-QA-{indice}', equipo=modelo, laboratorio=self.otra)
            activo.laboratorios.add(self.unidad)
            originales.append(activo.pk)
        self.aplicar()
        self.aplicar()
        self.assertEqual(list(modelo.unidades.order_by('pk').values_list('pk', flat=True)), originales)
        self.assertEqual(EquiposServicios.objects.filter(
            Q(unidades__laboratorio=self.unidad) | Q(unidades__laboratorios=self.unidad),
            marca='Bambu Lab', modelo='H2C',
        ).distinct().count(), 1)
        self.assertFalse(UnidadEquipo.objects.filter(equipo=modelo, laboratorio=self.unidad).exists())
        self.assertEqual(UnidadEquipo.objects.filter(laboratorio=self.unidad).count(), 8)
        for activo in modelo.unidades.all():
            self.assertEqual(activo.laboratorio_id, self.otra.pk)

    def test_pf001_p_compartido_por_m2m_conserva_activo_y_mediciones(self):
        modelo = EquiposServicios.objects.create(
            codigo='COMPARTIDO-X1-QA', nombre='Impresora genérica', marca='Bambulab', modelo='PF001 - P',
            origen_datos_tecnicos='medido', especificaciones={'Comprobación de placa': 'Registro validado'},
            caracteristicas_publicas='Levantamiento propio del responsable.',
        )
        activo = UnidadEquipo.objects.create(codigo_unidad='COMP-X1-QA-01', equipo=modelo, laboratorio=self.otra)
        activo.laboratorios.add(self.unidad)
        self.aplicar()
        self.aplicar()
        modelo.refresh_from_db()
        self.assertEqual(modelo.modelo, 'X1-Carbon')
        self.assertEqual(modelo.origen_datos_tecnicos, 'medido')
        self.assertEqual(modelo.caracteristicas_publicas, 'Levantamiento propio del responsable.')
        self.assertEqual(modelo.especificaciones['Comprobación de placa'], 'Registro validado')
        self.assertEqual(modelo.especificaciones, {'Comprobación de placa': 'Registro validado'})
        self.assertEqual(modelo.unidades.get().pk, activo.pk)

    def test_repeticion_preserva_ediciones_tecnicas_y_completa_solo_claves_faltantes(self):
        self.aplicar()
        modelo = EquiposServicios.objects.filter(unidades__laboratorio=self.unidad, modelo='H2C').distinct().get()
        modelo.nombre = 'Impresora H2C validada por el responsable'
        modelo.origen_datos_tecnicos = 'referencia'
        modelo.caracteristicas_publicas = 'Levantamiento propio de capacidad efectiva.'
        modelo.uso_publico = 'Uso acordado en la unidad.'
        modelo.instrucciones_publicas = 'Instrucción validada para esta instalación.'
        modelo.especificaciones['Volumen nominal combinado'] = 'Valor contrastado por el responsable'
        modelo.especificaciones['Horas de prueba verificadas'] = 0
        modelo.especificaciones.pop('Diámetro de filamento')
        modelo.save()
        self.aplicar()
        modelo.refresh_from_db()
        self.assertEqual(modelo.nombre, 'Impresora H2C validada por el responsable')
        self.assertEqual(modelo.origen_datos_tecnicos, 'referencia')
        self.assertEqual(modelo.caracteristicas_publicas, 'Levantamiento propio de capacidad efectiva.')
        self.assertEqual(modelo.uso_publico, 'Uso acordado en la unidad.')
        self.assertEqual(modelo.instrucciones_publicas, 'Instrucción validada para esta instalación.')
        self.assertEqual(modelo.especificaciones['Volumen nominal combinado'], 'Valor contrastado por el responsable')
        self.assertEqual(modelo.especificaciones['Horas de prueba verificadas'], 0)
        self.assertEqual(modelo.especificaciones['Diámetro de filamento'], '1,75 mm')
        self.assertIn('Fuente técnica', modelo.especificaciones)
        self.assertEqual(UnidadEquipo.objects.filter(laboratorio=self.unidad).count(), 12)

    def test_levantamiento_medido_no_recibe_ni_siquiera_claves_o_textos_faltantes(self):
        modelo = EquiposServicios.objects.create(
            codigo='MEDIDO-H2C-QA', nombre='H2C con levantamiento validado', marca='Bambu Lab', modelo='H2C',
            origen_datos_tecnicos='medido', especificaciones={'Medición de referencia local': 'Valor validado'},
        )
        UnidadEquipo.objects.create(codigo_unidad='MEDIDO-H2C-QA-01', equipo=modelo, laboratorio=self.unidad)
        actualizado = modelo.fecha_actualizacion
        self.aplicar()
        modelo.refresh_from_db()
        self.assertEqual(modelo.especificaciones, {'Medición de referencia local': 'Valor validado'})
        self.assertEqual(modelo.origen_datos_tecnicos, 'medido')
        self.assertEqual(modelo.caracteristicas_publicas, '')
        self.assertEqual(modelo.instrucciones_publicas, '')
        self.assertEqual(modelo.uso_publico, '')
        self.assertEqual(modelo.fecha_actualizacion, actualizado)

    def test_catalogo_compartido_completa_referencia_sin_reabrir_contraste_y_respeta_medido(self):
        for origen in ('referencia', 'medido'):
            with self.subTest(origen=origen):
                previas = {'Contraste documental pendiente': 'Contraste resuelto por el responsable',
                           'Fecha del contraste': '2026-10-22', 'Dato propio': 'Valor registrado'}
                modelo = EquiposServicios.objects.create(
                    codigo=f'CAT-COMP-{origen}', nombre='Equipo con contraste propio',
                    origen_datos_tecnicos=origen, especificaciones=previas,
                )
                activo = UnidadEquipo.objects.create(codigo_unidad=f'CAT-ACT-{origen}', equipo=modelo, laboratorio=self.otra)
                activo.laboratorios.add(self.unidad)
                actualizado = modelo.fecha_actualizacion
                catalogos = ((modelo.codigo, 'Modelo del documento', 'Catálogo QA.pdf',
                              'Observación de referencia por contrastar', 'https://example.org/catalogo'),)
                with patch('apps.recursos.management.commands.preparar_fablab_2026.CATALOGOS_APORTADOS', catalogos):
                    self.aplicar()
                modelo.refresh_from_db()
                self.assertEqual({k: modelo.especificaciones[k] for k in previas}, previas)
                if origen == 'medido':
                    self.assertEqual(modelo.especificaciones, previas)
                    self.assertEqual(modelo.fecha_actualizacion, actualizado)
                else:
                    self.assertEqual(modelo.especificaciones['Catálogo aportado'], 'Catálogo QA.pdf')
                    self.assertEqual(modelo.especificaciones['Consulta de fabricante'], 'https://example.org/catalogo')
                self.assertEqual(modelo.unidades.get().pk, activo.pk)
                self.assertEqual(modelo.unidades.get().laboratorio_id, self.otra.pk)

    def test_categoria_preexistente_con_codigo_distinto_se_reutiliza(self):
        CategoriaEquipo.objects.filter(nombre='Impresión 3D').delete()
        categoria = CategoriaEquipo.objects.create(nombre='Impresión 3D', codigo='IMPRESION-LEGADA')
        self.aplicar()
        self.assertEqual(CategoriaEquipo.objects.filter(nombre='Impresión 3D').count(), 1)
        self.assertEqual(categoria.equipos.filter(unidades__laboratorio=self.unidad).distinct().count(), 3)

    def test_compras_conserva_fuente_y_condicion_de_propuesta_sin_carencia_confirmada(self):
        from apps.documentos.presentation.diagnostico_compras import diagnostico_unidad
        from apps.documentos.presentation.compras_contraste import contrastar_compras
        self.aplicar()
        documento = SimpleNamespace(unidad=self.unidad, unidad_id=self.unidad.pk, anio=2026, estado='pendiente')
        diagnostico = diagnostico_unidad(documento, hoy=date(2026, 10, 21))
        referencias = [r for a in diagnostico['areas'] for r in a['dotacion_referencia'] if r.get('solo_referencia')]
        self.assertTrue(referencias)
        equipos = [r for r in referencias if r['tipo'] == 'equipo']
        self.assertTrue(all(r['fuente'].startswith('https://') for r in equipos))
        contraste = contrastar_compras({}, diagnostico)
        propuestas = [r for a in contraste['areas'] for r in a['referencias'] if r.get('solo_referencia')]
        self.assertTrue(propuestas)
        self.assertTrue(all(not r['carencia_confirmada'] for r in propuestas))
        self.assertTrue(all('no acredita adquisición' in r['lectura'] for r in propuestas))
