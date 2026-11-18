"""Lo que un observatorio muestra y administra que un laboratorio no: tableros nativos, visores externos con sus datos,
política de datos, uso e impacto, y un panel de gestión propio.

Un observatorio no presta su sala con la agenda de reservas: la ficha ofrece «Solicitar datos» y el panel abre en sus
indicadores, sin pestañas de laboratorio. Los valores se cargan uno a uno o con la plantilla CSV; las descargas se
cuentan por día y formato sin guardar quién descarga.
"""
from datetime import date
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from apps.gestion_unidades.presentation.edicion_registro import REGISTRO
from apps.observatorios.operacion.presentation.gestion_observatorio import estado_de_actualizacion, importar_valores
from apps.gestion_unidades.models.operaciones import ConfiguracionOperativaUnidad
from apps.observatorios.operacion.models.observatorios import DescargaDatos, IndicadorObservatorio, PoliticaDatosObservatorio, TableroObservatorio, ValorIndicador, VisorExterno
from apps.directorio_unidades.models.core import Unidad


class GestionDeObservatorioTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.obs = Unidad.objects.create(
            nombre='Observatorio de prueba', descripcion='Prueba.', fecha_inicio=date(2026, 1, 1),
            slug='observatorio-gestion-prueba', dependencia='observatorios', clasificacion_funcional='observatorio')
        ConfiguracionOperativaUnidad.objects.update_or_create(unidad=cls.obs, defaults={
            'reservas_espacios': False, 'reservas_equipos': False, 'solicitudes_servicio': False,
            'acepta_visitas': True})
        cls.precio = IndicadorObservatorio.objects.create(
            unidad=cls.obs, codigo='precio-leche', nombre='Precio de la leche al productor', definicion='Precio.',
            unidad_medida='USD/litro', fuente='Encuesta a centros de acopio', periodicidad='mensual')
        for mes, valor in ((7, '0.52'), (8, '0.50'), (9, '0.47')):
            ValorIndicador.objects.create(indicador=cls.precio, periodo=f'2026-{mes:02d}', fecha=date(2026, mes, 1),
                                          valor=Decimal(valor))
        cls.papa = IndicadorObservatorio.objects.create(
            unidad=cls.obs, codigo='papa', nombre='Producción de papa', definicion='Toneladas.', unidad_medida='t',
            fuente='INEC, ESPAC', periodicidad='anual', orden=2)
        cls.tablero = TableroObservatorio.objects.create(unidad=cls.obs, titulo='Leche y papa',
                                                         descripcion='Lo esencial de la cadena.')
        cls.tablero.indicadores.set([cls.precio, cls.papa])
        cls.visor = VisorExterno.objects.create(
            unidad=cls.obs, titulo='Perfil del visitante', plataforma='powerbi',
            url='https://app.powerbi.com/view?r=abc', responsable='Carrera de Turismo')
        cls.admin = get_user_model().objects.create_superuser('obs-gestion', 'g@example.org', 'clave')
        cls.ana = get_user_model().objects.create_user('ana-gestion', 'ana@example.org', 'clave')

    def url(self, nombre, *args):
        return reverse(nombre, args=[self.obs.slug, *args])

    def test_el_tablero_nativo_muestra_cada_indicador_con_su_serie_y_sus_datos(self):
        indice = self.client.get(self.url('tableros_observatorio'))
        self.assertContains(indice, 'Leche y papa')
        self.assertNotContains(indice, 'Perfil del visitante')
        visores = self.client.get(self.url('visores_observatorio'))
        self.assertContains(visores, 'Perfil del visitante')
        self.assertContains(visores, 'sin datos descargables')
        tablero = self.client.get(self.url('tablero_observatorio', self.tablero.pk))
        self.assertContains(tablero, 'Precio de la leche al productor')
        self.assertContains(tablero, '0,47')
        self.assertContains(tablero, 'Sin datos publicados todavía.')
        self.assertContains(tablero, self.url('datos_csv_observatorio'))
        self.tablero.publicado = False
        self.tablero.save()
        self.assertEqual(self.client.get(self.url('tablero_observatorio', self.tablero.pk)).status_code, 404)

    def test_el_visor_externo_exige_https_y_avisa_cuando_no_ofrece_sus_datos(self):
        visor = self.client.get(self.url('visor_observatorio', self.visor.pk))
        self.assertContains(visor, 'src="https://app.powerbi.com/view?r=abc"')
        self.assertContains(visor, 'todavía no ofrece sus datos para descargar')
        self.assertContains(visor, 'Carrera de Turismo')
        self.visor.url_datos = 'https://datos.example.org/visitantes.csv'
        self.visor.save()
        self.assertContains(self.client.get(self.url('visor_observatorio', self.visor.pk)),
                            'Descargar los datos de este visor')
        with self.assertRaisesMessage(ValidationError, 'https'):
            VisorExterno(unidad=self.obs, titulo='x', url='http://inseguro.example.org/').full_clean()

    def test_la_politica_de_datos_separa_lo_abierto_lo_reservado_y_lo_que_se_cobra(self):
        politica = self.client.get(self.url('politica_observatorio'))
        for texto in ('Abiertos', 'Por solicitud', 'Por convenio', 'Reservados', 'Servicios con tarifa',
                      'CC BY 4.0', 'Protección de Datos Personales', 'Código Ingenios'):
            self.assertContains(politica, texto)
        self.assertContains(politica, 'Observatorio de prueba, Universidad Politécnica Estatal del Carchi')
        self.assertEqual(PoliticaDatosObservatorio.objects.filter(unidad=self.obs).count(), 1)
        edicion = REGISTRO['politica_datos']
        self.assertEqual(edicion.unico(self.obs, 'unidad').unidad, self.obs)

    def test_las_descargas_se_cuentan_por_dia_y_formato_y_se_ven_en_el_impacto(self):
        self.client.get(self.url('datos_csv_observatorio'))
        self.client.get(self.url('datos_csv_observatorio'))
        self.client.get(self.url('datos_json_observatorio'))
        hoy = timezone.localdate()
        self.assertEqual(DescargaDatos.objects.get(unidad=self.obs, fecha=hoy, formato='csv', conjunto='').veces, 2)
        self.assertEqual(DescargaDatos.objects.get(unidad=self.obs, fecha=hoy, formato='json').veces, 1)
        impacto = self.client.get(self.url('impacto_observatorio'))
        self.assertEqual(impacto.context['total_descargas'], 3)
        self.assertContains(impacto, 'sin guardar quién descarga')

    def test_la_plantilla_csv_carga_valores_nuevos_corrige_los_existentes_y_reporta_errores(self):
        self.client.force_login(self.admin)
        plantilla = self.client.get(reverse('plantilla_csv_observatorio', args=[self.obs.slug]))
        contenido = plantilla.content.decode('utf-8-sig').splitlines()
        self.assertEqual(contenido[0], 'codigo;indicador;periodo;fecha;territorio;valor;provisional;nota')
        self.assertTrue(any(fila.startswith('precio-leche;Precio de la leche al productor;') for fila in contenido))
        archivo = SimpleUploadedFile('valores.csv', (
            'codigo;indicador;periodo;fecha;territorio;valor;provisional;nota\n'
            'precio-leche;Precio;2026-09;;Carchi;0,48;;Corregido\n'
            'precio-leche;Precio;2026-10;;Carchi;0,49;sí;\n'
            'papa;Papa;2025;;Carchi;;;\n'
            'inexistente;X;2026;;Carchi;1;;\n').encode('utf-8'))
        respuesta = self.client.post(reverse('importar_valores_observatorio', args=[self.obs.slug]),
                                     {'archivo': archivo})
        self.assertRedirects(respuesta, reverse('gestion_unidad', args=[self.obs.slug]) + '?view=obs_indicadores',
                             fetch_redirect_response=False)
        septiembre = self.precio.valores.get(periodo='2026-09')
        self.assertEqual((septiembre.valor, septiembre.nota), (Decimal('0.48'), 'Corregido'))
        self.assertTrue(self.precio.valores.get(periodo='2026-10').provisional)
        self.assertFalse(self.papa.valores.exists())
        archivo = SimpleUploadedFile('malo.csv', b'codigo;valor\nprecio-leche;1\n')
        self.assertEqual(importar_valores(self.obs, archivo), (0, 0, ['Faltan las columnas: periodo.']))

    def test_solo_quien_gestiona_descarga_la_plantilla_o_carga_valores(self):
        self.client.force_login(self.ana)
        self.assertEqual(self.client.get(reverse('plantilla_csv_observatorio', args=[self.obs.slug])).status_code, 403)
        archivo = SimpleUploadedFile('v.csv', b'codigo;periodo;valor\nprecio-leche;2026-11;0,5\n')
        self.assertEqual(self.client.post(reverse('importar_valores_observatorio', args=[self.obs.slug]),
                                          {'archivo': archivo}).status_code, 403)
        self.assertFalse(self.precio.valores.filter(periodo='2026-11').exists())

    def test_un_indicador_sin_valores_recientes_queda_atrasado(self):
        ultimo = self.precio.valores.order_by('-fecha').first()
        self.assertEqual(estado_de_actualizacion(self.precio, ultimo, date(2026, 10, 5)), 'al_dia')
        self.assertEqual(estado_de_actualizacion(self.precio, ultimo, date(2027, 3, 1)), 'atrasado')
        self.assertEqual(estado_de_actualizacion(self.papa, None), 'sin_datos')

    def test_el_panel_del_observatorio_abre_en_sus_indicadores_sin_pestanas_de_laboratorio(self):
        self.client.force_login(self.admin)
        panel = self.client.get(reverse('gestion_unidad', args=[self.obs.slug]))
        self.assertEqual(panel.status_code, 200)
        self.assertEqual(panel.context['vista_gestion'], 'obs_indicadores')
        claves = [seccion['clave'] for seccion in panel.context['secciones_navegacion']]
        self.assertEqual(claves[:3], ['obs_indicadores', 'obs_publicaciones', 'obs_solicitudes'])
        # Sus equipos y su mantenimiento sí: son sus anexos 1 y 2. Lo demás de un laboratorio, no.
        for clave in ('indicadores', 'reservas', 'practicas', 'seguridad'):
            self.assertNotIn(clave, claves)
        self.assertTrue(all(seccion['habilitada'] for seccion in panel.context['secciones_navegacion']))
        self.assertContains(panel, 'Panel del observatorio')
        self.assertContains(panel, 'Gestionar observatorio')
        self.assertContains(panel, 'Precio de la leche al productor')
        # Una vista de laboratorio pedida a mano vuelve a los indicadores del observatorio.
        reservas = self.client.get(reverse('gestion_unidad', args=[self.obs.slug]) + '?view=reservas')
        self.assertEqual(reservas.context['vista_gestion'], 'obs_indicadores')

    def test_la_ficha_ofrece_solicitar_datos_en_vez_de_reservar(self):
        ficha = self.client.get(self.obs.get_absolute_url())
        self.assertContains(ficha, 'Solicitar datos')
        self.assertContains(ficha, self.url('solicitudes_observatorio'))
        self.assertNotContains(ficha, 'abrirModalEquipos()" class="unit-action unit-action--primary"')
        self.client.force_login(self.admin)
        self.assertContains(self.client.get(self.obs.get_absolute_url()), 'Gestionar observatorio')
