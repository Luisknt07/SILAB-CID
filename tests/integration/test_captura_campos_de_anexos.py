"""Los datos que piden los anexos del expediente se capturan donde la unidad ya trabaja: la unidad del syllabus en los
temas de la asignatura, el tipo y la superficie de cada espacio, el simulador entre el software, y los agroquímicos y
medicamentos veterinarios entre los insumos, como sustancias con lote, vencimiento y ficha de seguridad.

Los ensayos del centro experimental se prueban en test_centros_experimentales_ejes."""
import re
from datetime import date
from decimal import Decimal
from types import SimpleNamespace

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from apps.directorio_unidades.models.core import Unidad
from apps.documentos.presentation.protocolo_contexto import CLASES_DE_SUSTANCIAS, propuestas_de
from apps.formacion.models.asignaturas import Asignatura, TemaAsignatura
from apps.formacion.presentation.practicas_forms import PlanificacionPracticaForm
from apps.gestion_unidades.models.espacios import EspacioReservable
from apps.gestion_unidades.presentation.edicion_area import tipos_de_espacio
from apps.recursos.models.consumibles import Consumible
from apps.recursos.models.software import SoftwareDisponible
from apps.reservas.models.reservas import CatalogoActividadReserva
from tests.integration.utiles import identificar

LABORATORIO = ['area', 'estacion', 'sala', 'puesto', 'cabina', 'taller']
TIPOS_POR_DEPENDENCIA = {
    'laboratorios': [*LABORATORIO, 'otro'],
    'plantas_piloto': [*LABORATORIO, 'linea', 'camara', 'otro'],
    'centro_experimental': [*LABORATORIO, 'parcela', 'invernadero', 'establo', 'otro'],
    'observatorios': ['sala', 'area', 'puesto', 'otro'],
}


def _unidad(slug, dependencia, administrador):
    return Unidad.objects.create(nombre=f'Unidad {slug}', slug=slug, dependencia=dependencia, descripcion='.',
                                 fecha_inicio=date(2026, 1, 1), administrador=administrador)


def _opciones_del_tipo(html, formulario):
    """Los valores del selector «tipo» de un formulario del panel, en su orden."""
    bloque = re.search(rf'data-agenda-operation-form="{formulario}".*?<select name="tipo">(.*?)</select>', html, re.S)
    return re.findall(r'<option value="([^"]+)"', bloque.group(1)) if bloque else []


class BaseCaptura(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.gestor = get_user_model().objects.create_user('gestor-captura-anexos', password='clave')
        identificar(cls.gestor, tipo_usuario='administrativo', carrera='')
        cls.lab = _unidad('lab-captura-anexos', 'laboratorios', cls.gestor)

    def setUp(self):
        self.client.force_login(self.gestor)

    def operar(self, unidad=None, **datos):
        return self.client.post(reverse('gestion_operacion_accion', args=[(unidad or self.lab).slug]), datos)

    def panel(self, unidad=None, **parametros):
        return self.client.get(reverse('gestion_unidad', args=[(unidad or self.lab).slug]), parametros)


class UnidadDelSyllabusTests(BaseCaptura):
    def test_el_tema_guarda_su_unidad_del_syllabus_y_se_ve_en_practicas(self):
        asignatura = Asignatura.objects.create(unidad=self.lab, codigo='CAP-ASIG', nombre='Diseño asistido')
        respuesta = self.operar(modulo='tema_asignatura', asignatura_id=str(asignatura.pk), orden='1',
                                unidad_tematica='Unidad 2. Modelado 3D', nombre='Piezas paramétricas')
        self.assertEqual(respuesta.status_code, 200, respuesta.content)
        tema = TemaAsignatura.objects.get(asignatura=asignatura)
        self.assertEqual(tema.unidad_tematica, 'Unidad 2. Modelado 3D')
        # Un formulario abierto antes de que existiera el campo no la borra.
        self.operar(modulo='tema_asignatura', registro_id=str(tema.pk), asignatura_id=str(asignatura.pk), orden='1',
                    nombre='Piezas con restricciones')
        tema.refresh_from_db()
        self.assertEqual((tema.nombre, tema.unidad_tematica), ('Piezas con restricciones', 'Unidad 2. Modelado 3D'))

        panel = self.panel(view='practicas')
        self.assertContains(panel, 'name="unidad_tematica"')
        self.assertContains(panel, '<small>Unidad 2. Modelado 3D</small>')
        self.assertContains(panel, 'data-field-unidad_tematica="Unidad 2. Modelado 3D"')
        # La planificación de una práctica nombra el tema con su unidad del syllabus.
        planificacion = PlanificacionPracticaForm(unidad=self.lab, actividades=CatalogoActividadReserva.objects.none())
        self.assertEqual(planificacion.fields['tema_asignatura'].label_from_instance(tema),
                         'Diseño asistido · Unidad 2. Modelado 3D · Piezas con restricciones')

        # Quien la vacía a propósito, la vacía; el tema sin unidad se nombra sin el hueco.
        self.operar(modulo='tema_asignatura', registro_id=str(tema.pk), asignatura_id=str(asignatura.pk), orden='1',
                    unidad_tematica='', nombre='Piezas con restricciones')
        tema.refresh_from_db()
        self.assertEqual(tema.unidad_tematica, '')
        self.assertEqual(planificacion.fields['tema_asignatura'].label_from_instance(tema),
                         'Diseño asistido · Piezas con restricciones')


class EspaciosTests(BaseCaptura):
    def test_cada_tipo_de_unidad_ofrece_sus_tipos_de_espacio(self):
        etiquetas = dict(EspacioReservable.TIPO_CHOICES)
        for dependencia, esperados in TIPOS_POR_DEPENDENCIA.items():
            with self.subTest(dependencia=dependencia):
                opciones = tipos_de_espacio(Unidad(dependencia=dependencia))
                self.assertEqual([clave for clave, _ in opciones], esperados)
                self.assertEqual(dict(opciones), {clave: etiquetas[clave] for clave in esperados})
        # El tipo que un espacio ya tiene se ofrece siempre, aunque no sea de su tipo de unidad.
        self.assertEqual([clave for clave, _ in tipos_de_espacio(Unidad(dependencia='observatorios'),
                                                                 conservar=('taller', ''))],
                         ['sala', 'area', 'puesto', 'taller', 'otro'])

    def test_el_panel_ofrece_los_tipos_de_la_unidad_y_guarda_la_superficie(self):
        planta = _unidad('planta-captura-anexos', 'plantas_piloto', self.gestor)
        EspacioReservable.objects.create(unidad=planta, codigo='CAP-PLA-INV', nombre='Invernadero heredado',
                                         tipo='invernadero')
        html = self.panel(planta, view='recursos', modo_recursos='espacios').content.decode()
        self.assertEqual(_opciones_del_tipo(html, 'espacio'),
                         [*LABORATORIO, 'linea', 'camara', 'invernadero', 'otro'])
        self.assertIn('name="superficie_m2"', html)

        respuesta = self.operar(planta, modulo='recursos', entidad='espacio', codigo='CAP-PLA-LIN',
                                nombre='Línea de quesos', tipo='linea', politica_reserva='general', capacidad='4',
                                superficie_m2='48.5', activo='on')
        self.assertEqual(respuesta.status_code, 200, respuesta.content)
        linea = EspacioReservable.objects.get(codigo='CAP-PLA-LIN')
        self.assertEqual((linea.tipo, linea.superficie_m2), ('linea', Decimal('48.50')))
        # El botón de editar lleva la superficie sin formato local, para el campo numérico.
        self.assertContains(self.panel(planta, view='recursos', modo_recursos='espacios'),
                            'data-field-superficie_m2="48.50"')

        # Un formulario sin el campo conserva tipo y superficie; una superficie negativa se rechaza; vaciarla la borra.
        self.operar(planta, modulo='recursos', entidad='espacio', registro_id=str(linea.pk), capacidad='5', activo='on')
        linea.refresh_from_db()
        self.assertEqual((linea.tipo, linea.superficie_m2, linea.capacidad), ('linea', Decimal('48.50'), 5))
        rechazo = self.operar(planta, modulo='recursos', entidad='espacio', registro_id=str(linea.pk), capacidad='5',
                              superficie_m2='-3', activo='on')
        self.assertEqual(rechazo.status_code, 400)
        self.operar(planta, modulo='recursos', entidad='espacio', registro_id=str(linea.pk), capacidad='5',
                    superficie_m2='', activo='on')
        linea.refresh_from_db()
        self.assertIsNone(linea.superficie_m2)

    def test_la_pagina_del_area_edita_tipo_y_superficie_sin_perder_el_tipo_que_tiene(self):
        parcela = EspacioReservable.objects.create(unidad=self.lab, codigo='CAP-LAB-PARC', nombre='Huerto didáctico',
                                                   tipo='parcela', capacidad=10)
        url = reverse('editar_area', args=[self.lab.slug, parcela.codigo])
        formulario = self.client.get(url, {'seccion': 'datos'})
        opciones = [clave for clave, _ in formulario.context['form_datos'].fields['tipo'].choices]
        self.assertEqual(opciones, [*LABORATORIO, 'parcela', 'otro'])
        datos = {'seccion': 'datos', 'area-nombre': 'Huerto didáctico', 'area-capacidad': '10',
                 'area-superficie_m2': '120.75'}
        # Sin el tipo en el formulario (abierto antes del cambio), el área conserva el suyo.
        self.assertEqual(self.client.post(url, datos, HTTP_X_REQUESTED_WITH='fetch').json(), {'ok': True})
        parcela.refresh_from_db()
        self.assertEqual((parcela.tipo, parcela.superficie_m2), ('parcela', Decimal('120.75')))
        self.client.post(url, {**datos, 'area-tipo': 'taller'}, HTTP_X_REQUESTED_WITH='fetch')
        parcela.refresh_from_db()
        self.assertEqual(parcela.tipo, 'taller')
        # Un tipo de otra clase de unidad no se acepta, y la superficie no es negativa.
        rechazo = self.client.post(url, {**datos, 'area-tipo': 'establo', 'area-superficie_m2': '-1'})
        self.assertEqual(set(rechazo.context['form_datos'].errors), {'tipo', 'superficie_m2'})
        self.assertContains(self.client.get(reverse('area_unidad', args=[self.lab.slug, parcela.codigo])),
                            '<dt>Superficie</dt>')

    def test_una_area_nueva_nace_con_un_tipo_de_su_unidad_y_su_superficie(self):
        centro = _unidad('centro-captura-anexos', 'centro_experimental', self.gestor)
        url = reverse('nueva_area', args=[centro.slug])
        formulario = self.client.get(url)
        self.assertEqual([clave for clave, _ in formulario.context['formulario'].fields['tipo'].choices],
                         TIPOS_POR_DEPENDENCIA['centro_experimental'])
        respuesta = self.client.post(url, {'nombre': 'Invernadero de hortalizas', 'tipo': 'invernadero',
                                           'capacidad': 8, 'superficie_m2': '250'}, HTTP_X_REQUESTED_WITH='fetch')
        self.assertTrue(respuesta.json()['ok'])
        area = EspacioReservable.objects.get(unidad=centro, nombre='Invernadero de hortalizas')
        self.assertEqual((area.tipo, area.superficie_m2), ('invernadero', Decimal('250')))
        rechazo = self.client.post(url, {'nombre': 'Línea ajena', 'tipo': 'linea', 'capacidad': 2})
        self.assertIn('tipo', rechazo.context['formulario'].errors)


class SoftwareEInsumosTests(BaseCaptura):
    def test_el_software_ofrece_simulador_en_el_panel_y_en_la_pagina(self):
        panel = self.panel(view='recursos', modo_recursos='software')
        self.assertContains(panel, '<option value="simulador">Simulador</option>')
        respuesta = self.operar(modulo='recursos', entidad='software', nombre='Simulador de soldadura',
                                tipo_recurso='simulador', tipo_acceso='instalacion', licencias_totales='2',
                                licencias_disponibles='2', activo='on')
        self.assertEqual(respuesta.status_code, 200, respuesta.content)
        simulador = SoftwareDisponible.objects.get(unidad=self.lab, nombre='Simulador de soldadura')
        self.assertEqual(simulador.tipo_recurso, 'simulador')
        cuadro = self.client.get(reverse('editar_registro', args=[self.lab.slug, 'software', simulador.pk]))
        self.assertIn(('simulador', 'Simulador'), cuadro.context['formulario'].fields['tipo_recurso'].choices)
        self.assertEqual(cuadro.context['formulario'].initial['tipo_recurso'], 'simulador')

    def test_agroquimicos_y_veterinarios_se_registran_y_se_tratan_como_sustancias(self):
        centro = _unidad('centro-insumos-anexos', 'centro_experimental', self.gestor)
        panel = self.panel(centro, view='recursos', modo_recursos='insumos')
        self.assertContains(panel, '<option value="agroquimico">Agroquímico</option>')
        self.assertContains(panel, '<option value="veterinario">Medicamento o insumo veterinario</option>')
        for codigo, nombre, clase in (('CAP-AGRO-UREA', 'Urea granulada', 'agroquimico'),
                                      ('CAP-VET-AFTOSA', 'Vacuna contra la fiebre aftosa', 'veterinario')):
            respuesta = self.operar(centro, modulo='consumible', codigo=codigo, nombre=nombre, clasificacion=clase,
                                    familia='Sanidad y nutrición', unidad_medida='unidad', stock_total='0',
                                    minimo='0', activo='on')
            self.assertEqual(respuesta.status_code, 200, respuesta.content)
            self.assertEqual(Consumible.objects.get(codigo=codigo).clasificacion, clase)
        Consumible.objects.create(unidad=centro, codigo='CAP-EMP-SACO', nombre='Sacos de yute', clasificacion='empaque')
        # El protocolo de seguridad los propone como sustancias, igual que a un reactivo; un empaque, no.
        self.assertEqual(set(CLASES_DE_SUSTANCIAS), {'reactivo', 'agroquimico', 'veterinario'})
        riesgos = {riesgo['actividad']: riesgo for riesgo in
                   propuestas_de(SimpleNamespace(unidad=centro))['riesgos_protocolo']}
        origen = riesgos['Sustancias químicas']['origen']
        self.assertIn('Urea granulada', origen)
        self.assertIn('Vacuna contra la fiebre aftosa', origen)
        self.assertNotIn('Sacos de yute', origen)

    def test_el_panel_guarda_la_sustancia_controlada_y_su_autorizacion(self):
        panel = self.panel(view='recursos', modo_recursos='insumos')
        self.assertContains(panel, '<select name="sustancia_controlada">')
        self.assertContains(panel, 'name="autorizacion_control" maxlength="160"')
        ficha = dict(modulo='consumible', codigo='CAP-REA-CTRL', nombre='Acetona de prueba', clasificacion='reactivo',
                     unidad_medida='l', minimo='0', activo='on')
        respuesta = self.operar(**ficha, sustancia_controlada='true', autorizacion_control=' Licencia de prueba 001 ')
        self.assertEqual(respuesta.status_code, 200, respuesta.content)
        reactivo = Consumible.objects.get(codigo='CAP-REA-CTRL')
        self.assertEqual((reactivo.sustancia_controlada, reactivo.autorizacion_control),
                         (True, 'Licencia de prueba 001'))
        # El botón de editar lleva los dos datos de vuelta al formulario.
        panel = self.panel(view='recursos', modo_recursos='inventario')
        self.assertContains(panel, 'data-field-sustancia_controlada="true"')
        self.assertContains(panel, 'data-field-autorizacion_control="Licencia de prueba 001"')
        ficha['registro_id'] = str(reactivo.pk)
        # Un formulario abierto antes de que existieran los campos no borra la marca ni la autorización.
        self.operar(**ficha)
        reactivo.refresh_from_db()
        self.assertEqual((reactivo.sustancia_controlada, reactivo.autorizacion_control),
                         (True, 'Licencia de prueba 001'))
        # Controlada sin autorización se guarda: no se bloquea a la unidad; el anexo lo dirá.
        respuesta = self.operar(**ficha, sustancia_controlada='true', autorizacion_control='')
        self.assertEqual(respuesta.status_code, 200, respuesta.content)
        reactivo.refresh_from_db()
        self.assertEqual((reactivo.sustancia_controlada, reactivo.autorizacion_control), (True, ''))
        self.operar(**ficha, sustancia_controlada='false', autorizacion_control='')
        reactivo.refresh_from_db()
        self.assertFalse(reactivo.sustancia_controlada)

    def test_la_pagina_de_insumos_edita_la_sustancia_controlada_y_su_autorizacion(self):
        reactivo = Consumible.objects.create(unidad=self.lab, codigo='CAP-REA-PAG', nombre='Éter de prueba',
                                             clasificacion='reactivo', unidad_medida='l')
        url = reverse('editar_registro', args=[self.lab.slug, 'insumo', reactivo.pk])
        campos = self.client.get(url).context['formulario'].fields
        self.assertEqual(campos['sustancia_controlada'].label, 'Sustancia sujeta a control')
        self.assertEqual(campos['autorizacion_control'].max_length, 160)
        datos = {'registro-nombre': reactivo.nombre, 'registro-codigo': reactivo.codigo,
                 'registro-clasificacion': 'reactivo', 'registro-cantidad_por_presentacion': '1',
                 'registro-unidad_medida': 'l', 'registro-activo': 'on', 'registro-sustancia_controlada': 'on',
                 'registro-autorizacion_control': 'Licencia de prueba 002'}
        self.assertEqual(self.client.post(url, datos, HTTP_X_REQUESTED_WITH='fetch').json(), {'ok': True})
        reactivo.refresh_from_db()
        self.assertEqual((reactivo.sustancia_controlada, reactivo.autorizacion_control),
                         (True, 'Licencia de prueba 002'))
