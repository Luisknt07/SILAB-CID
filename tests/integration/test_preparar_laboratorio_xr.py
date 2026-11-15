"""La preparación del Laboratorio de Realidad Extendida completa su operación sin inventar inventario ni pisar lo editado."""
import shutil
import tempfile
from datetime import date
from io import StringIO
from pathlib import Path

from django.contrib.auth import get_user_model
from django.core.management import call_command
from django.core.management.base import CommandError
from django.test import TestCase, override_settings
from django.urls import reverse

from apps.directorio_unidades.models.core import Unidad
from apps.formacion.management.cursos_precargados import realidad_extendida as curso_xr
from apps.formacion.models.cursos import Curso
from apps.formacion.models.practicas import RegistroAuditoriaUnidad
from apps.gestion_unidades.management.fichas_area import FUENTE
from apps.gestion_unidades.models.espacios import EspacioReservable
from apps.gestion_unidades.models.fichas_area import FichaArea
from apps.gestion_unidades.models.interior import MARCA_IMAGEN_REFERENCIAL, MedioInterior
from apps.gestion_unidades.models.presentacion import HitoUnidad
from apps.laboratorios.operacion.management.laboratorios import esquemas
from apps.laboratorios.operacion.management.laboratorios import realidad_extendida as datos
from apps.laboratorios.operacion.models.fablab import FablabService
from apps.recursos.models.consumibles import Consumible
from apps.recursos.models.equipos import EquiposServicios
from apps.recursos.models.recursos import Recurso
from apps.recursos.models.unidades import UnidadEquipo
from apps.reservas.models.reservas import CatalogoActividadReserva, EjemploSolicitudUnidad, GuiaActividadReserva
from apps.reservas.models.seguridad import RequisitoAcceso
from apps.reservas.presentation.seguridad import acceso_de_usuario, controla_acceso, pendientes_al_reservar

MEDIOS = tempfile.mkdtemp(prefix='citt-xr-')
PNG = b'\x89PNG'


@override_settings(MEDIA_ROOT=MEDIOS)
class PrepararLaboratorioXRTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        # El comando se limita a su slug; se aparta cualquier unidad sembrada con ese nombre.
        Unidad.objects.filter(slug=datos.SLUG).update(slug='xr-historico-prueba')
        cls.unidad = Unidad.objects.create(nombre='Laboratorio XR QA', slug=datos.SLUG, dependencia='laboratorios',
                                           descripcion='.', fecha_inicio=date(2026, 1, 1))
        cls.otra = Unidad.objects.create(nombre='Otra unidad QA', slug='xr-no-es-otra-qa', dependencia='laboratorios',
                                         descripcion='.', fecha_inicio=date(2026, 1, 1))
        cls.areas = {}
        for orden, codigo in enumerate(datos.AREAS, start=1):
            area = EspacioReservable.objects.create(unidad=cls.unidad, codigo=codigo, nombre=f'Área {codigo}', capacidad=8,
                                                    orden=orden)
            FichaArea.objects.create(espacio=area, fuente=FUENTE, distribucion=(
                'Estaciones de desarrollo | Se programa en Unity o Unreal. | Portátil de desarrollo\n'
                'Estaciones de desarrollo | Se programa en Unity con AR Foundation. | Tableta'))
            cls.areas[codigo] = area
        cls.mascaras = Consumible.objects.create(unidad=cls.unidad, codigo='XR-QA-I01', unidad_medida='unidad',
                                                 nombre='Máscaras faciales desechables')
        cls.induccion = CatalogoActividadReserva.objects.create(
            unidad=cls.unidad, proposito_codigo='capacitacion', subtipo_actividad='induccion',
            nombre=datos.ACTIVIDADES_A_PUBLICAR[0], estado_publicacion='borrador')
        cls.hito = HitoUnidad.objects.create(unidad=cls.unidad, anio=2026, titulo='Apertura',
                                             descripcion='El laboratorio abre sus seis áreas en el aula 015.')
        rv = cls.areas[datos.AREA_RV]
        for _ in range(2):
            MedioInterior.objects.create(unidad=cls.unidad, espacio=rv, tipo='foto', titulo='Realidad extendida',
                                         descripcion=MARCA_IMAGEN_REFERENCIAL + ' (copia)', imagen='unidades/interior/qa-xr.png')
        cls.foto_propia = MedioInterior.objects.create(unidad=cls.unidad, espacio=rv, tipo='foto', titulo='Foto de la sala',
                                                       imagen='unidades/interior/qa-xr.png')
        modelo = EquiposServicios.objects.create(codigo='XR-QA-GEN', nombre='Equipo de prueba QA')
        cls.equipo_de_prueba = UnidadEquipo.objects.create(codigo_unidad=datos.EQUIPO_DE_PRUEBA, equipo=modelo,
                                                           laboratorio=cls.unidad)
        cls.estudiante = get_user_model().objects.create_user('xr-estudiante', 'xr-estudiante@example.org', 'clave')
        cls.estudiante.profile.tipo_usuario = 'estudiante'
        cls.estudiante.profile.save()

    @classmethod
    def tearDownClass(cls):
        super().tearDownClass()
        shutil.rmtree(MEDIOS, ignore_errors=True)

    def ejecutar(self, aplicar=True):
        salida = StringIO()
        call_command('preparar_laboratorio_xr', aplicar=aplicar, stdout=salida)
        return salida.getvalue()

    def estado(self):
        return (FablabService.objects.count(), EjemploSolicitudUnidad.objects.count(), RequisitoAcceso.objects.count(),
                CatalogoActividadReserva.objects.count(), GuiaActividadReserva.objects.count(), Recurso.objects.count(),
                Curso.objects.count(), MedioInterior.objects.count(), UnidadEquipo.objects.count(),
                Consumible.objects.count(), RegistroAuditoriaUnidad.objects.count(),
                FichaArea.objects.filter(publicada=True).count(),
                EspacioReservable.objects.filter(visitable=True).count())

    @staticmethod
    def archivos():
        return {ruta for ruta in Path(MEDIOS).rglob('*') if ruta.is_file()}

    def test_la_simulacion_no_guarda_nada_ni_escribe_archivos(self):
        antes, archivos = self.estado(), self.archivos()
        salida = self.ejecutar(aplicar=False)
        self.assertIn('Simulación (nada se guardó)', salida)
        self.assertIn('servicios: 7', salida)
        self.assertEqual(self.estado(), antes)
        self.assertEqual(self.archivos(), archivos)
        self.hito.refresh_from_db()
        self.assertIn('seis áreas', self.hito.descripcion)

    def test_aplicar_deja_la_unidad_lista_para_atender(self):
        equipos, insumos = UnidadEquipo.objects.count(), Consumible.objects.count()
        self.ejecutar()
        unidad = Unidad.objects.get(pk=self.unidad.pk)

        servicios = FablabService.objects.filter(unidad=unidad)
        self.assertEqual(servicios.count(), len(datos.SERVICIOS))
        # Sin precios inventados: toda tarifa queda en cero hasta que la unidad la apruebe.
        self.assertFalse(servicios.exclude(tarifa_base=0, costo_hora_equipo=0, costo_hora_mano_obra=0,
                                           costo_diseno_asistido=0, costo_diseno_completo=0).exists())
        for servicio in servicios:
            self.assertEqual(servicio.imagen_referencial.read(4), PNG, servicio.code)
        self.assertEqual(EjemploSolicitudUnidad.objects.filter(unidad=unidad, activo=True).count(), len(datos.EJEMPLOS))

        requisitos = {requisito.codigo: requisito for requisito in RequisitoAcceso.objects.filter(unidad=unidad)}
        self.assertEqual(set(requisitos), {requisito['codigo'] for requisito in datos.REQUISITOS})
        self.assertEqual(requisitos['XR-ACC-HIGIENE'].consumible, self.mascaras)
        self.induccion.refresh_from_db()
        self.assertEqual(self.induccion.estado_publicacion, 'publicado')

        guias = GuiaActividadReserva.objects.filter(actividad__unidad=unidad)
        self.assertEqual(guias.count(), len(datos.GUIAS))
        for guia in guias:
            self.assertEqual((guia.estado_publicacion, guia.es_vigente, guia.secciones_faltantes()), ('publicada', True, []))

        fichas = FichaArea.objects.filter(espacio__unidad=unidad)
        self.assertFalse(fichas.exclude(publicada=True, fuente=datos.FUENTE_FICHAS).exists())
        zonas = [zona['nombre'] for zona in fichas.get(espacio=self.areas[datos.AREA_RV]).zonas]
        self.assertEqual(zonas, ['Estaciones de desarrollo', 'Estaciones de desarrollo de RA'])
        self.assertEqual(set(EspacioReservable.objects.filter(unidad=unidad, visitable=True).values_list('codigo', flat=True)),
                         set(datos.AREAS_DEL_RECORRIDO))

        self.equipo_de_prueba.refresh_from_db()
        self.assertFalse(self.equipo_de_prueba.activa)
        self.hito.refresh_from_db()
        self.assertIn('cinco áreas', self.hito.descripcion)
        fotos = MedioInterior.objects.filter(unidad=unidad, tipo='foto')
        self.assertEqual(sorted(foto.es_referencial for foto in fotos), [False, True])

        self.assertEqual(unidad.plano_espacios.read(4), PNG)
        for area in EspacioReservable.objects.filter(unidad=unidad):
            self.assertEqual(area.imagen.read(4), PNG, area.codigo)
        documentos = Recurso.objects.filter(unidad=unidad, palabras_clave__startswith=datos.MARCA)
        self.assertEqual(documentos.count(), len(datos.DOCUMENTOS))
        for documento in documentos:
            self.assertEqual(documento.archivo.read(4), b'%PDF', documento.nombre)
            self.assertEqual((documento.visibilidad, documento.activo), ('publica', True))
        curso = Curso.objects.get(unidad=unidad, nombre=curso_xr.CURSO['nombre'])
        self.assertFalse(curso.publicado)
        self.assertEqual(curso.imagen.read(4), PNG)

        # No fabrica inventario ni toca otra unidad, y deja una sola huella de auditoría.
        self.assertEqual((UnidadEquipo.objects.count(), Consumible.objects.count()), (equipos, insumos))
        self.assertEqual(RegistroAuditoriaUnidad.objects.filter(unidad=unidad, descripcion__startswith=datos.VERSION).count(), 1)
        self.assertFalse(FablabService.objects.filter(unidad=self.otra).exists())
        self.assertFalse(RequisitoAcceso.objects.filter(unidad=self.otra).exists())
        self.assertFalse(RegistroAuditoriaUnidad.objects.filter(unidad=self.otra).exists())

    def test_repetir_no_duplica_ni_pisa_lo_que_la_unidad_edito(self):
        self.ejecutar()
        estado, archivos = self.estado(), self.archivos()
        self.assertIn('nada nuevo', self.ejecutar())
        self.assertEqual((self.estado(), self.archivos()), (estado, archivos))

        # La unidad corrige textos y cambia decisiones que el cargador solo propone la primera vez.
        FablabService.objects.filter(code='XR-SRV-SESION').update(nombre='Sesión editada por la unidad', tarifa_base=5)
        RequisitoAcceso.objects.filter(unidad=self.unidad, codigo='XR-ACC-INDUCCION').update(obligatorio=False)
        EjemploSolicitudUnidad.objects.filter(unidad=self.unidad, proposito_codigo='vinculacion').update(ejemplo='Propio.')
        FichaArea.objects.filter(espacio=self.areas[datos.SALA_EXP]).update(publicada=False)
        EspacioReservable.objects.filter(unidad=self.unidad).update(visitable=False)
        CatalogoActividadReserva.objects.filter(pk=self.induccion.pk).update(estado_publicacion='borrador')
        GuiaActividadReserva.objects.filter(codigo_guia='XR-GUI-01').update(titulo='Guía adaptada')
        self.ejecutar()

        self.assertEqual(self.estado()[:11], estado[:11])
        servicio = FablabService.objects.get(code='XR-SRV-SESION')
        self.assertEqual((servicio.nombre, servicio.tarifa_base), ('Sesión editada por la unidad', 5))
        self.assertFalse(RequisitoAcceso.objects.get(unidad=self.unidad, codigo='XR-ACC-INDUCCION').obligatorio)
        self.assertEqual(EjemploSolicitudUnidad.objects.get(unidad=self.unidad, proposito_codigo='vinculacion').ejemplo, 'Propio.')
        self.assertFalse(FichaArea.objects.get(espacio=self.areas[datos.SALA_EXP]).publicada)
        self.assertFalse(EspacioReservable.objects.filter(unidad=self.unidad, visitable=True).exists())
        self.induccion.refresh_from_db()
        self.assertEqual(self.induccion.estado_publicacion, 'borrador')
        self.assertEqual(GuiaActividadReserva.objects.get(codigo_guia='XR-GUI-01').titulo, 'Guía adaptada')

    def test_lo_que_la_unidad_borra_por_error_se_repone(self):
        self.ejecutar()
        Recurso.objects.filter(unidad=self.unidad, palabras_clave=datos.MARCA + 'como-reservar').delete()
        FablabService.objects.filter(code='XR-SRV-GEMELO').delete()
        salida = self.ejecutar()
        self.assertIn('servicios: 1', salida)
        self.assertIn('documentos de la sala: 1', salida)
        self.assertEqual(Recurso.objects.filter(unidad=self.unidad, palabras_clave__startswith=datos.MARCA).count(),
                         len(datos.DOCUMENTOS))

    def test_la_induccion_se_exige_al_ingresar_y_no_al_reservar(self):
        self.assertFalse(controla_acceso(self.unidad))
        self.ejecutar()
        self.assertTrue(controla_acceso(self.unidad))
        # Quien nunca vino puede reservar; la inducción se comprueba en la puerta.
        self.assertEqual(pendientes_al_reservar(self.unidad, self.estudiante), [])
        acceso = acceso_de_usuario(self.unidad, self.estudiante)
        self.assertEqual(acceso['categoria'], 'estudiante')
        self.assertEqual(acceso['pendientes'], ['Inducción de seguridad de la sala'])
        # El personal imparte la inducción y las visitas entran con su lista: a ellos no se les exige.
        induccion = RequisitoAcceso.objects.get(unidad=self.unidad, codigo='XR-ACC-INDUCCION')
        self.assertFalse(induccion.aplica('personal') or induccion.aplica('visitante'))
        self.assertTrue(RequisitoAcceso.objects.get(unidad=self.unidad, codigo='XR-ACC-SALUD').aplica('visitante'))

    def test_las_paginas_publicas_abren_con_lo_cargado(self):
        self.ejecutar()
        for nombre, argumentos in [('area_unidad', [datos.SLUG, datos.AREA_RV]), ('area_unidad', [datos.SLUG, datos.SALA_EXP]),
                                   ('cursos_unidad', [datos.SLUG]), ('software_unidad', [datos.SLUG])]:
            with self.subTest(pagina=nombre, argumentos=argumentos):
                self.assertEqual(self.client.get(reverse(nombre, args=argumentos)).status_code, 200)

    def test_la_portada_del_curso_sin_publicar_solo_la_ve_quien_lo_prepara(self):
        self.ejecutar()
        curso = Curso.objects.get(unidad=self.unidad, nombre=curso_xr.CURSO['nombre'])
        self.assertEqual(self.client.get(curso.imagen.url).status_code, 404)
        gestor = get_user_model().objects.create_user('xr-gestor', password='clave')
        Unidad.objects.filter(pk=self.unidad.pk).update(administrador=gestor)
        self.client.force_login(gestor)
        self.assertEqual(self.client.get(curso.imagen.url).status_code, 200)
        Curso.objects.filter(pk=curso.pk).update(publicado=True)
        self.client.logout()
        self.assertEqual(self.client.get(curso.imagen.url).status_code, 200)

    def test_sin_sus_cinco_areas_no_aplica_nada(self):
        EspacioReservable.objects.filter(unidad=self.unidad, codigo=datos.AREA_META).update(activo=False)
        antes = self.estado()
        with self.assertRaisesMessage(CommandError, datos.AREA_META):
            self.ejecutar()
        self.assertEqual(self.estado(), antes)

    def test_los_datos_son_coherentes_con_lo_que_el_comando_dibuja_y_valida(self):
        self.assertEqual(set(datos.MOTIVOS_DE_AREA), set(datos.AREAS))
        self.assertEqual(set(datos.MOTIVOS_DE_SERVICIO), {servicio['code'] for servicio in datos.SERVICIOS})
        self.assertLessEqual(set(datos.MOTIVOS_DE_AREA.values()) | set(datos.MOTIVOS_DE_SERVICIO.values()), set(esquemas.MOTIVOS))
        self.assertLessEqual({guia['area'] for guia in datos.GUIAS}, set(datos.AREAS))
        self.assertLessEqual(set(datos.AREAS_DEL_RECORRIDO), set(datos.AREAS))
        # Ningún servicio declara tarifas ni costos: eso lo decide la unidad.
        for servicio in datos.SERVICIOS:
            self.assertFalse([campo for campo in servicio if campo.startswith(('tarifa', 'costo', 'descuento'))])
