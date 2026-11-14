"""Lo propio de un observatorio: indicadores con ficha, series descargables, alertas por umbral, publicaciones con
calendario, encuestas, aliados, solicitudes de datos con cuenta y datos abiertos.

Las secciones del mapa se llenan solas con estos registros y quedan pendientes mientras no los haya; los datos
agregados se descargan en CSV y JSON con licencia CC BY 4.0, y solo un observatorio puede registrarlos.
"""
import json
from datetime import date, timedelta
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from apps.observatorios.operacion.presentation.observatorio import cumplimiento, resumen
from apps.observatorios.operacion.models.observatorios import AliadoObservatorio, EncuestaObservatorio, IndicadorObservatorio, PublicacionObservatorio, SolicitudDatos, ValorIndicador
from apps.directorio_unidades.models.core import Unidad


class FuncionesDeObservatorioTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.obs = Unidad.objects.create(
            nombre='Observatorio Agroalimentario', descripcion='Prueba.', fecha_inicio=date(2026, 1, 1),
            slug='observatorio-agro-prueba', dependencia='observatorios', clasificacion_funcional='observatorio')
        cls.precio = IndicadorObservatorio.objects.create(
            unidad=cls.obs, codigo='precio-leche', nombre='Precio de la leche al productor',
            definicion='Precio promedio pagado al productor por litro de leche cruda.', unidad_medida='USD/litro',
            fuente='Encuesta a centros de acopio', tipo_fuente='encuesta', periodicidad='mensual', sentido='subir',
            umbral_bajo=Decimal('0.45'), mensaje_alerta='El productor recibe menos del precio de sustentación.')
        for mes, valor in ((7, '0.52'), (8, '0.50'), (9, '0.44')):
            ValorIndicador.objects.create(indicador=cls.precio, periodo=f'2026-{mes:02d}', fecha=date(2026, mes, 1),
                                          valor=Decimal(valor))
        ValorIndicador.objects.create(indicador=cls.precio, periodo='2026-09', fecha=date(2026, 9, 1),
                                      territorio='Tulcán', valor=Decimal('0.43'))
        cls.papa = IndicadorObservatorio.objects.create(
            unidad=cls.obs, codigo='papa-participacion', nombre='Participación del Carchi en la papa nacional',
            definicion='Producción de papa del Carchi sobre la nacional.', unidad_medida='%',
            fuente='INEC, ESPAC', periodicidad='anual', orden=2)
        ValorIndicador.objects.create(indicador=cls.papa, periodo='2023', fecha=date(2023, 1, 1), valor=Decimal('44.0'))
        ValorIndicador.objects.create(indicador=cls.papa, periodo='2024', fecha=date(2024, 1, 1), valor=Decimal('60.7'))
        IndicadorObservatorio.objects.create(unidad=cls.obs, codigo='borrador', nombre='Indicador en borrador',
                                             definicion='-', unidad_medida='-', fuente='-', publicado=False)
        cls.ana = get_user_model().objects.create_user('ana-obs', 'ana@example.org', 'clave')
        cls.admin = get_user_model().objects.create_superuser('admin-obs', 'a@example.org', 'clave')

    def url(self, nombre, *args):
        return reverse(nombre, args=[self.obs.slug, *args])

    def test_solo_un_observatorio_registra_indicadores_y_los_umbrales_tienen_sentido(self):
        laboratorio = Unidad.objects.create(nombre='Lab', descripcion='.', fecha_inicio=date(2026, 1, 1),
                                            slug='lab-no-observa', dependencia='laboratorios')
        with self.assertRaisesMessage(ValidationError, 'Solo los observatorios'):
            IndicadorObservatorio(unidad=laboratorio, codigo='x', nombre='x', definicion='x', unidad_medida='x',
                                  fuente='x').full_clean()
        with self.assertRaisesMessage(ValidationError, 'mayor que el bajo'):
            IndicadorObservatorio(unidad=self.obs, codigo='y', nombre='y', definicion='y', unidad_medida='y', fuente='y',
                                  umbral_bajo=Decimal('5'), umbral_alto=Decimal('2')).full_clean()

    def test_el_resumen_da_ultimo_valor_cambio_tendencia_y_alerta(self):
        fila = resumen(self.precio)
        self.assertEqual((fila['ultimo'].periodo, fila['ultimo_texto'], fila['cambio_texto']), ('2026-09', '0,44', '-0,06'))
        self.assertEqual((fila['direccion'], fila['favorable'], fila['alerta']), ('baja', False, 'bajo'))
        self.assertTrue(fila['puntos'])
        self.assertEqual(resumen(self.papa)['cambio_texto'], '+16,7')

    def test_las_secciones_del_mapa_se_llenan_con_los_registros(self):
        self.client.force_login(self.admin)
        ficha = self.client.get(self.obs.get_absolute_url())
        for texto in ('Todos los indicadores (2)', 'Precio de la leche al productor', 'Fichas metodológicas (2)',
                      'Estado de las alertas (1 de 1 vigilados)', 'Solicitar datos o un análisis', 'Datos abiertos y API'):
            self.assertContains(ficha, texto)
        self.assertNotContains(ficha, 'Indicador en borrador')
        self.client.logout()
        publica = self.client.get(self.obs.get_absolute_url())
        self.assertContains(publica, 'Datos y monitoreo')
        self.assertContains(publica, 'Alertas y criterios')

    def test_las_paginas_del_visor_muestran_indicadores_ficha_y_alertas(self):
        indicadores = self.client.get(self.url('indicadores_observatorio'))
        self.assertContains(indicadores, '0,44')
        self.assertContains(indicadores, 'Bajo el umbral')
        ficha = self.client.get(self.url('indicador_observatorio', 'precio-leche'))
        self.assertContains(ficha, 'Precio promedio pagado al productor')
        self.assertContains(ficha, 'TULCÁN')
        self.assertContains(ficha, 'El productor recibe menos del precio de sustentación.')
        self.assertEqual(self.client.get(self.url('indicador_observatorio', 'borrador')).status_code, 404)
        alertas = self.client.get(self.url('alertas_observatorio'))
        self.assertContains(alertas, 'Precio de la leche al productor')
        for nombre in ('fichas_observatorio', 'datos_observatorio', 'fuentes_observatorio', 'calendario_observatorio',
                       'encuestas_observatorio', 'aliados_observatorio', 'api_datos_observatorio'):
            with self.subTest(pagina=nombre):
                self.assertEqual(self.client.get(self.url(nombre)).status_code, 200)

    def test_los_datos_se_descargan_en_csv_y_json_con_su_licencia(self):
        csv = self.client.get(self.url('datos_csv_observatorio')).content.decode('utf-8-sig')
        self.assertIn('Precio de la leche al productor;precio-leche;2026-09;2026-09-01;Carchi;0,44;USD/litro', csv)
        self.assertIn('CC BY 4.0', csv)
        self.assertNotIn('borrador', csv)
        solo = self.client.get(self.url('datos_csv_indicador_observatorio', 'papa-participacion')).content.decode('utf-8-sig')
        self.assertIn('60,7', solo)
        self.assertNotIn('precio-leche', solo)
        datos = json.loads(self.client.get(self.url('datos_json_observatorio')).content)
        self.assertEqual(datos['licencia'], 'CC BY 4.0')
        self.assertEqual([indicador['codigo'] for indicador in datos['indicadores']], ['precio-leche', 'papa-participacion'])
        self.assertEqual(self.client.get(reverse('datos_json_observatorio', args=['no-existe'])).status_code, 404)

    def test_las_publicaciones_miden_el_cumplimiento_del_calendario(self):
        hoy = timezone.localdate()
        boletin = PublicacionObservatorio.objects.create(
            unidad=self.obs, tipo='boletin', titulo='Boletín de precios de septiembre', fecha_planificada=hoy - timedelta(days=5),
            fecha_publicada=hoy - timedelta(days=6), estado='publicada', enlace='https://example.org/boletin.pdf')
        boletin.indicadores.add(self.precio)
        PublicacionObservatorio.objects.create(unidad=self.obs, tipo='informe', titulo='Informe anual',
                                               fecha_planificada=hoy - timedelta(days=1))
        PublicacionObservatorio.objects.create(unidad=self.obs, tipo='boletin', titulo='Boletín de octubre',
                                               fecha_planificada=hoy + timedelta(days=20))
        self.assertEqual(cumplimiento(self.obs), {'vencidas': 2, 'cumplidas': 1, 'a_tiempo': 1, 'porcentaje': 50})
        with self.assertRaisesMessage(ValidationError, 'necesita su archivo o su enlace'):
            PublicacionObservatorio(unidad=self.obs, titulo='Sin archivo', fecha_planificada=hoy, estado='publicada').full_clean()
        boletines = self.client.get(self.url('publicaciones_observatorio', 'boletines'))
        self.assertContains(boletines, 'Boletín de precios de septiembre')
        self.assertNotContains(boletines, 'Boletín de octubre')
        calendario = self.client.get(self.url('calendario_observatorio'))
        self.assertContains(calendario, 'Atrasada')
        self.assertContains(calendario, '50 %')
        self.assertContains(self.client.get(self.url('indicador_observatorio', 'precio-leche')), 'Boletín de precios de septiembre')

    def test_las_solicitudes_exigen_cuenta_y_cada_persona_ve_las_suyas(self):
        url = self.url('solicitudes_observatorio')
        self.assertContains(self.client.get(url), 'Iniciar sesión')
        self.assertEqual(self.client.post(url, {'descripcion': 'x', 'finalidad': 'y'}).status_code, 302)
        self.assertFalse(SolicitudDatos.objects.exists())
        self.client.force_login(self.ana)
        self.assertContains(self.client.post(url, {'tipo': 'datos', 'descripcion': '', 'finalidad': ''}),
                            'Describe qué datos necesitas')
        respuesta = self.client.post(url, {'tipo': 'datos', 'descripcion': 'Precio de la leche 2020-2026 por cantón',
                                           'finalidad': 'Tesis de Agropecuaria', 'institucion': 'UPEC'})
        self.assertRedirects(respuesta, f'{url}?enviada=1', fetch_redirect_response=False)
        solicitud = SolicitudDatos.objects.get()
        self.assertEqual((solicitud.usuario, solicitud.estado), (self.ana, 'recibida'))
        self.assertContains(self.client.get(url), 'Tesis de Agropecuaria')
        otra = get_user_model().objects.create_user('luis-obs', 'l@example.org', 'clave')
        self.client.force_login(otra)
        self.assertNotContains(self.client.get(url), 'Tesis de Agropecuaria')
        self.client.force_login(self.admin)
        self.assertContains(self.client.get(url), 'Tesis de Agropecuaria')

    def test_quien_gestiona_agrega_valores_y_responde_solicitudes_desde_la_pagina(self):
        def guardar(clave, pk, datos, padre=''):
            url = reverse('editar_registro', args=[self.obs.slug, clave, pk]) + (f'?padre={padre}' if padre else '')
            return self.client.post(url, {f'registro-{k}': v for k, v in datos.items()}, HTTP_X_REQUESTED_WITH='fetch')

        self.client.force_login(self.ana)
        self.assertEqual(guardar('valor_indicador', 'nuevo', {}, self.papa.pk).status_code, 403)
        self.client.force_login(self.admin)
        self.assertContains(self.client.get(self.url('indicador_observatorio', 'papa-participacion')), 'Agregar un valor')
        respuesta = guardar('valor_indicador', 'nuevo', {'periodo': '2025', 'fecha': '2025-01-01', 'territorio': 'Carchi',
                                                         'valor': '58.1', 'nota': 'ESPAC 2025'}, self.papa.pk)
        self.assertLess(respuesta.status_code, 400)
        self.assertEqual(resumen(self.papa)['ultimo'].periodo, '2025')
        otro = Unidad.objects.create(nombre='Otro observatorio', descripcion='.', fecha_inicio=date(2026, 1, 1),
                                     slug='otro-obs', dependencia='observatorios')
        ajeno = IndicadorObservatorio.objects.create(unidad=otro, codigo='ajeno', nombre='Ajeno', definicion='-',
                                                     unidad_medida='-', fuente='-')
        self.assertEqual(guardar('valor_indicador', 'nuevo', {'periodo': '2025', 'fecha': '2025-01-01', 'valor': '1'},
                                 ajeno.pk).status_code, 404)
        solicitud = SolicitudDatos.objects.create(unidad=self.obs, usuario=self.ana, descripcion='Serie', finalidad='Tesis')
        guardar('solicitud_datos', solicitud.pk, {'estado': 'atendida', 'respuesta': 'Te enviamos el CSV.'})
        solicitud.refresh_from_db()
        self.assertEqual((solicitud.estado, solicitud.respuesta), ('atendida', 'Te enviamos el CSV.'))
        self.assertIsNotNone(solicitud.atendida)

    def test_oferta_comparacion_participacion_y_boletin_en_pdf(self):
        oferta = self.client.get(self.url('oferta_observatorio'))
        self.assertContains(oferta, 'Cursos y capacitaciones')
        self.assertContains(oferta, 'Análisis de muestras o ensayos')
        mapas = self.client.get(self.url('mapas_observatorio'))
        self.assertContains(mapas, 'PRECIO DE LA LECHE AL PRODUCTOR')
        self.assertContains(mapas, 'Tulcán')
        participa = self.client.get(self.url('participa_observatorio'))
        self.assertContains(participa, 'Prácticas preprofesionales')
        sin_datos = IndicadorObservatorio.objects.create(unidad=self.obs, codigo='calidad', nombre='Calidad de la leche',
                                                         definicion='-', unidad_medida='-', fuente='Laboratorio')
        self.assertContains(self.client.get(self.url('participa_observatorio')), sin_datos.nombre)
        equipos = self.client.get(self.url('equipos_observatorio'))
        self.assertContains(equipos, 'El observatorio todavía no registra su espacio.')
        boletin = self.client.get(self.url('boletin_observatorio'))
        self.assertEqual(boletin['Content-Type'], 'application/pdf')
        self.assertTrue(boletin.content.startswith(b'%PDF'))

    def test_encuestas_y_aliados_se_publican_con_su_metodologia_y_su_rol(self):
        EncuestaObservatorio.objects.create(unidad=self.obs, nombre='Encuesta a centros de acopio',
                                            objetivo='Precio y volumen recibidos.', poblacion='Centros de acopio del Carchi')
        AliadoObservatorio.objects.create(unidad=self.obs, nombre='MAG Carchi', tipo='gobierno', rol='fuente',
                                          aporte='Precios del SIPA')
        encuestas = self.client.get(self.url('encuestas_observatorio'))
        self.assertContains(encuestas, 'Centros de acopio del Carchi')
        self.assertContains(encuestas, 'Ley Orgánica de Protección de Datos Personales')
        aliados = self.client.get(self.url('aliados_observatorio'))
        self.assertContains(aliados, 'APORTA DATOS')
        self.assertContains(aliados, 'Por firmar')
