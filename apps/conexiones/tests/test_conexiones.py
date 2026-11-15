"""Módulo opcional: se prueba con ``SLCID_MODULO_CONEXIONES=true``.

Sin el módulo instalado las clases se omiten una a una. No se omite el archivo
entero: la ejecución en paralelo no puede transportar un módulo omitido.
"""
import json
import unittest
from datetime import date, timedelta
from io import StringIO

from django.apps import apps
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.core.management import call_command
from django.test import Client, TestCase, override_settings
from django.urls import reverse
from django.utils import timezone

from apps.directorio_unidades.models.core import Unidad
from config.modulos import registro_de_despliegue

INSTALADO = apps.is_installed('apps.conexiones')
if INSTALADO:
    from apps.conexiones import credenciales
    from apps.conexiones.ingesta import MAX_LECTURAS_POR_LOTE
    from apps.conexiones.models import CanalMedicion, DispositivoConectado, LecturaCanal


@unittest.skipUnless(INSTALADO, 'El módulo de conexiones no está instalado en este entorno.')
class BaseConexiones(TestCase):
    @classmethod
    def setUpTestData(cls):
        Usuario = get_user_model()
        cls.gestor = Usuario.objects.create_user('gestor-conexiones')
        cls.ajeno = Usuario.objects.create_user('ajeno-conexiones')
        cls.unidad = Unidad.objects.create(
            nombre='Laboratorio conectado', slug='laboratorio-conectado', administrador=cls.gestor,
            descripcion='Pruebas de conexiones', fecha_inicio=date(2026, 1, 1), dependencia='laboratorios')
        cls.dispositivo = DispositivoConectado.objects.create(
            unidad=cls.unidad, codigo='lab-clima-01', nombre='Clima de la sala', tipo='sensor')
        cls.canal = CanalMedicion.objects.create(
            dispositivo=cls.dispositivo, clave='temperatura', nombre='Temperatura', unidad_medida='°C',
            minimo_esperado=15, maximo_esperado=30)
        cls.credencial = cls.dispositivo.generar_clave()
        cls.url = reverse('conexiones_ingesta')

    def enviar(self, lecturas, credencial=None, cliente=None, **extra):
        cabeceras = {'HTTP_AUTHORIZATION': f'Bearer {credencial or self.credencial}', **extra}
        return (cliente or self.client).post(self.url, json.dumps({'lecturas': lecturas}),
                                             content_type='application/json', **cabeceras)

    @staticmethod
    def lectura(minutos_atras=1, valor=21.5, canal='temperatura'):
        return {'canal': canal, 'instante': (timezone.now() - timedelta(minutes=minutos_atras)).isoformat(),
                'valor': valor}


class CredencialTests(BaseConexiones):
    def test_la_clave_solo_se_conoce_al_generarla_y_la_anterior_deja_de_servir(self):
        identificador, secreto = credenciales.separar(self.credencial)
        self.dispositivo.refresh_from_db()
        self.assertEqual(identificador, self.dispositivo.pk)
        self.assertNotIn(secreto, self.dispositivo.clave_hash)
        self.assertEqual(DispositivoConectado.autenticar(self.credencial), self.dispositivo)
        nueva = self.dispositivo.generar_clave()
        self.assertIsNone(DispositivoConectado.autenticar(self.credencial))
        self.assertEqual(DispositivoConectado.autenticar(nueva), self.dispositivo)

    def test_credenciales_mal_formadas_ajenas_o_de_dispositivos_inactivos_no_autentican(self):
        _, secreto = credenciales.separar(self.credencial)
        otro = DispositivoConectado.objects.create(unidad=self.unidad, codigo='lab-sin-clave', nombre='Sin clave')
        for credencial in ('', 'sin-punto', f'{self.dispositivo.pk}.corta', f'999999.{secreto}',
                           f'{otro.pk}.{secreto}', f'{otro.pk}.' + 'x' * 43, f'abc.{secreto}'):
            self.assertIsNone(DispositivoConectado.autenticar(credencial), credencial[:12])
        DispositivoConectado.objects.filter(pk=self.dispositivo.pk).update(activo=False)
        self.assertIsNone(DispositivoConectado.autenticar(self.credencial))
        DispositivoConectado.objects.filter(pk=self.dispositivo.pk).update(activo=True)
        Unidad.objects.filter(pk=self.unidad.pk).update(activo=False)
        self.assertIsNone(DispositivoConectado.autenticar(self.credencial))


class IngestaTests(BaseConexiones):
    def test_lote_valido_se_guarda_sin_sesion_ni_csrf_y_repetirlo_no_duplica(self):
        cliente = Client(enforce_csrf_checks=True)
        lote = [self.lectura(3, 20.0), self.lectura(2, 21.0), self.lectura(1, 45.0)]
        respuesta = self.enviar(lote, cliente=cliente)
        self.assertEqual(respuesta.status_code, 200, respuesta.content)
        self.assertEqual(respuesta.json(), {'aceptadas': 3, 'repetidas': 0, 'fuera_de_rango': 1, 'rechazadas': []})
        self.assertEqual(respuesta['Cache-Control'], 'no-store')
        self.assertEqual(LecturaCanal.objects.filter(canal=self.canal).count(), 3)
        self.dispositivo.refresh_from_db()
        self.assertIsNotNone(self.dispositivo.ultima_senal)
        repetido = self.enviar(lote, cliente=cliente).json()
        self.assertEqual((repetido['aceptadas'], repetido['repetidas']), (0, 3))
        self.assertEqual(LecturaCanal.objects.count(), 3)

    def test_las_lecturas_invalidas_se_devuelven_con_su_posicion_y_las_demas_se_guardan(self):
        futuro = (timezone.now() + timedelta(hours=2)).isoformat()
        antiguo = (timezone.now() - timedelta(days=90)).isoformat()
        lote = [
            self.lectura(1), 'no es un objeto', self.lectura(2, canal='desconocido'), self.lectura(3, valor=True),
            self.lectura(4, valor='21'), {'canal': 'temperatura', 'instante': '2026-11-14T10:00:00', 'valor': 1},
            {'canal': 'temperatura', 'instante': futuro, 'valor': 1},
            {'canal': 'temperatura', 'instante': antiguo, 'valor': 1},
            {'canal': 'temperatura', 'instante': 'ayer', 'valor': 1},
        ]
        datos = self.enviar(lote).json()
        self.assertEqual(datos['aceptadas'], 1)
        self.assertEqual([fila['posicion'] for fila in datos['rechazadas']], [1, 2, 3, 4, 5, 6, 7, 8])
        self.assertEqual(LecturaCanal.objects.count(), 1)

    def test_sin_credencial_valida_no_se_guarda_ni_se_distingue_el_motivo(self):
        respuestas = [
            self.client.post(self.url, '{"lecturas": []}', content_type='application/json'),
            self.enviar([self.lectura()], credencial='1.' + 'x' * 43),
            self.client.post(self.url, json.dumps({'lecturas': [self.lectura()]}), content_type='application/json',
                             HTTP_AUTHORIZATION=f'Basic {self.credencial}'),
        ]
        for respuesta in respuestas:
            self.assertEqual(respuesta.status_code, 401)
            self.assertEqual(respuesta['WWW-Authenticate'], 'Bearer')
        self.assertEqual(len({respuesta.content for respuesta in respuestas}), 1)
        self.assertFalse(LecturaCanal.objects.exists())

    def test_forma_del_envio(self):
        self.assertEqual(self.client.get(self.url).status_code, 405)
        cabecera = {'HTTP_AUTHORIZATION': f'Bearer {self.credencial}'}
        self.assertEqual(self.client.post(self.url, 'canal=1', content_type='text/plain', **cabecera).status_code, 415)
        for cuerpo in ('{"lecturas": []}', '{"otra": 1}', '{"lecturas": "no"}'):
            self.assertEqual(
                self.client.post(self.url, cuerpo, content_type='application/json', **cabecera).status_code, 400)
        exceso = [self.lectura(1)] * (MAX_LECTURAS_POR_LOTE + 1)
        self.assertEqual(self.enviar(exceso).status_code, 400)
        self.assertFalse(LecturaCanal.objects.exists())

    def test_un_canal_inactivo_o_de_otro_dispositivo_no_recibe_lecturas(self):
        otro = DispositivoConectado.objects.create(unidad=self.unidad, codigo='lab-energia-01', nombre='Energía')
        CanalMedicion.objects.create(dispositivo=otro, clave='consumo', nombre='Consumo')
        CanalMedicion.objects.filter(pk=self.canal.pk).update(activo=False)
        datos = self.enviar([self.lectura(1), self.lectura(2, canal='consumo')]).json()
        self.assertEqual((datos['aceptadas'], len(datos['rechazadas'])), (0, 2))


class SeriesTests(BaseConexiones):
    def setUp(self):
        self.base = timezone.now().replace(minute=10, second=0, microsecond=0) - timedelta(hours=3)
        LecturaCanal.objects.bulk_create([
            LecturaCanal(canal=self.canal, instante=self.base + timedelta(minutes=minuto), valor=valor)
            for minuto, valor in ((0, 20.0), (10, 22.0), (60, 24.0), (70, 26.0))
        ])
        self.url_serie = reverse('conexiones_lecturas_canal', args=[self.canal.pk])

    def test_solo_el_personal_de_la_unidad_consulta_sus_series(self):
        self.assertEqual(self.client.get(self.url_serie).status_code, 401)
        self.client.force_login(self.ajeno)
        self.assertEqual(self.client.get(self.url_serie).status_code, 403)
        self.client.force_login(self.gestor)
        self.assertEqual(self.client.get(self.url_serie).status_code, 200)
        self.assertEqual(self.client.get(reverse('conexiones_lecturas_canal', args=[999999])).status_code, 404)

    def test_serie_resumida_por_hora_y_serie_cruda(self):
        self.client.force_login(self.gestor)
        datos = self.client.get(self.url_serie).json()
        self.assertEqual(datos['canal']['clave'], 'temperatura')
        self.assertEqual([(punto['promedio'], punto['lecturas']) for punto in datos['puntos']], [(21.0, 2), (25.0, 2)])
        self.assertEqual((datos['resumen']['lecturas'], datos['resumen']['minimo'], datos['resumen']['maximo']),
                         (4, 20.0, 26.0))
        crudo = self.client.get(self.url_serie, {'intervalo': 'crudo'}).json()
        self.assertEqual([punto['valor'] for punto in crudo['puntos']], [20.0, 22.0, 24.0, 26.0])

    def test_consultas_fuera_de_contrato_se_rechazan(self):
        self.client.force_login(self.gestor)
        for parametros in ({'intervalo': 'segundo'}, {'desde': 'ayer'}, {'desde': '2026-01-01T00:00:00'},
                           {'desde': '2020-01-01T00:00:00+00:00', 'hasta': '2026-01-01T00:00:00+00:00'},
                           {'desde': '2026-02-01T00:00:00+00:00', 'hasta': '2026-01-01T00:00:00+00:00'}):
            self.assertEqual(self.client.get(self.url_serie, parametros).status_code, 400, parametros)


class LimitesDeEnvioTests(BaseConexiones):
    @override_settings(RATE_LIMIT_ENABLED=True, RATE_LIMIT_WRITE_PER_MINUTE=1, CONEXIONES_ENVIOS_POR_MINUTO=2)
    def test_cada_dispositivo_cuenta_sus_envios_y_no_los_de_su_red(self):
        otro = DispositivoConectado.objects.create(unidad=self.unidad, codigo='lab-clima-02', nombre='Clima 2')
        CanalMedicion.objects.create(dispositivo=otro, clave='temperatura', nombre='Temperatura')
        otra_credencial = otro.generar_clave()
        # El límite general de escrituras por dirección (1) no se aplica a esta entrada.
        self.assertEqual(self.enviar([self.lectura(1)]).status_code, 200)
        self.assertEqual(self.enviar([self.lectura(2)]).status_code, 200)
        excedido = self.enviar([self.lectura(3)])
        self.assertEqual(excedido.status_code, 429)
        self.assertTrue(1 <= int(excedido['Retry-After']) <= 60)
        # Otro dispositivo de la misma dirección sigue enviando.
        self.assertEqual(self.enviar([self.lectura(1)], credencial=otra_credencial).status_code, 200)
        self.assertEqual(LecturaCanal.objects.count(), 3)

    @override_settings(RATE_LIMIT_ENABLED=True)
    def test_los_intentos_sin_credencial_se_cortan_por_direccion(self):
        from apps.conexiones.presentation.views import MAX_FALLOS_POR_MINUTO

        estados = [self.enviar([self.lectura()], credencial='1.' + 'x' * 43).status_code
                   for _ in range(MAX_FALLOS_POR_MINUTO + 1)]
        self.assertEqual(set(estados[:-1]), {401})
        self.assertEqual(estados[-1], 429)
        # Los fallos no consumen el cupo de un dispositivo legítimo de esa dirección.
        self.assertEqual(self.enviar([self.lectura()]).status_code, 200)


class EstadoDeUnidadTests(BaseConexiones):
    def setUp(self):
        self.url_estado = reverse('conexiones_estado_unidad', args=[self.unidad.slug])

    def test_solo_el_personal_de_la_unidad_ve_sus_dispositivos(self):
        anonimo = self.client.get(self.url_estado)
        self.assertEqual(anonimo.status_code, 302)
        self.assertIn(reverse('login'), anonimo['Location'])
        self.client.force_login(self.ajeno)
        self.assertEqual(self.client.get(self.url_estado).status_code, 403)
        self.assertEqual(self.client.get(self.url_estado, {'formato': 'json'}).status_code, 403)
        self.client.force_login(self.gestor)
        self.assertEqual(self.client.get(reverse('conexiones_estado_unidad', args=['no-existe'])).status_code, 404)

    def test_pagina_y_json_muestran_ultima_lectura_estado_y_fuera_de_rango(self):
        CanalMedicion.objects.create(dispositivo=self.dispositivo, clave='humedad', nombre='Humedad', unidad_medida='%')
        DispositivoConectado.objects.create(unidad=self.unidad, codigo='lab-sin-uso', nombre='Sin canales', activo=False)
        self.client.force_login(self.gestor)
        pagina = self.client.get(self.url_estado)
        self.assertContains(pagina, 'Sin señal')
        self.assertContains(pagina, 'Sin lecturas')
        self.assertContains(pagina, 'Este dispositivo no tiene canales declarados.')
        self.assertEqual(self.enviar([self.lectura(5, 21.0), self.lectura(1, 45.5)]).status_code, 200)

        pagina = self.client.get(self.url_estado)
        self.assertContains(pagina, 'En línea')
        self.assertContains(pagina, '45,50 °C')
        self.assertContains(pagina, 'Fuera de rango')
        self.assertContains(pagina, '15 – 30 °C')
        self.assertContains(pagina, reverse('conexiones_lecturas_canal', args=[self.canal.pk]))
        self.assertEqual(pagina['Cache-Control'].count('no-cache'), 1)

        datos = self.client.get(self.url_estado, {'formato': 'json'}).json()
        dispositivo = next(fila for fila in datos['dispositivos'] if fila['codigo'] == 'lab-clima-01')
        self.assertTrue(dispositivo['en_linea'])
        canales = {canal['clave']: canal for canal in dispositivo['canales']}
        self.assertEqual((canales['temperatura']['valor'], canales['temperatura']['fuera_de_rango']), (45.5, True))
        self.assertIsNone(canales['humedad']['valor'])
        inactivo = next(fila for fila in datos['dispositivos'] if fila['codigo'] == 'lab-sin-uso')
        self.assertEqual((inactivo['activo'], inactivo['en_linea'], inactivo['canales']), (False, False, []))


class MantenimientoTests(BaseConexiones):
    def test_depuracion_respeta_la_retencion_de_cada_canal(self):
        CanalMedicion.objects.filter(pk=self.canal.pk).update(retencion_dias=7)
        ahora = timezone.now()
        LecturaCanal.objects.bulk_create([
            LecturaCanal(canal=self.canal, instante=ahora - timedelta(days=dias), valor=1.0) for dias in (1, 6, 8, 40)])
        salida = StringIO()
        call_command('depurar_lecturas', simular=True, stdout=salida)
        self.assertIn('2 lecturas', salida.getvalue())
        self.assertEqual(LecturaCanal.objects.count(), 4)
        call_command('depurar_lecturas', stdout=StringIO())
        self.assertEqual(LecturaCanal.objects.count(), 2)

    def test_validaciones_de_modelo_y_registro_del_modulo(self):
        canal = CanalMedicion(dispositivo=self.dispositivo, clave='humedad', nombre='Humedad',
                              minimo_esperado=80, maximo_esperado=20)
        with self.assertRaises(ValidationError):
            canal.full_clean()
        registro = registro_de_despliegue()
        self.assertIn('conexiones', registro.manifiestos)
        registro.validar_apps({config.name for config in apps.get_app_configs()})
        self.assertEqual(registro.manifiestos['conexiones'].contratos, ('lectura_dispositivo_v1',))
