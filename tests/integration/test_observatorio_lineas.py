"""Líneas temáticas, fuentes, conexiones automáticas, historial de correcciones y vistas de tablero.

Una línea es lo que en un laboratorio es un área: su página explica qué estudia y muestra sus datos vivos, sus videos
y lo que aún le falta. Las conexiones traen valores de APIs públicas (aquí, respuestas simuladas) y, si un valor ya
publicado cambia, la versión anterior queda en un historial que cualquiera descarga.
"""
from datetime import date
from decimal import Decimal
from tempfile import TemporaryDirectory
from unittest import mock

from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase, override_settings
from django.urls import reverse
from django.utils import timezone

from apps.observatorios.operacion.presentation import conectores_observatorio
from apps.observatorios.operacion.presentation.conectores_observatorio import ErrorDeConexion, pendientes, sincronizar
from apps.observatorios.operacion.models.observatorios import ConectorIndicador, DescargaDatos, FuenteDatos, ImagenLinea, IndicadorObservatorio, LineaObservatorio, RevisionValor, SolicitudDatos, TableroObservatorio, ValorIndicador
from apps.directorio_unidades.models.core import Unidad


class LineasYFuentesTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.obs = Unidad.objects.create(
            nombre='Observatorio de líneas', descripcion='Prueba.', fecha_inicio=date(2026, 1, 1),
            slug='observatorio-lineas-prueba', dependencia='observatorios', clasificacion_funcional='observatorio')
        cls.linea = LineaObservatorio.objects.create(
            unidad=cls.obs, codigo='salud', titulo='Salud y nutrición', icono='fas fa-heartbeat',
            resumen='La desnutrición y la anemia de la niñez.', que_estudia='La salud infantil del Carchi.',
            por_que_importa='La desnutrición deja daños para toda la vida.',
            preguntas='¿Baja la desnutrición?\n¿Cuánta anemia hay?', como_trabaja='Captura | ENDI del INEC\nUso | GAD',
            temas_investigacion='Factores de la desnutrición rural', pendiente='Falta la vacunación por cantón.',
            videos='abc123XYZ | Desnutrición crónica | UNICEF | Explica la desnutrición')
        cls.fuente = FuenteDatos.objects.create(nombre='INEC · ENDI', institucion='INEC', metodo='descarga',
                                                acceso='abierto', licencia='Uso con cita')
        cls.cerrada = FuenteDatos.objects.create(nombre='INAMHI · estaciones', institucion='INAMHI', metodo='solicitud',
                                                 acceso='convenio')
        cls.anemia = IndicadorObservatorio.objects.create(
            unidad=cls.obs, codigo='anemia', nombre='Anemia infantil', definicion='Anemia de 6 a 59 meses.',
            unidad_medida='%', fuente='INEC, ENDI', periodicidad='eventual', sentido='bajar', umbral_alto=Decimal('40'),
            linea=cls.linea, fuente_datos=cls.fuente)
        cls.valor = ValorIndicador.objects.create(indicador=cls.anemia, periodo='2023', fecha=date(2023, 1, 1),
                                                  valor=Decimal('39.7'), origen='cargador')
        ValorIndicador.objects.create(indicador=cls.anemia, periodo='2024', fecha=date(2024, 1, 1),
                                      valor=Decimal('48.7'), origen='cargador')
        cls.dci = IndicadorObservatorio.objects.create(
            unidad=cls.obs, codigo='dci', nombre='Desnutrición por cantón', definicion='DCI menores de 5.',
            unidad_medida='%', fuente='INEC', linea=cls.linea)
        for canton, cifra in (('Tulcán', '23.7'), ('Montúfar', '22.4'), ('Bolívar', '16.2'), ('Mira', '16.7')):
            ValorIndicador.objects.create(indicador=cls.dci, periodo='2023', fecha=date(2023, 1, 1),
                                          territorio=canton, valor=Decimal(cifra))
        cls.admin = get_user_model().objects.create_superuser('obs-lineas', 'l@example.org', 'clave')
        cls.ana = get_user_model().objects.create_user('ana-lineas', 'al@example.org', 'clave')

    def url(self, nombre, *args):
        return reverse(nombre, args=[self.obs.slug, *args])

    def test_la_linea_explica_que_estudia_con_sus_datos_videos_y_lo_que_falta(self):
        pagina = self.client.get(self.url('linea_observatorio', 'salud'))
        for texto in ('La salud infantil del Carchi.', '¿Baja la desnutrición?', 'ENDI del INEC', 'Anemia infantil',
                      'Falta la vacunación por cantón.', 'data-video="abc123XYZ"', 'Eje temático',
                      'Factores de la desnutrición rural', 'INEC · ENDI'):
            self.assertContains(pagina, texto)
        indice = self.client.get(self.url('lineas_observatorio'))
        self.assertContains(indice, 'Salud y nutrición')
        self.assertContains(indice, '1 en alerta')
        self.assertContains(self.client.get(self.url('estudios_observatorio')), 'Factores de la desnutrición rural')

    def test_el_area_muestra_su_portada_y_galeria_con_el_credito_de_cada_foto(self):
        media = TemporaryDirectory(ignore_cleanup_errors=True)
        self.addCleanup(media.cleanup)
        with override_settings(MEDIA_ROOT=media.name):
            for orden, titulo in enumerate(('Centro de salud', 'Vacunación'), start=1):
                ImagenLinea.objects.create(linea=self.linea, titulo=titulo, orden=orden, credito='Autora · CC BY-SA 4.0',
                                           fuente='https://commons.wikimedia.org/wiki/File:Ejemplo.jpg',
                                           imagen=SimpleUploadedFile(f'{orden}.jpg', b'jpg', content_type='image/jpeg'))
            pagina = self.client.get(self.url('linea_observatorio', 'salud'))
            indice = self.client.get(self.url('lineas_observatorio'))
        self.assertContains(pagina, 'Foto:')
        self.assertContains(pagina, 'Centro de salud · Autora · CC BY-SA 4.0')
        self.assertContains(pagina, 'Galería del eje')
        self.assertContains(pagina, 'data-visor-imagenes')
        self.assertContains(indice, 'obs-lineas__foto')

    def test_la_alerta_por_variacion_avisa_solo_cuando_el_indicador_empeora(self):
        self.anemia.umbral_alto = None
        self.anemia.alerta_variacion = Decimal('15')
        self.anemia.save()
        self.assertEqual(self.anemia.alerta(), 'variacion')  # De 39,7 a 48,7: sube 22,7 % y conviene que baje.
        self.anemia.alerta_variacion = Decimal('30')
        self.assertEqual(self.anemia.alerta(), '')
        self.anemia.sentido, self.anemia.alerta_variacion = 'subir', Decimal('15')
        self.assertEqual(self.anemia.alerta(), '')  # Subir es mejorar: no hay alerta.
        self.anemia.sentido = 'neutro'
        self.assertEqual(self.anemia.alerta(), '')
        self.assertTrue(self.anemia.vigilado)

    def test_el_reporte_de_la_linea_es_un_pdf_y_cuenta_su_descarga(self):
        respuesta = self.client.get(self.url('informe_linea_observatorio', 'salud'))
        self.assertEqual(respuesta['Content-Type'], 'application/pdf')
        # El visor de la página los muestra en un marco: el sitio debe permitirlo (con DENY sale el ícono roto).
        self.assertEqual(respuesta['X-Frame-Options'], 'SAMEORIGIN')
        self.assertEqual(self.client.get(self.url('boletin_observatorio'))['X-Frame-Options'], 'SAMEORIGIN')
        self.assertTrue(respuesta.content.startswith(b'%PDF'))
        self.assertTrue(DescargaDatos.objects.filter(unidad=self.obs, formato='pdf', conjunto='linea:salud').exists())
        self.linea.publicada = False
        self.linea.save()
        self.assertEqual(self.client.get(self.url('linea_observatorio', 'salud')).status_code, 404)

    def test_una_correccion_queda_en_el_historial_y_se_descarga(self):
        self.valor.valor = Decimal('49.5')
        self.valor.save()
        self.valor.save()  # Guardar sin cambiar el valor no deja otra revisión.
        revision = RevisionValor.objects.get()
        self.assertEqual((revision.anterior, revision.nuevo, revision.origen), (Decimal('39.7'), Decimal('49.5'), 'cargador'))
        csv = self.client.get(self.url('historial_observatorio')).content.decode('utf-8-sig')
        self.assertIn('anemia;2023;Carchi;39,7;49,5;Carga inicial verificada en su fuente', csv.replace('Anemia infantil;', ''))
        actualizaciones = self.client.get(self.url('actualizaciones_observatorio'))
        self.assertContains(actualizaciones, 'ÚLTIMAS CORRECCIONES')
        self.assertContains(actualizaciones, 'Carga inicial verificada en su fuente')

    def test_las_fuentes_dicen_su_acceso_y_las_conexiones_su_estado(self):
        ConectorIndicador.objects.create(indicador=self.anemia, tipo='csv', parametros={'url': 'https://example.org/a.csv'})
        pagina = self.client.get(self.url('fuentes_observatorio'))
        for texto in ('INEC · ENDI', 'Abierto y gratuito', 'CONEXIONES AUTOMÁTICAS', 'Sin ejecutar todavía',
                      'CÓMO ENTRA UN DATO AL OBSERVATORIO'):
            self.assertContains(pagina, texto)
        self.assertNotContains(pagina, 'Actualizar ahora')  # Solo quien gestiona lo ve.

    def test_las_vistas_del_tablero_dibujan_semaforo_mapa_y_comparacion(self):
        semaforo = TableroObservatorio.objects.create(unidad=self.obs, titulo='Semáforo', vista='semaforo', linea=self.linea)
        semaforo.indicadores.set([self.anemia])
        pagina = self.client.get(self.url('tablero_observatorio', semaforo.pk))
        self.assertContains(pagina, 'Fuera de su criterio de alerta')
        self.assertContains(pagina, 'is-rojo')
        mapa = TableroObservatorio.objects.create(unidad=self.obs, titulo='Mapa', vista='mapa')
        mapa.indicadores.set([self.dci, self.anemia])
        pagina = self.client.get(self.url('tablero_observatorio', mapa.pk))
        self.assertContains(pagina, '<path d="M', count=6)  # Los seis cantones, con o sin dato.
        self.assertContains(pagina, 'class="t4"')  # Tulcán, el valor más alto, en el tono más oscuro.
        self.assertContains(pagina, 'sin dato')
        self.assertContains(pagina, 'todavía no tiene valores de al menos tres cantones')
        comparacion = TableroObservatorio.objects.create(unidad=self.obs, titulo='Comparación', vista='comparacion')
        comparacion.indicadores.set([self.dci])
        self.assertContains(self.client.get(self.url('tablero_observatorio', comparacion.pk)), 'obs-barras__pista')

    def test_los_servicios_con_tarifa_explican_que_el_dato_no_se_cobra(self):
        pagina = self.client.get(self.url('servicios_observatorio'))
        self.assertContains(pagina, 'El dato abierto nunca se cobra')
        self.assertContains(pagina, '?tipo=analisis')

    def test_el_eje_dice_para_quien_sirve_y_como_obtener_sus_datos(self):
        LineaObservatorio.objects.filter(pk=self.linea.pk).update(
            usuarios='Docentes | Casos para clases de salud pública\nEstudiantes | Series para tesis de enfermería')
        IndicadorObservatorio.objects.filter(pk=self.dci.pk).update(fuente_datos=self.cerrada)
        self.assertEqual(LineaObservatorio.objects.get(pk=self.linea.pk).para_quien[1],
                         ('Estudiantes', 'Series para tesis de enfermería'))
        pagina = self.client.get(self.url('linea_observatorio', 'salud'))
        for texto in ('Para quién sirve', 'Casos para clases de salud pública', 'fas fa-user-graduate',
                      'Cómo obtener y usar sus datos', '?eje=salud', '?tipo=analisis', 'INAMHI · estaciones',
                      'Por convenio'):
            self.assertContains(pagina, texto)
        # La fuente abierta no aparece entre las que se piden en su origen.
        self.assertNotContains(pagina, 'INEC · Abierto y gratuito')
        suelto = IndicadorObservatorio.objects.create(unidad=self.obs, codigo='suelto', nombre='Indicador sin eje',
                                                      definicion='Sin eje.', unidad_medida='u', fuente='Propia')
        ValorIndicador.objects.create(indicador=suelto, periodo='2023', fecha=date(2023, 1, 1), valor=Decimal('1'))
        csv = self.client.get(self.url('datos_csv_observatorio') + '?eje=salud')
        self.assertIn('filename="observatorio-lineas-prueba-salud.csv"', csv['Content-Disposition'])
        self.assertIn('Anemia infantil', csv.content.decode('utf-8'))
        self.assertNotIn('Indicador sin eje', csv.content.decode('utf-8'))
        self.assertTrue(DescargaDatos.objects.filter(unidad=self.obs, formato='csv', conjunto='linea:salud').exists())
        self.assertEqual(self.client.get(self.url('datos_csv_observatorio') + '?eje=no-existe').status_code, 404)

    def test_las_capacitaciones_explican_como_se_piden_dictan_y_certifican(self):
        pagina = self.client.get(self.url('capacitaciones_observatorio'))
        for texto in ('Se pide', 'Se acuerda', 'Se dicta', 'Se certifica', 'código QR', 'tarifa aprobada por la universidad'):
            self.assertContains(pagina, texto)
        url = self.url('solicitudes_observatorio')
        self.client.force_login(self.ana)
        formulario = self.client.get(url + '?tipo=capacitacion&tema=Mapas%20con%20QGIS')
        self.assertContains(formulario, 'value="capacitacion" selected')
        self.assertContains(formulario, 'Mapas con QGIS')
        self.client.post(url, {'tipo': 'capacitacion', 'descripcion': 'Mapas con QGIS para 20 estudiantes',
                               'finalidad': 'Clase de Agropecuaria'})
        self.assertEqual(SolicitudDatos.objects.get(unidad=self.obs).get_tipo_display(), 'Capacitación o curso')


class ConexionesAutomaticasTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.obs = Unidad.objects.create(
            nombre='Observatorio de conexiones', descripcion='Prueba.', fecha_inicio=date(2026, 1, 1),
            slug='observatorio-conexiones-prueba', dependencia='observatorios', clasificacion_funcional='observatorio')
        cls.trm = IndicadorObservatorio.objects.create(
            unidad=cls.obs, codigo='trm', nombre='Pesos por dólar', definicion='TRM.', unidad_medida='COP por USD',
            fuente='datos.gov.co', periodicidad='mensual', territorio_principal='Frontera')
        cls.conector = ConectorIndicador.objects.create(indicador=cls.trm, tipo='socrata', parametros={
            'dominio': 'www.datos.gov.co', 'conjunto': '32sa-8pi3', 'campo_fecha': 'vigenciadesde',
            'campo_valor': 'valor::number', 'agregacion': 'avg', 'por': 'mes', 'territorio': 'Frontera'})
        cls.admin = get_user_model().objects.create_superuser('obs-conexiones', 'c@example.org', 'clave')

    def test_socrata_por_fecha_trae_valores_marca_el_mes_en_curso_y_registra_correcciones(self):
        hoy = timezone.localdate()
        respuesta = [{'periodo': '2025-01-01T00:00:00.000', 'valor': '4300.5'},
                     {'periodo': f'{hoy:%Y-%m}-01T00:00:00.000', 'valor': '3300'}]
        with mock.patch.object(conectores_observatorio, '_json', return_value=respuesta) as consulta:
            self.assertEqual(sincronizar(self.conector), (2, 0))
        url = consulta.call_args.args[0]
        self.assertIn('32sa-8pi3.json', url)
        self.assertIn('avg%28valor%3A%3Anumber%29', url)
        enero = ValorIndicador.objects.get(indicador=self.trm, periodo='2025-01')
        self.assertEqual((enero.valor, enero.provisional, enero.origen, enero.territorio),
                         (Decimal('4300.5'), False, 'api', 'Frontera'))
        self.assertTrue(ValorIndicador.objects.get(indicador=self.trm, periodo=f'{hoy:%Y-%m}').provisional)
        respuesta[0]['valor'] = '4310'
        with mock.patch.object(conectores_observatorio, '_json', return_value=respuesta):
            self.assertEqual(sincronizar(self.conector), (0, 1))
        self.assertEqual(RevisionValor.objects.get().origen, 'api')
        self.conector.refresh_from_db()
        self.assertEqual(self.conector.estado, 'ok')
        self.assertFalse(self.conector.vencido())
        self.assertEqual(pendientes(self.obs), [])

    def test_socrata_con_anio_y_mes_en_texto_como_migracion_colombia(self):
        conector = ConectorIndicador(indicador=self.trm, tipo='socrata', parametros={
            'dominio': 'www.datos.gov.co', 'conjunto': '96sh-4v8d', 'campo_anio': 'a_o', 'campo_mes': 'mes',
            'campo_valor': 'total::number', 'filtro': "ubicacion_pcm='(0.814836,-77.662532)'", 'desde_anio': '2025'})
        filas = [{'anio': '2025', 'mes': 'Enero', 'valor': '6778'}, {'anio': '2025', 'mes': 'Agosto', 'valor': '13755'},
                 {'anio': '2025', 'mes': 'Desconocido', 'valor': '1'}]
        with mock.patch.object(conectores_observatorio, '_json', return_value=filas) as consulta:
            valores = conectores_observatorio.socrata(conector.parametros)
        self.assertEqual([(periodo, cifra) for periodo, _fecha, cifra in valores],
                         [('2025-01', Decimal('6778')), ('2025-08', Decimal('13755'))])
        self.assertIn('a_o+%3E%3D+%272025%27', consulta.call_args.args[0])

    def test_un_csv_publicado_por_anio_y_un_error_queda_registrado(self):
        conector = ConectorIndicador(indicador=self.trm, tipo='csv', parametros={
            'url': 'https://example.org/perdida.csv', 'columna_periodo': 'anio', 'columna_valor': 'ha', 'desde_anio': '2021'})
        with mock.patch.object(conectores_observatorio, '_leer', return_value=b'anio,ha\n2020,299.5\n2021,201.8\n'):
            self.assertEqual(conectores_observatorio.csv_publicado(conector.parametros),
                             [('2021', date(2021, 1, 1), Decimal('201.8'))])
        with mock.patch.object(conectores_observatorio, '_json', side_effect=ErrorDeConexion('La fuente no respondió')):
            self.assertEqual(sincronizar(self.conector), (0, 0))
        self.conector.refresh_from_db()
        self.assertEqual((self.conector.estado, self.conector.mensaje), ('error', 'La fuente no respondió'))

    def test_los_focos_de_calor_se_cuentan_por_dia_solo_dentro_del_carchi(self):
        from apps.core.presentation.cantones_carchi import canton_de

        self.assertEqual(canton_de(0.81, -77.72), 'Tulcán')
        self.assertEqual(canton_de(0.60, -77.83), 'Montúfar')
        self.assertIsNone(canton_de(0.20, -78.0))  # Imbabura: fuera del Carchi.
        hoy = timezone.localdate()
        archivo = ('latitude,longitude,acq_date,confidence\n'
                   f'0.81,-77.72,{hoy:%Y-%m-%d},nominal\n'
                   f'0.60,-77.83,{hoy:%Y-%m-%d},high\n'
                   f'0.20,-78.0,{hoy:%Y-%m-%d},high\n'
                   '0.81,-77.72,2026-01-02,low\n'
                   '-6.19,-35.24,2026-01-01,nominal\n').encode('utf-8')
        focos = IndicadorObservatorio.objects.create(unidad=self.obs, codigo='focos', nombre='Focos de calor',
                                                     definicion='Focos.', unidad_medida='focos', fuente='NASA FIRMS',
                                                     periodicidad='diaria')
        conector = ConectorIndicador.objects.create(indicador=focos, tipo='firms', parametros={
            'url': 'https://example.org/firms.csv', 'por': 'dia'})
        with mock.patch.object(conectores_observatorio, '_leer', return_value=archivo):
            self.assertEqual(sincronizar(conector), (3, 0))
        valores = {v.periodo: (int(v.valor), v.provisional) for v in ValorIndicador.objects.filter(indicador=focos)}
        # Los días del archivo sin focos en el Carchi valen cero; el día en curso es provisional.
        self.assertEqual(valores, {'2026-01-01': (0, False), '2026-01-02': (1, False), f'{hoy:%Y-%m-%d}': (2, True)})
        with mock.patch.object(conectores_observatorio, '_leer', return_value=archivo):
            self.assertEqual(conectores_observatorio.focos_de_calor({'url': 'x', 'confianza_minima': 'high'})[-1][2], 1)

    def test_quien_gestiona_actualiza_desde_el_panel_y_vuelve_sin_salir_del_sitio(self):
        url = reverse('sincronizar_observatorio', args=[self.obs.slug])
        self.client.force_login(get_user_model().objects.create_user('ana-conexiones', 'ac@example.org', 'clave'))
        self.assertEqual(self.client.post(url).status_code, 403)
        self.client.force_login(self.admin)
        panel = self.client.get(reverse('gestion_unidad', args=[self.obs.slug]))
        self.assertContains(panel, 'Automático')
        self.assertContains(panel, 'se actualiza solo desde una API pública')
        with mock.patch.object(conectores_observatorio, '_json', return_value=[]):
            respuesta = self.client.post(url, {'volver': 'https://sitio-ajeno.example.org/'})
        self.assertRedirects(respuesta, reverse('gestion_unidad', args=[self.obs.slug]) + '?view=obs_indicadores',
                             fetch_redirect_response=False)
        with mock.patch.object(conectores_observatorio, '_json', return_value=[]):
            respuesta = self.client.post(url, {'volver': '/observatorio/observatorio-conexiones-prueba/fuentes/'})
        self.assertEqual(respuesta['Location'], '/observatorio/observatorio-conexiones-prueba/fuentes/')
