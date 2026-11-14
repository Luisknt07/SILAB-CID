"""«Contenidos de la ficha»: el menú público de una unidad, organizado desde el admin.

Las secciones comunes de una planta se ven con lo que las llena solas, se
renombran u ocultan por unidad y se restablecen; las carpetas propias se crean,
editan, mueven, ocultan y solo se eliminan vacías. Lo oculto sale de la ficha
pública y sus archivos dejan de abrirse para el público.
"""
import re
from datetime import date

from django.contrib.auth import get_user_model
from django.contrib.auth.models import AnonymousUser
from django.urls import reverse

from apps.formacion.presentation.recursos_publicos import _acceso_recurso
from apps.gestion_unidades.models.secciones import AjusteSeccionPlanta
from apps.recursos.models.recursos import CarpetaRecurso, ModuloUnidad, Recurso
from apps.directorio_unidades.models.core import Unidad
from tests.integration.test_reserva_por_proceso import BasePracticaPorProceso


class BaseContenidos(BasePracticaPorProceso):
    def setUp(self):
        super().setUp()
        self.admin = get_user_model().objects.create_superuser('contenidos.admin', 'c@example.org', 'clave')
        self.client.force_login(self.admin)
        self.url = reverse('admin:plantas_piloto_plantapiloto_contenidos', args=[self.unidad.pk])

    def actuar(self, accion, **datos):
        return self.client.post(self.url, {'accion': accion, **datos}, follow=True)

    def ficha(self):
        return self.client.get(self.unidad.get_absolute_url()).content.decode()

    def carpeta(self, nombre='Normas INEN', seccion='1.4', **datos):
        return CarpetaRecurso.objects.create(
            unidad=self.unidad, nombre=nombre, seccion_planta=seccion, visibilidad='publica',
            modulo_config=ModuloUnidad.objects.get(unidad=self.unidad, clave='informacion-general'), **datos)


class ContenidosDeLaFichaTests(BaseContenidos):
    databases = {'default', 'centros'}
    def test_informacion_general_muestra_sus_cinco_secciones_y_de_donde_salen(self):
        pagina = self.client.get(self.url)
        self.assertEqual(pagina.status_code, 200)
        html = pagina.content.decode()
        posiciones = [html.index(titulo) for titulo in ('Presentación', 'La unidad', 'La planta por dentro',
                                                       'Normativa y marco sanitario', 'Repositorio y descargas')]
        self.assertEqual(posiciones, sorted(posiciones))
        self.assertContains(pagina, 'Ninguno: se llena solo con carpetas propias.')
        self.assertContains(pagina, 'id="seccion-5-3"')
        # Se llega desde el editor de la planta, su tablero y su tarjeta en el inicio del admin.
        for origen in (reverse('admin:plantas_piloto_plantapiloto_change', args=[self.unidad.pk]),
                       reverse('admin:plantas_piloto_plantapiloto_tablero', args=[self.unidad.pk]),
                       reverse('admin:index')):
            self.assertContains(self.client.get(origen), self.url)

    def test_una_seccion_se_renombra_se_oculta_y_se_restablece(self):
        self.assertContains(self.actuar('renombrar_seccion', numero='1.4', nombre='Normas sanitarias'),
                            'La sección 1.4 ahora se llama «Normas sanitarias».')
        self.assertIn('aria-label="Normas sanitarias"', self.ficha())
        self.actuar('renombrar_seccion', numero='5.3', nombre='HACCP de la planta')
        self.assertIn('HACCP de la planta', self.ficha())
        self.actuar('alternar_seccion', numero='5.3')
        html = self.ficha()
        self.assertNotIn('data-seccion="5.3"', html)
        self.assertNotIn('plan-haccp-', html)
        self.actuar('alternar_seccion', numero='6.3')
        self.assertNotIn('data-seccion="6.3"', self.ficha())
        self.actuar('restablecer_seccion', numero='5.3')
        self.assertIn('data-seccion="5.3"', self.ficha())
        # Volver al nombre común no deja un ajuste vacío.
        self.actuar('renombrar_seccion', numero='1.4', nombre='Normativa y marco sanitario')
        self.assertEqual(list(AjusteSeccionPlanta.objects.filter(unidad=self.unidad).values_list('numero', flat=True)),
                         ['6.3'])

    def test_la_seccion_oculta_se_lleva_sus_carpetas_y_sus_archivos(self):
        carpeta = self.carpeta()
        norma = Recurso.objects.create(unidad=self.unidad, carpeta=carpeta, nombre='NTE INEN 9',
                                       url='https://www.normalizacion.gob.ec/', seguridad_verificada=True)
        self.assertIn(f'data-target="#carpetaContenido{carpeta.pk}"', self.ficha())
        self.assertEqual(_acceso_recurso(norma, AnonymousUser()), 'permitido')
        self.actuar('alternar_seccion', numero='1.4')
        self.assertNotIn(f'carpetaContenido{carpeta.pk}', self.ficha())
        norma.refresh_from_db()
        self.assertEqual(_acceso_recurso(norma, AnonymousUser()), 'denegado')
        self.assertNotEqual(_acceso_recurso(norma, self.admin), 'denegado')

    def test_carpetas_se_crean_editan_mueven_ocultan_y_solo_se_eliminan_vacias(self):
        self.assertContains(self.actuar('crear_carpeta', destino='s:1.4', nombre='  Normas   INEN ', visibilidad='publica'),
                            'Carpeta «Normas INEN» creada.')
        carpeta = CarpetaRecurso.objects.get(unidad=self.unidad, nombre='Normas INEN')
        self.assertEqual((carpeta.modulo_config.clave, carpeta.seccion_planta), ('informacion-general', '1.4'))
        self.assertContains(self.client.get(self.url), 'Vacía: no aparece en la ficha hasta tener archivos')
        self.actuar('crear_carpeta', padre=carpeta.pk, nombre='Lácteos', visibilidad='restringida')
        hija = CarpetaRecurso.objects.get(unidad=self.unidad, nombre='Lácteos')
        self.assertEqual((hija.carpeta_padre, hija.seccion_planta), (carpeta, '1.4'))
        self.assertContains(self.actuar('crear_carpeta', destino='s:1.5', nombre='Lácteos'), 'Ya hay una carpeta «Lácteos»')
        self.assertContains(self.actuar('crear_carpeta', padre=hija.pk, nombre='Tercer nivel'), 'dos niveles')
        self.actuar('editar_carpeta', carpeta=carpeta.pk, nombre='Normas técnicas', visibilidad='interna')
        carpeta.refresh_from_db()
        self.assertEqual((carpeta.nombre, carpeta.visibilidad), ('Normas técnicas', 'interna'))
        self.actuar('mover_carpeta', carpeta=carpeta.pk, destino='s:5.5')
        carpeta.refresh_from_db()
        hija.refresh_from_db()
        self.assertEqual((carpeta.modulo_config.clave, carpeta.seccion_planta, hija.seccion_planta),
                         ('calidad-inocuidad', '5.5', '5.5'))
        self.assertContains(self.actuar('mover_carpeta', carpeta=hija.pk, destino='s:1.4'), 'se mueve junto con')
        self.actuar('alternar_carpeta', carpeta=carpeta.pk)
        carpeta.refresh_from_db()
        self.assertFalse(carpeta.activa)
        Recurso.objects.create(unidad=self.unidad, carpeta=hija, nombre='Guía', url='https://example.org/guia')
        self.assertContains(self.actuar('eliminar_carpeta', carpeta=carpeta.pk), 'Solo se elimina una carpeta vacía')
        self.assertContains(self.actuar('eliminar_carpeta', carpeta=hija.pk), 'Solo se elimina una carpeta vacía')
        hija.recursos.all().delete()
        self.actuar('eliminar_carpeta', carpeta=hija.pk)
        self.actuar('eliminar_carpeta', carpeta=carpeta.pk)
        self.assertFalse(CarpetaRecurso.objects.filter(pk__in=[carpeta.pk, hija.pk]).exists())

    def test_la_carpeta_sin_seccion_se_ve_aparte_y_se_ubica_moviendola(self):
        suelta = CarpetaRecurso.objects.create(unidad=self.unidad, nombre='Material suelto', visibilidad='publica')
        pagina = self.client.get(self.url)
        self.assertContains(pagina, 'Carpetas sin ubicar')
        self.assertContains(pagina, 'No tiene pestaña: no aparece en la ficha.')
        self.actuar('mover_carpeta', carpeta=suelta.pk, destino='s:1.5')
        suelta.refresh_from_db()
        self.assertEqual((suelta.modulo_config.clave, suelta.seccion_planta), ('informacion-general', '1.5'))
        self.assertNotContains(self.client.get(self.url), 'Carpetas sin ubicar')

    def test_las_pestanas_se_renombran_y_se_ocultan_sin_quedarse_sin_ninguna(self):
        calidad = ModuloUnidad.objects.get(unidad=self.unidad, clave='calidad-inocuidad')
        self.actuar('renombrar_pestana', modulo=calidad.pk, nombre='Calidad')
        self.actuar('alternar_pestana', modulo=calidad.pk)
        calidad.refresh_from_db()
        self.assertEqual((calidad.nombre, calidad.activo), ('Calidad', False))
        self.assertNotIn('data-modulo="calidad-inocuidad"', self.ficha())
        ModuloUnidad.objects.filter(unidad=self.unidad).exclude(pk=calidad.pk).update(activo=False)
        calidad.activo = True
        calidad.save(update_fields=['activo'])
        self.assertContains(self.actuar('alternar_pestana', modulo=calidad.pk), 'al menos una pestaña visible')
        # Las comunes no se eliminan; una propia se crea junto a ellas y se elimina vacía.
        self.assertContains(self.actuar('eliminar_pestana', modulo=calidad.pk), 'no se eliminan')
        self.assertContains(self.actuar('nueva_pestana', nombre='Extra'), 'Nueva pestaña «Extra»')
        extra = ModuloUnidad.objects.get(unidad=self.unidad, nombre='Extra')
        self.assertTrue(extra.clave.startswith('propia-'))
        self.assertContains(self.actuar('eliminar_pestana', modulo=extra.pk), 'Pestaña «Extra» eliminada.')

    def test_fuera_de_su_alcance_no_existe_y_los_cambios_quedan_en_el_historial(self):
        self.actuar('alternar_seccion', numero='1.4')
        from django.contrib.admin.models import LogEntry
        self.assertTrue(LogEntry.objects.filter(object_id=str(self.unidad.pk),
                                                change_message__contains='Contenidos de la ficha').exists())
        personal = get_user_model().objects.create_user('personal.contenidos', password='clave', is_staff=True)
        self.client.force_login(personal)
        self.assertEqual(self.client.get(self.url).status_code, 404)
        self.assertEqual(self.client.post(self.url, {'accion': 'alternar_seccion', 'numero': '1.4'}).status_code, 404)


class RutasDeLaFichaTests(BaseContenidos):
    """Todo dato tiene ruta: el editor dice adónde llega cada bloque y el organizador dónde se edita cada sección."""

    def editor(self):
        return self.client.get(reverse('admin:plantas_piloto_plantapiloto_change', args=[self.unidad.pk]))

    def test_el_editor_rotula_cada_bloque_con_la_seccion_a_la_que_llega(self):
        self.actuar('renombrar_seccion', numero='1.2', nombre='Quiénes somos')
        pagina = self.editor()
        html = pagina.content.decode()
        for rotulo in ('1.2 Quiénes somos — Atención', '1.2 Quiénes somos — Conoce la unidad: presentación',
                       '1.2 y 1.3 — La planta por dentro: fotos y videos', '6.6 Reglamento de uso — Reglamento de uso',
                       'Uso interno — '):
            self.assertIn(rotulo, html)
        self.assertIn('id="bloque-atencion"', html)
        self.assertIn('Se ve en la ficha: 1.2 Quiénes somos.', html)
        # Los bloques siguen el orden de la ficha y las carpetas ya no se editan aquí.
        self.assertLess(html.index('id="presentacion-group"'), html.index('id="reglamento_publico-group"'))
        self.assertNotIn('carpetas-TOTAL_FORMS', html)
        self.assertIn('admin/js/editor_unidad.js', html)
        self.assertIn(self.url, html)

    def test_cada_seccion_dice_donde_se_edita_lo_que_muestra(self):
        pagina = self.client.get(self.url)
        secciones = {seccion['numero']: seccion for pestana in pagina.context['pestanas'] for seccion in pestana['secciones']}
        editor = reverse('admin:plantas_piloto_plantapiloto_change', args=[self.unidad.pk])
        fuentes = {fuente['nombre']: fuente for fuente in secciones['1.2']['fuentes']}
        self.assertEqual(fuentes['Atención']['url'], f'{editor}#bloque-atencion')
        self.assertEqual(fuentes['Conoce la unidad: presentación']['url'], f'{editor}#presentacion-group')
        self.assertEqual(fuentes['Conoce la unidad: presentación']['estado'], 'Sin registros')
        recetas = reverse('admin:plantas_piloto_receta_changelist') + f'?unidad__id__exact={self.unidad.pk}'
        self.assertIn(recetas, [fuente['url'] for fuente in secciones['2.1']['fuentes']])
        self.assertIn(reverse('gestion_unidad', args=[self.unidad.slug]) + '?view=seguridad',
                      [fuente['url'] for fuente in secciones['6.4']['fuentes']])
        self.assertEqual(secciones['1.4']['fuentes'], [])
        self.assertIn('Información General', [fuente['nombre'] for fuente in pagina.context['cabecera']])
        self.assertTrue(pagina.context['internos'])
        self.assertContains(pagina, f'href="{editor}#presentacion-group"')

    def test_el_archivo_sin_ruta_se_ve_y_se_lleva_a_una_carpeta(self):
        suelto = Recurso.objects.create(unidad=self.unidad, nombre='Acta suelta', url='https://example.org/acta')
        gobernado = Recurso.objects.create(unidad=self.unidad, nombre='Norma general', descripcion='Norma',
                                           tipo_adjunto='norma', seguridad_verificada=True,
                                           url='https://example.org/norma')
        pagina = self.client.get(self.url)
        self.assertEqual(pagina.context['archivos_sin_ruta'], [suelto])
        self.assertContains(pagina, 'Sin ruta: no aparece en ninguna parte')
        self.assertContains(pagina, 'la verificación de seguridad')
        carpeta = self.carpeta()
        self.assertContains(self.actuar('asignar_carpeta', recurso=suelto.pk, carpeta=carpeta.pk),
                            '«Acta suelta» queda en la carpeta «Normas INEN».')
        self.assertEqual(self.client.get(self.url).context['archivos_sin_ruta'], [])
        editor = self.editor().content.decode()
        self.assertIn('Se ve en: Información general › 1.4 Normativa y marco sanitario › Normas INEN', editor)
        self.assertIn(f'id="recurso-editor-{gobernado.pk}" class="ruta-ficha">Se ve en: 1.5 Repositorio y descargas', editor)

    def test_las_carpetas_se_ordenan_entre_hermanas(self):
        primera, segunda, tercera = (self.carpeta(nombre, orden=orden) for orden, nombre in
                                     enumerate(('Normas INEN', 'Codex', 'ARCSA'), start=1))
        self.actuar('ordenar_carpeta', carpeta=primera.pk, direccion='bajar')
        orden = list(CarpetaRecurso.objects.filter(unidad=self.unidad, seccion_planta='1.4').order_by('orden')
                     .values_list('nombre', flat=True))
        self.assertEqual(orden, ['Codex', 'Normas INEN', 'ARCSA'])
        self.assertContains(self.actuar('ordenar_carpeta', carpeta=segunda.pk, direccion='subir'), 'ya está primera')
        self.actuar('ordenar_carpeta', carpeta=tercera.pk, direccion='subir')
        self.assertEqual(list(CarpetaRecurso.objects.filter(unidad=self.unidad, seccion_planta='1.4')
                              .order_by('orden').values_list('nombre', flat=True)), ['Codex', 'ARCSA', 'Normas INEN'])


class EditorPorGruposTests(BaseContenidos):
    """El editor se recorre por grupos, con un mapa arriba como los módulos del portal UPEC."""

    def test_cada_bloque_va_a_su_grupo_y_el_mapa_los_ofrece(self):
        html = self.client.get(reverse('admin:plantas_piloto_plantapiloto_change', args=[self.unidad.pk])).content.decode()
        self.assertIn('data-grupos-editor', html)
        for clave in ('unidad', 'presentacion', 'espacios', 'reservas', 'contenidos', 'pantallas', 'interno'):
            self.assertIn(f'href="#grupo-{clave}"', html)
        self.assertIn('grupo-editor-reservas', html[html.rindex('<div', 0, html.index('id="reglamento_publico-group"')):
                                                     html.index('id="reglamento_publico-group"')])
        # La imagen y el video presentan; el plano y los recorridos orientan dentro de la planta.
        self.assertIn('1.3 La planta por dentro — Plano y recorridos', html)
        self.assertIn('grupo-editor-presentacion', html)
        self.assertIn('grupo-editor-espacios', html)
        # El software no agrega una fila vacía: se suma con «Agregar».
        formularios = {clave: re.search(rf'name="software_disponible-{clave}_FORMS" value="(\d+)"', html).group(1)
                       for clave in ('TOTAL', 'INITIAL')}
        self.assertEqual(formularios['TOTAL'], formularios['INITIAL'])

    def test_un_laboratorio_tambien_se_recorre_por_grupos_con_los_numeros_de_su_mapa(self):
        laboratorio = Unidad.objects.create(nombre='Laboratorio por grupos', slug='lab-por-grupos',
                                            dependencia='laboratorios', fecha_inicio=date(2026, 1, 1))
        html = self.client.get(reverse('admin:directorio_unidades_unidad_change', args=[laboratorio.pk])).content.decode()
        self.assertIn('href="#grupo-reservas"', html)
        self.assertIn('Cabecera y 1.2', html)
        self.assertIn('Se ve en la ficha:', html)

    def test_las_areas_listan_sus_herramientas_como_modulos(self):
        area = self.client.get(reverse('admin:index')).content.decode()
        tablero = reverse('admin:plantas_piloto_plantapiloto_tablero', args=[self.unidad.pk])
        self.assertIn(f'<strong><a href="{tablero}">{self.unidad.nombre}</a></strong>', area)
        # Cada herramienta abre desde su título, con el ícono de su bloque.
        sedes = reverse('admin:directorio_unidades_sedeinstitucional_changelist')
        self.assertIn(f'<strong><a href="{sedes}"', area)
        self.assertIn('is-building', area)
        # En el tablero de la planta, cada herramienta es una fila con su ícono y lo de esa planta.
        self.assertContains(self.client.get(tablero), 'class="tablero-lista"')


class EntradaPorUnidadTests(BaseContenidos):
    """Cada tipo de unidad entra por unidad, como las plantas: lo común aparte, lo demás en su tablero."""

    def test_los_laboratorios_entran_por_unidad_con_su_tablero(self):
        from django.apps import apps
        from django.contrib import admin
        laboratorio = Unidad.objects.create(nombre='Laboratorio de entrada', slug='lab-entrada',
                                            dependencia='laboratorios', fecha_inicio=date(2026, 1, 1))
        tablero = reverse('admin:laboratorios_laboratorio_tablero', args=[laboratorio.pk])
        area = self.client.get(reverse('admin:index')).content.decode()
        self.assertIn(f'<strong><a href="{tablero}">Laboratorio de entrada</a></strong>', area)
        self.assertIn('Por laboratorio', area)
        self.assertIn(reverse('admin:laboratorios_laboratorio_add'), area)
        reservas = reverse('admin:laboratorios_reserva_changelist')
        self.assertNotIn(f'<strong><a href="{reservas}"', area)
        # Su tablero reúne su operación, ya filtrada, y lo que enseña su ficha numerada.
        pagina = self.client.get(tablero)
        self.assertContains(pagina, 'Operación de la unidad')
        self.assertContains(pagina, 'Lo que muestra la ficha pública')
        panel = admin.site._registry[apps.get_model('laboratorios', 'Reserva')]
        self.assertContains(pagina, f'{reservas}?{panel.parametro_unidad}={laboratorio.pk}')
        editor = self.client.get(reverse('admin:laboratorios_laboratorio_change', args=[laboratorio.pk]))
        self.assertContains(editor, tablero)

    def test_con_muchas_unidades_aparece_el_buscador(self):
        for numero in range(7):
            Unidad.objects.create(nombre=f'Laboratorio {numero}', slug=f'lab-buscador-{numero}',
                                  dependencia='laboratorios', fecha_inicio=date(2026, 1, 1))
        area = self.client.get(reverse('admin:index')).content.decode()
        self.assertIn('data-filtrar-unidades', area)
        self.assertIn('data-unidad="laboratorio 3"', area)


class ContenidosDeUnLaboratorioTests(BasePracticaPorProceso):
    def test_un_laboratorio_organiza_sus_carpetas_por_las_secciones_de_su_mapa(self):
        self.client.force_login(get_user_model().objects.create_superuser('lab.admin', 'l@example.org', 'clave'))
        laboratorio = Unidad.objects.create(nombre='Laboratorio de prueba', slug='lab-prueba-contenidos',
                                            dependencia='laboratorios', fecha_inicio=date(2026, 1, 1))
        url = reverse('admin:directorio_unidades_unidad_contenidos', args=[laboratorio.pk])
        self.assertContains(self.client.get(reverse('admin:directorio_unidades_unidad_change', args=[laboratorio.pk])), url)
        # Las carpetas van a una sección de su mapa; una pestaña suelta o una sección de planta no valen.
        self.client.post(url, {'accion': 'crear_carpeta', 'destino': 's:4.4', 'nombre': 'Guías'})
        self.assertTrue(CarpetaRecurso.objects.filter(unidad=laboratorio, nombre='Guías', seccion_planta='4.4',
                                                      modulo_config__clave='docencia-capacitacion').exists())
        pestana = ModuloUnidad.objects.filter(unidad=laboratorio).order_by('orden').first()
        for destino in (f'm:{pestana.pk}', 's:4.5'):
            rechazo = self.client.post(url, {'accion': 'crear_carpeta', 'destino': destino, 'nombre': 'Normas'}, follow=True)
            self.assertContains(rechazo, 'Elija dónde va la carpeta.')
        # Junto a las comunes de los laboratorios, una pestaña propia recibe carpetas directo en ella.
        self.assertContains(self.client.post(url, {'accion': 'nueva_pestana', 'nombre': 'Proyectos'}, follow=True),
                            'Nueva pestaña «Proyectos»')
        self.assertEqual(ModuloUnidad.objects.filter(unidad=laboratorio).count(), 7)
        propia = ModuloUnidad.objects.get(unidad=laboratorio, nombre='Proyectos')
        self.client.post(url, {'accion': 'crear_carpeta', 'destino': f'm:{propia.pk}', 'nombre': 'Semilleros'})
        self.assertTrue(CarpetaRecurso.objects.filter(unidad=laboratorio, nombre='Semilleros', modulo_config=propia,
                                                      seccion_planta='').exists())
        self.assertContains(self.client.post(url, {'accion': 'eliminar_pestana', 'modulo': propia.pk}, follow=True),
                            'Solo se elimina una pestaña vacía')
        pagina = self.client.get(url)
        self.assertContains(pagina, 'Las 28 secciones numeradas son las mismas en cada laboratorio')
        self.assertContains(pagina, 'id="seccion-4-4"')
        self.assertNotContains(pagina, 'id="seccion-4-5"')
        self.assertContains(pagina, 'Contenido automático:')
        self.assertContains(pagina, 'Guías')
