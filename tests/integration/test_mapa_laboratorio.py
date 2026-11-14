"""El mapa de un laboratorio: seis pestañas y 28 secciones numeradas, como el de las plantas.

La ficha pública numera sus secciones, coloca las carpetas propias en ellas y no ofrece al
público pestañas sin nada publicado; quien gestiona las ve marcadas. El software y las
asignaturas salen de sus registros en páginas del visor; el organizador, el editor y el
tablero del admin recorren el mismo mapa; y las pestañas antiguas llegan al mapa v2 sin
perder carpetas, con la de investigación formativa solo donde el laboratorio investiga.
"""
from datetime import date
from importlib import import_module
from tempfile import TemporaryDirectory

from tests.historia import registro_anterior

from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase, override_settings
from django.urls import reverse

from apps.plantas_piloto.operacion.presentation.secciones_plantas import MAPA_LABORATORIO, MAPA_PLANTA, mapa_de
from apps.gestion_unidades.models.secciones import AjusteSeccionPlanta
from apps.formacion.models.asignaturas import Asignatura
from apps.recursos.models.recursos import CarpetaRecurso, ModuloUnidad, Recurso
from apps.recursos.models.software import SoftwareDisponible
from apps.directorio_unidades.models.core import TipoLaboratorio, Unidad

PESTANAS_V2 = ['informacion-general', 'areas-equipos', 'procesos-productos', 'docencia-capacitacion',
               'reservas-servicios', 'investigacion-formativa']


class MapaDeLaboratorioTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.laboratorio = Unidad.objects.create(
            nombre='Laboratorio con mapa', descripcion='Prueba.', fecha_inicio=date(2026, 1, 1),
            slug='laboratorio-con-mapa', dependencia='laboratorios',
            clasificacion_funcional='laboratorio_academico',
        )
        cls.admin = get_user_model().objects.create_superuser('mapa.admin', 'm@example.org', 'clave')

    def setUp(self):
        media = TemporaryDirectory()
        self.addCleanup(media.cleanup)
        self.enterContext(override_settings(MEDIA_ROOT=media.name))

    def carpeta_con_archivo(self, clave, seccion, nombre):
        modulo = self.laboratorio.modulos_contenido.get(clave=clave)
        carpeta = CarpetaRecurso.objects.create(nombre=nombre, unidad=self.laboratorio, modulo_config=modulo,
                                                seccion_planta=seccion, visibilidad='publica')
        Recurso.objects.create(nombre=f'Archivo de {nombre}', unidad=self.laboratorio, carpeta=carpeta,
                               archivo=SimpleUploadedFile('archivo.txt', b'contenido'),
                               descripcion='Material publicado.', seguridad_verificada=True)
        return carpeta

    def test_el_mapa_tiene_seis_pestanas_y_28_secciones_con_las_claves_compartidas(self):
        self.assertIs(mapa_de(self.laboratorio), MAPA_LABORATORIO)
        self.assertEqual(list(MAPA_LABORATORIO.pestanas), PESTANAS_V2)
        self.assertEqual(len(MAPA_LABORATORIO.secciones), 28)
        # La misma clave cambia de número según el mapa: las guías son 2.6 en la planta y 4.1 aquí.
        self.assertEqual((MAPA_PLANTA.numero('guias'), MAPA_LABORATORIO.numero('guias')), ('2.6', '4.1'))
        self.assertEqual((MAPA_PLANTA.numero('reservar'), MAPA_LABORATORIO.numero('reservar')), ('6.1', '5.1'))
        self.assertEqual(MAPA_LABORATORIO.numero('colaboracion_centros'), '6.2')
        self.assertEqual(MAPA_LABORATORIO.modulo_reservas, 'reservas-servicios')
        self.assertEqual(MAPA_LABORATORIO.numero('haccp'), '')
        # Las pestañas del laboratorio nacen con el mapa, en su orden.
        self.assertEqual(list(self.laboratorio.modulos_contenido.order_by('orden').values_list('clave', flat=True)),
                         PESTANAS_V2)

    def test_la_carpeta_se_valida_contra_el_mapa_de_su_tipo(self):
        docencia = self.laboratorio.modulos_contenido.get(clave='docencia-capacitacion')
        CarpetaRecurso(nombre='Guías', unidad=self.laboratorio, modulo_config=docencia,
                       seccion_planta='4.4').clean()
        with self.assertRaises(ValidationError):
            CarpetaRecurso(nombre='Corridas', unidad=self.laboratorio, modulo_config=docencia,
                           seccion_planta='4.5').clean()
        with self.assertRaises(ValidationError):
            CarpetaRecurso(nombre='Fuera de pestaña', unidad=self.laboratorio, modulo_config=docencia,
                           seccion_planta='2.4').clean()

    def test_la_ficha_numera_sus_secciones_y_solo_ofrece_al_publico_las_pestanas_con_contenido(self):
        self.carpeta_con_archivo('docencia-capacitacion', '4.4', 'Simuladores del semestre')
        pagina = self.client.get(self.laboratorio.get_absolute_url())
        self.assertEqual(pagina.status_code, 200)
        secciones = pagina.context['secciones_planta']
        self.assertEqual(secciones['guias']['numero'], '4.1')
        self.assertNotIn('haccp', secciones)
        self.assertContains(pagina, 'data-seccion="4.4"')
        self.assertContains(pagina, 'Simuladores del semestre')
        # El público ve información general, reservas y la pestaña con la carpeta; no las vacías.
        visibles = [modulo.clave for modulo in pagina.context['modulos']]
        self.assertEqual(visibles, ['informacion-general', 'docencia-capacitacion', 'reservas-servicios'])
        self.assertNotContains(pagina, 'data-modulo="procesos-productos"')
        self.assertNotContains(pagina, 'Contenido pendiente')
        # Quien gestiona ve las seis, con las vacías marcadas y sus secciones pendientes.
        self.client.force_login(self.admin)
        gestor = self.client.get(self.laboratorio.get_absolute_url())
        self.assertEqual([modulo.clave for modulo in gestor.context['modulos']], PESTANAS_V2)
        self.assertContains(gestor, 'el público no ve esta pestaña', count=3)
        self.assertContains(gestor, 'Contenido pendiente')

    def test_software_y_asignaturas_salen_de_sus_registros(self):
        SoftwareDisponible.objects.create(unidad=self.laboratorio, nombre='Fusion 360', version='2026',
                                          tipo_recurso='licencia', tipo_acceso='red')
        SoftwareDisponible.objects.create(unidad=self.laboratorio, nombre='Blender', version='4.2')
        SoftwareDisponible.objects.create(unidad=self.laboratorio, nombre='Retirado', activo=False)
        Asignatura.objects.create(unidad=self.laboratorio, codigo='ING-301', nombre='Diseño asistido',
                                  carrera='Ingeniería Industrial', semestre='Tercero')
        Asignatura.objects.create(unidad=self.laboratorio, codigo='ING-405', nombre='Prototipado',
                                  carrera='Ingeniería Industrial', semestre='Cuarto')
        Asignatura.objects.create(unidad=self.laboratorio, codigo='ART-101', nombre='Modelado 3D',
                                  carrera='Diseño', activa=False)

        software = self.client.get(reverse('software_unidad', args=[self.laboratorio.slug]))
        self.assertEqual(software.status_code, 200)
        self.assertEqual([grupo['nombre'] for grupo in software.context['grupos']],
                         ['Licencia institucional', 'Software instalado o de libre acceso'])
        self.assertEqual(software.context['seccion'], '2.3')
        self.assertContains(software, 'Fusion 360')
        self.assertNotContains(software, 'Retirado')

        asignaturas = self.client.get(reverse('asignaturas_unidad', args=[self.laboratorio.slug]))
        self.assertEqual(asignaturas.status_code, 200)
        self.assertEqual([carrera['nombre'] for carrera in asignaturas.context['carreras']], ['Ingeniería Industrial'])
        self.assertEqual((asignaturas.context['total'], asignaturas.context['seccion']), (2, '4.2'))
        self.assertNotContains(asignaturas, 'Modelado 3D')

        # La ficha las enlaza desde sus secciones 2.3 y 4.2, y por ellas el público ve esas pestañas.
        ficha = self.client.get(self.laboratorio.get_absolute_url())
        self.assertContains(ficha, reverse('software_unidad', args=[self.laboratorio.slug]))
        self.assertContains(ficha, reverse('asignaturas_unidad', args=[self.laboratorio.slug]))
        self.assertContains(ficha, 'Software y plataformas (2)')
        self.assertContains(ficha, 'Asignaturas y carreras (2)')
        self.assertContains(ficha, 'data-modulo="areas-equipos"')
        self.assertContains(ficha, 'data-modulo="docencia-capacitacion"')

    def test_el_organizador_el_editor_y_el_tablero_recorren_el_mismo_mapa(self):
        self.client.force_login(self.admin)
        organizador = self.client.get(reverse('admin:directorio_unidades_unidad_contenidos', args=[self.laboratorio.pk]))
        self.assertEqual(organizador.status_code, 200)
        self.assertContains(organizador, 'Las 28 secciones numeradas son las mismas en cada laboratorio')
        for numero in ('1-6', '2-1', '3-1', '4-1', '5-7', '6-2'):
            self.assertContains(organizador, f'id="seccion-{numero}"')
        self.assertNotContains(organizador, 'id="seccion-4-5"')
        self.assertContains(organizador, 'Se edita en')
        editor = self.client.get(reverse('admin:directorio_unidades_unidad_change', args=[self.laboratorio.pk]))
        self.assertContains(editor, 'Contenido propio del laboratorio')
        self.assertContains(editor, 'Se ve en la ficha:')
        tablero = self.client.get(reverse('admin:laboratorios_laboratorio_tablero', args=[self.laboratorio.pk]))
        self.assertContains(tablero, 'Lo que muestra la ficha pública')


class MigracionDePestanasTests(TestCase):
    """Las pestañas antiguas de un laboratorio llegan al mapa v2 sin perder carpetas ni nombres propios."""

    def laboratorio(self, slug, investiga):
        unidad = Unidad.objects.create(nombre=slug, descripcion='.', fecha_inicio=date(2025, 1, 1), slug=slug,
                                       dependencia='laboratorios')
        if investiga:
            unidad.tipos_laboratorio.add(TipoLaboratorio.objects.get_or_create(nombre='Investigación')[0])
        ModuloUnidad.objects.filter(unidad=unidad).delete()
        antiguas = ('informacion-general', 'recursos-practicas', 'tecnologia-software', 'gestion-reserva',
                    'proyectos', 'formacion-comunidad')
        modulos = {clave: ModuloUnidad.objects.create(unidad=unidad, clave=clave, nombre=clave, orden=orden)
                   for orden, clave in enumerate(antiguas, start=1)}
        return unidad, modulos

    def migrar(self):
        for nombre in ('0262_pestanas_de_laboratorio_al_mapa', '0265_mapa_v2_de_laboratorios'):
            import_module(f'apps.historial_modelos.migrations.{nombre}').alinear(registro_anterior(), None)

    def test_las_pestanas_antiguas_llegan_al_mapa_v2_y_sus_carpetas_a_su_seccion(self):
        laboratorio, modulos = self.laboratorio('laboratorio-antiguo', investiga=True)
        guias = CarpetaRecurso.objects.create(unidad=laboratorio, nombre='Guías', modulo_config=modulos['recursos-practicas'])
        anual = CarpetaRecurso.objects.create(unidad=laboratorio, nombre='2025', carpeta_padre=guias,
                                              modulo_config=modulos['recursos-practicas'])
        cursos = CarpetaRecurso.objects.create(unidad=laboratorio, nombre='Cursos abiertos',
                                               modulo_config=modulos['formacion-comunidad'])
        insumos = CarpetaRecurso.objects.create(unidad=laboratorio, nombre='Insumos',
                                                modulo_config=modulos['gestion-reserva'])
        proyectos = CarpetaRecurso.objects.create(unidad=laboratorio, nombre='Proyectos',
                                                  modulo_config=modulos['proyectos'])
        self.migrar()
        AjusteSeccionPlanta.objects.create(unidad=laboratorio, numero='6.1', titulo='Semilleros')

        self.assertEqual(list(laboratorio.modulos_contenido.order_by('orden').values_list('clave', flat=True)),
                         PESTANAS_V2)
        self.assertTrue(laboratorio.modulos_contenido.get(clave='investigacion-formativa').activo)
        self.assertTrue(laboratorio.modulos_contenido.get(clave='reservas-servicios').mostrar_herramientas_reserva)
        for carpeta in (guias, anual, cursos, insumos, proyectos):
            carpeta.refresh_from_db()
        self.assertEqual((guias.modulo_config.clave, guias.seccion_planta), ('docencia-capacitacion', '4.4'))
        self.assertEqual((anual.modulo_config_id, anual.seccion_planta), (guias.modulo_config_id, '4.4'))
        self.assertEqual((cursos.modulo_config.clave, cursos.seccion_planta), ('docencia-capacitacion', '4.3'))
        self.assertEqual((insumos.modulo_config.clave, insumos.seccion_planta), ('areas-equipos', '2.4'))
        self.assertEqual((proyectos.modulo_config.clave, proyectos.seccion_planta), ('investigacion-formativa', '6.1'))
        # Volver a correrla no cambia nada.
        import_module('apps.historial_modelos.migrations.0265_mapa_v2_de_laboratorios').alinear(registro_anterior(), None)
        self.assertEqual(laboratorio.modulos_contenido.count(), 6)
        self.assertEqual(CarpetaRecurso.objects.filter(unidad=laboratorio).count(), 5)
        self.assertEqual(AjusteSeccionPlanta.objects.get(unidad=laboratorio).numero, '6.1')

    def test_los_nombres_propios_siguen_a_su_seccion_y_sin_investigacion_la_pestana_se_oculta(self):
        laboratorio, _modulos = self.laboratorio('laboratorio-docente', investiga=False)
        import_module('apps.historial_modelos.migrations.0262_pestanas_de_laboratorio_al_mapa').alinear(registro_anterior(), None)
        AjusteSeccionPlanta.objects.create(unidad=laboratorio, numero='3.3', titulo='Talleres abiertos')
        AjusteSeccionPlanta.objects.create(unidad=laboratorio, numero='4.2', oculta=True)
        import_module('apps.historial_modelos.migrations.0265_mapa_v2_de_laboratorios').alinear(registro_anterior(), None)
        ajustes = dict(AjusteSeccionPlanta.objects.filter(unidad=laboratorio).values_list('numero', 'titulo'))
        self.assertEqual(ajustes, {'4.3': 'Talleres abiertos', '6.3': ''})
        self.assertTrue(AjusteSeccionPlanta.objects.get(unidad=laboratorio, numero='6.3').oculta)
        self.assertFalse(laboratorio.modulos_contenido.get(clave='investigacion-formativa').activo)
