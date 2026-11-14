"""Los cinco observatorios: la reorganización crea los dos propuestos «En creación» y amplía el OCL a la papa; la
carga de contenidos llena indicadores, valores, encuestas, aliados y calendario sin duplicar al repetirse, respeta
lo que el observatorio editó y no marca nada como publicado."""
from decimal import Decimal
from io import StringIO

from django.core.management import call_command
from django.test import TestCase

from apps.observatorios.operacion.presentation.observatorio import alertas_vigentes, resumen
from apps.observatorios.operacion.management.observatorios.contenidos import OBSERVATORIOS
from apps.observatorios.operacion.management.observatorios.indicadores_lineas import NUEVOS
from apps.gestion_unidades.models.operaciones import ConfiguracionOperativaUnidad
from apps.observatorios.operacion.models.observatorios import IndicadorObservatorio, PublicacionObservatorio, ValorIndicador
from apps.directorio_unidades.models.core import Unidad


class ContenidosDeObservatoriosTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        call_command('reorganizar_unidades', stdout=StringIO())

    def cargar(self, *opciones):
        salida = StringIO()
        call_command('cargar_observatorios', *opciones, stdout=salida)
        return salida.getvalue()

    def test_la_reorganizacion_deja_cinco_observatorios_y_los_nuevos_en_creacion(self):
        observatorios = Unidad.objects.filter(dependencia='observatorios', activo=True)
        self.assertEqual(set(observatorios.values_list('slug', flat=True)), set(OBSERVATORIOS))
        for slug in ('observatorio-ambiental-agua-clima', 'observatorio-social-frontera'):
            unidad = Unidad.objects.get(slug=slug)
            self.assertEqual(unidad.estado_catalogo, 'en_creacion')
            self.assertEqual(unidad.get_estado_catalogo_display(), 'En creación: pendiente de su resolución')
        ocl = Unidad.objects.get(slug='observatorio-cadena-lactea-carchi')
        self.assertIn('papa', ocl.descripcion)
        self.assertEqual(ocl.resolucion_numero, '027-CSUP-2025')
        self.assertEqual(Unidad.objects.get(slug='observatorio-turismo').estado_catalogo, 'disponible')

    def test_la_carga_llena_los_cinco_sin_duplicar_y_sin_publicar_nada(self):
        self.assertIn('Simulación', self.cargar('--simular'))
        self.assertFalse(IndicadorObservatorio.objects.exists())
        self.cargar()
        esperados = (sum(len(contenido['indicadores']) for contenido in OBSERVATORIOS.values())
                     + sum(len(nuevos) for nuevos in NUEVOS.values()))
        self.assertEqual(IndicadorObservatorio.objects.count(), esperados)
        self.assertEqual(PublicacionObservatorio.objects.exclude(estado='planificada').count(), 0)
        self.assertIn('nada nuevo', self.cargar())
        social = Unidad.objects.get(slug='observatorio-social-frontera')
        self.assertIn('desnutricion-cronica', [fila['indicador'].codigo for fila in alertas_vigentes(social)])
        nbi = IndicadorObservatorio.objects.get(unidad__slug='observatorio-osezif', codigo='pobreza-nbi')
        self.assertEqual(nbi.valores.filter(fecha__year=2022).count(), 7)
        papa = IndicadorObservatorio.objects.get(codigo='papa-participacion')
        self.assertEqual(resumen(papa)['ultimo_texto'], '46,8')  # ESPAC 2025
        # Cada observatorio tiene su sala visitable (se usa con una solicitud, no con la agenda de reservas), su
        # software, las visitas abiertas, sus tableros, su política de datos y, ODETUR, sus visores de Power BI.
        turismo = Unidad.objects.get(slug='observatorio-turismo')
        sala = turismo.espacios_reservables.get()
        self.assertEqual((sala.reservable, sala.visitable, sala.ubicacion), (False, True, 'Aulas 1, planta baja, sala de Turismo'))
        self.assertTrue(turismo.software_disponible.filter(nombre='QGIS').exists())
        configuracion = ConfiguracionOperativaUnidad.objects.get(unidad=turismo)
        self.assertTrue(configuracion.acepta_visitas)
        self.assertFalse(configuracion.reservas_espacios or configuracion.reservas_equipos
                         or configuracion.solicitudes_servicio)
        visitantes = turismo.tableros_observatorio.get(titulo='Visitantes y feriados')
        self.assertEqual((visitantes.linea.codigo, visitantes.vista, visitantes.indicadores.count()), ('demanda', 'series', 7))
        self.assertEqual(set(turismo.visores_observatorio.values_list('plataforma', flat=True)),
                         {'powerbi', 'mymaps', 'tableau'})
        # Los visores propios de ODETUR no ofrecen datos para descargar; cada uno queda en su línea.
        self.assertFalse(turismo.visores_observatorio.filter(institucion='ODETUR').exclude(url_datos='').exists())
        self.assertFalse(turismo.visores_observatorio.filter(linea__isnull=True).exists())
        self.assertEqual(list(turismo.lineas_observatorio.values_list('codigo', flat=True)), ['demanda', 'oferta', 'eventos'])
        self.assertFalse(IndicadorObservatorio.objects.filter(linea__isnull=True).exists())
        # El OCL sigue tres ejes y los nombres no repiten lo que ya dice la palabra «ambiental» o «agroalimentario».
        ocl = Unidad.objects.get(slug='observatorio-cadena-lactea-carchi')
        self.assertEqual(list(ocl.lineas_observatorio.values_list('codigo', flat=True)), ['papa', 'leche', 'precios'])
        self.assertEqual(IndicadorObservatorio.objects.get(codigo='precio-leche-productor').linea.codigo, 'precios')
        self.assertEqual((ocl.nombre, Unidad.objects.get(slug='observatorio-ambiental-agua-clima').nombre),
                         ('Observatorio Agroalimentario del Carchi (OCL)', 'Observatorio Ambiental del Carchi'))
        self.assertEqual(turismo.politica_datos.licencia, 'CC BY 4.0')
        self.assertEqual((turismo.nombre, turismo.nombre_corto), ('Observatorio de Turismo del Carchi (ODETUR)', 'ODETUR'))
        self.assertFalse(turismo.categorias.exists())

    def test_la_carga_respeta_lo_editado_salvo_que_se_pida_reescribir(self):
        self.cargar()
        papa = IndicadorObservatorio.objects.get(codigo='papa-participacion')
        papa.definicion = 'Definición editada por el observatorio.'
        papa.save()
        valor = papa.valores.get(periodo='2024')
        valor.valor = Decimal('61')
        valor.save()
        self.cargar()
        papa.refresh_from_db()
        valor.refresh_from_db()
        self.assertEqual((papa.definicion, valor.valor), ('Definición editada por el observatorio.', Decimal('61')))
        self.cargar('--reescribir')
        papa.refresh_from_db()
        self.assertEqual(ValorIndicador.objects.get(pk=valor.pk).valor, Decimal('60.7'))
        self.assertIn('Producción de papa del Carchi', papa.definicion)
