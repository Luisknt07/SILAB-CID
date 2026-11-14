"""El CIDT-UPEC montado desde su documentación técnica como un centro que opera: la carga, la ficha con su
visualizador, las secciones, las áreas, el portafolio, las solicitudes con su ruta de atención, el reporte en PDF y la
articulación con las unidades."""
import base64
import tempfile
from datetime import date, datetime, timedelta
from decimal import Decimal
from io import StringIO

from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.core.files.uploadedfile import SimpleUploadedFile
from django.core.management import call_command
from django.test import TestCase, override_settings
from django.urls import reverse
from django.utils import timezone
from django.utils.html import escape

from apps.centros_id.carga import Cargador
from apps.centros_id.contenido import cidt
from apps.centros_id.mapa import MAPA
from apps.centros_id.models import (
    AjusteSeccion, CarpetaCentro, CentroID, EquipoCentro, ImagenCentro, PlanoCentro, Proyecto, RecursoCentro,
    HorarioRecurso, SolicitudCentro, Zona,
)
from apps.centros_id.vinculos import centros_que_integran, proveedor_unidades, sedes_en_el_mapa, unidad_publica
from apps.integraciones.unidades import modelo_unidad

ROBOTICA = 'laboratorio-robotica-electronica-automatizacion'
PNG_1X1 = base64.b64decode('iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNkYPhfDwAChwGA60e6kgAAAABJRU5ErkJggg==')


class CargaCIDTTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.cargador = Cargador(cidt)
        cls.centro = cls.cargador.cargar()

    def test_carga_todo_lo_que_documenta_el_centro(self):
        centro = self.centro
        self.assertEqual(centro.sigla, 'CIDT-UPEC')
        self.assertEqual(centro.componentes.filter(tipo='division').count(), 5)
        self.assertEqual(centro.componentes.count(), len(cidt.COMPONENTES))
        self.assertEqual(centro.servicios.count(), 61)
        for relacion, filas in (('gobierno', cidt.GOBIERNO), ('ruta', cidt.RUTA), ('modalidades', cidt.MODALIDADES),
                                ('lineas', cidt.LINEAS), ('zonas', cidt.ZONAS), ('riesgos', cidt.RIESGOS),
                                ('indicadores', cidt.INDICADORES), ('articulaciones', cidt.ARTICULACION),
                                ('relaciones_areas', cidt.RELACIONES)):
            with self.subTest(relacion=relacion):
                self.assertEqual(getattr(centro, relacion).count(), len(filas))

    def test_el_centro_se_carga_operando_sin_nada_de_planeacion(self):
        centro = self.centro
        self.assertEqual(centro.estado, 'operativo')
        self.assertTrue(centro.en_operacion)
        self.assertEqual(centro.fuente, '')
        for relacion in ('fases', 'presupuesto', 'documentos'):
            with self.subTest(relacion=relacion):
                self.assertEqual(getattr(centro, relacion).count(), 0)
        # Los indicadores con los que se evalúa el centro se cargan con su cálculo, nunca con valores escritos.
        self.assertFalse(centro.indicadores.filter(valor__isnull=False).exists())
        self.assertFalse(centro.indicadores.filter(calculo='').exists())
        self.assertEqual(set(centro.indicadores.values_list('categoria', flat=True)),
                         {'Proyectos', 'Talento', 'Producción científica', 'Propiedad intelectual y transferencia',
                          'Alianzas', 'Capacidades'})
        self.assertFalse(centro.articulaciones.filter(tipo='futura').exists())
        # Los riesgos son los de operar el centro, no los del montaje.
        self.assertEqual(set(centro.riesgos.values_list('categoria', flat=True)),
                         {'Operativo', 'Mantenimiento', 'Seguridad', 'Ciberseguridad'})
        texto = ' '.join([centro.objetivo_general, centro.objetivos_especificos, centro.visitas_texto, centro.como_llegar,
                          centro.cifras] + [i.credito for i in centro.imagenes.all()]).lower()
        for palabra in ('factibilidad', 'implementar ', 'anteproyecto', 'cuando el centro opere', 'estimad', 'referencial'):
            with self.subTest(palabra=palabra):
                self.assertNotIn(palabra, texto)

    def test_las_areas_y_sus_equipos_operan_desde_la_carga(self):
        areas = self.centro.componentes.all()
        self.assertEqual({a.estado for a in areas}, {'operativa'})
        equipos = EquipoCentro.objects.filter(componente__centro=self.centro)
        self.assertEqual(equipos.count(), sum(len(a.lista_equipamiento) for a in areas))
        self.assertEqual({e.estado for e in equipos}, {'operativo'})
        # La categoría de cada equipo es el tipo de su área, lo que sirve para filtrar el catálogo.
        self.assertEqual(set(equipos.values_list('categoria', flat=True)), {str(a.get_tipo_display()) for a in areas})
        for codigo in cidt.PROCESOS:
            with self.subTest(area=codigo):
                area = areas.get(codigo=codigo)
                proceso = area.procesos.get()
                self.assertEqual(proceso.pasos.count(), len(area.pasos))
        # Los pasos del CEDI pierden la numeración del documento: el número lo pone el proceso.
        primero = areas.get(codigo='smart-cedi').procesos.get().pasos.first()
        self.assertEqual(primero.nombre, 'Planificar ingreso')

    def test_los_espacios_quedan_ubicados_en_el_plano(self):
        zonas = {z.codigo: z for z in self.centro.zonas.all()}
        self.assertTrue(zonas['PB-01'].en_plano)
        self.assertEqual((zonas['PB-01'].plano_x, zonas['PB-01'].plano_y), (Decimal(44), Decimal(17)))
        self.assertFalse(zonas['PB-14'].en_plano)

    def test_las_superficies_cuadran_con_el_programa_arquitectonico(self):
        def suma(nivel):
            return sum(z.area_m2 for z in Zona.objects.filter(centro=self.centro, nivel=nivel))

        self.assertEqual(suma('Nivel 1'), Decimal('1945'))
        self.assertEqual(suma('Nivel 2 en L'), Decimal('571'))
        self.assertTrue(Zona.objects.filter(centro=self.centro, reservable=True).exists())

    def test_cargar_de_nuevo_no_duplica_ni_pisa_lo_editado(self):
        self.centro.lema = 'Lema editado en el administrador'
        self.centro.save()
        servicios = self.centro.servicios.count()
        equipos = EquipoCentro.objects.filter(componente__centro=self.centro).count()

        otra = Cargador(cidt)
        otra.cargar()

        self.centro.refresh_from_db()
        self.assertEqual(self.centro.lema, 'Lema editado en el administrador')
        self.assertEqual(self.centro.servicios.count(), servicios)
        self.assertEqual(EquipoCentro.objects.filter(componente__centro=self.centro).count(), equipos)
        self.assertEqual(otra.resumen(), 'Al día')

    def test_reescribir_devuelve_el_texto_del_documento(self):
        CentroID.objects.filter(pk=self.centro.pk).update(lema='Otro lema')
        Cargador(cidt, reescribir=True).cargar()
        self.centro.refresh_from_db()
        self.assertEqual(self.centro.lema, cidt.CENTRO['lema'])

    def test_el_comando_informa_lo_que_hizo(self):
        salida = StringIO()
        call_command('cargar_centros_id', '--centro', cidt.CENTRO['slug'], stdout=salida)
        self.assertIn('Al día', salida.getvalue())


class PaginasCIDTTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.centro = Cargador(cidt).cargar()
        cls.laboratorio = modelo_unidad().objects.create(
            nombre='Laboratorio de Robótica, Electrónica y Automatización', slug=ROBOTICA, dependencia='laboratorios',
            descripcion='Unidad de prueba.', fecha_inicio=date(2026, 1, 1))
        cls.usuario = get_user_model().objects.create_user('solicitante.cidt', password='clave-segura-123')
        cls.gestor = get_user_model().objects.create_user('gestor.cidt', password='clave-segura-123')
        cls.centro.gestores.add(cls.gestor)

    def seccion(self, clave, **parametros):
        return self.client.get(reverse('seccion_centro_id', args=[self.centro.slug, clave]), parametros)

    def test_la_portada_presenta_el_centro_con_sus_cifras_y_sus_areas(self):
        pagina = self.client.get(reverse('centros_id'))
        self.assertEqual(pagina.status_code, 200)
        self.assertContains(pagina, 'Centro de Innovación y Desarrollo Tecnológico')
        claves = {cifra['clave'] for cifra in pagina.context['cifras']}
        self.assertTrue({'centros', 'areas', 'servicios'} <= claves)
        # Con un solo centro no hay nada que filtrar; sus áreas se abren dentro de la ficha desde su tarjeta.
        self.assertNotContains(pagina, 'class="cid-filtros"')
        self.assertContains(pagina, 'Áreas del centro')
        self.assertContains(pagina, 'IA, Datos y Software')
        self.assertNotContains(pagina, 'Tres puertas de entrada')
        self.assertNotContains(pagina, 'institutional-local-nav')
        self.assertNotContains(pagina, '#como-trabajar')
        # La portada no reúne las áreas de todos los centros: con muchos centros ese bloque no tendría control.
        self.assertNotContains(pagina, 'Las áreas de los centros')
        self.assertNotIn('areas_destacadas', pagina.context)

    def test_la_franja_de_la_portada_pasa_las_fotos_de_los_centros(self):
        # Sin fotos registradas, la franja no queda en verde: lleva la imagen genérica.
        sin_fotos = self.client.get(reverse('centros_id'))
        self.assertEqual(sin_fotos.context['diapositivas'], [])
        self.assertContains(sin_fotos, 'hero-centros-id-v2.png')
        self.assertNotContains(sin_fotos, 'cid-portada__leyenda')
        with override_settings(MEDIA_ROOT=tempfile.mkdtemp()):
            CentroID.objects.filter(pk=self.centro.pk).update(imagen='centros_id/portadas/cidt.png')
            ImagenCentro.objects.create(centro=self.centro, titulo='Render del edificio',
                                        imagen=SimpleUploadedFile('render.png', PNG_1X1, 'image/png'))
            ImagenCentro.objects.create(centro=self.centro, titulo='Layout del primer nivel', es_plano=True,
                                        imagen=SimpleUploadedFile('layout.png', PNG_1X1, 'image/png'))
            pagina = self.client.get(reverse('centros_id'))
        # Primero la portada del centro con su lema, luego sus imágenes generales; los planos no pasan por la franja.
        fotos = pagina.context['diapositivas']
        self.assertEqual([f['texto'] for f in fotos], [self.centro.lema, 'Render del edificio'])
        self.assertTrue(all(f['centro'] == self.centro for f in fotos))
        self.assertContains(pagina, 'data-diapositiva="1"')
        self.assertContains(pagina, 'cid-portada__leyenda')
        self.assertContains(pagina, 'data-punto="1"')
        self.assertContains(pagina, 'centros_id/portada.js')

    def test_la_portada_no_oculta_centros_por_filtros_antiguos(self):
        pagina = self.client.get(reverse('centros_id'), {'q': 'sin coincidencias', 'area': 'otra',
                                                        'linea': 'antigua', 'servicio': 'anterior'})
        self.assertEqual([c.pk for c in pagina.context['centros']], [self.centro.pk])
        self.assertNotContains(pagina, 'class="cid-filtros"')
        self.assertNotContains(pagina, 'Ningún centro coincide con esos filtros.')

    def test_la_ficha_tiene_pestanas_visualizador_y_contenidos(self):
        pagina = self.client.get(reverse('centro_id', args=[self.centro.slug]))
        self.assertEqual(pagina.status_code, 200)
        # Las carreras, las líneas y los actores externos del proyecto encienden las seis pestañas; dentro de cada una
        # solo se ofrecen las secciones con contenido.
        self.assertEqual([p['clave'] for p in pagina.context['pestanas']], list(MAPA.pestanas))
        equipo = next(p for p in pagina.context['pestanas'] if p['clave'] == 'equipo')
        self.assertEqual([c['clave'] for c in equipo['carpetas']], ['grupos'])
        self.assertEqual(pagina.context['inicial']['url'], reverse('seccion_centro_id', args=[self.centro.slug, 'presentacion']))
        for texto in ('Áreas y capacidades', 'Innovación y transferencia', 'Smart Factory', 'Contenidos',
                      reverse('componente_centro_id', args=[self.centro.slug, 'smart-factory']),
                      reverse('seccion_centro_id', args=[self.centro.slug, 'portafolio']),
                      reverse('seccion_centro_id', args=[self.centro.slug, 'documentos'])):
            with self.subTest(texto=texto):
                self.assertContains(pagina, texto)
        # Las unidades vinculadas se enlazan desde su sección, no desde un panel lateral que repita la ficha.
        self.assertContains(self.seccion('vinculadas'), reverse('laboratorio_detalle', kwargs={'slug': ROBOTICA}))

    def test_el_gestor_ve_las_secciones_pendientes_con_su_enlace_para_completarlas(self):
        self.client.force_login(self.gestor)
        pagina = self.client.get(reverse('centro_id', args=[self.centro.slug]))
        equipo = next(p for p in pagina.context['pestanas'] if p['clave'] == 'equipo')
        self.assertEqual([c['clave'] for c in equipo['carpetas']], ['direccion', 'investigadores', 'grupos', 'personal'])
        self.assertEqual(equipo['pendientes'], 3)
        self.assertContains(pagina, 'Completar contenido')
        self.assertContains(pagina, reverse('gestion_centro_id', args=[self.centro.slug]) + '?panel=equipo&amp;tipo=personas')

    def test_el_panel_muestra_solo_lo_esencial_de_cada_seccion(self):
        pagina = self.client.get(reverse('centro_id', args=[self.centro.slug]))
        secciones = {c['clave']: c for p in pagina.context['pestanas'] for c in p['carpetas']}
        # Seis pestañas iguales para todo centro; ninguna depende de cómo se organiza el centro.
        self.assertEqual([p['clave'] for p in pagina.context['pestanas']],
                         ['el-centro', 'areas', 'investigacion', 'innovacion', 'equipo', 'servicios'])
        # Las áreas son elementos de «Áreas del centro», en el orden del centro: primero sus divisiones.
        areas = secciones['areas']
        self.assertEqual([b['nombre'] for b in areas['botones']][:3], ['Todas las áreas', 'IA, Datos y Software',
                                                                       'Automatización, Robótica e IoT'])
        self.assertEqual(len(areas['botones']), 1 + self.centro.componentes.count())
        self.assertEqual(areas['grupos'], [])
        # Lo demás es una sola página que se abre directo: sin carpetas de equipos, procesos, servicios ni personas.
        for clave in ('como_trabaja', 'gobierno', 'relaciones', 'vinculadas', 'lineas', 'portafolio', 'alianzas', 'grupos'):
            with self.subTest(seccion=clave):
                self.assertTrue(secciones[clave]['directa'])
        self.assertEqual([c for c in secciones.values() if c['grupos']], [])
        self.assertEqual([b['nombre'] for b in secciones['presentacion']['botones']],
                         ['Conoce el centro', 'Identidad y contacto', 'Ubicación y cómo llegar'])
        # Sin numeración, sin saltos dentro de una página y sin secciones de otras estructuras.
        self.assertFalse([c for c in secciones.values() if 'numero' in c])
        self.assertFalse([b['url'] for c in secciones.values() for b in c['botones'] if '#' in b['url']])
        for vieja in ('normativa', 'repositorio', 'equipos', 'area-fablab'):
            self.assertNotIn(vieja, secciones)
        # Un área del panel abre su página con todo lo que hace.
        fablab = next(b for b in areas['botones'] if b['nombre'] == 'Prototipado y FabLab')
        pagina_area = self.client.get(fablab['url'])
        self.assertContains(pagina_area, 'Corte láser')
        self.assertEqual(pagina_area.context['total_equipos'], 12)
        self.assertEqual(pagina_area.context['pestana']['clave'], 'areas')

    def test_los_enlaces_directos_abren_lo_pedido_en_el_visualizador(self):
        url = reverse('centro_id', args=[self.centro.slug])
        # Toda área se abre en «Áreas y capacidades», sea división, plataforma o laboratorio.
        for codigo in ('smart-cedi', 'fablab'):
            with self.subTest(area=codigo):
                area = self.client.get(url, {'area': codigo}).context['inicial']
                self.assertEqual((area['pestana'], area['url']), ('areas', reverse('componente_centro_id', args=[self.centro.slug, codigo])))
        seccion = self.client.get(url, {'seccion': 'portafolio', 'linea': 'IA'}).context['inicial']
        self.assertEqual(seccion['pestana'], 'servicios')
        self.assertTrue(seccion['url'].endswith('/s/portafolio/?linea=IA'))
        # Dentro de una sección, «linea» y «abrir» viajan como filtros con la sección.
        servicio_abierto = self.client.get(url, {'seccion': 'portafolio', 'linea': 'IA', 'abrir': '7'}).context['inicial']
        self.assertTrue(servicio_abierto['url'].endswith('/s/portafolio/?linea=IA&abrir=7'))
        pestana = self.client.get(url, {'pestana': 'servicios'}).context['inicial']
        self.assertEqual(pestana['url'], reverse('pestana_centro_id', args=[self.centro.slug, 'servicios']))
        # Lo que no existe cae a la presentación.
        self.assertEqual(self.client.get(url, {'seccion': 'proyectos'}).context['inicial']['url'],
                         reverse('seccion_centro_id', args=[self.centro.slug, 'presentacion']))

    def test_cada_pestana_tiene_su_portada_dentro_del_visualizador(self):
        # Con la pieza de Laboratorios: escenario de fotos, frase, cifras, «Qué vas a encontrar», datos y lectura. La de
        # áreas presenta primero las áreas mismas, con su foto.
        pagina = self.client.get(reverse('pestana_centro_id', args=[self.centro.slug, 'areas']))
        self.assertEqual(pagina.status_code, 200)
        for texto in ('tech-portada', 'Donde se hace el trabajo', 'Qué vas a encontrar', 'De dónde salen los datos',
                      'Cómo se lee', 'portada_tecnologica.css', 'Prototipado y FabLab'):
            with self.subTest(texto=texto):
                self.assertContains(pagina, texto)
        self.assertEqual(pagina.context['modulos'][0]['titulo'], 'IA, Datos y Software')
        self.assertEqual([c['nombre'] for c in pagina.context['cifras']][:2], ['Áreas propias', 'Equipos con ficha'])
        for vieja in ('divisiones', 'plataformas', 'no-existe'):
            with self.subTest(pestana=vieja):
                self.assertEqual(self.client.get(reverse('pestana_centro_id', args=[self.centro.slug, vieja])).status_code, 404)
        # Si el centro oculta la única sección con contenido de una pestaña, la pestaña desaparece para el público.
        AjusteSeccion.objects.create(centro=self.centro, clave='grupos', oculta=True)
        self.assertEqual(self.client.get(reverse('pestana_centro_id', args=[self.centro.slug, 'equipo'])).status_code, 404)
        self.assertNotIn('equipo', [p['clave'] for p in self.client.get(reverse('centro_id', args=[self.centro.slug])).context['pestanas']])

    def test_otro_centro_lleva_la_misma_estructura(self):
        otro = CentroID.objects.create(nombre='Centro de Investigación en Agroindustria', sigla='CIAB', slug='ciab',
                                       area='agroindustria', proposito='Bioprocesos y alimentos con valor agregado.')
        gestor = get_user_model().objects.create_user('gestor.ciab', password='clave-segura-123')
        otro.gestores.add(gestor)
        self.client.force_login(gestor)
        pagina = self.client.get(reverse('centro_id', args=[otro.slug]))
        self.assertEqual([p['clave'] for p in pagina.context['pestanas']], list(MAPA.pestanas))
        self.assertEqual({p['clave']: [c['clave'] for c in p['carpetas']] for p in pagina.context['pestanas']},
                         {clave: [s['clave'] for s in p['secciones']] for clave, p in MAPA.pestanas.items()})

    def test_las_secciones_con_contenido_responden_y_las_vacias_solo_al_gestor(self):
        for clave in ('presentacion', 'como_trabaja', 'gobierno', 'relaciones',
                      'vinculadas', 'grupos', 'lineas', 'alianzas', 'portafolio', 'solicitar', 'visitas', 'documentos'):
            with self.subTest(seccion=clave):
                self.assertEqual(self.seccion(clave).status_code, 200)
        # «Ahora en el centro» solo existe para el público cuando hay algo en marcha registrado.
        for clave in ('ahora', 'proyectos', 'produccion', 'casos', 'direccion', 'oportunidades'):
            with self.subTest(seccion=clave):
                self.assertEqual(self.seccion(clave).status_code, 404)
        self.assertEqual(self.seccion('areas').status_code, 200)
        for vieja in ('no-existe', 'normativa', 'repositorio', 'equipos', 'edificio', 'galeria'):
            with self.subTest(seccion=vieja):
                self.assertEqual(self.seccion(vieja).status_code, 404)
        self.client.force_login(self.gestor)
        pendiente = self.seccion('proyectos')
        self.assertEqual(pendiente.status_code, 200)
        self.assertContains(pendiente, 'El público no ve este bloque mientras esté vacío.')

    def test_las_areas_traen_el_edificio_que_las_aloja_y_la_cadena_las_enlaza(self):
        # Las instalaciones no son una sección aparte: el edificio vive con las áreas que aloja.
        areas = self.seccion('areas')
        self.assertContains(areas, 'Tecnologías aplicadas')
        self.assertContains(areas, 'Nivel 2 en L')
        self.assertContains(areas, '571 m²')
        self.assertNotContains(areas, 'cv-plano__punto')
        self.assertEqual([c['titulo'] for c in areas.context['cifras']][:2], ['Áreas propias', 'Equipos con ficha'])
        with override_settings(MEDIA_ROOT=tempfile.mkdtemp()):
            PlanoCentro.objects.create(centro=self.centro, nivel='Nivel 1', titulo='Layout del primer nivel',
                                       imagen=SimpleUploadedFile('nivel1.png', PNG_1X1, 'image/png'))
            con_plano = self.seccion('areas')
        # Cada espacio con coordenadas es un punto del plano que lleva a su área.
        self.assertContains(con_plano, 'cv-plano__punto')
        self.assertContains(con_plano, 'left: 44%; top: 17%')
        self.assertContains(con_plano, reverse('componente_centro_id', args=[self.centro.slug, 'smart-cedi']))
        trabaja = self.seccion('como_trabaja')
        self.assertContains(trabaja, reverse('componente_centro_id', args=[self.centro.slug, 'fablab']))
        relaciones = self.seccion('relaciones')
        self.assertContains(relaciones, 'data-relaciones')
        self.assertContains(relaciones, 'Piezas, carcasas, jigs y fixtures')

    def test_conoce_el_centro_abre_con_portada_temas_y_accesos_y_cuelga_sus_paginas(self):
        pagina = self.seccion('presentacion')
        self.assertContains(pagina, 'conoce__portada')
        self.assertContains(pagina, 'Quiénes somos')
        self.assertContains(pagina, 'Para qué existe')
        # El centro se presenta por sus funciones como centro de investigación y desarrollo, sin compararse con nadie.
        self.assertContains(pagina, 'Sus funciones')
        funciones = {f['titulo']: f for f in pagina.context['funciones']}
        self.assertEqual(funciones['Servicios científico-tecnológicos']['evidencias'][0], '61 servicios')
        self.assertTrue(funciones['Capacidades propias y vinculadas']['url'].endswith('/s/areas/'))
        self.assertNotIn('Investigación aplicada y desarrollo experimental', funciones)
        for comparacion in ('laboratorio tradicional', 'Laboratorio tradicional', 'laboratorio más', 'no es un laboratorio'):
            for pagina_centro in (pagina, self.seccion('como_trabaja')):
                with self.subTest(comparacion=comparacion):
                    self.assertNotContains(pagina_centro, comparacion)
        self.assertContains(pagina, 'Ver presentación')
        for clave in ('identidad', 'ubicacion'):
            self.assertContains(pagina, reverse('seccion_centro_id', args=[self.centro.slug, clave]))
        # En el árbol, de «Conoce el centro» cuelgan la identidad y la ubicación; ya no hay galería ni instalaciones.
        ficha = self.client.get(reverse('centro_id', args=[self.centro.slug]))
        secciones = {c['clave']: c for p in ficha.context['pestanas'] for c in p['carpetas']}
        self.assertEqual(secciones['presentacion']['titulo'], 'Conoce el centro')
        self.assertEqual([b['nombre'] for b in secciones['presentacion']['botones']][1:3],
                         ['Identidad y contacto', 'Ubicación y cómo llegar'])
        self.assertNotIn('edificio', secciones)
        self.assertNotIn('Fotos y videos por área', [b['nombre'] for s in secciones.values() for b in s['botones']])
        # Un enlace directo a una de esas páginas la abre en el visualizador con su sección.
        inicial = self.client.get(reverse('centro_id', args=[self.centro.slug]), {'seccion': 'ubicacion'}).context['inicial']
        self.assertEqual((inicial['pestana'], inicial['titulo']), ('el-centro', 'Ubicación y cómo llegar'))
        self.assertTrue(inicial['url'].endswith('/s/ubicacion/'))
        # Si el centro oculta la presentación, sus páginas se ocultan con ella.
        AjusteSeccion.objects.create(centro=self.centro, clave='presentacion', oculta=True)
        self.assertEqual(self.seccion('identidad').status_code, 404)

    def test_la_identidad_dice_cuantos_atienden_sin_nombrarlos(self):
        pagina = self.seccion('identidad')
        self.assertEqual(pagina.status_code, 200)
        self.assertContains(pagina, 'Ficha de identidad')
        self.assertContains(pagina, 'Calle Antisana')
        self.assertContains(pagina, '1 persona atiende')
        self.assertNotContains(pagina, 'gestor.cidt')
        self.assertEqual(pagina.context['subpagina']['clave'], 'identidad')

    def test_la_ubicacion_dibuja_el_centro_sobre_el_mapa_de_las_sedes(self):
        pagina = self.seccion('ubicacion')
        self.assertEqual(pagina.status_code, 200)
        self.assertContains(pagina, 'datosMapaUnidad')
        self.assertContains(pagina, 'mapa_unidad.js')
        self.assertContains(pagina, 'Calle Antisana')
        mapa = pagina.context['mapa']
        self.assertEqual(mapa['punto'], [0.805253, -77.734336])
        self.assertIsInstance(mapa['sedes'], list)
        self.assertIn('destination=0.805253%2C-77.734336', mapa['comoLlegar'])
        # Sin punto exacto, la página lo dice, muestra las sedes y ofrece buscar la dirección.
        CentroID.objects.filter(pk=self.centro.pk).update(latitud=None, longitud=None)
        sin_punto = self.seccion('ubicacion')
        self.assertContains(sin_punto, 'Punto exacto por marcar')
        self.assertIn('maps/search', sin_punto.context['mapa']['comoLlegar'])

    def test_la_ubicacion_exacta_necesita_latitud_y_longitud(self):
        centro = CentroID(nombre='Centro de prueba', slug='centro-de-prueba', area='digitales', proposito='Probar.',
                          latitud=Decimal('0.8'))
        with self.assertRaises(ValidationError) as aviso:
            centro.full_clean()
        self.assertIn('longitud', aviso.exception.message_dict)

    def test_las_fotos_viven_en_su_area_y_las_del_edificio_con_las_areas(self):
        with override_settings(MEDIA_ROOT=tempfile.mkdtemp()):
            fablab = self.centro.componentes.get(codigo='fablab')
            ImagenCentro.objects.create(centro=self.centro, componente=fablab, titulo='Impresoras del FabLab',
                                        imagen=SimpleUploadedFile('fablab.png', PNG_1X1, 'image/png'))
            ImagenCentro.objects.create(centro=self.centro, titulo='Render del edificio',
                                        imagen=SimpleUploadedFile('render.png', PNG_1X1, 'image/png'))
            # No hay una galería aparte: cada área muestra sus fotos con el visor de Laboratorios y sus videos.
            self.assertEqual(self.seccion('galeria').status_code, 404)
            area = self.client.get(reverse('componente_centro_id', args=[self.centro.slug, 'fablab']))
            for texto in ('Impresoras del FabLab', 'area__collage', 'data-visor-imagenes', 'area__videos'):
                with self.subTest(texto=texto):
                    self.assertContains(area, texto)
            # Las imágenes del edificio están en «Áreas del centro», junto al plano y los espacios.
            areas = self.seccion('areas')
            self.assertContains(areas, 'Render del edificio')
            self.assertNotContains(areas, 'Impresoras del FabLab')
            # «Conoce el centro» muestra las fotos y las abre todas en su visor.
            presentacion = self.seccion('presentacion')
            self.assertContains(presentacion, 'Ver las fotos')
            self.assertEqual(presentacion.context['fotos'][:1], [ImagenCentro.objects.get(titulo='Render del edificio').imagen.url])
            self.assertEqual([i.titulo for i in presentacion.context['galeria']], ['Render del edificio', 'Impresoras del FabLab'])

    def test_las_paginas_se_arman_con_las_piezas_de_laboratorios(self):
        # La página de un área, «Conoce el centro» y cada sección usan las hojas y los guiones de Laboratorios.
        area = self.client.get(reverse('componente_centro_id', args=[self.centro.slug, 'smart-cedi']))
        for texto in ('conoce_unidad.css', 'area_unidad.css', 'area_unidad.js', 'conoce__portada', 'conoce__cifras',
                      'conoce__indice', 'area__diagrama', 'area__dialogo', 'area__tabla--equipos', 'area__verificacion'):
            with self.subTest(pagina='área', texto=texto):
                self.assertContains(area, texto)
        conoce = self.seccion('presentacion')
        for texto in ('conoce__pestanas', 'role="tablist"', 'conoce__rumbo', 'area__tarjetas', 'area__videos',
                      'data-accion="ubicacion"'):
            with self.subTest(pagina='conoce', texto=texto):
                self.assertContains(conoce, texto)
        portafolio = self.seccion('portafolio')
        for texto in ('ficha__cabecera', 'conoce__cifras', 'conoce__indice', 'area__tabla', 'area__pasos'):
            with self.subTest(pagina='portafolio', texto=texto):
                self.assertContains(portafolio, texto)
        # Los estilos propios de antes ya no están: lo que queda en visor.css es solo lo que Laboratorios no tiene.
        for pagina in (area, conoce, portafolio):
            for vieja in ('cv-cabecera__', 'cv-area-hero', 'cv-conoce__', 'cv-seccion"', 'cv-titulo'):
                with self.subTest(pagina=pagina.request['PATH_INFO'], vieja=vieja):
                    self.assertNotContains(pagina, vieja)

    def test_cada_servicio_abre_su_ficha_completa_desde_el_portafolio(self):
        servicio = self.centro.servicios.first()
        portafolio = self.seccion('portafolio', linea=servicio.linea, abrir=servicio.pk)
        self.assertContains(portafolio, 'data-abrir-auto')
        self.assertContains(portafolio, reverse('fragmento_centro_id', args=[self.centro.slug, 'servicio', servicio.pk]))
        ficha = self.client.get(reverse('fragmento_centro_id', args=[self.centro.slug, 'servicio', servicio.pk]))
        self.assertEqual(ficha.status_code, 200)
        self.assertContains(ficha, servicio.nombre)
        self.assertContains(ficha, servicio.entregable)
        self.assertContains(ficha, 'Consultar servicio')
        self.assertContains(ficha, 'Cómo se atiende')

    def test_el_estado_registrado_no_se_afirma_sin_respaldo_institucional(self):
        paginas = [self.client.get(reverse('centros_id')), self.client.get(reverse('centro_id', args=[self.centro.slug])),
                   self.seccion('presentacion'), self.seccion('identidad'), self.seccion('areas'),
                   self.seccion('gobierno'), self.client.get(reverse('componente_centro_id', args=[self.centro.slug, 'fablab'])),
                   self.seccion('ubicacion')]
        for pagina in paginas:
            for frase in ('Proyecto de factibilidad', 'Fase 1', 'Previsto en el proyecto', 'Planificado o por adquirir',
                          'Hoja de ruta de implementación', 'Presupuesto referencial', 'anteproyecto', 'is-propuesta',
                          'cv-chip is-operativa'):
                with self.subTest(pagina=pagina.request['PATH_INFO'], frase=frase):
                    self.assertNotContains(pagina, frase)
        # Se conserva el estado registrado, pero se informa su validación pendiente hasta contar con respaldo.
        self.assertNotContains(paginas[0], 'cid-centro__fase')
        self.assertNotContains(paginas[1], 'cid-chip is-operativo')
        self.assertNotContains(paginas[1], 'cid-panel--ficha')
        self.assertNotContains(paginas[1], 'cid-panel--vinculadas')
        self.assertNotContains(paginas[3], 'Operativo')
        self.assertContains(paginas[1], 'Estado pendiente de validación')

    def test_el_administrador_marca_el_punto_del_centro_en_el_mapa(self):
        administrador = get_user_model().objects.create_superuser('admin.cidt', 'admin.cidt@example.com', 'clave-segura-123')
        self.client.force_login(administrador)
        formulario = self.client.get(reverse('admin:centros_id_centroid_change', args=[self.centro.pk]))
        self.assertEqual(formulario.status_code, 200)
        for fragmento in ('data-mapa-editor', 'name="latitud"', 'name="longitud"', 'name="direccion"', 'mapa_unidad.js'):
            self.assertContains(formulario, fragmento)

    def test_cada_area_tiene_su_pagina_con_equipos_procesos_y_relaciones(self):
        for componente in self.centro.componentes.all():
            with self.subTest(componente=componente.codigo):
                pagina = self.client.get(reverse('componente_centro_id', args=[self.centro.slug, componente.codigo]))
                self.assertEqual(pagina.status_code, 200)
                self.assertContains(pagina, escape(componente.nombre))
                self.assertContains(pagina, 'Solicitar acceso al área')
        cedi = self.client.get(reverse('componente_centro_id', args=[self.centro.slug, 'smart-cedi']))
        self.assertContains(cedi, 'Flujo logístico en U')
        self.assertContains(cedi, 'Recibe de')
        automatizacion = self.client.get(reverse('componente_centro_id', args=[self.centro.slug, 'automatizacion']))
        self.assertContains(automatizacion, reverse('laboratorio_detalle', kwargs={'slug': ROBOTICA}))
        self.assertEqual(self.client.get(reverse('componente_centro_id', args=[self.centro.slug, 'no-existe'])).status_code, 404)

    def test_los_equipos_viven_en_su_area_y_cada_uno_abre_su_ficha(self):
        # No hay catálogo de equipos del centro: el equipamiento es capacidad de cada área.
        self.assertEqual(self.seccion('equipos').status_code, 404)
        fablab = self.client.get(reverse('componente_centro_id', args=[self.centro.slug, 'fablab']))
        self.assertEqual(fablab.context['total_equipos'], 12)
        self.assertContains(fablab, 'Corte láser')
        self.assertContains(fablab, 'Solicitar acceso al área')
        self.assertNotContains(fablab, '/s/equipos/')
        equipo = EquipoCentro.objects.get(componente__codigo='fablab', nombre='Corte láser')
        ficha = self.client.get(reverse('fragmento_centro_id', args=[self.centro.slug, 'equipo', equipo.pk]))
        self.assertEqual(ficha.status_code, 200)
        self.assertContains(ficha, 'area__estado is-ok')
        self.assertContains(ficha, 'Especificaciones técnicas')
        # En su área, cada equipo abre su ficha técnica sin salir de la página.
        self.assertContains(fablab, f'id="ficha-equipo-{equipo.pk}"')
        # Un equipo no se pide suelto: se accede al área para un proyecto, una práctica o un servicio.
        self.assertNotContains(ficha, 'Pedir uso')
        self.assertNotContains(ficha, '<html')
        self.assertEqual(self.client.get(reverse('fragmento_centro_id', args=[self.centro.slug, 'otro', 1])).status_code, 404)

    def test_los_indicadores_se_miden_solos_desde_los_registros(self):
        from apps.centros_id.models import Indicador

        self.assertEqual(self.centro.indicadores.count(), len(cidt.INDICADORES))
        publico = self.seccion('gobierno')
        valores = {i.nombre: i.valor for filas in publico.context['indicadores'].values() for i in filas}
        # Cero es un conteo válido, distinto de una medición manual pendiente.
        self.assertEqual(valores['Servicios en el portafolio'], 61)
        self.assertEqual(valores['Proyectos de I+D+i activos'], 0)
        self.assertContains(publico, 'Lo que mide')
        self.assertFalse(Indicador.objects.filter(centro=self.centro, valor__isnull=False).exists())
        # Un indicador que se registra a mano no aparece hasta tener su medición.
        Indicador.objects.create(centro=self.centro, categoria='Impacto', nombre='Beneficiarios en el territorio',
                                 medicion='Personas y organizaciones alcanzadas')
        self.assertNotIn('Beneficiarios en el territorio',
                         [i.nombre for filas in self.seccion('gobierno').context['indicadores'].values() for i in filas])
        self.client.force_login(self.gestor)
        self.assertGreaterEqual(self.seccion('gobierno').context['por_medir'], 1)
        self.client.logout()
        Indicador.objects.filter(centro=self.centro, nombre='Beneficiarios en el territorio').update(
            valor=120, actualizado=date(2026, 9, 30))
        self.assertContains(self.seccion('gobierno'), '30/09/2026')

    def test_la_articulacion_lleva_modalidad_e_instrumento(self):
        articulacion = self.centro.articulaciones.filter(tipo='unidad', unidad_slug=ROBOTICA).first()
        self.assertIsNotNone(articulacion)
        articulacion.modalidad = 'capacidad'
        articulacion.instrumento = 'Resolución del Consejo Universitario 2026-014'
        articulacion.reglas = 'Prioridad para proyectos del centro en horario de investigación'
        articulacion.save()
        vinculadas = self.seccion('vinculadas')
        self.assertContains(vinculadas, 'Acceso a la capacidad para proyectos del centro')
        self.assertContains(vinculadas, 'Resolución del Consejo Universitario 2026-014')
        self.assertContains(vinculadas, 'Prioridad para proyectos del centro')

    def test_el_portafolio_se_filtra_por_area_y_texto(self):
        url = reverse('servicios_centro_id', args=[self.centro.slug])
        self.assertEqual(self.client.get(url).context['total'], 61)
        cedi = self.client.get(url, {'area': 'smart-cedi'})
        self.assertEqual(cedi.context['total'], self.centro.servicios.filter(componente__codigo='smart-cedi').count())
        self.assertContains(cedi, 'Optimización de picking y packing')
        self.assertEqual(self.client.get(url, {'q': 'Desarrollo de dashboards'}).context['total'], 1)

    def test_un_centro_retirado_deja_de_publicarse(self):
        CentroID.objects.filter(pk=self.centro.pk).update(activo=False)
        self.assertEqual(self.client.get(reverse('centro_id', args=[self.centro.slug])).status_code, 404)

    def test_el_reporte_sale_en_pdf(self):
        respuesta = self.client.get(reverse('reporte_centro_id', args=[self.centro.slug]))
        self.assertEqual(respuesta.status_code, 200)
        self.assertEqual(respuesta['Content-Type'], 'application/pdf')
        self.assertTrue(respuesta.content.startswith(b'%PDF'))

    def test_sin_sesion_la_solicitud_muestra_la_ruta_y_pide_entrar(self):
        pagina = self.client.get(reverse('solicitar_centro_id', args=[self.centro.slug]))
        self.assertEqual(pagina.status_code, 200)
        self.assertContains(pagina, reverse('login'))
        self.assertNotContains(pagina, 'csrfmiddlewaretoken')
        self.assertEqual(self.client.post(reverse('solicitar_centro_id', args=[self.centro.slug]), {}).status_code, 302)

    def test_una_solicitud_de_servicio_entra_a_la_ruta_y_la_ve_quien_la_envio(self):
        self.client.force_login(self.usuario)
        url = reverse('solicitar_centro_id', args=[self.centro.slug])
        servicio = self.centro.servicios.get(nombre='Desarrollo de dashboards')
        self.assertEqual(self.client.get(url, {'tipo': 'servicio', 'servicio': servicio.pk}).status_code, 200)

        respuesta = self.client.post(url, {
            'tipo': 'servicio', 'perfil': 'externo', 'institucion': 'GAD de prueba', 'titulo': 'Tablero de agua potable',
            'problema': 'Necesitamos ver el consumo por sector.', 'resultado_esperado': 'Dashboard',
            'servicio': servicio.pk,
        })

        self.assertRedirects(respuesta, f'{url}#mis-solicitudes', fetch_redirect_response=False)
        solicitud = SolicitudCentro.objects.get(usuario=self.usuario)
        self.assertEqual((solicitud.centro, solicitud.estado, solicitud.servicio), (self.centro, 'recibida', servicio))
        self.assertContains(self.client.get(url), 'Tablero de agua potable')

    def test_sin_recursos_habilitados_el_acceso_orienta_a_plantear_necesidad(self):
        self.client.force_login(self.usuario)
        respuesta = self.client.post(reverse('solicitar_centro_id', args=[self.centro.slug]), {
            'tipo': 'uso', 'perfil': 'interno', 'titulo': 'Práctica de picking', 'problema': 'Práctica de la carrera.',
            'resultado_esperado': 'Práctica realizada',
        })
        self.assertEqual(respuesta.status_code, 200)
        self.assertIsNone(respuesta.context['formulario'])
        self.assertContains(respuesta, 'No hay recursos habilitados para solicitar uso')
        self.assertContains(respuesta, 'Plantear una necesidad')
        self.assertFalse(SolicitudCentro.objects.exists())

    def test_la_ficha_del_laboratorio_dice_a_que_centro_se_integra(self):
        integran = centros_que_integran(ROBOTICA)
        self.assertEqual([fila['url'] for fila in integran], [reverse('centro_id', args=[self.centro.slug])])
        self.assertTrue(integran[0]['componentes'])
        pagina = self.client.get(reverse('laboratorio_detalle', kwargs={'slug': ROBOTICA}))
        self.assertContains(pagina, 'Se integra al Centro I+D')
        self.assertContains(pagina, reverse('centro_id', args=[self.centro.slug]))
        self.assertEqual(centros_que_integran('unidad-sin-centro'), [])


class PersonalizacionDeLaFichaTests(TestCase):
    """El mapa es el mismo para todos los centros; cada uno lo renombra, lo oculta o lo amplía con lo suyo."""

    @classmethod
    def setUpTestData(cls):
        cls.centro = Cargador(cidt).cargar()
        cls.gestor = get_user_model().objects.create_user('gestor.ficha', password='clave-segura-123')
        cls.centro.gestores.add(cls.gestor)

    def carpetas(self, pestana, usuario=None):
        if usuario:
            self.client.force_login(usuario)
        pagina = self.client.get(reverse('centro_id', args=[self.centro.slug]))
        return {p['clave']: p['carpetas'] for p in pagina.context['pestanas']}.get(pestana, [])

    def test_un_ajuste_renombra_u_oculta_una_seccion(self):
        AjusteSeccion.objects.create(centro=self.centro, clave='portafolio', titulo='Catálogo de servicios del CIDT')
        AjusteSeccion.objects.create(centro=self.centro, clave='vinculadas', oculta=True)
        servicios = {c['clave']: c for c in self.carpetas('servicios')}
        self.assertEqual(servicios['portafolio']['titulo'], 'Catálogo de servicios del CIDT')
        self.assertNotIn('vinculadas', {c['clave'] for c in self.carpetas('areas')})
        self.assertEqual(self.client.get(reverse('seccion_centro_id', args=[self.centro.slug, 'vinculadas'])).status_code, 404)
        self.assertContains(self.client.get(reverse('seccion_centro_id', args=[self.centro.slug, 'portafolio'])),
                            'Catálogo de servicios del CIDT')

    def test_una_carpeta_propia_entra_a_la_pestana_con_sus_recursos(self):
        carpeta = CarpetaCentro.objects.create(centro=self.centro, pestana='el-centro', nombre='Boletines del centro',
                                               descripcion='Lo que el centro publica cada trimestre.')
        RecursoCentro.objects.create(carpeta=carpeta, tipo='texto', titulo='Boletín 1', texto='Primer boletín.')
        RecursoCentro.objects.create(carpeta=carpeta, tipo='enlace', titulo='Sitio del proyecto', url='https://example.org/')
        propias = [c for c in self.carpetas('el-centro') if c['propia']]
        self.assertEqual([c['titulo'] for c in propias], ['Boletines del centro'])
        self.assertEqual(propias[0]['total'], 2)
        pagina = self.client.get(propias[0]['url'])
        self.assertEqual(pagina.status_code, 200)
        self.assertContains(pagina, 'Primer boletín.')
        self.assertContains(pagina, 'https://example.org/')
        abierta = self.client.get(reverse('centro_id', args=[self.centro.slug]), {'seccion': f'carpeta-{carpeta.pk}'})
        self.assertEqual(abierta.context['inicial']['url'], propias[0]['url'])
        # Una carpeta dentro de una sección cuelga de ella como una carpeta más del árbol.
        anexa = CarpetaCentro.objects.create(centro=self.centro, pestana='el-centro', seccion='documentos', nombre='Anexos')
        RecursoCentro.objects.create(carpeta=anexa, tipo='texto', titulo='Anexo A', texto='Texto del anexo.')
        documentos = next(c for c in self.carpetas('el-centro') if c['clave'] == 'documentos')
        self.assertEqual([(g['nombre'], g['propia'], len(g['botones'])) for g in documentos['grupos']], [('Anexos', True, 1)])
        self.assertEqual(documentos['total'], 1)

    def test_una_carpeta_interna_solo_la_ve_quien_gestiona(self):
        carpeta = CarpetaCentro.objects.create(centro=self.centro, pestana='servicios', nombre='Tarifario en revisión',
                                               visibilidad='interna')
        self.assertNotIn('Tarifario en revisión', [c['titulo'] for c in self.carpetas('servicios')])
        self.assertEqual(self.client.get(reverse('carpeta_centro_id', args=[self.centro.slug, carpeta.pk])).status_code, 404)
        self.assertIn('Tarifario en revisión', [c['titulo'] for c in self.carpetas('servicios', self.gestor)])
        self.assertEqual(self.client.get(reverse('carpeta_centro_id', args=[self.centro.slug, carpeta.pk])).status_code, 200)

    def test_lo_registrado_aparece_en_tiempo_real_en_sus_secciones(self):
        """Un proyecto nuevo actualiza proyectos, «Ahora» y las cifras de «Conoce el centro»."""
        self.assertNotIn('proyectos', [c['clave'] for c in self.carpetas('investigacion')])
        proyecto = Proyecto.objects.create(centro=self.centro, titulo='Trazabilidad de la leche con RFID', estado='ejecucion',
                                           etapa='prototipado', avance=40, resumen='Piloto con la planta de lácteos.',
                                           avance_metodo='Hitos ponderados', avance_fecha=timezone.localdate(),
                                           avance_evidencia='Informe de seguimiento')
        proyecto.componentes.add(self.centro.componentes.get(codigo='smart-cedi'))
        pagina = self.client.get(reverse('seccion_centro_id', args=[self.centro.slug, 'presentacion']))
        self.assertIn('proyectos', [c['clave'] for c in self.carpetas('investigacion')])
        self.assertEqual(pagina.context['cifras'][0], {'clave': 'proyectos', 'valor': 1, 'titulo': 'Proyectos en curso', 'icono': 'fas fa-rocket'})
        ahora = self.client.get(reverse('seccion_centro_id', args=[self.centro.slug, 'ahora']))
        self.assertContains(ahora, 'Trazabilidad de la leche con RFID')
        ficha = self.client.get(reverse('fragmento_centro_id', args=[self.centro.slug, 'proyecto', proyecto.pk]))
        self.assertContains(ficha, 'Prototipado')
        self.assertContains(ficha, '40%')
        cedi = self.client.get(reverse('componente_centro_id', args=[self.centro.slug, 'smart-cedi']))
        self.assertContains(cedi, 'Proyectos en los que interviene')


class RutaDeSolicitudTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.centro = Cargador(cidt).cargar()
        cls.usuario = get_user_model().objects.create_user('ruta.cidt')
        cls.zona = cls.centro.zonas.filter(reservable=True).first()
        cls.zona.estado_acceso, cls.zona.aforo = 'disponible', 20
        cls.zona.save()
        for dia in range(7):
            HorarioRecurso.objects.create(centro=cls.centro, zona=cls.zona, dia=dia, abre='08:00', cierra='18:00')

    def solicitud(self, **campos):
        datos = {'centro': self.centro, 'usuario': self.usuario, 'tipo': 'uso', 'titulo': 'Uso del Smart CEDI',
                 'problema': 'Práctica.', 'resultado_esperado': 'Práctica', 'zona': self.zona,
                 'participantes': 2, 'requisitos_validados': True, 'evidencia_requisitos': 'Comprobación de prueba'}
        datos.update(campos)
        return SolicitudCentro.objects.create(**datos)

    def test_la_ruta_avanza_paso_a_paso_y_registra_el_cierre(self):
        solicitud = self.solicitud()
        for estado in ('evaluacion', 'aprobada', 'ejecucion', 'entregada', 'cerrada'):
            solicitud.avanzar(estado)
        self.assertEqual(solicitud.estado, 'cerrada')
        self.assertIsNotNone(solicitud.cerrada_en)

    def test_la_ruta_no_salta_pasos_ni_reabre_lo_cerrado(self):
        solicitud = self.solicitud()
        with self.assertRaises(ValidationError):
            solicitud.avanzar('ejecucion')
        solicitud.avanzar('no_procede')
        with self.assertRaises(ValidationError):
            solicitud.avanzar('evaluacion')

    def test_un_area_no_se_asigna_dos_veces_en_el_mismo_horario(self):
        inicio = timezone.make_aware(datetime(2026, 11, 3, 9))
        self.solicitud(estado='aprobada', inicio_reservado=inicio, fin_reservado=inicio + timedelta(hours=2))
        choque = self.solicitud(inicio_reservado=inicio + timedelta(hours=1), fin_reservado=inicio + timedelta(hours=3))
        choque.estado = 'aprobada'
        with self.assertRaises(ValidationError) as error:
            choque.full_clean()
        self.assertIn('inicio_reservado', error.exception.message_dict)
        libre = self.solicitud(inicio_reservado=inicio + timedelta(hours=2), fin_reservado=inicio + timedelta(hours=4))
        libre.estado = 'aprobada'
        libre.full_clean()

    def test_el_acceso_termina_despues_de_empezar_y_en_un_area_del_centro(self):
        inicio = timezone.make_aware(datetime(2026, 11, 4, 9))
        with self.assertRaises(ValidationError):
            self.solicitud(inicio_reservado=inicio, fin_reservado=inicio).full_clean()
        otro = CentroID.objects.create(nombre='Otro centro', slug='otro-centro', area='digitales', proposito='Prueba.')
        ajena = Zona.objects.create(centro=otro, codigo='X-01', nombre='Área ajena', nivel='Nivel 1', area_m2=10)
        with self.assertRaises(ValidationError):
            self.solicitud(zona=ajena).full_clean()


class ProveedorDeUnidadesTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        modelo_unidad().objects.create(nombre='Laboratorio de prueba', slug=ROBOTICA, dependencia='laboratorios',
                                       descripcion='Unidad de prueba.', fecha_inicio=date(2026, 1, 1))

    def test_con_el_directorio_la_unidad_se_nombra_y_enlaza(self):
        self.assertEqual(unidad_publica(ROBOTICA)['url'], reverse('laboratorio_detalle', kwargs={'slug': ROBOTICA}))
        self.assertIsNone(unidad_publica('unidad-que-no-existe'))

    @override_settings(CENTROS_ID_UNIT_PROVIDER='')
    def test_sin_proveedor_el_centro_no_enlaza_unidades(self):
        self.assertIsNone(unidad_publica(ROBOTICA))

    @override_settings(CENTROS_ID_UNIT_PROVIDER='os.system')
    def test_solo_acepta_el_proveedor_registrado(self):
        with self.assertRaises(ValueError):
            proveedor_unidades()

    def test_las_sedes_del_mapa_llegan_solo_por_su_proveedor_registrado(self):
        self.assertIsInstance(sedes_en_el_mapa(), list)
        with override_settings(CENTROS_ID_SEDES_PROVIDER=''):
            self.assertEqual(sedes_en_el_mapa(), [])
        with override_settings(CENTROS_ID_SEDES_PROVIDER='os.listdir'):
            with self.assertRaises(ValueError):
                sedes_en_el_mapa()

@override_settings(MEDIA_ROOT=tempfile.mkdtemp())
class CentroOperandoConSuContenidoTests(TestCase):
    """Las muestras se conservan para revisión administrativa y nunca se publican como evidencia."""

    @classmethod
    def setUpTestData(cls):
        cls.centro = Cargador(cidt, medios=True, muestra=True).cargar()
        cls.gestor = get_user_model().objects.create_user('gestor.muestra', password='clave-segura-123')
        cls.centro.gestores.add(cls.gestor)

    def test_las_muestras_no_completan_las_secciones_institucionales(self):
        self.client.force_login(self.gestor)
        pagina = self.client.get(reverse('centro_id', args=[self.centro.slug]))
        carpetas = [c for p in pagina.context['pestanas'] for c in p['carpetas']]
        pendientes = {c['clave'] for c in carpetas if c['pendiente']}
        self.assertTrue({'direccion', 'investigadores', 'personal', 'proyectos', 'produccion',
                         'desarrollos', 'casos', 'oportunidades'} <= pendientes)
        self.assertNotContains(pagina, 'Muestras por revisar')
        self.assertNotContains(pagina, 'es_muestra__exact=1')
        self.client.logout()
        for clave in pendientes:
            with self.subTest(seccion=clave):
                respuesta = self.client.get(reverse('seccion_centro_id', args=[self.centro.slug, clave]))
                self.assertEqual(respuesta.status_code, 404)

    def test_cada_division_muestra_todo_lo_que_hace(self):
        for area in self.centro.componentes.filter(tipo='division'):
            with self.subTest(division=area.codigo):
                pagina = self.client.get(reverse('componente_centro_id', args=[self.centro.slug, area.codigo]))
                self.assertEqual(len(pagina.context['procesos']), 1)
                self.assertTrue(pagina.context['total_equipos'])
                self.assertTrue(pagina.context['servicios'])
                self.assertEqual(pagina.context['proyectos'], [])
                self.assertEqual(pagina.context['personas'], [])
        # Las divisiones son el primer grupo de áreas: van destacadas en «Conoce el centro» y en «Áreas del centro».
        areas = self.client.get(reverse('seccion_centro_id', args=[self.centro.slug, 'areas']))
        self.assertEqual([tipo for tipo, _ in areas.context['grupos_areas']][0], 'Tecnologías aplicadas')
        self.assertEqual(len(areas.context['grupos_areas'][0][1]), 5)
        conoce = self.client.get(reverse('seccion_centro_id', args=[self.centro.slug, 'presentacion']))
        self.assertEqual(conoce.context['grupos_areas'][0][0], 'Tecnologías aplicadas')

    def test_los_tesistas_institucionales_solo_se_cuentan_en_publico(self):
        from apps.centros_id.models import Integrante

        tecnico = Integrante.objects.create(centro=self.centro, nombre='Ana Técnica', rol='tecnico')
        tesista = Integrante.objects.create(centro=self.centro, nombre='Sofía Tesista', rol='tesista')
        proyecto = Proyecto.objects.create(centro=self.centro, titulo='Proyecto institucional', resumen='Investigación real')
        proyecto.equipo.add(tecnico, tesista)
        personal = self.client.get(reverse('seccion_centro_id', args=[self.centro.slug, 'personal']))
        self.assertContains(personal, tecnico.nombre)
        self.assertNotContains(personal, tesista.nombre)
        url = reverse('fragmento_centro_id', args=[self.centro.slug, 'proyecto', proyecto.pk])
        ficha = self.client.get(url)
        self.assertNotContains(ficha, tesista.nombre)
        self.assertContains(ficha, 'en formación')
        self.assertEqual(self.client.get(reverse('fragmento_centro_id', args=[self.centro.slug, 'persona', tesista.pk])).status_code, 404)
        self.client.force_login(self.gestor)
        self.assertContains(self.client.get(url), tesista.nombre)

    def test_los_documentos_se_generan_en_pdf_desde_los_registros(self):
        documentos = {d.titulo: d for d in self.centro.documentos.all()}
        for titulo in ('Plan de desarrollo y fortalecimiento del CIDT-UPEC', 'Ruta de atención y reglas de acceso',
                       'Protocolo de seguridad operacional', 'Catálogo de servicios del CIDT-UPEC',
                       'Equipamiento por división y plataforma', 'Política de datos, confidencialidad y propiedad intelectual',
                       'Código de ética e integridad en la investigación aplicada'):
            with self.subTest(documento=titulo):
                self.assertIn(titulo, documentos)
                with documentos[titulo].archivo.open('rb') as archivo:
                    self.assertEqual(archivo.read(4), b'%PDF')

    def test_los_indicadores_se_cuentan_con_el_contenido(self):
        from apps.centros_id.contenidos import Contenidos

        valores = {i.nombre: i.valor for i in Contenidos(self.centro).indicadores_medidos}
        self.assertEqual(valores['Proyectos de I+D+i activos'], 0)
        self.assertEqual(valores['Proyectos concluidos'], 0)
        self.assertEqual(valores['Aliados vigentes'], 0)

    def test_cargar_de_nuevo_no_duplica_el_contenido(self):
        proyectos, integrantes = self.centro.proyectos.count(), self.centro.integrantes.count()
        otra = Cargador(cidt, medios=True, muestra=True)
        otra.cargar()
        self.assertEqual((self.centro.proyectos.count(), self.centro.integrantes.count()), (proyectos, integrantes))
        self.assertEqual(otra.resumen(), 'Al día')
