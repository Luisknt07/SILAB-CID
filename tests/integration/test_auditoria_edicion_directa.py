"""Editar desde la página de la unidad deja el mismo rastro de auditoría que el panel de gestión."""
from datetime import date

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from apps.directorio_unidades.models.core import Unidad
from apps.formacion.models.practicas import RegistroAuditoriaUnidad
from apps.gestion_unidades.models.espacios import EspacioReservable
from apps.gestion_unidades.models.secciones_propias import SeccionPropia
from apps.recursos.models.recursos import CarpetaRecurso, ModuloUnidad
from tests.integration.utiles import identificar


class AuditoriaEdicionDirectaTests(TestCase):
    databases = {'default', 'centros'}

    @classmethod
    def setUpTestData(cls):
        cls.coordinador = get_user_model().objects.create_superuser('coordinador-rastro', 'rastro@example.org', 'clave')
        identificar(cls.coordinador, tipo_usuario='administrativo', carrera='')
        cls.lab = Unidad.objects.create(nombre='Laboratorio con rastro', slug='lab-rastro', dependencia='laboratorios',
                                        descripcion='.', fecha_inicio=date(2026, 1, 1), administrador=cls.coordinador)
        cls.area = EspacioReservable.objects.create(unidad=cls.lab, codigo='RAS-AREA-BASE', nombre='Sala base', capacidad=8)
        cls.modulo = ModuloUnidad.objects.get(unidad=cls.lab, clave='areas-equipos')

    def setUp(self):
        self.client.force_login(self.coordinador)

    def rastro(self, entidad):
        return list(RegistroAuditoriaUnidad.objects.filter(unidad=self.lab, entidad=entidad)
                    .order_by('pk').values_list('accion', 'objeto_id', 'usuario_id'))

    def test_altas_de_area_y_equipo(self):
        self.client.post(reverse('nueva_area', args=[self.lab.slug]),
                         {'nombre': 'Metaverso', 'tipo': 'area', 'capacidad': 12}, HTTP_X_REQUESTED_WITH='fetch')
        area = EspacioReservable.objects.get(unidad=self.lab, nombre='Metaverso')
        # Nace como plantilla: no se ofrece para reservas hasta que la unidad la habilite.
        self.assertFalse(area.reservable)
        self.assertEqual(self.rastro('gestion_unidades.EspacioReservable'),
                         [('crear', str(area.pk), self.coordinador.pk)])
        registro = RegistroAuditoriaUnidad.objects.get(entidad='gestion_unidades.EspacioReservable')
        self.assertEqual(registro.datos_nuevos['reservable'], False)

        self.client.post(reverse('nuevo_equipo', args=[self.lab.slug]), {
            'nombre': 'Visor autónomo', 'area': self.area.pk, 'marca': 'Meta', 'modelo': 'Quest 3', 'cantidad': 2},
            HTTP_X_REQUESTED_WITH='fetch')
        equipo = RegistroAuditoriaUnidad.objects.get(entidad='recursos.EquiposServicios')
        self.assertEqual((equipo.accion, len(equipo.datos_nuevos['unidades'])), ('crear', 2))

    def test_edicion_del_area(self):
        self.client.post(reverse('editar_area', args=[self.lab.slug, self.area.codigo]), {
            'seccion': 'contenido', 'ficha-que_es': 'Sala de trabajo.', 'ficha-como_funciona': 'Por turnos.'},
            HTTP_X_REQUESTED_WITH='fetch')
        self.assertEqual(self.rastro('gestion_unidades.EspacioReservable'),
                         [('actualizar', str(self.area.pk), self.coordinador.pk)])

    def test_secciones_propias_y_sus_elementos(self):
        self.client.post(reverse('nueva_seccion_propia', args=[self.lab.slug]),
                         {'titulo': 'Convenios', 'plantilla': 'tarjetas', 'modulo': self.modulo.pk},
                         HTTP_X_REQUESTED_WITH='fetch')
        seccion = SeccionPropia.objects.get(unidad=self.lab, titulo='Convenios')
        editar = reverse('editar_seccion_propia', args=[self.lab.slug, seccion.pk])
        self.client.post(editar, {'seccion-titulo': 'Alianzas', 'seccion-resumen': 'Con quién trabajamos',
                                  'seccion-plantilla': 'tabla', 'seccion-icono': 'fas fa-handshake'})
        self.assertEqual(self.rastro('gestion_unidades.SeccionPropia'),
                         [('crear', str(seccion.pk), self.coordinador.pk),
                          ('actualizar', str(seccion.pk), self.coordinador.pk)])

        muestra = seccion.elementos.first()
        self.client.post(editar, {'elemento': muestra.pk, 'elemento-titulo': 'Firma', 'elemento-orden': '1',
                                  'elemento-activo': 'on'}, HTTP_X_REQUESTED_WITH='fetch')
        self.client.post(editar, {'elemento': 'nuevo', 'elemento-titulo': 'Seguimiento', 'elemento-orden': '9',
                                  'elemento-activo': 'on'}, HTTP_X_REQUESTED_WITH='fetch')
        nuevo = seccion.elementos.get(titulo='Seguimiento')
        self.client.post(editar, {'elemento': nuevo.pk, 'elemento-titulo': 'Seguimiento', 'elemento-orden': '9',
                                  'elemento-eliminar': 'on'}, HTTP_X_REQUESTED_WITH='fetch')
        self.assertFalse(seccion.elementos.filter(titulo='Seguimiento').exists())
        self.assertEqual(self.rastro('gestion_unidades.ElementoSeccionPropia'),
                         [('actualizar', str(muestra.pk), self.coordinador.pk),
                          ('crear', str(nuevo.pk), self.coordinador.pk),
                          ('eliminar', str(nuevo.pk), self.coordinador.pk)])

    def test_editor_de_registros_de_la_pagina(self):
        carpeta = CarpetaRecurso.objects.create(unidad=self.lab, nombre='Inventario', modulo_config=self.modulo,
                                                seccion_planta='2.4', visibilidad='publica')
        url = reverse('editar_registro', args=[self.lab.slug, 'carpeta', carpeta.pk])
        self.client.post(url, {'registro-nombre': 'Inventario 2026', 'registro-visibilidad': 'restringida'})
        self.client.post(f"{reverse('editar_registro', args=[self.lab.slug, 'carpeta', 'nuevo'])}?padre={carpeta.pk}",
                         {'registro-nombre': 'Equipos de captura', 'registro-visibilidad': 'publica'})
        hija = CarpetaRecurso.objects.get(nombre='Equipos de captura')
        self.assertEqual(self.rastro('recursos.CarpetaRecurso'),
                         [('actualizar', str(carpeta.pk), self.coordinador.pk),
                          ('crear', str(hija.pk), self.coordinador.pk)])
        editado = RegistroAuditoriaUnidad.objects.filter(entidad='recursos.CarpetaRecurso').order_by('pk').first()
        self.assertEqual(editado.datos_nuevos['campos'], ['nombre', 'visibilidad'])
        # Un formulario rechazado no deja rastro.
        self.client.post(url, {'registro-nombre': '', 'registro-visibilidad': 'restringida'})
        self.assertEqual(len(self.rastro('recursos.CarpetaRecurso')), 2)
