"""Fase 4: los contenidos de referencia de los laboratorios se cargan en borrador.

El público no ve nada de lo cargado; quien gestiona el laboratorio lo ve marcado como
pendiente y lo activa en el editor. La carga es idempotente, no pisa lo que el laboratorio
corrigió, avisa de lo que falta y no inventa equipos ni insumos.
"""
from datetime import date
from io import StringIO

from django.contrib.auth import get_user_model
from django.core.management import call_command
from django.test import TestCase
from django.urls import reverse

from apps.laboratorios.operacion.management.laboratorios.contenidos import CONTENIDOS
from apps.recursos.models.recursos import CarpetaRecurso, Recurso
from apps.reservas.models.reservas import CatalogoActividadReserva
from apps.gestion_unidades.models.espacios import EspacioReservable
from apps.gestion_unidades.models.fichas_area import FichaArea
from apps.plantas_piloto.operacion.models.produccion import Producto, Receta
from apps.recursos.models.software import SoftwareDisponible
from apps.directorio_unidades.models.core import Unidad

SLUG = 'laboratorio-realidad-extendida'


class CargaDeContenidosTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.laboratorio = Unidad.objects.create(nombre='Laboratorio de Realidad Extendida', descripcion='.', slug=SLUG,
                                                fecha_inicio=date(2026, 1, 1), dependencia='laboratorios')
        # Falta a propósito la sala de experiencias: la carga debe avisarlo.
        for codigo in ('XR-AREA-RV', 'XR-AREA-RA', 'XR-AREA-SIM', 'XR-AREA-MOCAP', 'XR-AREA-3D'):
            EspacioReservable.objects.create(unidad=cls.laboratorio, codigo=codigo, nombre=codigo, capacidad=4)
        cls.gestor = get_user_model().objects.create_user('admin.xr.prueba', 'x@example.org', 'clave')
        cls.laboratorio.administrador = cls.gestor
        cls.laboratorio.save(update_fields=['administrador'])

    def cargar(self, *opciones):
        salida = StringIO()
        call_command('cargar_contenidos_laboratorio', '--laboratorio', SLUG, *opciones, stdout=salida)
        return salida.getvalue()

    def test_la_simulacion_no_guarda_nada(self):
        salida = self.cargar('--simular')
        self.assertIn('[simulación]', salida)
        self.assertFalse(Receta.objects.filter(unidad=self.laboratorio).exists())
        self.assertFalse(SoftwareDisponible.objects.filter(unidad=self.laboratorio).exists())

    def test_todo_queda_en_borrador_y_la_carga_es_idempotente(self):
        salida = self.cargar()
        contenido = CONTENIDOS[SLUG]
        self.assertEqual(Receta.objects.filter(unidad=self.laboratorio, activa=False, origen='referencia').count(),
                         len(contenido['procesos']))
        self.assertFalse(Producto.objects.filter(unidad=self.laboratorio, publico=True).exists())
        self.assertFalse(SoftwareDisponible.objects.filter(unidad=self.laboratorio, activo=True).exists())
        self.assertFalse(CatalogoActividadReserva.objects.filter(unidad=self.laboratorio)
                         .exclude(estado_publicacion='borrador').exists())
        carpeta = CarpetaRecurso.objects.get(unidad=self.laboratorio, nombre='Recursos en línea recomendados')
        self.assertEqual((carpeta.visibilidad, carpeta.seccion_planta), ('interna', '4.4'))
        self.assertFalse(Recurso.objects.filter(carpeta=carpeta).exclude(visibilidad='interna').exists())
        self.assertIn('XR-SALA-EXP no existe', salida)
        # Lo que el laboratorio corrigió se conserva al repetir la carga.
        proceso = Receta.objects.get(unidad=self.laboratorio, codigo='XR-PRO-RV')
        proceso.nombre = 'Experiencia de RV corregida por el laboratorio'
        proceso.save(update_fields=['nombre'])
        self.assertIn('nada nuevo', self.cargar())
        proceso.refresh_from_db()
        self.assertEqual(proceso.nombre, 'Experiencia de RV corregida por el laboratorio')
        self.assertEqual(Receta.objects.filter(unidad=self.laboratorio).count(), len(contenido['procesos']))

    def test_el_publico_no_ve_borradores_y_quien_gestiona_los_revisa(self):
        self.cargar()
        proceso = Receta.objects.get(unidad=self.laboratorio, codigo='XR-PRO-GEMELO')
        url = reverse('proceso_laboratorio', args=[SLUG, proceso.pk])
        ficha = self.client.get(self.laboratorio.get_absolute_url())
        self.assertNotContains(ficha, url)
        self.assertNotIn('procesos-productos', [modulo.clave for modulo in ficha.context['modulos']])
        self.assertEqual(self.client.get(url).status_code, 404)
        self.assertNotContains(self.client.get(reverse('productos_laboratorio', args=[SLUG])), 'Gemelo digital')

        self.client.force_login(self.gestor)
        ficha = self.client.get(self.laboratorio.get_absolute_url())
        self.assertContains(ficha, url)
        self.assertContains(ficha, 'is-pendiente')
        pagina = self.client.get(url)
        self.assertContains(pagina, 'Borrador de referencia')
        # Se revisa y activa en la propia página, sin ir al administrador.
        self.assertContains(pagina, reverse('editar_registro', args=[SLUG, 'proceso', proceso.pk]))
        self.assertContains(pagina, 'Eclipse Ditto')
        self.assertContains(self.client.get(reverse('productos_laboratorio', args=[SLUG])), 'Borrador')

        # La ficha explicativa del área también es borrador: su administrador la ve con el aviso,
        # con su diagrama, su boceto, insumos y seguridad.
        call_command('cargar_fichas_area', '--unidad', SLUG, stdout=StringIO())
        area = reverse('area_unidad', args=[SLUG, 'XR-AREA-RA'])
        pagina_area = self.client.get(area)
        for visible in ('Ficha en borrador', 'Qué es y cómo funciona', 'data-diagrama', 'data-plano',
                        'Insumos y materiales', 'data-verificacion', 'ARCore', 'Desarrollo de una aplicación de realidad aumentada',
                        'area__collage', 'data-abrir-imagen', 'data-visor', 'area__franja', 'data-videos', 'i.ytimg.com/vi/'):
            self.assertContains(pagina_area, visible)
        # Los equipos que la ficha solo describe no están registrados: no existen y no salen en la tabla de equipos.
        self.assertNotContains(pagina_area, 'data-abrir-ficha')
        # El video se inserta solo al pulsarlo: la página no trae marcos de YouTube.
        self.assertNotContains(pagina_area, '<iframe')

        # Al activarlo, el proceso se publica.
        proceso.activa = True
        proceso.save(update_fields=['activa'])
        self.client.logout()
        publica = self.client.get(url)
        self.assertEqual(publica.status_code, 200)
        self.assertNotContains(publica, 'Borrador de referencia')
        # Sin publicar, el público ve el área sin su ficha; al publicarla, la ve completa.
        self.assertNotContains(self.client.get(area), 'Qué es y cómo funciona')
        FichaArea.objects.filter(espacio__codigo='XR-AREA-RA', espacio__unidad=self.laboratorio).update(publicada=True)
        publica_area = self.client.get(area)
        self.assertContains(publica_area, 'Qué es y cómo funciona')
        self.assertNotContains(publica_area, 'Ficha en borrador')

    def test_cada_area_recibe_su_ficha_completa_y_la_carga_respeta_lo_publicado(self):
        salida = StringIO()
        call_command('cargar_fichas_area', '--unidad', SLUG, stdout=salida)
        self.assertIn('XR-SALA-EXP no existe', salida.getvalue())
        ficha = FichaArea.objects.get(espacio__unidad=self.laboratorio, espacio__codigo='XR-AREA-RA')
        self.assertFalse(ficha.publicada)
        self.assertTrue(ficha.que_es and ficha.como_funciona and ficha.lista_aplicaciones and ficha.lista_seguridad)
        self.assertGreaterEqual(len(ficha.pasos), 4)
        self.assertGreaterEqual(len(ficha.zonas), 3)
        self.assertEqual(set(ficha.elementos.values_list('tipo', flat=True)),
                         {'equipo', 'insumo', 'software', 'documento', 'imagen', 'video'})
        equipo = ficha.elementos.filter(tipo='equipo').first()
        self.assertTrue(equipo.icono and equipo.lista_especificaciones and equipo.lista_cuidados)
        for imagen in ficha.elementos.filter(tipo='imagen'):
            self.assertTrue(imagen.imagen_url and imagen.nombre)
        for video in ficha.elementos.filter(tipo='video'):
            self.assertEqual(len(video.youtube_id), 11)
        self.assertEqual(FichaArea.objects.filter(espacio__unidad=self.laboratorio).count(), 5)
        # Una ficha publicada nunca se rehace; un borrador del cargador, solo si se pide.
        ficha.que_es = 'Texto corregido por el laboratorio.'
        ficha.publicada = True
        ficha.save()
        call_command('cargar_fichas_area', '--unidad', SLUG, '--reemplazar-borradores', stdout=StringIO())
        ficha.refresh_from_db()
        self.assertEqual(ficha.que_es, 'Texto corregido por el laboratorio.')
        otra = FichaArea.objects.get(espacio__unidad=self.laboratorio, espacio__codigo='XR-AREA-RV')
        call_command('cargar_fichas_area', '--unidad', SLUG, '--reemplazar-borradores', stdout=StringIO())
        self.assertFalse(FichaArea.objects.filter(pk=otra.pk).exists())
        self.assertTrue(FichaArea.objects.filter(espacio__unidad=self.laboratorio, espacio__codigo='XR-AREA-RV').exists())
        # Con --medios, una ficha sin videos los recibe sin perder su texto ni repetir sus imágenes.
        imagenes = ficha.elementos.filter(tipo='imagen').count()
        ficha.elementos.filter(tipo='video').delete()
        call_command('cargar_fichas_area', '--unidad', SLUG, '--medios', stdout=StringIO())
        ficha.refresh_from_db()
        self.assertEqual(ficha.que_es, 'Texto corregido por el laboratorio.')
        self.assertTrue(ficha.elementos.filter(tipo='video').exists())
        self.assertEqual(ficha.elementos.filter(tipo='imagen').count(), imagenes)


class EsquemaDeFichasTests(TestCase):
    """Las fichas de todas las unidades cumplen el esquema que lee el cargador y dibuja la página."""

    def test_cada_ficha_trae_todo_lo_que_la_pagina_dibuja(self):
        from apps.gestion_unidades.management.fichas_area import FICHAS

        total = 0
        for slug, areas in FICHAS.items():
            for codigo, ficha in areas.items():
                with self.subTest(area=f'{slug}/{codigo}'):
                    total += 1
                    self.assertTrue(ficha['que_es'] and ficha['como_funciona'])
                    self.assertGreaterEqual(len(ficha['principio']), 4)
                    self.assertGreaterEqual(len(ficha['equipos']), 5)
                    nombres = {equipo['nombre'] for equipo in ficha['equipos']}
                    for _zona, _uso, equipos in ficha['distribucion']:
                        self.assertLessEqual(set(equipos), nombres)
                    for equipo in ficha['equipos']:
                        self.assertIn(equipo['nivel'], ('basico', 'alta'))
                        self.assertTrue(equipo['icono'].startswith('fas fa-'))
                        self.assertGreaterEqual(len(equipo['especificaciones']), 3)
                    self.assertGreaterEqual(len(ficha['insumos']), 3)
                    self.assertGreaterEqual(len(ficha['seguridad']), 3)
        self.assertEqual(total, 134)

    def test_cada_area_tiene_su_collage_y_sus_videos(self):
        from django.contrib.staticfiles import finders

        from apps.gestion_unidades.management.fichas_area import FICHAS
        from apps.gestion_unidades.management.fichas_area.medios import imagenes_de, videos_de

        for slug, areas in FICHAS.items():
            for codigo in areas:
                with self.subTest(area=f'{slug}/{codigo}'):
                    imagenes = imagenes_de(slug, codigo)
                    self.assertGreaterEqual(len(imagenes), 3)
                    for ruta, pie in imagenes:
                        self.assertTrue(pie and finders.find(ruta), ruta)
                    videos = videos_de(slug, codigo)
                    self.assertTrue(videos)
                    for identificador, titulo, canal, descripcion in videos:
                        self.assertRegex(identificador, r'^[A-Za-z0-9_-]{11}$')
                        self.assertTrue(titulo and canal and descripcion)
