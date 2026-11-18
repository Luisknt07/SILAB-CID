"""Rutas de captura de seguridad, desechos, investigación, transferencia y servicios, su respaldo y los documentos principales.

Es la prueba de cargue de cada documento: con la cuenta de la unidad (administra y coordina, no es
superusuario) se registra por HTTP lo que enviaría cada pantalla, se lleva el registro hasta el estado
en que el documento lo cuenta y se comprueba que sale en su tabla: en los registros del anexo, en su
PDF con los datos al día o en la consulta del Centro de reportes.

Lo que no es de estos documentos (el equipo, la sesión reservada, sus participantes) se prepara con el
modelo: su ruta de captura se prueba con los anexos de equipamiento y de uso.
"""
import json
from datetime import time, timedelta
from decimal import Decimal
from html.parser import HTMLParser
from io import BytesIO
from tempfile import TemporaryDirectory

from django.contrib.auth import get_user_model
from django.contrib.messages import get_messages
from django.core.files.uploadedfile import SimpleUploadedFile
from django.http import QueryDict
from django.test import TestCase, override_settings
from django.urls import reverse
from django.utils import timezone
from pypdf import PdfReader

from apps.directorio_unidades.models.core import Unidad
from apps.documentos.models.constancias import ConstanciaDocumento
from apps.documentos.models.expediente import DocumentoExpediente
from apps.documentos.models.medicion import EvidenciaGestionUnidad
from apps.documentos.presentation.anexos_evidencia import constructor_de, contexto_del_anexo
from apps.documentos.presentation.aprobacion_en_linea import estado_constancia
from apps.documentos.presentation.conformidad_permanente import aprobacion_vigente
from apps.documentos.presentation.expediente import (
    anexos_del, construir_expediente, cortes_del_anio, periodo_vigente, tramo_del_documento,
)
from apps.documentos.presentation.expediente_catalogo import asegurar_catalogo
from apps.formacion.models.practicas import RegistroAuditoriaUnidad
from apps.gestion_unidades.models.espacios import EspacioReservable, ResponsableUnidad
from apps.recursos.models.desechos import RegistroDesecho
from apps.recursos.models.equipos import EquiposServicios
from apps.recursos.models.mantenimiento import IncidenciaEquipo
from apps.recursos.models.unidades import UnidadEquipo
from apps.reservas.models.reservas import RegistroParticipanteReserva, Reserva
from apps.reservas.models.seguridad import HabilitacionAcceso, RegistroIngreso, RequisitoAcceso
from tests.integration.test_seguimiento_gobernanza import designar
from tests.integration.utiles import abrir_entrega, identificar, pdf_legible_prueba

CONDICIONES_COMUNES = ('infraestructura', 'equipos', 'emergencias', 'proteccion', 'almacenamiento', 'limpieza',
                       'desechos')


def _texto_del_pdf(contenido):
    """El texto del PDF en una sola línea, para buscar datos que la celda parte en renglones."""
    return ' '.join(' '.join(pagina.extract_text() or '' for pagina in PdfReader(BytesIO(contenido)).pages).split())


def _plano(valor):
    """El texto de una celda del anexo, sea texto, par o enlace."""
    if isinstance(valor, (list, tuple)):
        return ' '.join(_plano(parte) for parte in valor)
    partes = [getattr(valor, nombre, None) for nombre in ('arriba', 'abajo', 'texto', 'rotulo', 'url')]
    partes = [_plano(parte) for parte in partes if parte not in (None, '')]
    return ' '.join(partes) if partes else str(valor)


@override_settings(MEDICION_METAS_HABILITADA=True, MEDICION_SOLO_DEMO=False)
class BaseDeRutas(TestCase):
    """Un laboratorio ficticio y su cuenta de unidad, como las `admin.<unidad>` de la plataforma."""

    @classmethod
    def setUpTestData(cls):
        asegurar_catalogo()
        usuarios = get_user_model().objects
        cls.cuenta = usuarios.create_user('admin.laboratorio-rutas-h4', password='clave-segura',
                                          first_name='Alba', last_name='Administradora')
        cls.estudiante = usuarios.create_user('estudiante.rutas-h4', password='clave-segura',
                                              first_name='Elías', last_name='Estudiante')
        identificar(cls.cuenta, tipo_usuario='administrativo', carrera='')
        identificar(cls.estudiante, tipo_usuario='estudiante')
        cls.unidad = Unidad.objects.create(
            nombre='Laboratorio ficticio de rutas H4', slug='laboratorio-rutas-h4', dependencia='laboratorios',
            descripcion='Unidad ficticia para la prueba de cargue.', fecha_inicio=timezone.localdate().replace(
                year=timezone.localdate().year - 1, month=1, day=1), administrador=cls.cuenta, activo=True)
        # La cuenta de la unidad es administradora y, además, coordinación.
        ResponsableUnidad.objects.create(unidad=cls.unidad, usuario=cls.cuenta, nombre='Alba Administradora',
                                         rol='coordinacion')
        cls.espacio = EspacioReservable.objects.create(unidad=cls.unidad, codigo='H4-AREA', nombre='Área de ensayos',
                                                       tipo='area', capacidad=10)
        cls.equipo = UnidadEquipo.objects.create(
            codigo_unidad='H4-EQ-01', laboratorio=cls.unidad,
            equipo=EquiposServicios.objects.create(nombre='Campana de extracción ficticia', codigo='H4-MODELO-01'))

    def setUp(self):
        carpeta = TemporaryDirectory(prefix='rutas-h4-', ignore_cleanup_errors=True)
        self.addCleanup(carpeta.cleanup)
        medios = override_settings(MEDIA_ROOT=carpeta.name)
        medios.enable()
        self.addCleanup(medios.disable)
        self.hoy = timezone.localdate()
        self.anio = self.hoy.year
        self.corte = periodo_vigente(cortes_del_anio(self.anio), self.hoy)
        self.client.force_login(self.cuenta)

    # ---- ayudas -----------------------------------------------------------------------------------

    def operar(self, **datos):
        """Lo que envía un formulario del panel de gestión de la unidad."""
        return self.client.post(reverse('gestion_operacion_accion', args=[self.unidad.slug]), datos)

    def respaldo(self, nombre):
        return SimpleUploadedFile(f'{nombre}.pdf', pdf_legible_prueba(
            f'Respaldo ficticio {nombre}: acta de prueba sin validez institucional.'), content_type='application/pdf')

    def evidencia(self, tipo, codigo, titulo, descripcion, **campos):
        """Guarda una evidencia de gestión desde su pantalla, verificada y con su respaldo en PDF."""
        datos = dict(anio=self.anio, corte=self.corte, tipo=tipo, codigo=codigo, fecha=self.hoy.isoformat(),
                     titulo=titulo, descripcion=descripcion, responsable=self.cuenta.pk, verificar='on',
                     archivo=self.respaldo(codigo))
        datos.update(campos)
        respuesta = self.client.post(reverse('fuentes_metas_unidad', args=[self.unidad.slug]), datos)
        self.assertEqual(respuesta.status_code, 302, respuesta.context and respuesta.context['form'].errors)
        evidencia = EvidenciaGestionUnidad.objects.get(unidad=self.unidad, codigo=codigo)
        self.assertEqual((evidencia.tipo, evidencia.estado, evidencia.validado_por), (tipo, 'validado', self.cuenta))
        return evidencia

    def anexo(self, codigo):
        documentos = construir_expediente(self.unidad, self.anio, hoy=self.hoy)
        informe = next(d for d in documentos if d.exigido.codigo == 'INFORME-SEMESTRAL' and d.corte == self.corte)
        return informe, next(a for a in anexos_del(informe, incluir_no_aplica=True) if a.exigido.codigo == codigo)

    def tablas(self, codigo):
        """Las tablas del anexo con los registros al día: {título: filas en texto}."""
        _informe, anexo = self.anexo(codigo)
        inicio, fin = tramo_del_documento(anexo)
        registros = constructor_de(codigo)(contexto_del_anexo(anexo, inicio, fin))
        return {registro.titulo: [[_plano(celda) for celda in fila] for fila in registro.filas]
                for registro in registros}

    def pdf_del_anexo(self, codigo):
        """El PDF del anexo con los datos al día, como lo abre la unidad desde su expediente."""
        informe, anexo = self.anexo(codigo)
        respuesta = self.client.get(reverse('gestion_expediente_unidad', args=[self.unidad.slug]), dict(
            anio=self.anio, corte=self.corte, gestionar=informe.pk, anexo=anexo.pk, borrador='1'))
        self.assertEqual(respuesta.status_code, 200)
        self.assertEqual(respuesta['Content-Type'], 'application/pdf')
        return _texto_del_pdf(respuesta.content)

    def consulta(self, categoria, formato=''):
        """Una consulta del Centro de reportes de la unidad para el período en curso."""
        inicio, fin = cortes_del_anio(self.anio)[self.corte]
        ruta = reverse('gestion_reporte_unidad_pdf' if formato == 'pdf' else 'gestion_reporte_unidad',
                       args=[self.unidad.slug])
        respuesta = self.client.get(ruta, dict(categoria_reporte=categoria, desde=inicio.isoformat(),
                                               hasta=fin.isoformat()))
        self.assertEqual(respuesta.status_code, 200)
        return respuesta

    def sesion(self, **datos):
        """Una sesión ya aprobada de hoy, con el estudiante identificado: la reserva se prueba con el anexo de uso."""
        base = dict(laboratorio=self.unidad, usuario=self.estudiante, fecha=self.hoy, hora_inicio=time(8),
                    hora_fin=time(10), estado='confirmada', titulo_solicitud='Sesión ficticia H4',
                    numero_participantes=1)
        reserva = Reserva.objects.create(**(base | datos))
        reserva.espacios_solicitados.add(self.espacio)
        RegistroParticipanteReserva.objects.create(
            reserva=reserva, usuario=self.estudiante, rol='solicitante', nombre='Elías Estudiante',
            tipo_usuario='estudiante')
        reserva.refresh_from_db()
        return reserva


class SeguridadYCondicionesDeOperacionTests(BaseDeRutas):
    """Anexo 8 · Reportes de seguridad y condiciones de operación."""

    def requisito(self, codigo='H4-INDUCCION', **datos):
        base = dict(modulo='requisito_acceso', codigo=codigo, nombre='Inducción de seguridad ficticia',
                    tipo='induccion', momento='reservar', vigencia_dias='180', orden='1', consumible_id='',
                    cantidad_por_persona='1', descripcion='Riesgos del área y salidas de emergencia.',
                    aplica_a=['estudiante'], obligatorio='1')
        respuesta = self.operar(**(base | datos))
        self.assertEqual(respuesta.status_code, 200, respuesta.content)
        return RequisitoAcceso.objects.get(unidad=self.unidad, codigo=codigo)

    def habilitar(self, requisito):
        respuesta = self.operar(modulo='habilitacion_acceso', persona=self.estudiante.username,
                                requisito_id=requisito.pk, fecha=self.hoy.isoformat(), vence='', origen='documento',
                                documento='CERT-H4-0001', observaciones='Certificado ficticio presentado.')
        self.assertEqual(respuesta.status_code, 200, respuesta.content)
        return HabilitacionAcceso.objects.get(requisito=requisito, usuario=self.estudiante)

    def test_un_requisito_de_acceso_se_crea_en_el_panel_y_sale_en_la_tabla_8_1(self):
        panel = self.client.get(reverse('gestion_unidad', args=[self.unidad.slug]), {'view': 'seguridad'})
        self.assertContains(panel, 'data-agenda-operation-open="requisito_acceso"')
        self.assertContains(panel, 'data-agenda-operation-form="requisito_acceso"')
        requisito = self.requisito()
        self.assertEqual((requisito.tipo, requisito.aplica_a, requisito.obligatorio, requisito.vigencia_dias,
                          requisito.activo), ('induccion', ['estudiante'], True, 180, True))
        fila = self.tablas('INDUCCION-SEGURIDAD')['Requisitos de acceso'][0]
        self.assertIn('H4-INDUCCION', fila[0])
        self.assertEqual(fila[1:6], ['Inducción', 'Estudiantes', 'Al reservar y al ingresar', 'Sí', '180 días'])
        self.assertIn('H4-INDUCCION', self.pdf_del_anexo('INDUCCION-SEGURIDAD'))

    def test_una_habilitacion_se_registra_a_una_persona_y_sale_en_la_tabla_8_2(self):
        habilitacion = self.habilitar(self.requisito())
        self.assertEqual((habilitacion.origen, habilitacion.otorgada_por, habilitacion.vence),
                         ('documento', self.cuenta, self.hoy + timedelta(days=180)))
        fila = self.tablas('INDUCCION-SEGURIDAD')['Inducciones y habilitaciones del período'][0]
        self.assertEqual((fila[1], fila[5], fila[6], fila[7]),
                         ('Elías Estudiante', 'Alba Administradora', 'CERT-H4-0001', 'Vigente'))
        self.assertIn('CERT-H4-0001', self.pdf_del_anexo('INDUCCION-SEGURIDAD'))

    def test_una_inspeccion_verificada_con_su_respaldo_sale_en_las_tablas_8_3_y_8_4(self):
        inspeccion = self.evidencia(
            'INSPECCION', 'INS-H4-001', 'Inspección mensual ficticia', 'Chequeo completo sin novedades.',
            area='Área de ensayos', condiciones_revisadas=list(CONDICIONES_COMUNES), estado_condiciones='seguro',
            sin_hallazgos='on', estado_accion='no_requiere')
        self.assertTrue(inspeccion.recurso.hash_sha256)
        tablas = self.tablas('INDUCCION-SEGURIDAD')
        fila = tablas['Inspecciones de condiciones'][0]
        self.assertEqual((fila[1], fila[3], fila[4], fila[6], fila[7]),
                         ('Área de ensayos', 'Sin hallazgos', 'Seguro', 'No requiere', 'Alba Administradora'))
        self.assertIn('7 de 7', fila[2])
        self.assertIn('Evidencia verificada', fila[8])
        # La cobertura del mes en curso cuenta la inspección registrada y verificada.
        del_mes = [f for f in tablas['Cobertura mensual de inspecciones'] if f[2] == '1']
        self.assertEqual(len(del_mes), 1, tablas['Cobertura mensual de inspecciones'])
        self.assertEqual(del_mes[0][3:], ['1', 'Cubierto'])
        self.assertIn('Área de ensayos', self.pdf_del_anexo('INDUCCION-SEGURIDAD'))

    def test_el_control_de_ingreso_de_una_sesion_sale_en_la_tabla_8_5(self):
        self.habilitar(self.requisito())
        reserva = self.sesion()
        panel = self.client.get(reverse('gestion_unidad', args=[self.unidad.slug]), {'view': 'seguridad'})
        self.assertContains(panel, f'data-field-reserva_id="{reserva.pk}"')
        persona = reserva.registros_participantes.get()
        respuesta = self.operar(modulo='ingreso', reserva_id=reserva.pk, personas_ids=str(persona.pk), **{
            f'persona_{persona.pk}_ingresa': '1', f'persona_{persona.pk}_proteccion': '1',
            f'persona_{persona.pk}_restricciones': '1', f'persona_{persona.pk}_hora': '08:05',
            f'persona_{persona.pk}_salida': '09:55', f'persona_{persona.pk}_motivo': ''})
        self.assertEqual(respuesta.status_code, 200, respuesta.content)
        ingreso = RegistroIngreso.objects.get(reserva=reserva)
        self.assertEqual((ingreso.ingresa, ingreso.habilitaciones_vigentes, ingreso.registrado_por),
                         (True, True, self.cuenta))
        self.assertEqual((ingreso.hora_ingreso, ingreso.hora_salida), (time(8, 5), time(9, 55)))
        fila = self.tablas('INDUCCION-SEGURIDAD')['Control de ingresos'][0]
        self.assertIn('ingreso 08:05 · salida 09:55', fila[0])
        self.assertEqual(fila[1], reserva.codigo_reserva)
        self.assertIn('Elías Estudiante', fila[2])
        self.assertEqual(fila[3:7], ['Sí', 'Sí', 'Sí', 'Sí'])
        self.assertIn(reserva.codigo_reserva, self.pdf_del_anexo('INDUCCION-SEGURIDAD'))

    def test_un_incidente_de_seguridad_con_su_solucion_sale_en_la_tabla_8_6(self):
        panel = self.client.get(reverse('gestion_unidad', args=[self.unidad.slug]), {'view': 'mantenimiento'})
        self.assertContains(panel, 'data-agenda-operation-form="incidencia"')
        datos = dict(modulo='incidencia', equipo_id=self.equipo.pk, titulo='Salpicadura ficticia de reactivo',
                     tipo='seguridad', prioridad='alta', estado='abierta',
                     descripcion='Salpicadura menor durante un ensayo; sin lesiones.', asignada_a='', solucion='')
        respuesta = self.operar(**datos)
        self.assertEqual(respuesta.status_code, 200, respuesta.content)
        incidente = IncidenciaEquipo.objects.get(unidad=self.unidad)
        respuesta = self.operar(**(datos | dict(registro_id=incidente.pk, estado='resuelta',
                                                solucion='Se limpió el área y se repuso la pantalla de la campana.')))
        self.assertEqual(respuesta.status_code, 200, respuesta.content)
        incidente.refresh_from_db()
        self.assertEqual((incidente.tipo, incidente.estado, incidente.reportada_por),
                         ('seguridad', 'resuelta', self.cuenta))
        fila = self.tablas('INDUCCION-SEGURIDAD')['Incidentes de seguridad'][0]
        self.assertIn('H4-EQ-01', fila[1])
        self.assertIn('Salpicadura ficticia de reactivo', fila[2])
        self.assertEqual((fila[3], fila[6], fila[7]), ('Alta', 'Resuelta', 'Alba Administradora'))
        self.assertIn('Se limpió el área', fila[5])
        self.assertIn('Salpicadura ficticia', self.pdf_del_anexo('INDUCCION-SEGURIDAD'))

    def test_un_incidente_sin_equipo_y_de_otro_dia_sale_en_la_8_6_con_su_lugar_y_su_fecha(self):
        panel = self.client.get(reverse('gestion_unidad', args=[self.unidad.slug]), {'view': 'mantenimiento'})
        self.assertContains(panel, 'name="fecha_hecho"')
        self.assertContains(panel, 'name="espacio_id"')
        # El hecho, dos días antes si el período lo admite; si el período empieza hoy, hoy mismo.
        _informe, anexo = self.anexo('INDUCCION-SEGURIDAD')
        inicio, _fin = tramo_del_documento(anexo)
        dia = self.hoy - timedelta(days=2) if (self.hoy - inicio).days >= 2 else self.hoy
        base = dict(modulo='incidencia', equipo_id='', tipo='seguridad', prioridad='media', estado='abierta',
                    asignada_a='', solucion='')
        respuesta = self.operar(**base, titulo='Caída ficticia en el pasillo', espacio_id=self.espacio.pk,
                                fecha_hecho=f'{dia.isoformat()}T07:30',
                                descripcion='Resbalón sin lesiones junto a la puerta.')
        self.assertEqual(respuesta.status_code, 200, respuesta.content)
        respuesta = self.operar(**base, titulo='Derrame ficticio de agua', espacio_id='', fecha_hecho='',
                                descripcion='Derrame menor en la unidad; se secó al momento.')
        self.assertEqual(respuesta.status_code, 200, respuesta.content)
        caida = IncidenciaEquipo.objects.get(titulo='Caída ficticia en el pasillo')
        self.assertEqual((caida.equipo, caida.espacio, caida.unidad, caida.reportada_por),
                         (None, self.espacio, self.unidad, self.cuenta))
        self.assertEqual(timezone.localtime(caida.fecha_hecho).date(), dia)
        self.assertEqual(timezone.localtime(caida.fecha_reporte).date(), self.hoy)
        tabla = self.tablas('INDUCCION-SEGURIDAD')['Incidentes de seguridad']
        filas = {titulo: fila for fila in tabla for titulo in ('Caída', 'Derrame') if titulo in fila[2]}
        self.assertEqual(set(filas), {'Caída', 'Derrame'}, tabla)
        self.assertIn(dia.strftime('%d/%m/%Y'), filas['Caída'][0])
        if dia != self.hoy:
            self.assertIn(f'reportado el {self.hoy:%d/%m}', filas['Caída'][0])
        self.assertIn(self.espacio.nombre, filas['Caída'][1])
        self.assertEqual(filas['Derrame'][1], 'Unidad')
        self.assertNotIn('reportado el', filas['Derrame'][0])
        # Una incidencia técnica sigue exigiendo el equipo, y la fecha del hecho no puede ser futura.
        respuesta = self.operar(**(base | dict(tipo='falla')), titulo='Falla ficticia sin equipo',
                                descripcion='No enciende.')
        self.assertNotEqual(respuesta.status_code, 200)
        manana = self.hoy + timedelta(days=1)
        respuesta = self.operar(**base, titulo='Incidente ficticio futuro', fecha_hecho=f'{manana.isoformat()}T09:00',
                                descripcion='No debería guardarse.')
        self.assertNotEqual(respuesta.status_code, 200)
        self.assertFalse(IncidenciaEquipo.objects.filter(titulo__in=('Falla ficticia sin equipo',
                                                                     'Incidente ficticio futuro')).exists())


class GestionDeDesechosTests(BaseDeRutas):
    """Anexo 9 · Registros de gestión de desechos peligrosos y especiales."""

    def setUp(self):
        super().setUp()
        self.ruta = reverse('entregas_desechos_unidad', args=[self.unidad.slug])

    def generado(self, **campos):
        datos = {'accion': 'generar', 'desecho-fecha_generacion': self.hoy.isoformat(),
                 'desecho-nombre': 'Solventes usados ficticios', 'desecho-clase': 'peligroso',
                 'desecho-clave_listado': 'Q-FICTICIA-01', 'desecho-estado_fisico': 'liquido',
                 'desecho-origen': 'Limpieza de material de vidrio', 'desecho-cantidad': '4.5',
                 'desecho-unidad_medida': 'l', 'desecho-envase': 'Bidón de 5 L', 'desecho-etiquetado': 'on',
                 'desecho-almacenamiento': 'Bodega de reactivos', 'desecho-etapa': 'almacenado',
                 'desecho-responsable': self.cuenta.pk, 'desecho-observaciones': ''}
        datos.update({f'desecho-{clave}': valor for clave, valor in campos.items()})
        return self.client.post(self.ruta, datos)

    def test_el_centro_de_reportes_lleva_a_registrar_el_desecho_aunque_no_haya_ninguno(self):
        pagina = self.consulta('desechos')
        self.assertContains(pagina, 'Registrar desecho generado')
        self.assertContains(pagina, self.ruta + '#generacion')
        pantalla = self.client.get(self.ruta)
        self.assertContains(pantalla, '1. Registrar un desecho generado')
        self.assertContains(pantalla, 'name="desecho-cantidad"')
        self.assertContains(pantalla, 'Registra primero el desecho generado, en el paso 1.')
        # Viene con lo habitual puesto: hoy, quien administra la unidad y «almacenado».
        formulario = pantalla.context['form_generacion']
        self.assertEqual((formulario['fecha_generacion'].value(), formulario['responsable'].value(),
                          formulario['etapa'].value()), (self.hoy, self.cuenta.pk, 'almacenado'))
        self.assertEqual([clave for clave, _etiqueta in formulario.fields['etapa'].choices],
                         ['almacenado', 'tratado'])

    def test_un_desecho_generado_se_registra_desde_la_unidad_y_sale_en_las_tablas_9_1_y_9_3(self):
        respuesta = self.generado()
        self.assertRedirects(respuesta, self.ruta, fetch_redirect_response=False)
        desecho = RegistroDesecho.objects.get(unidad=self.unidad)
        self.assertEqual((desecho.nombre, desecho.cantidad, desecho.unidad_medida, desecho.etapa, desecho.etiquetado,
                          desecho.responsable, desecho.registrado_por),
                         ('Solventes usados ficticios', Decimal('4.500'), 'l', 'almacenado', True, self.cuenta,
                          self.cuenta))
        rastro = RegistroAuditoriaUnidad.objects.get(unidad=self.unidad, entidad=RegistroDesecho._meta.label,
                                                     objeto_id=str(desecho.pk), accion='crear')
        self.assertEqual((rastro.usuario, rastro.datos_nuevos['etapa'], rastro.datos_nuevos['cantidad']),
                         (self.cuenta, 'almacenado', '4.500'))
        self.assertContains(self.client.get(self.ruta), 'Desecho registrado: Solventes usados ficticios.')

        tablas = self.tablas('DESECHOS')
        generacion = tablas['Generación y almacenamiento'][0]
        self.assertIn('Solventes usados ficticios', generacion[1])
        self.assertIn('Q-FICTICIA-01', generacion[1])
        self.assertEqual((generacion[3], generacion[4], generacion[6], generacion[7], generacion[8]),
                         ('Limpieza de material de vidrio', '4,5 L', 'Bodega de reactivos', 'Almacenado',
                          'Alba Administradora'))
        almacenado = tablas['Almacenado al corte'][0]
        self.assertIn('Solventes usados ficticios', almacenado[0])
        self.assertEqual((almacenado[1], almacenado[4]), ('4,5 L', 'Bodega de reactivos'))
        self.assertEqual(tablas['Entregas al gestor autorizado'], [])
        self.assertIn('Q-FICTICIA-01', self.pdf_del_anexo('DESECHOS'))
        self.assertContains(self.consulta('desechos'), 'Solventes usados ficticios')

    def test_el_ciclo_generacion_almacenamiento_y_entrega_al_gestor_con_su_manifiesto(self):
        self.generado()
        desecho = RegistroDesecho.objects.get(unidad=self.unidad)
        pantalla = self.client.get(self.ruta)
        self.assertEqual(list(pantalla.context['form'].fields['desechos'].queryset), [desecho])
        respuesta = self.client.post(self.ruta, {
            'desechos': [desecho.pk], 'fecha_entrega': self.hoy.isoformat(),
            'gestor_autorizado': 'Gestor Ficticio S.A.', 'licencia_gestor': 'LIC-FICTICIA-001',
            'manifiesto': 'MAN-H4-0001', 'responsable': self.cuenta.pk, 'documento': self.respaldo('MAN-H4-0001')})
        self.assertRedirects(respuesta, self.ruta)
        desecho.refresh_from_db()
        self.assertEqual((desecho.etapa, desecho.manifiesto, bool(desecho.documento)),
                         ('entregado', 'MAN-H4-0001', True))
        tablas = self.tablas('DESECHOS')
        self.assertEqual(tablas['Generación y almacenamiento'][0][7], 'Entregado')
        entrega = tablas['Entregas al gestor autorizado'][0]
        self.assertIn('Gestor Ficticio S.A.', entrega[3])
        self.assertIn('LIC-FICTICIA-001', entrega[3])
        self.assertEqual((entrega[2], entrega[4]), ('4,5 L', 'MAN-H4-0001'))
        self.assertIn(reverse('manifiesto_desecho_unidad', args=[self.unidad.slug, desecho.pk]), entrega[5])
        self.assertEqual(tablas['Almacenado al corte'], [])
        self.assertIn('MAN-H4-0001', self.pdf_del_anexo('DESECHOS'))
        manifiesto = self.client.get(reverse('manifiesto_desecho_unidad', args=[self.unidad.slug, desecho.pk]))
        self.assertEqual(manifiesto.status_code, 200)
        self.assertTrue(b''.join(manifiesto.streaming_content).startswith(b'%PDF'))

    def test_el_desecho_se_corrige_mientras_sigue_en_la_unidad_y_puede_quedar_como_tratado(self):
        self.generado()
        desecho = RegistroDesecho.objects.get(unidad=self.unidad)
        self.assertContains(self.client.get(self.ruta), f'?editar={desecho.pk}#generacion')
        formulario = self.client.get(self.ruta, {'editar': desecho.pk})
        self.assertContains(formulario, 'Corregir el desecho «Solventes usados ficticios»')
        self.assertContains(formulario, 'value="4.500"')
        respuesta = self.client.post(self.ruta + f'?editar={desecho.pk}', {
            'accion': 'generar', 'editar': desecho.pk, 'desecho-fecha_generacion': self.hoy.isoformat(),
            'desecho-nombre': 'Solventes usados ficticios', 'desecho-clase': 'peligroso',
            'desecho-estado_fisico': 'liquido', 'desecho-cantidad': '3.25', 'desecho-unidad_medida': 'l',
            'desecho-almacenamiento': '', 'desecho-etapa': 'tratado', 'desecho-responsable': self.cuenta.pk,
            'desecho-observaciones': 'Neutralizado en la unidad con el procedimiento ficticio P-01.'})
        self.assertRedirects(respuesta, self.ruta)
        desecho.refresh_from_db()
        self.assertEqual((desecho.cantidad, desecho.etapa, desecho.registrado_por),
                         (Decimal('3.250'), 'tratado', self.cuenta))
        rastro = RegistroAuditoriaUnidad.objects.get(unidad=self.unidad, entidad=RegistroDesecho._meta.label,
                                                     objeto_id=str(desecho.pk), accion='actualizar')
        self.assertEqual((rastro.datos_anteriores['cantidad'], rastro.datos_nuevos['cantidad'],
                          rastro.datos_nuevos['etapa']), ('4.500', '3.250', 'tratado'))
        tablas = self.tablas('DESECHOS')
        self.assertEqual(tablas['Generación y almacenamiento'][0][7], 'Tratado')
        self.assertEqual(tablas['Almacenado al corte'], [])
        # Lo tratado ya no se ofrece para entregar.
        self.assertFalse(self.client.get(self.ruta).context['form'].fields['desechos'].queryset.exists())

    def test_lo_que_no_se_puede_demostrar_no_se_guarda_y_dice_que_falta(self):
        casos = (
            (dict(cantidad='0'), 'cantidad', 'La cantidad debe ser mayor que cero.'),
            (dict(cantidad=''), 'cantidad', 'Este campo es obligatorio.'),
            (dict(fecha_generacion=(self.hoy + timedelta(days=1)).isoformat()), 'fecha_generacion',
             'la fecha no puede ser futura'),
            (dict(almacenamiento=''), 'almacenamiento', 'Indica dónde queda almacenado el desecho'),
            (dict(etapa='entregado'), 'etapa', 'Escoja una opción válida'),
            (dict(responsable=self.estudiante.pk), 'responsable', 'Escoja una opción válida'),
        )
        for campos, campo, mensaje in casos:
            with self.subTest(campo=campo, campos=campos):
                respuesta = self.generado(**campos)
                self.assertEqual(respuesta.status_code, 200)
                self.assertIn(mensaje, ' '.join(respuesta.context['form_generacion'].errors[campo]))
        self.assertFalse(RegistroDesecho.objects.filter(unidad=self.unidad).exists())

    def test_solo_registra_quien_gestiona_la_seguridad_de_la_unidad_y_solo_lo_suyo(self):
        self.generado()
        desecho = RegistroDesecho.objects.get(unidad=self.unidad)
        otra = Unidad.objects.create(nombre='Laboratorio vecino ficticio H4', slug='laboratorio-vecino-rutas-h4',
                                     dependencia='laboratorios', fecha_inicio=self.hoy.replace(month=1, day=1))
        ajeno = RegistroDesecho.objects.create(unidad=otra, fecha_generacion=self.hoy, clase='especial',
                                               nombre='De otra unidad', cantidad=Decimal('1'))
        self.assertEqual(self.client.get(self.ruta, {'editar': ajeno.pk}).status_code, 404)
        RegistroDesecho.objects.filter(pk=desecho.pk).update(
            etapa='entregado', fecha_entrega=self.hoy, gestor_autorizado='Gestor Ficticio S.A.',
            licencia_gestor='LIC-FICTICIA-001', manifiesto='MAN-H4-0002')
        # Lo entregado se corrige en su entrega, no en la generación.
        self.assertEqual(self.client.get(self.ruta, {'editar': desecho.pk}).status_code, 404)
        self.client.force_login(self.estudiante)
        self.assertEqual(self.client.get(self.ruta).status_code, 403)
        self.assertEqual(self.generado(nombre='Intruso').status_code, 403)
        self.assertEqual(RegistroDesecho.objects.filter(unidad=self.unidad).count(), 1)


class _ConSesionAtendida(BaseDeRutas):
    def atender(self, reserva):
        """La unidad inicia la sesión y la cierra como atendida desde la gestión de reservas."""
        ruta = reverse('gestion_reserva_accion', args=[self.unidad.slug, reserva.pk])
        respuesta = self.client.post(ruta, dict(accion='iniciar', observacion='Inicia la atención.'))
        self.assertEqual(respuesta.status_code, 200, respuesta.content)
        respuesta = self.client.post(
            ruta,
            dict(accion='completar', observacion='Sesión atendida en la prueba de cargue.', ejecucion_registrada='1',
                 participantes_seleccionados=json.dumps([]), asistencia_solicitante='asistio',
                 ejecucion_hora_inicio='08:00', ejecucion_hora_fin='10:00', ejecucion_asistentes_total='1',
                 ejecucion_cumplimiento='si', ejecucion_observaciones='Trabajo concluido sin novedades.'))
        self.assertEqual(respuesta.status_code, 200, respuesta.content)
        reserva.refresh_from_db()
        self.assertEqual((reserva.estado, reserva.resultado_cierre, reserva.es_efectiva),
                         ('completada', 'atendida', True))
        return reserva


class ResultadosDeInvestigacionTests(_ConSesionAtendida):
    """Anexo 10 · Informes de resultados de investigación aplicada y desarrollo tecnológico."""

    def test_un_resultado_de_investigacion_verificado_sale_en_la_tabla_10_1(self):
        consulta = self.consulta('investigacion')
        ruta = reverse('fuentes_metas_unidad', args=[self.unidad.slug])
        self.assertContains(consulta, 'Registrar resultado y respaldo')
        pantalla = self.client.get(ruta, dict(anio=self.anio, corte=self.corte, tipo='INVESTIGACION'))
        self.assertContains(pantalla, 'Proyecto, trabajo o convenio relacionado')
        # El código viene propuesto: nadie tiene que inventar uno que no se repita.
        self.assertEqual(pantalla.context['form']['codigo'].value(), f'INV-{self.anio}-001')
        resultado = self.evidencia(
            'INVESTIGACION', f'INV-{self.anio}-001', 'Prototipo ficticio de sensor',
            'Se construyó y probó un prototipo; el informe adjunto recoge las mediciones.',
            proyecto='Proyecto ficticio de sensores H4', tipo_producto='prototipo',
            producto='Prototipo de sensor de humedad', beneficiario='Grupo de investigación ficticio')
        self.assertEqual(self.client.get(ruta, dict(anio=self.anio, corte=self.corte, tipo='INVESTIGACION'))
                         .context['form']['codigo'].value(), f'INV-{self.anio}-002')
        fila = self.tablas('INVESTIGACION')['Resultados'][0]
        self.assertEqual((fila[0], fila[2], fila[3], fila[5], fila[6], fila[7]),
                         (resultado.codigo, 'Proyecto ficticio de sensores H4', 'Prototipo o desarrollo tecnológico',
                          'Alba Administradora', 'Grupo de investigación ficticio', 'Evidencia verificada'))
        self.assertIn('Prototipo de sensor de humedad', fila[4])
        self.assertIn(reverse('recurso_unidad', args=[resultado.recurso_id]), fila[8])
        self.assertIn('Proyecto ficticio de sensores H4', self.pdf_del_anexo('INVESTIGACION'))

    def test_una_sesion_de_investigacion_atendida_sale_en_la_tabla_10_2(self):
        reserva = self.atender(self.sesion(
            proposito_codigo='investigacion_innovacion', subtipo_actividad='proyecto_investigacion',
            referencia_actividad='Proyecto ficticio de sensores H4', responsable_actividad='Elías Estudiante'))
        fila = self.tablas('INVESTIGACION')['Uso de la unidad para investigación'][0]
        self.assertEqual(fila, ['Proyecto ficticio de sensores H4', 'Elías Estudiante', '1', '1', '2',
                                reserva.codigo_reserva])
        self.assertIn(reserva.codigo_reserva, self.pdf_del_anexo('INVESTIGACION'))


class TransferenciaYServiciosTests(_ConSesionAtendida):
    """Anexo 11 · Informes de transferencia de conocimiento, tecnología y servicios especializados."""

    def test_una_transferencia_aceptada_y_verificada_sale_en_la_tabla_11_1(self):
        self.assertContains(self.consulta('transferencia'), 'Registrar entrega y aceptación')
        transferencia = self.evidencia(
            'TRANSFERENCIA', 'TRF-H4-001', 'Capacitación técnica ficticia a una asociación',
            'Se entregó el manual y se capacitó a la asociación; el acta adjunta recoge la aceptación.',
            proyecto='Convenio ficticio H4', tipo_producto='asistencia', producto='Manual de buenas prácticas',
            beneficiario='Asociación ficticia de productores', aceptacion='aceptado',
            fecha_aceptacion=self.hoy.isoformat(), referencia_aceptacion='ACTA-H4-0001')
        fila = self.tablas('TRANSFERENCIA')['Transferencias'][0]
        self.assertEqual((fila[0], fila[2], fila[3], fila[4], fila[6]),
                         (transferencia.codigo, 'Asociación ficticia de productores',
                          'Asistencia técnica o capacitación entregada', 'Manual de buenas prácticas',
                          'Evidencia verificada'))
        self.assertIn('ACTA-H4-0001', fila[5])
        self.assertIn('ACTA-H4-0001', self.pdf_del_anexo('TRANSFERENCIA'))

    def test_sin_la_aceptacion_del_destinatario_la_transferencia_no_se_verifica_y_dice_por_que(self):
        respuesta = self.client.post(reverse('fuentes_metas_unidad', args=[self.unidad.slug]), dict(
            anio=self.anio, corte=self.corte, tipo='TRANSFERENCIA', codigo='TRF-H4-002', fecha=self.hoy.isoformat(),
            titulo='Entrega ficticia sin aceptar', descripcion='Se entregó el manual; falta el acta.',
            responsable=self.cuenta.pk, verificar='on', archivo=self.respaldo('TRF-H4-002'),
            proyecto='Convenio ficticio H4', tipo_producto='asistencia', producto='Manual',
            beneficiario='Asociación ficticia', aceptacion='pendiente'))
        self.assertEqual(respuesta.status_code, 200)
        errores = respuesta.context['form'].errors
        self.assertIn('debe existir aceptación del destinatario', ' '.join(errores['aceptacion']))
        self.assertIn('referencia_aceptacion', errores)
        self.assertIn('fecha_aceptacion', errores)
        self.assertFalse(EvidenciaGestionUnidad.objects.filter(unidad=self.unidad).exists())

    def test_un_servicio_especializado_atendido_sale_en_la_tabla_11_2(self):
        reserva = self.atender(self.sesion(
            tipo_solicitud='servicio', titulo_solicitud='Servicio ficticio de análisis H4',
            nombre_solicitante='Elías Estudiante', entidad_beneficiaria='Empresa ficticia H4'))
        fila = self.tablas('TRANSFERENCIA')['Servicios especializados'][0]
        self.assertEqual((fila[0], fila[8]), (reserva.codigo_reserva, reserva.codigo_reserva))
        self.assertIn('Empresa ficticia H4', fila[2])
        self.assertIn('Completada', fila[5])
        self.assertIn('efectivas', fila[6])
        self.assertIn(reserva.codigo_reserva, self.pdf_del_anexo('TRANSFERENCIA'))


class RespaldoParaAuditoriaTests(BaseDeRutas):
    """Los documentos de respaldo que se llenan con evidencias de gestión."""

    def test_una_capacitacion_y_una_difusion_con_su_respaldo_salen_en_su_documento(self):
        consulta = self.consulta('capacitacion')
        ruta = reverse('fuentes_metas_unidad', args=[self.unidad.slug])
        corte = 'B' if self.hoy.month >= 7 else 'A'
        self.assertContains(consulta, 'Registrar capacitación del personal')
        self.assertContains(consulta, 'Registrar acción de difusión')
        self.assertContains(consulta, f'{ruta}?anio={self.anio}&amp;corte={corte}&amp;tipo=CAPACITACION')
        self.assertContains(consulta, f'{ruta}?anio={self.anio}&amp;corte={corte}&amp;tipo=DIFUSION')
        self.evidencia('CAPACITACION', 'CAP-H4-001', 'Curso ficticio de bioseguridad',
                       'El personal de la unidad aprobó el curso; se adjunta el certificado.')
        # La difusión se respalda con el enlace a la publicación.
        self.evidencia('DIFUSION', 'DIF-H4-001', 'Nota ficticia sobre los servicios de la unidad',
                       'Publicación en el portal institucional.', archivo='',
                       enlace='https://example.org/difusion/dif-h4-001')
        pagina = self.consulta('capacitacion')
        for dato in ('Curso ficticio de bioseguridad', 'CAP-H4-001', 'Nota ficticia sobre los servicios de la unidad',
                     'DIF-H4-001', 'Evidencia verificada', 'Alba Administradora'):
            self.assertContains(pagina, dato)
        texto = _texto_del_pdf(self.consulta('capacitacion', 'pdf').content)
        self.assertIn('CAP-H4-001', texto)
        self.assertIn('DIF-H4-001', texto)

    def test_un_simulacro_con_su_respaldo_sale_en_su_documento(self):
        consulta = self.consulta('simulacros')
        self.assertContains(consulta, 'Registrar simulacro o práctica de emergencia')
        self.assertContains(self.consulta('seguridad'), 'Registrar simulacro o práctica de emergencia')
        self.evidencia('SIMULACRO', 'SIM-H4-001', 'Simulacro ficticio de evacuación',
                       'Evacuación completa en tres minutos; una salida estaba sin señalizar.',
                       emergencia='sismo', participantes='18', accion_mejora='Señalizar la salida posterior.')
        pagina = self.consulta('simulacros')
        for dato in ('Simulacro ficticio de evacuación', 'Sismo', 'Señalizar la salida posterior.',
                     'Evidencia verificada'):
            self.assertContains(pagina, dato)
        self.assertIn('Simulacro ficticio de evacuación', _texto_del_pdf(self.consulta('simulacros', 'pdf').content))

    def test_un_borrador_no_acredita_y_solo_se_verifica_registrandolo_de_nuevo(self):
        ruta = reverse('fuentes_metas_unidad', args=[self.unidad.slug])
        datos = dict(anio=self.anio, corte=self.corte, tipo='CAPACITACION', codigo='CAP-H4-002',
                     fecha=self.hoy.isoformat(), titulo='Taller ficticio sin comprobar',
                     descripcion='Se guarda sin marcar la comprobación.', responsable=self.cuenta.pk,
                     archivo=self.respaldo('CAP-H4-002'))
        self.assertEqual(self.client.post(ruta, datos).status_code, 302)
        borrador = EvidenciaGestionUnidad.objects.get(unidad=self.unidad, codigo='CAP-H4-002')
        self.assertEqual(borrador.estado, 'borrador')
        self.assertContains(self.consulta('capacitacion'), 'Borrador')
        # No hay cómo verificar un borrador: se rectifica (queda anulado) y se registra otra vez, verificado.
        respuesta = self.client.post(ruta, dict(anio=self.anio, corte=self.corte, tipo='CAPACITACION',
                                                accion='rectificar', evidencia=borrador.pk,
                                                motivo='Se guardó sin comprobar.'))
        self.assertEqual(respuesta.status_code, 302)
        borrador.refresh_from_db()
        self.assertEqual(borrador.estado, 'anulado')
        self.evidencia('CAPACITACION', 'CAP-H4-003', 'Taller ficticio comprobado', 'Con su certificado.')
        pagina = self.consulta('capacitacion')
        self.assertContains(pagina, 'CAP-H4-003')
        self.assertNotContains(pagina, 'CAP-H4-002')


# -- documentos principales ---------------------------------------------------------------------------

class _LectorDeFormularios(HTMLParser):
    """Los formularios de una página con los campos que enviaría el navegador.

    No cuenta lo que está dentro de un `<template>` (filas modelo que el navegador no envía), ni los
    campos deshabilitados, ni las casillas sin marcar.
    """

    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.formularios, self.actual, self.textarea, self.select, self.plantillas = [], None, None, None, 0

    def handle_starttag(self, etiqueta, atributos):
        a = dict(atributos)
        if etiqueta == 'template':
            self.plantillas += 1
            return
        if self.plantillas:
            return
        if etiqueta == 'form':
            self.actual = dict(campos=[], opciones={})
            self.formularios.append(self.actual)
            return
        if etiqueta == 'option' and self.select is not None:
            self.select['opciones'].append((a.get('value', ''), 'selected' in a))
            return
        if self.actual is None or not a.get('name'):
            return
        if etiqueta == 'input':
            tipo = a.get('type', 'text').lower()
            if tipo in ('submit', 'button', 'image', 'file', 'reset'):
                return
            if tipo in ('checkbox', 'radio'):
                self.actual['opciones'].setdefault(a['name'], []).append(a.get('value', 'on'))
                if 'checked' not in a:
                    return
            if 'disabled' not in a:
                self.actual['campos'].append((a['name'], a.get('value', 'on' if tipo in ('checkbox', 'radio') else '')))
        elif etiqueta == 'textarea':
            self.textarea = dict(destino=self.actual, nombre=a['name'], texto=[], inactivo='disabled' in a)
        elif etiqueta == 'select':
            self.select = dict(destino=self.actual, nombre=a['name'], multiple='multiple' in a, opciones=[],
                               inactivo='disabled' in a)

    def handle_data(self, datos):
        if self.textarea is not None:
            self.textarea['texto'].append(datos)

    def handle_endtag(self, etiqueta):
        if etiqueta == 'template':
            self.plantillas = max(0, self.plantillas - 1)
        elif self.plantillas:
            return
        elif etiqueta == 'form':
            self.actual = None
        elif etiqueta == 'textarea' and self.textarea is not None:
            if not self.textarea['inactivo']:
                self.textarea['destino']['campos'].append(
                    (self.textarea['nombre'], ''.join(self.textarea['texto']).lstrip('\n')))
            self.textarea = None
        elif etiqueta == 'select' and self.select is not None:
            destino = self.select['destino']
            destino['opciones'].setdefault(self.select['nombre'], []).extend(v for v, _m in self.select['opciones'])
            elegidas = [valor for valor, marcada in self.select['opciones'] if marcada]
            if not elegidas and not self.select['multiple'] and self.select['opciones']:
                elegidas = [self.select['opciones'][0][0]]
            if not self.select['inactivo']:
                destino['campos'].extend((self.select['nombre'], valor) for valor in elegidas)
            self.select = None


def _formulario_del_editor(html):
    """El formulario del editor guiado tal como lo trae la página: sus campos y las opciones que ofrece."""
    lector = _LectorDeFormularios()
    lector.feed(html)
    return next(f for f in lector.formularios if any(nombre == 'version_base' for nombre, _valor in f['campos']))


class DocumentosPrincipalesTests(BaseDeRutas):
    """Resolución, protocolo, plan de compras, planificación e informe, hasta que la Dirección los recibe.

    La unidad trabaja con su cuenta; la Dirección, con una cuenta de superusuario que tiene la función de
    seguimiento vigente y que no administra ni coordina la unidad. Lo que hace cada una va por HTTP: el
    expediente y el editor de la unidad, y «Cumplimiento del expediente» en la administración.
    """

    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()
        cls.direccion = get_user_model().objects.create_superuser(
            'direccion.rutas-h4', 'direccion.rutas-h4@example.org', 'clave-segura', first_name='Dora',
            last_name='Directora')
        designar(cls.direccion)

    def setUp(self):
        super().setUp()
        self.expediente = reverse('gestion_expediente_unidad', args=[self.unidad.slug])
        self.cumplimiento = reverse('admin:reportes-cumplimiento-expediente')
        # El semestre anterior ya concluyó: es el que admite enviar su informe.
        self.anterior = (self.anio, 'A') if self.corte == 'B' else (self.anio - 1, 'B')

    # ---- ayudas -----------------------------------------------------------------------------------

    def mensajes(self, respuesta):
        return ' '.join(str(mensaje) for mensaje in get_messages(respuesta.wsgi_request))

    def preparar(self, anio, corte):
        """«Preparar expediente para trabajar»: crea las filas del año con sus plazos."""
        respuesta = self.client.post(self.expediente, dict(anio=anio, corte=corte, accion='preparar'), follow=True)
        self.assertIn(f'Expediente de {anio} preparado para trabajar.', self.mensajes(respuesta))

    def documento(self, codigo, anio=None, corte=''):
        return DocumentoExpediente.objects.select_related('exigido', 'recurso').get(
            unidad=self.unidad, exigido__codigo=codigo, anio=anio or self.anio, corte=corte)

    def gestion(self, documento):
        """El cuadro «gestionar» del documento en el expediente de la unidad, en texto."""
        respuesta = self.client.get(self.expediente, dict(anio=documento.anio, corte=documento.corte,
                                                          gestionar=documento.pk, fragment='1'))
        self.assertEqual(respuesta.status_code, 200)
        return respuesta

    def editor(self, documento):
        respuesta = self.client.get(reverse('redactar_documento_expediente', args=[self.unidad.slug, documento.pk]))
        self.assertEqual(respuesta.status_code, 200)
        return respuesta

    def guardar(self, documento, **cambios):
        """Lo que envía el editor al guardar: todos sus campos, con lo que cambió el usuario."""
        formulario = _formulario_del_editor(self.editor(documento).content.decode())
        datos = QueryDict(mutable=True)
        for nombre, valor in formulario['campos']:
            if nombre not in cambios:
                datos.appendlist(nombre, valor)
        for nombre, valor in cambios.items():
            self.assertIn(nombre, {campo for campo, _valor in formulario['campos']} | set(formulario['opciones']),
                          f'El editor no ofrece el campo «{nombre}».')
            datos.setlist(nombre, valor if isinstance(valor, list) else [valor])
        respuesta = self.client.post(
            reverse('redactar_documento_expediente', args=[self.unidad.slug, documento.pk]), datos.urlencode(),
            content_type='application/x-www-form-urlencoded', HTTP_X_REQUESTED_WITH='XMLHttpRequest')
        self.assertEqual(respuesta.status_code, 200, respuesta.content)
        return respuesta.json()

    def generar_y_enviar(self, documento, version, accion='generar_enviar_guardado'):
        """El botón «Generar y enviar» del editor, con el borrador ya guardado."""
        respuesta = self.client.post(
            reverse('redactar_documento_expediente', args=[self.unidad.slug, documento.pk]),
            dict(version_base=version, accion=accion), HTTP_X_REQUESTED_WITH='XMLHttpRequest')
        documento.refresh_from_db()
        return respuesta

    def texto_archivado(self, documento):
        documento.refresh_from_db()
        with documento.recurso.archivo.open('rb') as archivo:
            return _texto_del_pdf(archivo.read())

    def como_direccion(self, **datos):
        """Una decisión de la Dirección en «Cumplimiento del expediente»; vuelve a dejar la sesión de la unidad."""
        documento = datos['documento']
        self.client.force_login(self.direccion)
        try:
            respuesta = self.client.post(self.cumplimiento, dict(
                datos, documento=documento.pk, query=f'anio={documento.anio}&corte={documento.corte}'), follow=True)
            self.assertEqual(respuesta.status_code, 200)
            return self.mensajes(respuesta)
        finally:
            self.client.force_login(self.cuenta)
            documento.refresh_from_db()

    def aprobar(self, documento):
        documento.refresh_from_db()
        mensaje = self.como_direccion(documento=documento, accion='aprobar_documento', version=documento.version,
                                      huella=documento.recurso.hash_sha256)
        self.assertIn('Documento aprobado.', mensaje)
        self.assertEqual(documento.estado, 'validado')
        self.assertIsNotNone(documento.recibido_en)
        if documento.verificacion_qr:
            # Lo emitido con QR lo recibe el control automático al enviarse; la decisión queda en su constancia.
            constancia = ConstanciaDocumento.objects.get(token=documento.verificacion_qr)
            self.assertEqual((constancia.aprobado_por, estado_constancia(constancia)), (self.direccion, 'VIGENTE'))
        else:
            self.assertEqual(documento.recibido_por, self.direccion)

    def ultimatum(self, documento):
        hasta = (timezone.localtime() + timedelta(days=5)).strftime('%Y-%m-%dT%H:%M')
        return self.como_direccion(documento=documento, accion='ultimatum', hasta=hasta,
                                   motivo='Regularización ficticia de la entrega pendiente.')

    def abrir_si_vencio(self, documento):
        """Con el plazo vencido, la entrega la abre la Dirección con su ultimátum colectivo."""
        documento.refresh_from_db()
        if documento.vencido and not documento.prorroga_activa:
            self.assertIn('Ultimátum establecido para 1 unidades pendientes.', self.ultimatum(documento))
        elif not documento.abierto:
            # Antes de que abra su ventana no hay nada que la Dirección habilite: solo pasa el calendario.
            abrir_entrega(documento)
        documento.refresh_from_db()
        self.assertTrue(documento.entrega_abierta)

    def orden_preventiva(self, anio, corte):
        """La orden de mantenimiento preventivo que la planificación exige tener programada en el semestre."""
        inicio = cortes_del_anio(anio)[corte][0]
        respuesta = self.operar(modulo='mantenimiento', equipo_id=self.equipo.pk, tipo='preventivo',
                                estado='planificado', titulo='Limpieza preventiva ficticia',
                                descripcion='Limpieza de filtros de la campana.',
                                fecha_programada=f'{inicio + timedelta(days=40)}T09:00', responsable='',
                                ejecutor='interno', duracion_horas='2')
        self.assertEqual(respuesta.status_code, 200, respuesta.content)

    def planificacion_enviada(self, anio, corte):
        """La planificación del semestre redactada en el editor y enviada, con el plazo que abra la Dirección."""
        plan = self.documento('PLANIFICACION', anio, corte)
        self.abrir_si_vencio(plan)
        self.orden_preventiva(anio, corte)
        formulario = _formulario_del_editor(self.editor(plan).content.decode())
        cambios = dict(sectores=['docencia'], estado_operativo='B', revision_recursos='revisado',
                       uso_justificacion='Prácticas y sesiones previstas dentro de la jornada de la unidad.')
        for nombre, _valor in formulario['campos']:
            if nombre.startswith('uso_horas__'):
                cambios[nombre] = '4'
            elif nombre.startswith('act__') and nombre.endswith('__responsable'):
                cambios[nombre] = 'Alba Administradora'
        guardado = self.guardar(plan, **cambios)
        self.assertEqual((guardado['success'], guardado['faltantes']), (True, []))
        respuesta = self.generar_y_enviar(plan, guardado['version'])
        self.assertEqual(respuesta.status_code, 200, respuesta.content)
        self.assertTrue(respuesta.json()['enviado'])
        self.assertEqual(plan.estado, 'validado')
        return plan

    # ---- resolución de creación -------------------------------------------------------------------

    def test_la_resolucion_de_creacion_se_carga_se_envia_y_la_direccion_la_aprueba(self):
        # Antes de preparar el expediente, el documento ya se puede abrir y dice cómo empezar.
        sin_preparar = self.client.get(self.expediente, dict(anio=self.anio, corte=self.corte,
                                                             gestionar='RESOLUCION-CREACION', fragment='1'))
        self.assertContains(sin_preparar, 'Preparar expediente para trabajar')
        self.preparar(self.anio, self.corte)
        resolucion = self.documento('RESOLUCION-CREACION')
        self.assertTrue(resolucion.entrega_abierta)
        cuadro = self.gestion(resolucion)
        self.assertContains(cuadro, 'Cargar y enviar a Dirección')
        self.assertContains(cuadro, 'name="correspondencia_confirmada"')

        def carga(**extra):
            return self.client.post(self.expediente, dict(
                anio=self.anio, corte=self.corte, documento=resolucion.pk, accion='cargar', enviar='1',
                archivo=SimpleUploadedFile('resolucion-ficticia.pdf', pdf_legible_prueba(
                    'Resolución ficticia RES-H4-001 de creación del laboratorio de prueba.'), 'application/pdf'),
                **extra), follow=True)

        # Sin la casilla de comprobación no se carga, y el mensaje dice qué falta.
        self.assertIn('Confirma que abriste el archivo', self.mensajes(carga()))
        resolucion.refresh_from_db()
        self.assertEqual((resolucion.estado, resolucion.recurso), ('pendiente', None))
        confirmacion = dict(correspondencia_unidad_id=self.unidad.pk, correspondencia_documento_id=resolucion.pk,
                            correspondencia_codigo='RESOLUCION-CREACION', correspondencia_anio=self.anio,
                            correspondencia_corte='', correspondencia_mes='', correspondencia_version='0',
                            correspondencia_confirmada='1')
        self.assertIn('cargado y enviado a la Dirección.', self.mensajes(carga(**confirmacion)))
        resolucion.refresh_from_db()
        self.assertEqual((resolucion.estado, resolucion.cargado_por, resolucion.validado_por),
                         ('validado', self.cuenta, self.cuenta))
        self.assertIn('RES-H4-001', self.texto_archivado(resolucion))
        self.assertContains(self.gestion(resolucion), 'Documento enviado.')

        self.aprobar(resolucion)
        self.assertTrue(aprobacion_vigente(self.documento('RESOLUCION-CREACION')))
        self.assertTrue(self.documento('RESOLUCION-CREACION').cumple)

    # ---- protocolo ---------------------------------------------------------------------------------

    def test_el_protocolo_se_redacta_en_el_editor_se_envia_y_la_direccion_lo_aprueba(self):
        self.preparar(self.anio, self.corte)
        protocolo = self.documento('PROTOCOLO-BIOSEGURIDAD')
        self.assertContains(self.gestion(protocolo), 'Preparar y enviar')
        editor = self.editor(protocolo)
        # El editor propone casi todo y nombra, apartado por apartado, lo único que falta escribir.
        self.assertEqual(editor.context['faltantes'][:2], [
            'Emergencias y comunicación → Alarma, evacuación y punto de encuentro',
            'Responsables del documento → Revisión del contenido propuesto'])
        self.assertContains(editor, 'Generar y enviar')
        # Con faltantes no se emite, y la respuesta repite cuáles son.
        incompleto = self.guardar(protocolo)
        self.assertEqual(len(incompleto['faltantes']), 4)
        rechazo = self.generar_y_enviar(protocolo, incompleto['version'])
        self.assertEqual(rechazo.status_code, 400)
        self.assertIn('Faltan apartados obligatorios: Emergencias y comunicación', rechazo.json()['error'])

        guardado = self.guardar(
            protocolo, revision_propuestas='revisado',
            evacuacion_protocolo='<p>Alarma de viva voz; salida por la puerta ficticia H4; encuentro en el patio.</p>')
        self.assertEqual((guardado['porcentaje'], guardado['faltantes']), (100, []))
        respuesta = self.generar_y_enviar(protocolo, guardado['version'])
        self.assertEqual(respuesta.status_code, 200, respuesta.content)
        self.assertTrue(respuesta.json()['enviado'])
        self.assertEqual((protocolo.estado, protocolo.validado_por), ('validado', self.cuenta))
        # Se emite con su código QR: no pide descargar, firmar ni volver a cargar.
        self.assertTrue(protocolo.verificacion_qr)
        self.assertFalse(protocolo.firma_pendiente)
        self.assertIn('salida por la puerta ficticia H4', self.texto_archivado(protocolo))

        self.aprobar(protocolo)
        self.assertTrue(self.documento('PROTOCOLO-BIOSEGURIDAD').cumple)

    # ---- plan anual de compras ---------------------------------------------------------------------

    def test_el_plan_anual_de_compras_se_redacta_se_envia_y_la_direccion_confirma_su_conformidad(self):
        self.preparar(self.anio, self.corte)
        compras = self.documento('PLAN-COMPRAS-ANUAL')
        self.abrir_si_vencio(compras)
        editor = self.editor(compras)
        self.assertIn('Compras del año: añade las adquisiciones previstas o justifica por qué la unidad no requiere '
                      'compras.', editor.context['faltantes'])
        guardado = self.guardar(compras, sin_compras_justificacion=(
            '<p>La dotación ficticia H4 cubre las actividades previstas; no se solicitan compras.</p>'))
        self.assertEqual((guardado['porcentaje'], guardado['faltantes']), (100, []))
        respuesta = self.generar_y_enviar(compras, guardado['version'])
        self.assertEqual(respuesta.status_code, 200, respuesta.content)
        self.assertEqual(compras.estado, 'validado')
        self.assertIn('La dotación ficticia H4 cubre las actividades previstas', self.texto_archivado(compras))
        self.aprobar(compras)
        self.assertTrue(self.documento('PLAN-COMPRAS-ANUAL').cumple)

    # ---- planificación semestral y plazos ----------------------------------------------------------

    def test_la_planificacion_con_el_plazo_vencido_se_entrega_cuando_la_direccion_fija_el_ultimatum(self):
        anio, corte = self.anterior
        self.preparar(anio, corte)
        plan = self.documento('PLANIFICACION', anio, corte)
        self.assertTrue(plan.vencido)
        # La unidad ve por qué no puede entregar y a quién le toca destrabarlo.
        self.assertContains(self.gestion(plan), 'Plazo institucional vencido. Corresponde a la Dirección establecer '
                                                'el ultimátum colectivo.')
        guardado = self.guardar(plan)
        rechazo = self.generar_y_enviar(plan, guardado['version'])
        self.assertEqual(rechazo.status_code, 400)
        self.assertEqual(rechazo.json()['error'],
                         'El plazo institucional venció. La Dirección debe establecer el ultimátum colectivo.')
        self.assertEqual(plan.estado, 'pendiente')
        # Sin una orden preventiva programada, el editor dice dónde se registra.
        self.assertIn('Mantenimiento preventivo y correctivo de equipos: Pendiente de programar: registra en '
                      '«Mantenimiento e incidencias», en la gestión de la unidad, una orden de mantenimiento preventivo '
                      'con fecha dentro del semestre, y vuelve a abrir este editor.', guardado['faltantes'])

        self.assertIn('Ultimátum establecido para 1 unidades pendientes.', self.ultimatum(plan))
        self.assertContains(self.gestion(plan), 'Ultimátum vigente: completa y envía la entrega antes de la fecha '
                                                'indicada.')
        plan = self.planificacion_enviada(anio, corte)
        # Se recibe igual, marcada como entrega tardía.
        self.assertTrue(plan.entregado_tarde)
        texto = self.texto_archivado(plan)
        self.assertIn('Prácticas y sesiones previstas dentro de la jornada de la unidad.', texto)
        self.assertIn('Limpieza preventiva ficticia', texto)
        self.aprobar(plan)
        self.assertTrue(self.documento('PLANIFICACION', anio, corte).cumple)

    def test_vencido_el_ultimatum_la_unidad_solicita_la_entrega_tardia_y_la_direccion_la_habilita(self):
        anio, corte = self.anterior
        self.preparar(anio, corte)
        plan = self.documento('PLANIFICACION', anio, corte)
        # Mientras no haya ultimátum, la solicitud individual todavía no procede.
        respuesta = self.client.post(self.expediente, dict(anio=anio, corte=corte, documento=plan.pk,
                                                           accion='solicitar_tardia', motivo='Sin plazo.'), follow=True)
        self.assertIn('Primero corresponde el ultimátum colectivo de la Dirección.', self.mensajes(respuesta))
        self.ultimatum(plan)
        # Pasa el tiempo: el ultimátum vence sin que la unidad haya entregado.
        DocumentoExpediente.objects.filter(pk=plan.pk).update(ultimatum_hasta=timezone.now() - timedelta(hours=1))
        plan.refresh_from_db()
        self.assertFalse(plan.entrega_abierta)
        cuadro = self.gestion(plan)
        self.assertContains(cuadro, 'Solicitar entrega fuera de plazo')
        self.assertContains(cuadro, 'name="accion" value="solicitar_tardia"')
        rechazo = self.generar_y_enviar(plan, self.guardar(plan)['version'])
        self.assertIn('Solicita a la Dirección la entrega fuera de plazo', rechazo.json()['error'])

        respuesta = self.client.post(self.expediente, dict(
            anio=anio, corte=corte, documento=plan.pk, accion='solicitar_tardia',
            motivo='La cuenta de la unidad se entregó después del plazo.'), follow=True)
        self.assertIn('Solicitud enviada: la Dirección decide si habilita la entrega', self.mensajes(respuesta))
        self.assertContains(self.gestion(plan), 'espera que la Dirección habilite la entrega fuera de plazo')
        hasta = (timezone.localtime() + timedelta(days=3)).strftime('%Y-%m-%dT%H:%M')
        mensaje = self.como_direccion(documento=plan, accion='habilitar_tardia', hasta=hasta)
        self.assertIn('entrega fuera de plazo habilitada; lo que llegue quedará marcado como tardío.', mensaje)
        self.assertTrue(plan.entrega_abierta)
        self.assertContains(self.gestion(plan), 'Entrega fuera de plazo habilitada')

        plan = self.planificacion_enviada(anio, corte)
        self.assertEqual((plan.estado, plan.entregado_tarde), ('validado', True))

    # ---- informe semestral -------------------------------------------------------------------------

    def test_el_informe_del_semestre_en_curso_se_prepara_pero_no_se_envia_antes_del_cierre(self):
        self.preparar(self.anio, self.corte)
        informe = self.documento('INFORME-SEMESTRAL', self.anio, self.corte)
        fin = cortes_del_anio(self.anio)[self.corte][1]
        guardado = self.guardar(informe)
        self.assertEqual(guardado['faltantes'], [])
        if not informe.abierto:
            # Su ventana abre quince días antes del cierre del semestre; antes, el mensaje da la fecha.
            rechazo = self.generar_y_enviar(informe, guardado['version'], accion='generar_guardado')
            self.assertEqual(rechazo.json()['error'], f'La entrega se abre el {informe.abre_el:%d/%m/%Y}.')
            abrir_entrega(informe)
        self.assertFalse(self.editor(informe).context['envio_qr_disponible'])
        respuesta = self.generar_y_enviar(informe, guardado['version'], accion='generar_guardado')
        self.assertEqual(respuesta.status_code, 200, respuesta.content)
        self.assertEqual(informe.estado, 'generado')
        respuesta = self.client.post(reverse('enviar_documento_qr', args=[self.unidad.slug, informe.pk]),
                                     dict(token=informe.verificacion_qr, version=informe.version), follow=True)
        self.assertIn('El semestre de gestión aún no ha concluido.', self.mensajes(respuesta))
        informe.refresh_from_db()
        self.assertEqual(informe.estado, 'generado')
        self.assertLessEqual(self.hoy, fin)

    def test_el_informe_exige_la_planificacion_aprobada_y_la_direccion_lo_recibe_y_evalua(self):
        anio, corte = self.anterior
        fin = cortes_del_anio(anio)[corte][1]
        self.preparar(anio, corte)
        # Una capacitación del semestre, registrada y verificada desde su pantalla.
        respuesta = self.client.post(reverse('fuentes_metas_unidad', args=[self.unidad.slug]), dict(
            anio=anio, corte=corte, tipo='CAPACITACION', codigo='CAP-H4-INFORME', fecha=fin.isoformat(),
            titulo='Curso ficticio del semestre anterior', descripcion='Curso aprobado por el personal.',
            responsable=self.cuenta.pk, verificar='on', archivo=self.respaldo('CAP-H4-INFORME')))
        self.assertEqual(respuesta.status_code, 302, respuesta.context and respuesta.context['form'].errors)
        plan = self.planificacion_enviada(anio, corte)

        informe = self.documento('INFORME-SEMESTRAL', anio, corte)
        self.abrir_si_vencio(informe)
        self.assertTrue(self.editor(informe).context['envio_qr_disponible'])
        guardado = self.guardar(informe, logros='<ul><li>Logro ficticio H4: personal capacitado en bioseguridad.</li></ul>')
        self.assertEqual(guardado['faltantes'], [])
        # Con la planificación enviada pero sin aprobar, el informe no sale; el mensaje dice qué falta.
        rechazo = self.generar_y_enviar(informe, guardado['version'])
        self.assertEqual(rechazo.status_code, 400)
        self.assertEqual(rechazo.json()['error'],
                         'Antes de enviar el informe, la planificación del mismo semestre debe estar aprobada.')
        self.aprobar(plan)

        respuesta = self.generar_y_enviar(informe, guardado['version'])
        self.assertEqual(respuesta.status_code, 200, respuesta.content)
        self.assertTrue(respuesta.json()['enviado'])
        self.assertEqual((informe.estado, informe.validado_por), ('validado', self.cuenta))
        texto = self.texto_archivado(informe)
        self.assertIn('Logro ficticio H4: personal capacitado en bioseguridad.', texto)
        self.assertIn('Capacitación del personal de la unidad', texto)
        # Sus anexos se generan y viajan con él.
        anexos = {a.exigido.codigo: a for a in anexos_del(informe)}
        self.assertTrue({'INDUCCION-SEGURIDAD', 'DESECHOS'} <= set(anexos))
        self.assertTrue(all(a.recurso_id for a in anexos.values()))

        # La Dirección lo recibe y confirma el cumplimiento calculado de sus metas: esa es su evaluación.
        self.aprobar(informe)
        informe = self.documento('INFORME-SEMESTRAL', anio, corte)
        self.assertEqual(informe.evaluado_por, self.direccion)
        self.assertIsNotNone(informe.evaluacion)
        self.assertIsNotNone(informe.nota)
        self.assertGreater(informe.evaluacion, 0)
        # La cuenta de la unidad no decide por la Dirección.
        respuesta = self.client.post(self.expediente, dict(anio=anio, corte=corte, documento=informe.pk,
                                                           accion='recibir'))
        self.assertEqual(respuesta.status_code, 403)
