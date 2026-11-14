"""Carga reproducible de la red mínima y navegación de sus contenidos específicos."""
from django.core.management import call_command
from django.test import TestCase
from django.urls import reverse

from apps.centros_id.carga import Cargador
from apps.centros_id.contenido import CONTENIDOS, cdht, ciab
from apps.centros_id.contenidos import Contenidos
from apps.centros_id.models import CentroID, EquipoCentro, Proyecto


class CatalogoInterdisciplinarioTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        call_command('cargar_centros_id', verbosity=0)

    def test_tres_centros_sin_fragmentar_las_especialidades(self):
        self.assertEqual(set(CentroID.objects.values_list('slug', flat=True)), set(CONTENIDOS))
        agro = CentroID.objects.get(slug='ciab-upec')
        self.assertIn('Agropecuaria, Alimentos y Biodiversidad', agro.nombre)
        self.assertEqual(agro.componentes.count(), 5)
        self.assertTrue(agro.componentes.filter(codigo='ciencia-tecnologia-alimentos').exists())
        humano = CentroID.objects.get(slug='cdht-upec')
        self.assertEqual(humano.componentes.count(), 6)
        self.assertEqual(humano.articulaciones.filter(tipo='carrera').count(), 13)

    def test_propuestas_no_acreditan_personas_resultados_ni_equipos(self):
        for slug in ('ciab-upec', 'cdht-upec'):
            centro = CentroID.objects.get(slug=slug)
            with self.subTest(slug=slug):
                self.assertEqual(centro.estado, 'propuesta')
                self.assertFalse(centro.identidad_validada)
                self.assertFalse(centro.estado_validado)
                self.assertFalse(centro.integrantes.exists())
                self.assertFalse(centro.proyectos.exists())
                self.assertFalse(centro.resultados.exists())
                self.assertFalse(EquipoCentro.objects.filter(componente__centro=centro).exists())
                self.assertFalse(centro.zonas.exists())
                self.assertFalse(centro.documentos.exclude(estado_documental='informativo').exists())

    def test_oferta_tiene_condiciones_y_metodos_por_area(self):
        for contenido in (ciab, cdht):
            centro = CentroID.objects.get(slug=contenido.CENTRO['slug'])
            for servicio in centro.servicios.all():
                with self.subTest(servicio=servicio.nombre):
                    self.assertEqual(servicio.estado_oferta, 'consultar')
                    for campo in ('alcance', 'exclusiones', 'entradas', 'requisitos', 'metodo',
                                  'formato_entrega', 'plazo', 'aceptacion', 'condiciones'):
                        self.assertTrue(getattr(servicio, campo), campo)
            for linea in centro.lineas.all():
                self.assertTrue(linea.problema and linea.preguntas and linea.metodologia)
                self.assertTrue(linea.retos)
            for area in centro.componentes.all():
                self.assertEqual(area.procesos.get().pasos.count(), 4)

    def test_recarga_preserva_ediciones_y_no_duplica(self):
        centro = CentroID.objects.get(slug='ciab-upec')
        servicio = centro.servicios.first()
        servicio.alcance = 'Alcance revisado por el gestor'
        servicio.save()
        linea = centro.lineas.first()
        linea.metodologia = 'Método acordado con el equipo'
        linea.save()
        antes = (centro.servicios.count(), centro.lineas.count(), centro.documentos.count())
        Cargador(ciab).cargar()
        servicio.refresh_from_db()
        linea.refresh_from_db()
        self.assertEqual(servicio.alcance, 'Alcance revisado por el gestor')
        self.assertEqual(linea.metodologia, 'Método acordado con el equipo')
        self.assertEqual(antes, (centro.servicios.count(), centro.lineas.count(), centro.documentos.count()))

    def test_tarjetas_y_secciones_publicas_navegables(self):
        respuesta = self.client.get(reverse('centros_id'))
        self.assertEqual(respuesta.status_code, 200)
        for slug in CONTENIDOS:
            self.assertContains(respuesta, 'data-centro="'+slug+'"')
        self.assertContains(respuesta, 'Carreras vinculadas')
        for slug in ('ciab-upec', 'cdht-upec'):
            for clave in ('presentacion', 'como_trabaja', 'gobierno', 'lineas', 'grupos', 'documentos', 'portafolio', 'solicitar'):
                with self.subTest(slug=slug, seccion=clave):
                    pagina = self.client.get(reverse('seccion_centro_id', args=(slug, clave)))
                    self.assertEqual(pagina.status_code, 200)
            centro = CentroID.objects.get(slug=slug)
            for area in centro.componentes.all():
                pagina = self.client.get(reverse('componente_centro_id', args=(slug, area.codigo)))
                self.assertEqual(pagina.status_code, 200)
                self.assertContains(pagina, area.nombre)

    def test_imagenes_se_cargan_una_vez_y_con_credito(self):
        for contenido in (ciab, cdht):
            centro = Cargador(contenido, medios=True).cargar()
            self.assertTrue(centro.imagen.name.endswith('.webp'))
            self.assertIn('conceptual', centro.credito_imagen)
            nombre = centro.imagen.name
            Cargador(contenido, medios=True).cargar()
            centro.refresh_from_db()
            self.assertEqual(centro.imagen.name, nombre)
            self.assertEqual(centro.imagenes.count(), 1)

    def test_las_tarjetas_son_comparables_aunque_un_centro_tenga_proyectos(self):
        centro = CentroID.objects.get(slug='cidt-upec')
        Proyecto.objects.create(centro=centro, titulo='Proyecto en ejecución', estado='ejecucion', publicado=True)
        self.assertTrue(Contenidos(centro).proyectos_activos)
        pagina = self.client.get(reverse('centros_id'))
        claves = ['areas', 'servicios', 'vinculadas', 'lineas']
        titulos = ['Áreas del centro', 'Servicios en el portafolio', 'Unidades vinculadas', 'Líneas de investigación']
        for centro in pagina.context['centros']:
            with self.subTest(centro=centro.slug):
                self.assertEqual([c['clave'] for c in centro.cifras_tarjeta], claves)
                self.assertEqual([c['titulo'] for c in centro.cifras_tarjeta], titulos)
        self.assertNotContains(pagina, 'class="cid-filtros"')
        self.assertNotContains(pagina, 'Ver servicios')
        self.assertNotContains(pagina, 'Proponer un reto')
        self.assertContains(pagina, 'class="cid-boton cid-boton--centro"', count=3)
        self.assertContains(pagina, 'data-vista="list"')
        self.assertContains(pagina, 'data-vista-centros="grid"')
        self.assertContains(pagina, 'data-vista-centros="list"')
        vacio = CentroID.objects.create(nombre='Centro sin registros', slug='sin-registros')
        self.assertEqual([c['valor'] for c in Contenidos(vacio).cifras_capacidades()], [0, 0, 0, 0])

    def test_los_totales_no_duplican_unidades_compartidas(self):
        agro = CentroID.objects.get(slug='ciab-upec')
        humano = CentroID.objects.get(slug='cdht-upec')
        compartida = agro.articulaciones.filter(tipo='unidad').first().unidad_slug
        humano.articulaciones.create(tipo='unidad', actor='Unidad compartida', unidad_slug=compartida)
        pagina = self.client.get(reverse('centros_id'))
        centros = pagina.context['centros']
        cuentas = {c['clave']: c['valor'] for c in pagina.context['cifras']}
        self.assertEqual(cuentas['centros'], 3)
        self.assertEqual(cuentas['areas'], sum(len(c.contenidos.areas) for c in centros))
        self.assertEqual(cuentas['servicios'], sum(len(c.contenidos.servicios) for c in centros))
        self.assertEqual(cuentas['lineas'], sum(len(c.contenidos.lineas) for c in centros))
        unidades = {slug for c in centros for slug in c.contenidos.unidades_vinculadas}
        self.assertEqual(cuentas['vinculadas'], len(unidades))
        self.assertLess(cuentas['vinculadas'], sum(len(c.contenidos.unidades_vinculadas) for c in centros))
