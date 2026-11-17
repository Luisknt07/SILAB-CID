"""Dirección edita todas las metas del período en una sola tabla de Administración."""
from datetime import date

from django.contrib.admin.models import LogEntry
from django.contrib.auth import get_user_model
from django.test import RequestFactory, TestCase
from django.urls import reverse

from apps.directorio_unidades.models.core import Unidad
from apps.documentos.models.referencias_indicadores import ReferenciaIndicadorUnidad
from apps.documentos.presentation.evaluacion_cierre import medir_meta
from apps.documentos.presentation.expediente_redaccion import actividades_para
from apps.documentos.presentation.metas_administracion import tabla_de_metas
from apps.documentos.presentation.politica_metas_unidades import capacidad_de

INICIO, FIN = date(2026, 7, 1), date(2026, 12, 31)


class MetasDelPeriodoTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        usuarios = get_user_model().objects
        cls.direccion = usuarios.create_superuser('metas-direccion', password=None)
        cls.coordinador = usuarios.create_user('metas-coordinador', password=None, is_staff=True)
        cls.laboratorio = Unidad.objects.create(nombre='Laboratorio de metas', slug='laboratorio-metas',
                                                dependencia='laboratorios', administrador=cls.coordinador,
                                                fecha_inicio=date(2025, 1, 1))
        cls.ruta = reverse('admin:metas-del-periodo')

    def setUp(self):
        self.client.force_login(self.direccion)

    def formulario(self, fundamento='', **cambios):
        """Lo que envía el navegador: todas las casillas con su valor vigente, más lo que se cambia."""
        datos = {celda['campo']: celda['valor'] for grupo in tabla_de_metas()['grupos']
                 for fila in grupo['filas'] for celda in fila['celdas'] if celda['aplica']}
        datos.update({f'meta__{campo}': valor for campo, valor in cambios.items()})
        datos['fundamento'] = fundamento
        return datos

    def minimos(self):
        capacidad = capacidad_de(self.laboratorio, INICIO, FIN)
        return {a.codigo: a.minimo for a in actividades_para(self.laboratorio, capacidad=capacidad)}

    def test_la_tabla_muestra_todas_las_metas_de_cada_tipo_de_unidad(self):
        html = self.client.get(self.ruta).content.decode()
        for campo in ('laboratorios__USO', 'laboratorios__SEGURIDAD', 'laboratorios__INSPECCIONES',
                      'laboratorios__DESECHOS', 'laboratorios__PRACTICAS', 'laboratorios__PRACTICAS-PLAN',
                      'laboratorios__GUIAS', 'laboratorios__INVENTARIO', 'laboratorios__MANTENIMIENTO',
                      'laboratorios__INVESTIGACION', 'laboratorios__TRANSFERENCIA', 'laboratorios__SERVICIOS',
                      'plantas_piloto__PRODUCCION', 'plantas_piloto__CONTROL-CALIDAD',
                      'centro_experimental__ENSAYOS', 'observatorios__BOLETINES', 'observatorios__DATOS-ACTUALIZADOS'):
            self.assertIn(f'name="meta__{campo}"', html, campo)
        # Lo que el plan no propone a un tipo no se ofrece para ese tipo, ni los registros sin meta.
        for campo in ('observatorios__USO', 'laboratorios__PRODUCCION', 'laboratorios__PRESTAMOS',
                      'laboratorios__PROYECTOS'):
            self.assertNotIn(f'name="meta__{campo}"', html, campo)
        self.assertIn('name="meta__laboratorios__USO" value="100"', html)
        self.assertIn('Fundamento del cambio', html)

    def test_solo_la_administracion_general_entra(self):
        self.client.force_login(self.coordinador)
        self.assertNotEqual(self.client.get(self.ruta).status_code, 200)
        self.assertNotEqual(self.client.post(self.ruta, self.formulario('x', laboratorios__GUIAS='9')).status_code, 200)
        self.assertFalse(ReferenciaIndicadorUnidad.objects.filter(valor=9).exists())

    def test_guardar_cambia_cantidades_y_coberturas_y_el_plan_las_toma(self):
        antes = self.minimos()
        self.assertEqual(antes['USO'], '100 % de las sesiones')
        respuesta = self.client.post(self.ruta, self.formulario(
            'Acuerdo de prueba de la Dirección', laboratorios__GUIAS='3', laboratorios__USO='90',
            laboratorios__INVESTIGACION='2', laboratorios__SERVICIOS='4'), follow=True)
        self.assertContains(respuesta, 'Se guardaron 4 cambios')
        despues = self.minimos()
        self.assertEqual(despues['USO'], '90 % de las sesiones')
        self.assertEqual(despues['GUIAS'], '≥ 3 por período')
        self.assertEqual(despues['INVESTIGACION'], '≥ 2 por período')
        self.assertEqual(despues['SERVICIOS'], '≥ 4 por período')
        # Lo que no se tocó sigue igual, y el otro tipo de unidad no cambia.
        self.assertEqual(despues['SEGURIDAD'], antes['SEGURIDAD'])
        self.assertFalse(ReferenciaIndicadorUnidad.objects.filter(tipo_unidad='plantas_piloto', codigo='USO').exists())
        referencia = ReferenciaIndicadorUnidad.objects.get(tipo_unidad='laboratorios', codigo='USO')
        self.assertEqual((referencia.valor, referencia.activo, referencia.actualizado_por, referencia.fundamento),
                         (90, True, self.direccion, 'Acuerdo de prueba de la Dirección'))
        self.assertEqual(LogEntry.objects.filter(user=self.direccion).count(), 4)
        self.assertIn('name="meta__laboratorios__USO" value="90"', self.client.get(self.ruta).content.decode())

    def test_sin_fundamento_o_con_un_valor_invalido_no_se_guarda_nada(self):
        referencias = list(ReferenciaIndicadorUnidad.objects.values_list('pk', 'valor', 'activo'))
        respuesta = self.client.post(self.ruta, self.formulario(laboratorios__GUIAS='3'))
        self.assertContains(respuesta, 'Escribe el fundamento del cambio')
        # La persona no pierde lo que escribió.
        self.assertContains(respuesta, 'name="meta__laboratorios__GUIAS" value="3"')
        respuesta = self.client.post(self.ruta, self.formulario('Motivo', laboratorios__GUIAS='3',
                                                                laboratorios__USO='150'))
        self.assertContains(respuesta, 'entre 1 y 100')
        respuesta = self.client.post(self.ruta, self.formulario('Motivo', laboratorios__GUIAS='0'))
        self.assertContains(respuesta, 'entre 1 y 10000')
        self.assertEqual(list(ReferenciaIndicadorUnidad.objects.values_list('pk', 'valor', 'activo')), referencias)
        self.assertFalse(LogEntry.objects.exists())

    def test_guardar_sin_cambios_no_escribe(self):
        referencias = list(ReferenciaIndicadorUnidad.objects.values_list('pk', 'valor', 'activo', 'actualizado_en'))
        respuesta = self.client.post(self.ruta, self.formulario(), follow=True)
        self.assertContains(respuesta, 'No hubo cambios que guardar')
        self.assertEqual(list(ReferenciaIndicadorUnidad.objects.values_list('pk', 'valor', 'activo', 'actualizado_en')),
                         referencias)

    def test_dejar_la_casilla_vacia_vuelve_al_valor_inicial_del_sistema(self):
        self.client.post(self.ruta, self.formulario('Sube', laboratorios__USO='85'))
        self.assertEqual(self.minimos()['USO'], '85 % de las sesiones')
        respuesta = self.client.post(self.ruta, self.formulario('Se retira el ajuste', laboratorios__USO=''),
                                     follow=True)
        self.assertContains(respuesta, 'Se guardaron 1 cambios')
        self.assertEqual(self.minimos()['USO'], '100 % de las sesiones')
        self.assertFalse(ReferenciaIndicadorUnidad.objects.get(tipo_unidad='laboratorios', codigo='USO').activo)
        # Una casilla que no viaja en el envío no se restablece.
        self.client.post(self.ruta, {'fundamento': 'Envío parcial', 'meta__laboratorios__GUIAS': '2'})
        self.assertTrue(ReferenciaIndicadorUnidad.objects.filter(activo=True).exclude(codigo='GUIAS').exists()
                        or not ReferenciaIndicadorUnidad.objects.exclude(codigo='GUIAS').exists())

    def test_el_cierre_mide_contra_la_cobertura_que_fijo_direccion(self):
        registros = {'mediciones_porcentuales': {'SEGURIDAD': {'numerador': 9, 'denominador': 10}}}
        fila = dict(codigo='SEGURIDAD', nombre='Inducción', contador='habilitaciones', registrado=9)
        self.assertEqual(medir_meta({**fila, 'meta': '90 % de usuarios nuevos'}, registros)['porcentaje'], 100)
        self.assertEqual(medir_meta({**fila, 'meta': '100 % de usuarios nuevos'}, registros)['porcentaje'], 90)

    def test_la_tarjeta_esta_en_reportes_e_indicadores_y_el_listado_sale_de_catalogos(self):
        from django.contrib import admin
        peticion = RequestFactory().get('/admin/')
        peticion.user = self.direccion
        areas = {area['slug']: area for area in admin.site.get_app_list(peticion)}
        tarjetas = {m['object_name']: m for m in areas['reportes']['models']}
        self.assertEqual(tarjetas['metas-del-periodo']['admin_url'], self.ruta)
        self.assertEqual(tarjetas['metas-del-periodo']['name'], 'Metas del período')
        self.assertNotIn('ReferenciaIndicadorUnidad', {m['object_name'] for m in areas['catalogos']['models']})
        menu = areas['reportes']['menu_reportes']['secciones'][0]
        self.assertIn('metas-del-periodo', [t['object_name'] for c in menu['categorias']
                                             for s in c['subcategorias'] for t in s['models']])
        # El listado con el historial sigue abriéndose desde la pantalla.
        self.assertContains(self.client.get(self.ruta), reverse('admin:documentos_referenciaindicadorunidad_changelist'))
        peticion.user = self.coordinador
        visibles = {m['object_name'] for area in admin.site.get_app_list(peticion) for m in area['models']}
        self.assertNotIn('metas-del-periodo', visibles)
