"""Satisfacción de los usuarios: quién valora una reserva, cuándo y qué ve la unidad."""
from datetime import date, time, timedelta
from io import BytesIO
from zipfile import ZipFile

from django.contrib.auth import get_user_model
from django.db import IntegrityError, transaction
from django.test import Client, TestCase
from django.urls import reverse
from django.utils import timezone
from openpyxl import load_workbook
from pypdf import PdfReader

from apps.directorio_unidades.models.core import Unidad
from apps.documentos.presentation.expediente import consultas_de_la_unidad
from apps.formacion.models.practicas import RegistroAuditoriaUnidad
from apps.gestion_unidades.presentation.gestion_reportes import categorias_para
from apps.gestion_unidades.presentation.reportes_satisfaccion import reporte_satisfaccion
from apps.reservas.models.reservas import Reserva
from apps.reservas.models.valoraciones import ValoracionReserva
from tests.integration.utiles import identificar

COMENTARIO = 'COMENTARIO-FICTICIO-QA: el equipo estaba listo a la hora acordada.'


class ValoracionReservasTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        usuarios = get_user_model().objects
        cls.admin = usuarios.create_user('admin-valoracion-qa', first_name='Responsable', last_name='Ficticio')
        cls.titular = usuarios.create_user('titular-valoracion-qa', first_name='Zulema', last_name='Valoradora',
                                           email='zulema.valoradora@upec.edu.ec')
        cls.ajeno = usuarios.create_user('ajeno-valoracion-qa')
        cls.admin_otra = usuarios.create_user('admin-otra-valoracion-qa')
        for persona in (cls.admin, cls.titular, cls.ajeno, cls.admin_otra):
            identificar(persona)
        cls.unidad = Unidad.objects.create(
            nombre='Laboratorio ficticio de valoraciones', slug='laboratorio-valoraciones-qa',
            dependencia='laboratorios', fecha_inicio=date(2020, 1, 1), administrador=cls.admin, activo=True)
        cls.otra = Unidad.objects.create(
            nombre='Laboratorio ficticio vecino', slug='laboratorio-vecino-valoraciones-qa',
            dependencia='laboratorios', fecha_inicio=date(2020, 1, 1), administrador=cls.admin_otra, activo=True)
        cls.hasta = timezone.localdate()
        cls.desde = cls.hasta - timedelta(days=20)

    def reserva(self, *, unidad=None, usuario=None, dias=5, **campos):
        campos.setdefault('estado', 'completada')
        campos.setdefault('resultado_cierre', 'atendida' if campos['estado'] == 'completada' else '')
        return Reserva.objects.create(
            laboratorio=unidad or self.unidad, usuario=usuario or self.titular,
            fecha=self.hasta - timedelta(days=dias), hora_inicio=time(9), hora_fin=time(11),
            equipo_codigo='EQ-VALORACION-QA', equipo_nombre='Equipo ficticio',
            titulo_solicitud='Actividad ficticia', proposito_codigo='docencia_practica', **campos)

    def valorar(self, reserva, usuario=None, **datos):
        if usuario is not False:
            self.client.force_login(usuario or self.titular)
        datos.setdefault('general', '4')
        return self.client.post(reverse('valorar_reserva_usuario', args=[reserva.pk]), datos)

    def filtros(self, **extra):
        return dict(categoria_reporte='satisfaccion', desde=self.desde.isoformat(), hasta=self.hasta.isoformat(),
                    **extra)

    # ---- Quién y cuándo valora -----------------------------------------------------------------

    def test_solo_el_solicitante_valora_y_solo_una_vez(self):
        reserva = self.reserva()
        self.assertEqual(self.valorar(reserva, usuario=False).status_code, 401)
        self.assertEqual(self.valorar(reserva, usuario=self.ajeno).status_code, 404)
        # Tampoco el personal de la unidad valora por el solicitante.
        self.assertEqual(self.valorar(reserva, usuario=self.admin).status_code, 404)
        self.assertFalse(ValoracionReserva.objects.exists())

        respuesta = self.valorar(reserva, general='5', atencion_personal='4', comentario=COMENTARIO)
        self.assertEqual(respuesta.status_code, 201)
        self.assertEqual(respuesta.json()['valoracion']['general'], 5)
        valoracion = ValoracionReserva.objects.get(reserva=reserva)
        self.assertEqual((valoracion.general, valoracion.atencion_personal, valoracion.estado_equipos,
                          valoracion.instalaciones, valoracion.comentario), (5, 4, None, None, COMENTARIO))

        repetida = self.valorar(reserva, general='1')
        self.assertEqual(repetida.status_code, 409)
        valoracion.refresh_from_db()
        self.assertEqual(valoracion.general, 5)
        self.assertEqual(ValoracionReserva.objects.count(), 1)

    def test_una_reserva_no_atendida_no_se_puede_valorar(self):
        for campos in (dict(estado='pendiente'), dict(estado='confirmada'), dict(estado='cancelada'),
                       dict(estado='completada', resultado_cierre='no_presentado'),
                       dict(estado='completada', resultado_cierre='no_atendida')):
            with self.subTest(**campos):
                self.assertEqual(self.valorar(self.reserva(**campos)).status_code, 409)
        self.assertFalse(ValoracionReserva.objects.exists())

    def test_valores_fuera_de_1_a_5_se_rechazan(self):
        reserva = self.reserva()
        for datos in (dict(general=''), dict(general='0'), dict(general='6'), dict(general='4.5'),
                      dict(general='cinco'), dict(general='5', instalaciones='0'),
                      dict(general='5', estado_equipos='9'), dict(general='5', comentario='x' * 501)):
            with self.subTest(**datos):
                respuesta = self.valorar(reserva, **datos)
                self.assertEqual(respuesta.status_code, 400)
                self.assertFalse(respuesta.json()['success'])
        self.assertFalse(ValoracionReserva.objects.exists())
        # La base tampoco admite un valor fuera de la escala aunque no pase por la vista.
        with self.assertRaises(IntegrityError), transaction.atomic():
            ValoracionReserva.objects.create(reserva=reserva, general=6)
        with self.assertRaises(IntegrityError), transaction.atomic():
            ValoracionReserva.objects.create(reserva=reserva, general=5, instalaciones=0)

    def test_la_vista_exige_post_y_csrf(self):
        reserva = self.reserva()
        self.client.force_login(self.titular)
        self.assertEqual(self.client.get(reverse('valorar_reserva_usuario', args=[reserva.pk])).status_code, 405)
        estricto = Client(enforce_csrf_checks=True)
        estricto.force_login(self.titular)
        respuesta = estricto.post(reverse('valorar_reserva_usuario', args=[reserva.pk]), {'general': '5'})
        self.assertEqual(respuesta.status_code, 403)
        self.assertFalse(ValoracionReserva.objects.exists())

    def test_la_auditoria_de_la_unidad_registra_la_valoracion_sin_el_comentario(self):
        reserva = self.reserva()
        self.assertEqual(self.valorar(reserva, general='2', comentario=COMENTARIO).status_code, 201)
        rastro = RegistroAuditoriaUnidad.objects.get(unidad=self.unidad, entidad='reservas.ValoracionReserva')
        self.assertEqual((rastro.accion, rastro.usuario), ('crear', self.titular))
        self.assertEqual(rastro.objeto_id, str(reserva.valoracion.pk))
        self.assertNotIn('COMENTARIO-FICTICIO-QA', f'{rastro.descripcion} {rastro.datos_nuevos} {rastro.datos_anteriores}')

    # ---- Mis reservas --------------------------------------------------------------------------

    def test_mis_reservas_ofrece_valorar_la_atendida_y_despues_muestra_la_valoracion(self):
        atendida = self.reserva()
        pendiente = self.reserva(estado='confirmada', dias=-3)
        self.client.force_login(self.titular)

        def filas():
            datos = self.client.get(reverse('obtener_reservas_usuario')).json()['reservas']
            return {fila['id']: fila for fila in datos}

        antes = filas()
        self.assertTrue(antes[atendida.pk]['puede_valorar'])
        self.assertIsNone(antes[atendida.pk]['valoracion'])
        self.assertEqual(antes[atendida.pk]['valorar_url'], reverse('valorar_reserva_usuario', args=[atendida.pk]))
        self.assertFalse(antes[pendiente.pk]['puede_valorar'])

        self.assertEqual(self.valorar(atendida, general='4', instalaciones='3').status_code, 201)
        despues = filas()[atendida.pk]
        self.assertFalse(despues['puede_valorar'])
        self.assertEqual(despues['valoracion']['general'], 4)
        self.assertEqual(despues['valoracion']['aspectos'],
                         [{'codigo': 'instalaciones', 'nombre': 'Instalaciones', 'valor': 3}])

    # ---- Consulta de gestión -------------------------------------------------------------------

    def test_la_consulta_se_ofrece_solo_cuando_la_unidad_tiene_valoraciones(self):
        self.assertIn('satisfaccion', dict(categorias_para(self.unidad)))

        def ofrecidas():
            return {c['codigo']: c for c in consultas_de_la_unidad(self.unidad, self.desde, self.hasta)}

        self.assertNotIn('satisfaccion', ofrecidas())
        ValoracionReserva.objects.create(reserva=self.reserva(), general=5)
        consulta = ofrecidas()['satisfaccion']
        self.assertEqual(consulta['nombre'], 'Satisfacción de los usuarios')
        self.assertIn('categoria_reporte=satisfaccion', consulta['url'])
        # La unidad vecina sigue sin la consulta: las valoraciones no son suyas.
        self.assertNotIn('satisfaccion',
                         {c['codigo'] for c in consultas_de_la_unidad(self.otra, self.desde, self.hasta)})

    def test_el_reporte_trae_promedios_tasa_distribucion_meses_y_comentarios_sin_el_nombre(self):
        ValoracionReserva.objects.create(reserva=self.reserva(dias=3), general=5, atencion_personal=4,
                                         comentario=COMENTARIO)
        ValoracionReserva.objects.create(reserva=self.reserva(dias=4), general=4)
        self.reserva(dias=5)  # Atendida y sin valorar: cuenta en la tasa.
        self.reserva(dias=6, estado='completada', resultado_cierre='no_presentado')  # No cuenta.
        fuera = self.reserva(dias=40)  # Atendida y valorada, fuera del rango pedido.
        ValoracionReserva.objects.create(reserva=fuera, general=1, comentario='FUERA-DEL-RANGO-QA')

        datos = reporte_satisfaccion(self.unidad, self.desde, self.hasta)
        self.assertEqual(datos['cards'], [('Respuestas recibidas', 2), ('Reservas atendidas', 3),
                                          ('Tasa de respuesta', '66.7 %'), ('Promedio general', '4.50')])
        self.assertEqual(datos['rows'], [['Valoración general', 2, '4.50'], ['Atención del personal', 1, '4.00'],
                                         ['Estado de los equipos', 0, '—'], ['Instalaciones', 0, '—']])
        distribucion, meses, comentarios = datos['tablas']
        self.assertEqual(distribucion['rows'][:2], [['5 de 5', 1, '50.0 %'], ['4 de 5', 1, '50.0 %']])
        self.assertEqual(sum(fila[1] for fila in meses['rows']), 3)
        self.assertEqual(sum(fila[2] for fila in meses['rows']), 2)
        self.assertEqual(comentarios['headers'], ['Fecha', 'Valoración', 'Comentario'])
        self.assertEqual(comentarios['rows'], [[f'{timezone.localdate():%d/%m/%Y}', '5 de 5', COMENTARIO]])

        self.client.force_login(self.admin)
        ruta = reverse('gestion_reporte_unidad', args=[self.unidad.slug])
        pdf = self.client.get(ruta, self.filtros(formato='pdf'))
        self.assertEqual(pdf.status_code, 200)
        texto = ' '.join(' '.join(pagina.extract_text() for pagina in PdfReader(BytesIO(pdf.content)).pages).split())
        html = self.client.get(ruta, self.filtros())
        self.assertEqual(html.status_code, 200)
        excel = self.client.get(ruta, self.filtros(formato='xlsx'))
        self.assertEqual(excel.status_code, 200)
        hojas = str([fila for hoja in load_workbook(BytesIO(excel.content), data_only=True) for fila in hoja.values])
        word = self.client.get(ruta, self.filtros(formato='docx'))
        self.assertEqual(word.status_code, 200)
        with ZipFile(BytesIO(word.content)) as paquete:
            documento = paquete.read('word/document.xml').decode('utf-8')
        for contenido in (texto, html.content.decode('utf-8'), hojas, documento):
            self.assertIn('Satisfacción de los usuarios', contenido)
            self.assertIn('4.50', contenido)
            self.assertIn('66.7 %', contenido)
            self.assertIn('COMENTARIO-FICTICIO-QA', contenido)
            self.assertNotIn('FUERA-DEL-RANGO-QA', contenido)
            for dato in ('Zulema', 'Valoradora', 'titular-valoracion-qa', 'zulema.valoradora', 'EQ-VALORACION-QA'):
                self.assertNotIn(dato, contenido)

    def test_otra_unidad_no_ve_las_valoraciones_ajenas(self):
        ValoracionReserva.objects.create(reserva=self.reserva(), general=5, comentario=COMENTARIO)
        datos = reporte_satisfaccion(self.otra, self.desde, self.hasta)
        self.assertEqual(datos['cards'][0], ('Respuestas recibidas', 0))
        self.assertNotIn('COMENTARIO-FICTICIO-QA', str(datos))

        self.client.force_login(self.admin_otra)
        propia = self.client.get(reverse('gestion_reporte_unidad', args=[self.otra.slug]), self.filtros())
        self.assertEqual(propia.status_code, 200)
        self.assertNotIn('COMENTARIO-FICTICIO-QA', propia.content.decode('utf-8'))
        for nombre in ('gestion_reporte_unidad', 'gestion_reporte_unidad_pdf'):
            ajena = self.client.get(reverse(nombre, args=[self.unidad.slug]), self.filtros())
            self.assertEqual(ajena.status_code, 403)
