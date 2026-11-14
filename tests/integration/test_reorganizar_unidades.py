"""La reforma entra al sistema con un comando que se puede repetir.

Renombra lo que existe, crea lo que falta con sus áreas y responsables, integra los
duplicados en la unidad que los recibe y no toca los tres laboratorios propuestos. El
nombre corto acompaña al oficial en la ficha y en el catálogo. La auditoría de una unidad
eliminada queda como histórico; los desechos y demás registros protegidos solo la desactivan.
"""
from datetime import date
from io import StringIO
from tempfile import TemporaryDirectory

from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from django.core.management import call_command
from django.test import TestCase, override_settings
from django.urls import reverse

from apps.gestion_unidades.presentation.auditoria import registrar_auditoria
from apps.recursos.models.recursos import CarpetaRecurso, ModuloUnidad, Recurso
from apps.recursos.models.equipos import EquiposServicios
from apps.gestion_unidades.models.espacios import EspacioReservable, ResponsableUnidad
from apps.formacion.models.practicas import RegistroAuditoriaUnidad
from apps.recursos.models.desechos import RegistroDesecho
from apps.directorio_unidades.models.core import Unidad
from apps.recursos.models.unidades import UnidadEquipo


def unidad(slug, nombre, dependencia='laboratorios', descripcion='Registro anterior a la reforma, con su texto.'):
    return Unidad.objects.create(slug=slug, nombre=nombre, descripcion=descripcion, fecha_inicio=date(2025, 1, 1),
                                 dependencia=dependencia)


class ReorganizarUnidadesTests(TestCase):
    def setUp(self):
        media = TemporaryDirectory()
        self.addCleanup(media.cleanup)
        self.enterContext(override_settings(MEDIA_ROOT=media.name))
        self.fablab = unidad('laboratorio-manufactura-digital-prototipado-prueba',
                             'Laboratorio de Manufactura Digital y Prototipado')
        EspacioReservable.objects.create(unidad=self.fablab, codigo='FAB-AREA-IMP3D', nombre='Área de impresión 3D',
                                         capacidad=6)
        self.impresion = unidad('fablab-impresion-3d', 'FabLab Impresión 3D')
        carpeta = CarpetaRecurso.objects.create(unidad=self.impresion, nombre='Informes')
        Recurso.objects.create(unidad=self.impresion, carpeta=carpeta, nombre='Informe 2025',
                               archivo=SimpleUploadedFile('informe.txt', b'informe'))
        self.multimedia = unidad('laboratorio-multimedia-inmersiva', 'Laboratorio Multimedia Inmersiva')
        equipo = EquiposServicios.objects.create(codigo='EQ-VISOR', nombre='Visor de realidad virtual')
        self.visor = UnidadEquipo.objects.create(codigo_unidad='EQ-VISOR-01', equipo=equipo, laboratorio=self.multimedia)
        # Un registro que no se borra con la unidad (un desecho declarado) impide eliminarla: queda desactivada.
        simulacion = unidad('laboratorio-simulacion-gemelos-digitales-prueba', 'Laboratorio de Simulación y Gemelos Digitales')
        RegistroDesecho.objects.create(unidad=simulacion, fecha_generacion=date(2026, 3, 1), clase='peligroso',
                               nombre='Solvente usado', cantidad=2)
        logistica = unidad('smart-logistics-lab', 'Laboratorio Smart Logistic', descripcion='Laboratorio de Logístiica')
        # Tenía escondidas las pestañas del mapa y una propia visible.
        logistica.modulos_contenido.exclude(clave='informacion-general').update(activo=False)
        ModuloUnidad.objects.create(unidad=logistica, clave='pestana-propia', nombre='Pestaña propia', orden=9)
        unidad('planta-piloto-hortofruticola', 'Planta Piloto Hortofrutícola', 'plantas_piloto')
        unidad('centro-experimental-san-francisco-prueba', 'Centro Experimental San Francisco (prueba)',
               'centro_experimental')
        # Con auditoría sí se borra: el histórico queda con el nombre de la unidad.
        self.bioinnovacion = unidad('bioinnovacion-aplicada', 'Bioinnovación Aplicada', 'centro_experimental')
        registrar_auditoria(None, unidad=self.bioinnovacion, accion='consultar', objeto=self.bioinnovacion,
                            descripcion='Consulta de prueba')
        unidad('laboratorio-agroalimentario', 'Observatorio de Turismo', 'observatorios')

    def correr(self, **opciones):
        salida = StringIO()
        call_command('reorganizar_unidades', stdout=salida, **opciones)
        return salida.getvalue()

    def test_renombra_crea_e_integra_segun_la_reforma(self):
        salida = self.correr()
        self.fablab.refresh_from_db()
        self.assertEqual((self.fablab.nombre, self.fablab.nombre_corto, self.fablab.area_conocimiento),
                         ('Laboratorio de Fabricación Digital y Prototipado', 'FabLab UPEC', 'ingenieria'))
        # Las unidades sembradas con «-prueba» reciben su slug definitivo.
        self.assertEqual(self.fablab.slug, 'laboratorio-fabricacion-digital-prototipado')
        self.assertEqual(self.fablab.clasificacion_funcional, 'plataforma_tecnologica')
        self.assertIn('Titular: Computación', self.fablab.carreras)
        # La descripción escrita a mano se respeta; la de relleno se reemplaza.
        self.assertEqual(self.fablab.descripcion, 'Registro anterior a la reforma, con su texto.')
        logistica = Unidad.objects.get(slug='laboratorio-logistica-comercio-internacional')
        self.assertNotIn('Logístiica', logistica.descripcion)
        self.assertEqual((logistica.nombre, logistica.nombre_corto),
                         ('Laboratorio de Logística, Transporte y Cadena de Suministro', 'Smart Logistics Lab'))
        # Las pestañas del mapa quedan visibles y en orden; la propia, oculta. Logística es solo
        # de docencia: su pestaña de investigación formativa no se ve.
        self.assertEqual(list(logistica.modulos_contenido.filter(activo=True).order_by('orden')
                              .values_list('clave', flat=True)),
                         ['informacion-general', 'areas-equipos', 'procesos-productos',
                          'docencia-capacitacion', 'reservas-servicios'])
        self.assertTrue(self.fablab.modulos_contenido.get(clave='investigacion-formativa').activo)
        self.assertFalse(logistica.modulos_contenido.get(clave='pestana-propia').activo)
        # El área que ya existía cambia de nombre sin duplicarse; las que otra reúne ya no se crean.
        areas = EspacioReservable.objects.filter(unidad=self.fablab)
        self.assertEqual(areas.count(), 7)
        self.assertEqual(areas.get(codigo='FAB-AREA-IMP3D').nombre, 'Manufactura aditiva')
        self.assertFalse(areas.filter(codigo='FAB-AREA-VINILO').exists())
        self.assertEqual(areas.filter(activo=True).count(), 7)
        # Lo que se integra pasa sus equipos y desaparece; lo que la reforma mandó borrar se borra con su historial.
        realidad = Unidad.objects.get(slug='laboratorio-realidad-extendida')
        self.visor.refresh_from_db()
        self.assertEqual(self.visor.laboratorio, realidad)
        self.assertFalse(Unidad.objects.filter(slug='laboratorio-multimedia-inmersiva').exists())
        self.assertFalse(Unidad.objects.filter(pk=self.impresion.pk).exists())
        self.assertIn('Eliminada: FabLab Impresión 3D', salida)
        self.assertIn('se borraron sus 1 documentos', salida)
        self.assertIn('Eliminada: Laboratorio Multimedia Inmersiva', salida)
        # El desecho declarado protege a la unidad: queda desactivada y el mensaje dice por qué.
        simulacion = Unidad.objects.get(slug='laboratorio-simulacion-gemelos-digitales-prueba')
        self.assertFalse(simulacion.activo)
        self.assertIn('Desactivada: Laboratorio de Simulación y Gemelos Digitales', salida)
        self.assertIn('la protegen 1 registros de desechos peligrosos y especiales', salida)
        # La auditoría no protege: la unidad se elimina y su histórico queda con su nombre y la baja.
        self.assertFalse(Unidad.objects.filter(pk=self.bioinnovacion.pk).exists())
        self.assertIn('Eliminada: Bioinnovación Aplicada', salida)
        historico = RegistroAuditoriaUnidad.objects.filter(unidad__isnull=True, unidad_nombre='Bioinnovación Aplicada')
        self.assertEqual(set(historico.values_list('accion', flat=True)), {'consultar', 'eliminar'})
        self.assertEqual(historico.get(accion='eliminar').datos_anteriores['slug'], 'bioinnovacion-aplicada')
        self.assertEqual(historico.first().nombre_unidad, 'Bioinnovación Aplicada (unidad eliminada)')
        self.client.force_login(get_user_model().objects.create_superuser('audita', 'a@example.org', 'clave'))
        self.assertContains(self.client.get(reverse('admin:formacion_registroauditoriaunidad_changelist')),
                            'Bioinnovación Aplicada (unidad eliminada)')
        # Los laboratorios nuevos nacen con sus áreas, sus cinco pestañas y su responsable.
        clinico = Unidad.objects.get(slug='laboratorio-clinico')
        self.assertEqual((clinico.area_conocimiento, clinico.espacios_reservables.count()), ('salud', 6))
        self.assertEqual(clinico.modulos_contenido.count(), 6)
        self.assertEqual(list(ResponsableUnidad.objects.filter(unidad=clinico).values_list('nombre', 'rol')),
                         [('MSc. Miguel Ger', 'coordinacion')])
        self.assertEqual(Unidad.objects.filter(dependencia='laboratorios', activo=True).count(), 18)
        # Energías Renovables nace de unir el Laboratorio de Turismo: conserva sus áreas y suma las de energía,
        # que esperan equipo. Los otros dos laboratorios propuestos no se crean.
        energias = Unidad.objects.get(nombre='Laboratorio de Energías Renovables y Territorio')
        self.assertEqual(energias.slug, 'laboratorio-energias-renovables-territorio')
        self.assertFalse(Unidad.objects.filter(slug='laboratorio-turismo').exists())
        self.assertEqual(set(energias.espacios_reservables.filter(activo=False).values_list('codigo', flat=True)),
                         {'TUR-AREA-EFICIENCIA', 'TUR-AREA-SOLAR'})
        self.assertFalse(Unidad.objects.filter(nombre__icontains='Anatomía').exists())
        self.assertFalse(Unidad.objects.filter(nombre__icontains='Ciencias Básicas').exists())
        # Plantas, centro y observatorios.
        planta = Unidad.objects.get(slug='planta-piloto-frutas-vegetales')
        self.assertEqual((planta.nombre, planta.nombre_corto),
                         ('Planta Piloto de Procesamiento de Frutas y Vegetales', 'Frutas y Vegetales'))
        centro = Unidad.objects.get(slug='centro-experimental-san-francisco')
        self.assertEqual((centro.nombre, centro.espacios_reservables.count()), ('Centro Experimental San Francisco', 9))
        # Los dos centros experimentales: el de clima frío (Huaca) y el de clima cálido (Mira).
        alonso_tadeo = Unidad.objects.get(slug='centro-experimental-alonso-tadeo')
        self.assertEqual((alonso_tadeo.dependencia, alonso_tadeo.espacios_reservables.count()), ('centro_experimental', 6))
        # Las plantas que transformarán su café y sus frutales van en el catálogo de plantas, en creación.
        self.assertEqual(set(Unidad.objects.filter(slug__in=('planta-piloto-cafe', 'planta-piloto-citricos-frutales'))
                             .values_list('dependencia', 'estado_catalogo')), {('plantas_piloto', 'en_creacion')})
        turismo = Unidad.objects.get(slug='observatorio-turismo')
        self.assertEqual(turismo.resolucion_numero, '276-CSUP-2022')
        self.assertEqual(Unidad.objects.filter(dependencia='observatorios').count(), 5)  # 3 con resolución y 2 en creación

    def test_se_puede_repetir_sin_duplicar(self):
        self.correr()
        cuentas = (Unidad.objects.count(), EspacioReservable.objects.count(), ResponsableUnidad.objects.count())
        salida = self.correr()
        self.assertEqual(cuentas, (Unidad.objects.count(), EspacioReservable.objects.count(),
                                   ResponsableUnidad.objects.count()))
        self.assertIn('0 unidades creadas', salida)
        self.assertNotIn('Eliminada', salida)

    def test_simular_no_guarda_nada(self):
        salida = self.correr(simular=True)
        self.assertIn('Simulación', salida)
        self.fablab.refresh_from_db()
        self.assertEqual(self.fablab.nombre, 'Laboratorio de Manufactura Digital y Prototipado')
        self.assertFalse(Unidad.objects.filter(slug='laboratorio-clinico').exists())

    def test_el_nombre_corto_acompana_al_oficial_en_la_ficha_y_el_catalogo(self):
        self.correr()
        self.fablab.refresh_from_db()
        ficha = self.client.get(reverse('laboratorio_detalle', args=[self.fablab.slug]))
        self.assertContains(ficha, 'Laboratorio de Fabricación Digital y Prototipado')
        self.assertContains(ficha, 'FabLab UPEC')
        catalogo = self.client.get(reverse('laboratorios_unidades'), {'busqueda': 'Fabricación Digital'})
        self.assertContains(catalogo, 'FabLab UPEC')
