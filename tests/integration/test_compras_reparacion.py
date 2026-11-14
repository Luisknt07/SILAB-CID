"""El PAC conserva la decisión técnica y rechaza referencias de otra solicitud."""
from copy import deepcopy
from datetime import date, timedelta
from decimal import Decimal
from types import SimpleNamespace
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.utils import timezone

from apps.directorio_unidades.models.core import Unidad
from apps.documentos.presentation.compras_reparacion import propuestas_reparacion, revisar_referencias_reparacion
from apps.documentos.presentation.conformidad_planes import analizar_contenido_plan
from apps.documentos.presentation.diagnostico_compras import diagnostico_unidad, fijar_diagnostico
from apps.documentos.presentation.pac_universitario import preparar_pac
from apps.recursos.models.equipos import EquiposServicios, PiezaEquipo
from apps.recursos.models.mantenimiento import DiagnosticoIncidenciaEquipo, IncidenciaEquipo
from apps.recursos.models.unidades import UnidadEquipo


class ComprasReparacionTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.hoy = timezone.localdate()
        cls.usuario = get_user_model().objects.create_user('pac-reparacion-gestor')
        cls.unidad = Unidad.objects.create(nombre='Unidad PAC reparación', slug='pac-reparacion-unidad',
            dependencia='laboratorios', administrador=cls.usuario, fecha_inicio=date(2024, 1, 1))
        cls.otra = Unidad.objects.create(nombre='Unidad PAC ajena', slug='pac-reparacion-ajena',
            dependencia='laboratorios', administrador=cls.usuario, fecha_inicio=date(2024, 1, 1))
        cls.modelo = EquiposServicios.objects.create(nombre='Impresora 3D', codigo='PAC-REPAR-MOD')
        cls.equipo = UnidadEquipo.objects.create(codigo_unidad='PAC-REPAR-A1', equipo=cls.modelo,
            laboratorio=cls.unidad, estado_unidad='dañado', fecha_adquisicion=cls.hoy-timedelta(days=90),
            vida_util_anios=5, garantia_meses=12)
        cls.otro_equipo = UnidadEquipo.objects.create(codigo_unidad='PAC-REPAR-A2', equipo=cls.modelo,
            laboratorio=cls.unidad)
        cls.ajeno = UnidadEquipo.objects.create(codigo_unidad='PAC-REPAR-AJENO', equipo=cls.modelo,
            laboratorio=cls.otra)
        cls.pieza = PiezaEquipo.objects.create(equipo=cls.modelo, nombre='Sensor térmico')

    def documento(self):
        return SimpleNamespace(pk=None, unidad=self.unidad, unidad_id=self.unidad.pk,
            anio=self.hoy.year, estado='pendiente', exigido=SimpleNamespace(codigo='PLAN-COMPRAS-ANUAL'))

    def incidencia(self, equipo=None):
        return IncidenciaEquipo.objects.create(equipo=equipo or self.equipo, titulo='Sensor inestable',
            descripcion='Falla de regulación documentada.', tipo='accesorio', reportada_por=self.usuario)

    def diagnostico(self, incidencia=None, **cambios):
        datos = dict(incidencia=incidencia or self.incidencia(), fecha_evaluacion=self.hoy,
            evaluada_por=self.usuario, causa='Sensor abierto en prueba eléctrica.',
            impacto='Interrupción de prácticas; existe alternativa temporal.',
            garantia_revision='no_cubre', garantia_respaldo='Consulta documentada REF-SENSOR excluye desgaste.',
            decision='repuesto', pieza=self.pieza, cantidad_componente=Decimal('2'),
            especificacion_componente='Sensor compatible con modelo y rango de temperatura.',
            justificacion_decision='El equipo funciona; sólo el sensor requiere cambio.')
        datos.update(cambios)
        return DiagnosticoIncidenciaEquipo.objects.create(**datos)

    def contenido(self, diagnostico=None, **cambios):
        fila = dict(area_id='unidad', tipo_necesidad='mantenimiento', clase_bien='repuestos',
            item='Sensor térmico', cantidad='2', costo_unitario='25', mes_compra='4',
            justificacion='Cambio de componente según diagnóstico técnico.', equipos_referencia=[str(self.equipo.pk)])
        if diagnostico:
            fila.update(incidencia_referencia=str(diagnostico.incidencia_id), diagnostico_referencia=str(diagnostico.pk))
        fila.update(cambios)
        contenido = preparar_pac(dict(compras=[fila]))
        contenido.pop('inversion_gestion_version')  # Se prueba la decisión técnica, no otros requisitos de prioridad.
        return fijar_diagnostico(self.documento(), contenido, hoy=self.hoy)

    def reglas(self, contenido, **opciones):
        return {error['regla'] for error in revisar_referencias_reparacion(self.documento(), contenido, **opciones)}

    def test_propuesta_componente_conserva_nombre_cantidad_y_activo_sin_doble_sugerencia(self):
        diagnostico = self.diagnostico()
        propuestas, fuentes = propuestas_reparacion(self.unidad, [self.equipo], {}, {}, self.hoy)
        self.assertEqual(len(propuestas), 1)
        propuesta = propuestas[0]
        self.assertEqual((propuesta['item'], propuesta['clase_bien'], Decimal(propuesta['cantidad'])),
            ('Sensor térmico', 'repuestos', Decimal('2')))
        self.assertEqual(propuesta['equipos_referencia'], [self.equipo.pk])
        self.assertEqual(propuesta['diagnostico_id'], diagnostico.pk)
        self.assertNotIn(self.equipo.codigo_unidad, propuesta['item'])
        lectura = diagnostico_unidad(self.documento(), hoy=self.hoy)
        propias = [p for p in lectura['sugerencias'] if p.get('equipo_id') == self.equipo.pk]
        self.assertEqual(len(propias), 1)
        self.assertEqual(propias[0]['origen'], 'diagnostico_tecnico')
        self.assertEqual(fuentes[0]['recomendacion']['diagnostico_id'], diagnostico.pk)

    def test_referencia_valida_coincide_con_diagnostico_activo_y_clase(self):
        diagnostico = self.diagnostico()
        self.assertEqual(self.reglas(self.contenido(diagnostico)), set())

    def test_referencias_ajenas_pares_incompletos_y_otros_activos_bloquean(self):
        diagnostico = self.diagnostico()
        ajeno = self.diagnostico(self.incidencia(self.ajeno))
        variantes = (
            dict(incidencia_referencia=str(ajeno.incidencia_id), diagnostico_referencia=str(ajeno.pk)),
            dict(incidencia_referencia='', diagnostico_referencia=str(diagnostico.pk)),
            dict(incidencia_referencia=str(diagnostico.incidencia_id), diagnostico_referencia=''),
            dict(equipos_referencia=[str(self.otro_equipo.pk)]),
            dict(clase_bien='equipos'),
        )
        for cambios in variantes:
            with self.subTest(cambios=cambios):
                self.assertIn('referencia_reparacion_invalida', self.reglas(self.contenido(diagnostico, **cambios)))

    def test_reposicion_de_equipo_danado_sin_diagnostico_bloquea_antes_de_firmar(self):
        contenido = self.contenido(tipo_necesidad='reposicion', clase_bien='equipos', item='Impresora 3D')
        self.assertIn('reposicion_sin_diagnostico', self.reglas(contenido))
        with patch('apps.documentos.presentation.priorizacion_compras.analizar_priorizacion', return_value={}):
            errores, _ = analizar_contenido_plan(self.documento(),
                SimpleNamespace(inicio=date(self.hoy.year, 1, 1), fin=date(self.hoy.year, 12, 31)), contenido)
        self.assertTrue(any(e['regla'] == 'reposicion_sin_diagnostico' and e['severidad'] == 'bloqueo' for e in errores))

    def test_decision_de_repuesto_no_habilita_comprar_otro_equipo_completo(self):
        diagnostico = self.diagnostico()
        contenido = self.contenido(diagnostico, tipo_necesidad='reposicion', clase_bien='equipos', item='Impresora 3D')
        self.assertTrue({'referencia_reparacion_invalida', 'reposicion_sin_diagnostico'} <= self.reglas(contenido))

    def test_copia_archivada_conserva_decision_original_tras_cambio_del_registro_vivo(self):
        diagnostico = self.diagnostico()
        contenido = self.contenido(diagnostico)
        original = deepcopy(contenido)
        diagnostico.decision = 'retirar'
        diagnostico.justificacion_decision = 'Segunda evaluación recomienda retiro técnico.'
        diagnostico.save()
        UnidadEquipo.objects.filter(pk=self.equipo.pk).update(laboratorio=self.otra, codigo_unidad='CODIGO-ACTUAL-DISTINTO')
        with self.assertNumQueries(0), patch('apps.documentos.presentation.diagnostico_compras.diagnostico_unidad',
                side_effect=AssertionError('Una copia enviada no relee las fuentes.')):
            self.assertEqual(self.reglas(contenido, archivado=True), set())
        self.assertEqual(contenido, original)

    def test_archivado_sin_captura_o_de_otra_unidad_no_recurre_a_registros_actuales(self):
        diagnostico = self.diagnostico()
        original = self.contenido(diagnostico)
        for cambio in ('ausente', 'unidad', 'anio', 'version'):
            contenido = deepcopy(original)
            if cambio == 'ausente':
                contenido.pop('diagnostico_compras_fuentes')
            else:
                contenido['diagnostico_compras_fuentes'][cambio] = 99999
            with self.subTest(cambio=cambio), self.assertNumQueries(0), patch(
                    'apps.documentos.presentation.diagnostico_compras.lectura_diagnostico',
                    side_effect=AssertionError('No se sustituye la captura enviada.')):
                self.assertEqual(self.reglas(contenido, archivado=True), {'diagnostico_reparacion_sin_captura'})

    def test_documento_anterior_sin_marcador_no_adquiere_requisitos_nuevos(self):
        with self.assertNumQueries(0):
            self.assertEqual(self.reglas(dict(pac_version=2, compras=[]), archivado=True), set())
