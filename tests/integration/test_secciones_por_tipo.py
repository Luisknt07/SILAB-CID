"""Cada vertical administra sus unidades y ninguna ve las de otra.

La tabla de unidades sigue siendo una sola mientras dura la compatibilidad.
Lo que separa a las verticales es la tipología, así que la comprobación mira
lo que cada sección devuelve, no cómo lo consigue.
"""

from datetime import date
from unittest.mock import patch

from django.contrib import admin
from django.contrib.auth import get_user_model
from django.db.models import Q
from django.test import RequestFactory, TestCase

from apps.centros_experimentales.models import CentroExperimental
from apps.configuracion_institucional.tipologias.models import TipologiaUnidad, sembrar_bases
from apps.laboratorios.models import Laboratorio
from apps.observatorios.models import Observatorio
from apps.plantas_piloto.models import PlantaPiloto
from apps.directorio_unidades.models.core import Unidad

SECCIONES = (
    (Laboratorio, 'laboratorios'),
    (PlantaPiloto, 'plantas_piloto'),
    (CentroExperimental, 'centro_experimental'),
    (Observatorio, 'observatorios'),
)


class SeccionesPorTipoTests(TestCase):
    def setUp(self):
        self.autor = get_user_model().objects.create_superuser('secciones.qa')
        self.peticion = RequestFactory().get('/admin/')
        self.peticion.user = self.autor
        for codigo in ('laboratorios', 'plantas_piloto', 'centro_experimental', 'observatorios'):
            self.crear(f'Unidad {codigo}', f'unidad-{codigo}', codigo)

    def crear(self, nombre, slug, codigo):
        return Unidad.objects.create(nombre=nombre, slug=slug, dependencia=codigo,
                                     fecha_inicio=date(2026, 1, 1))

    def seccion(self, modelo):
        return admin.site._registry[modelo]

    def test_cada_seccion_solo_muestra_sus_unidades(self):
        for modelo, codigo in SECCIONES:
            with self.subTest(seccion=modelo._meta.label):
                listado = self.seccion(modelo).get_queryset(self.peticion)
                self.assertTrue(listado.exists())
                self.assertEqual({u.dependencia for u in listado}, {codigo})

    def test_las_cuatro_reparten_el_total_sin_solapes(self):
        """Ninguna unidad se queda fuera ni aparece en dos secciones."""
        vistas = []
        for modelo, _ in SECCIONES:
            vistas.extend(self.seccion(modelo).get_queryset(self.peticion).values_list('pk', flat=True))
        self.assertEqual(len(vistas), len(set(vistas)))
        self.assertEqual(set(vistas), set(Unidad.objects.values_list('pk', flat=True)))

    def test_una_tipologia_nueva_aparece_en_la_seccion_de_su_base(self):
        """Declarar una modalidad no obliga a tocar el código de la vertical."""
        sembrar_bases(TipologiaUnidad)
        TipologiaUnidad.objects.create(
            codigo='laboratorio_movil', nombre='Laboratorio móvil',
            nombre_plural='Laboratorios móviles', base='laboratorios', orden=50)
        movil = self.crear('Unidad móvil', 'unidad-movil', 'laboratorio_movil')

        listado = self.seccion(Laboratorio).get_queryset(self.peticion)
        self.assertIn(movil.pk, [u.pk for u in listado])
        for modelo, _ in SECCIONES[1:]:
            with self.subTest(seccion=modelo._meta.label):
                self.assertNotIn(movil.pk, [u.pk for u in self.seccion(modelo).get_queryset(self.peticion)])

    def test_desde_una_seccion_no_se_cambia_la_unidad_de_tipo(self):
        """El selector de tipo solo ofrece las tipologías de esa vertical."""
        for modelo, codigo in SECCIONES:
            with self.subTest(seccion=modelo._meta.label):
                # Se mira el formulario ya construido: las opciones se arman
                # al instanciarlo, no en la clase.
                formulario = self.seccion(modelo).get_form(self.peticion)()
                ofrecidas = {valor for valor, _ in formulario.fields['dependencia'].choices if valor}
                self.assertEqual(ofrecidas, {codigo})

    def test_una_unidad_nueva_nace_con_el_tipo_de_su_seccion(self):
        for modelo, codigo in SECCIONES:
            with self.subTest(seccion=modelo._meta.label):
                inicial = self.seccion(modelo).get_changeform_initial_data(self.peticion)
                self.assertEqual(inicial.get('dependencia'), codigo)

    def test_las_secciones_no_duplican_datos(self):
        """Son modelos delegados: una sola tabla, sin copias que sincronizar."""
        for modelo, _ in SECCIONES:
            with self.subTest(seccion=modelo._meta.label):
                self.assertTrue(modelo._meta.proxy)
                self.assertEqual(modelo._meta.db_table, Unidad._meta.db_table)

    def test_cada_tipo_tiene_su_area_y_la_encabeza_su_lista_de_unidades(self):
        """Un area por tipo; sin area declarada caerian en el cajon de sobras."""
        areas = {area['name']: area for area in admin.site.get_app_list(self.peticion)}
        for modelo, _ in SECCIONES:
            with self.subTest(seccion=modelo.__name__):
                nombre = str(modelo._meta.verbose_name_plural)
                self.assertIn(nombre, areas)
                herramientas = [m['object_name'] for m in areas[nombre]['models']]
                # La lista de unidades abre el area: es la entrada, no un anexo.
                self.assertEqual(herramientas[0], modelo.__name__)

    def test_ningun_registro_queda_sin_area(self):
        """El cajon de sobras deja de existir: todo tiene su sitio declarado."""
        areas = admin.site.get_app_list(self.peticion)
        sobras = [a for a in areas if a.get('slug') == 'configuracion']
        self.assertEqual(sobras, [], 'Hay registros sin area: '
                         + ', '.join(m['name'] for a in sobras for m in a['models']))

    def test_la_lista_combinada_sale_del_indice_pero_sigue_accesible(self):
        """Mezclar los tipos otra vez es justo lo que estas secciones evitan.

        Se retira del indice, no del registro: otras pantallas enlazan a la
        ficha de una unidad y los selectores de unidad la necesitan.
        """
        from django.urls import reverse

        mostrados = {m['object_name'] for area in admin.site.get_app_list(self.peticion)
                     for m in area['models']}
        self.assertNotIn('Unidad', mostrados)

        self.client.force_login(self.autor)
        unidad = Unidad.objects.first()
        self.assertEqual(self.client.get(reverse('admin:directorio_unidades_unidad_changelist')).status_code, 200)
        self.assertEqual(
            self.client.get(reverse('admin:directorio_unidades_unidad_change', args=[unidad.pk])).status_code, 200)

    def test_un_centro_id_no_es_una_unidad_ni_comparte_su_tabla(self):
        """Centros I+D es otra categoria: no se agenda ni presta equipos.

        Se comprueba desde fuera de las verticales porque la comparacion cruza
        la frontera entre el registro nuevo y el heredado.
        """
        from apps.centros_id.models import CentroID

        self.assertNotEqual(CentroID._meta.db_table, Unidad._meta.db_table)
        self.assertFalse(CentroID._meta.proxy)
        self.assertFalse(any(campo.related_model is Unidad
                             for campo in CentroID._meta.get_fields() if campo.is_relation))
        areas = {a['name']: a for a in admin.site.get_app_list(self.peticion)}
        for modelo, _ in SECCIONES:
            with self.subTest(area=modelo.__name__):
                area = areas[str(modelo._meta.verbose_name_plural)]
                self.assertNotIn('CentroID', {m['object_name'] for m in area['models']})
        self.assertIn('Centros de Investigación y Desarrollo', areas)

    def test_cada_area_se_lee_por_bloques_de_funcion_y_no_como_lista_plana(self):
        """Treinta herramientas seguidas no se siguen; por bloques, sí.

        El orden y los nombres de los bloques son los de las FUNCIONES que
        declara la vertical: la unidad primero, luego cada funcion.
        """
        from django.apps import apps

        from apps.integraciones.unidades import FUNCIONES_DE_UNIDAD

        areas = {a['name']: a for a in admin.site.get_app_list(self.peticion)}
        for modelo, _ in SECCIONES:
            with self.subTest(area=modelo.__name__):
                area = areas[str(modelo._meta.verbose_name_plural)]
                bloques = area.get('grupos') or []
                declaradas = apps.get_app_config(modelo._meta.app_label).models_module.FUNCIONES
                self.assertEqual([b['name'] for b in bloques],
                                 ['Fichas de unidad']
                                 + [FUNCIONES_DE_UNIDAD[clave].nombre for clave in declaradas])
                # La lista del tipo; los tipos de unidad se administran una sola vez, en Catálogos.
                self.assertEqual([m['object_name'] for m in bloques[0]['models']], [modelo.__name__])
                # Ningun bloque vacio y ninguna herramienta fuera de un bloque.
                repartidas = [m['object_name'] for bloque in bloques for m in bloque['models']]
                self.assertTrue(all(bloque['models'] for bloque in bloques))
                self.assertEqual(sorted(repartidas), sorted(m['object_name'] for m in area['models']))
                self.assertEqual(len(repartidas), len(set(repartidas)))

    def test_ningun_area_declara_herramientas_que_no_existen(self):
        """Un modelo mal escrito en una categoria desaparece sin avisar."""
        from apps.core.admin.site import categorias_admin

        registrados = {f'{m._meta.app_label}.{m.__name__}' for m in admin.site._registry}
        for categoria in categorias_admin():
            declarados = list(categoria.get('models') or ())
            for grupo in categoria.get('grupos', ()):
                declarados.extend(grupo['models'])
            for clave in declarados:
                with self.subTest(categoria=categoria['slug'], modelo=clave):
                    self.assertIn(clave, registrados)

    def test_lo_que_se_edita_dentro_de_la_unidad_no_se_lista_aparte(self):
        """Una lista de 105 horarios de 21 unidades no dice de quien es cada uno.

        Todo lo que el formulario de la unidad ya administra como bloque
        interno sale del indice: se abre la unidad y se ve lo suyo. Sigue
        registrado, porque otras pantallas enlazan a esas fichas.
        """
        from django.urls import reverse

        panel = admin.site._registry[Laboratorio]
        dentro = {inline.model._meta.label for inline in panel.inlines}
        nombres = {m['object_name'] for area in admin.site.get_app_list(self.peticion)
                   for m in area['models']}
        for etiqueta in dentro:
            with self.subTest(modelo=etiqueta):
                self.assertNotIn(etiqueta.split('.')[-1], nombres)

        # Pero siguen accesibles: sacarlas del indice no es desregistrarlas.
        self.client.force_login(self.autor)
        self.assertEqual(
            self.client.get(reverse('admin:gestion_unidades_horariooperacionunidad_changelist')).status_code, 200)

    def test_la_lista_muestra_el_nombre_del_tipo_y_no_su_codigo(self):
        """`laboratorios` es para el sistema; la persona lee «Laboratorio». En una
        seccion de un solo tipo la columna sobra."""
        from django.urls import reverse

        self.client.force_login(self.autor)
        general = self.client.get(reverse('admin:directorio_unidades_unidad_changelist')).content.decode()
        self.assertIn('field-tipo_de_unidad', general)
        self.assertNotIn('>laboratorios<', general)
        seccion = self.client.get(reverse('admin:laboratorios_laboratorio_changelist')).content.decode()
        self.assertNotIn('field-tipo_de_unidad', seccion)

    def test_abrir_una_unidad_da_acceso_a_todo_lo_suyo(self):
        """Lo que se saco del indice tiene que estar dentro de la unidad."""
        panel = admin.site._registry[Laboratorio]
        dentro = {inline.model._meta.label for inline in panel.inlines}
        for etiqueta in ('gestion_unidades.HorarioOperacionUnidad', 'gestion_unidades.EspacioReservable',
                         'gestion_unidades.CapacidadOperativaUnidad', 'gestion_unidades.BloqueoAgendaUnidad',
                         'recursos.ReglamentoUnidad', 'recursos.ModuloUnidad',
                         'gestion_unidades.ResponsableUnidad', 'recursos.Recurso'):
            with self.subTest(modelo=etiqueta):
                self.assertIn(etiqueta, dentro)
        # Las carpetas propias no son un bloque del editor: se ordenan en «Contenidos de la ficha» de la unidad.
        self.assertIn('laboratorios_laboratorio_contenidos', {ruta.name for ruta in panel.get_urls()})


class RegistrosDeCadaUnidadTests(TestCase):
    """Lo que pertenece a una unidad se tiene que poder mirar unidad por unidad.

    Los expedientes operativos (reservas, consumibles, produccion) no caben
    dentro del formulario de la unidad: son cientos de filas con su propio
    ciclo. Lo que si exigimos es que ninguno obligue a leer la lista entera de
    todas las unidades para encontrar la suya.
    """

    def setUp(self):
        self.peticion = RequestFactory().get('/admin/')
        self.peticion.user = get_user_model().objects.create_superuser('registros.qa')

    @staticmethod
    def ruta_a_la_unidad(modelo, profundidad=0):
        """Nombre del campo que lleva de este modelo a su unidad, o None."""
        from django.db import models as campos

        if profundidad > 2:
            return None
        relaciones = [c for c in modelo._meta.get_fields()
                      if isinstance(c, (campos.ForeignKey, campos.OneToOneField))]
        for campo in relaciones:
            if campo.related_model is Unidad:
                return campo.name
        for campo in relaciones:
            if campo.related_model is modelo:
                continue
            resto = RegistrosDeCadaUnidadTests.ruta_a_la_unidad(campo.related_model, profundidad + 1)
            if resto:
                return '{}__{}'.format(campo.name, resto)
        return None

    def test_todo_expediente_de_una_unidad_se_puede_filtrar_por_su_unidad(self):
        dentro = {inline.model._meta.label for inline in admin.site._registry[Laboratorio].inlines}
        sin_filtro = []
        for modelo, panel in admin.site._registry.items():
            if modelo is Unidad or modelo._meta.label in dentro:
                continue
            if modelo._meta.proxy and modelo._meta.concrete_model is Unidad:
                continue
            ruta = self.ruta_a_la_unidad(modelo)
            if not ruta:
                continue
            raiz = ruta.split('__')[0]
            declarados = [f[0] if isinstance(f, tuple) else f if isinstance(f, str)
                          else getattr(f, 'parameter_name', '') for f in (panel.list_filter or ())]
            if not any(str(f).split('__')[0] == raiz for f in declarados):
                sin_filtro.append('{} (ruta {})'.format(modelo._meta.label, ruta))
        self.assertEqual(sin_filtro, [], 'Paneles sin filtro por unidad: {}'.format(sin_filtro))

    def test_el_filtro_por_unidad_devuelve_solo_las_filas_de_esa_unidad(self):
        """El filtro no basta con estar declarado: tiene que acotar de verdad."""
        from django.urls import reverse

        from apps.reservas.models.reservas import CatalogoActividadReserva

        mia = Unidad.objects.create(nombre='Unidad propia', slug='unidad-propia',
                                    dependencia='laboratorios', fecha_inicio=date(2026, 1, 1))
        ajena = Unidad.objects.create(nombre='Unidad ajena', slug='unidad-ajena',
                                      dependencia='laboratorios', fecha_inicio=date(2026, 1, 1))
        CatalogoActividadReserva.objects.create(unidad=mia, nombre='Practica propia')
        CatalogoActividadReserva.objects.create(unidad=ajena, nombre='Practica ajena')

        self.client.force_login(self.peticion.user)
        pagina = self.client.get(
            reverse('admin:reservas_catalogoactividadreserva_changelist'), {'unidad__id__exact': mia.pk})

        self.assertEqual(pagina.status_code, 200)
        self.assertContains(pagina, 'Practica propia')
        self.assertNotContains(pagina, 'Practica ajena')


class FichaDeLaUnidadTests(TestCase):
    """La ficha de una unidad se abre igual desde su sección por tipo que desde la general."""

    def setUp(self):
        from apps.recursos.models.recursos import CarpetaRecurso
        from apps.recursos.models.unidades import UnidadEquipo

        self.autor = get_user_model().objects.create_superuser('ficha.qa')
        self.client.force_login(self.autor)
        self.mia = Unidad.objects.create(nombre='Laboratorio propio', slug='lab-propio',
                                         dependencia='laboratorios', fecha_inicio=date(2026, 1, 1))
        ajena = Unidad.objects.create(nombre='Laboratorio ajeno', slug='lab-ajeno',
                                      dependencia='laboratorios', fecha_inicio=date(2026, 1, 1))
        catalogo = UnidadEquipo._meta.get_field('equipo').related_model
        for unidad, apodo in ((self.mia, 'propio'), (ajena, 'ajeno')):
            equipo = catalogo.objects.create(codigo='EQ-' + apodo, nombre='Microscopio ' + apodo)
            UnidadEquipo.objects.create(laboratorio=unidad, equipo=equipo,
                                        codigo_unidad='UE-' + apodo, activa=True)
            CarpetaRecurso.objects.create(unidad=unidad, nombre='Carpeta ' + apodo)

    def rutas(self):
        from django.urls import reverse

        return (reverse('admin:laboratorios_laboratorio_change', args=[self.mia.pk]),
                reverse('admin:directorio_unidades_unidad_change', args=[self.mia.pk]))

    def test_los_selectores_ofrecen_lo_de_esa_unidad_desde_cualquier_seccion(self):
        """Antes se buscaba `/unidad/<id>/` en la URL: en la sección por tipo salían vacíos."""
        for ruta in self.rutas():
            with self.subTest(ruta=ruta):
                pagina = self.client.get(ruta)
                self.assertEqual(pagina.status_code, 200)
                self.assertContains(pagina, 'Microscopio propio')
                self.assertNotContains(pagina, 'Microscopio ajeno')
                self.assertContains(pagina, 'Carpeta propio')
                self.assertNotContains(pagina, 'Carpeta ajeno')

    def test_la_ficha_abre_sus_grupos_con_los_elementos_plegados(self):
        """Los grupos se ven de un vistazo; cada elemento se abre uno a uno."""
        import re

        for ruta in self.rutas():
            with self.subTest(ruta=ruta):
                html = self.client.get(ruta).content.decode()
                grupos = re.findall(r'class="inline-group grp-group grp-(?:stacked|tabular)([^"]*)"', html)
                self.assertGreaterEqual(len(grupos), 11)
                cerrados = [g for g in grupos if 'grp-collapse grp-open' not in g]
                self.assertEqual(cerrados, [], 'Grupos que no abren: {}'.format(cerrados))
                elementos = re.findall(r'class="inline-related grp-module ([^"]*)"', html)
                abiertos = [e for e in elementos if 'grp-closed' not in e]
                self.assertEqual(abiertos, [], 'Elementos abiertos de entrada: {}'.format(abiertos))


class FuncionesPorTipoTests(TestCase):
    """Cada tipo administra sus expedientes con los mismos nombres y solo sus datos."""

    @staticmethod
    def secciones_de_funcion():
        from django.apps import apps

        for modelo, _ in SECCIONES:
            modulo = apps.get_app_config(modelo._meta.app_label).models_module
            for proxy in modulo.MODELOS_DE_FUNCION:
                yield proxy

    def setUp(self):
        self.autor = get_user_model().objects.create_superuser('funciones.qa')
        self.peticion = RequestFactory().get('/admin/')
        self.peticion.user = self.autor
        self.laboratorio = Unidad.objects.create(nombre='Laboratorio propio', slug='lab-propio',
                                                 dependencia='laboratorios', fecha_inicio=date(2026, 1, 1))
        self.planta = Unidad.objects.create(nombre='Planta propia', slug='planta-propia',
                                            dependencia='plantas_piloto', fecha_inicio=date(2026, 1, 1))

    def test_cada_seccion_es_un_delegado_con_permisos_propios(self):
        """Misma tabla que el heredado; permisos por tipo, para dar acceso por separado."""
        from django.contrib.auth.models import Permission

        for proxy in self.secciones_de_funcion():
            with self.subTest(seccion=proxy._meta.label):
                self.assertTrue(proxy._meta.proxy)
                self.assertEqual(proxy._meta.db_table, proxy._meta.proxy_for_model._meta.db_table)
                self.assertTrue(Permission.objects.filter(
                    content_type__app_label=proxy._meta.app_label,
                    codename=f'view_{proxy._meta.model_name}').exists())

    def test_cada_seccion_solo_devuelve_lo_de_sus_unidades(self):
        """Las 127 consultas llevan el recorte por tipo; sin excepciones."""
        from apps.core.presentation.tipologias import codigos_por_base

        for proxy in self.secciones_de_funcion():
            with self.subTest(seccion=proxy._meta.label):
                panel = admin.site._registry[proxy]
                self.assertTrue(panel.ruta, 'sin camino a la unidad')
                codigos = codigos_por_base(panel.base_tipologia)
                self.assertTrue(codigos)
                propio = Q(**{f'{panel.ruta}__dependencia__in': codigos})
                if panel.ruta_inversa:
                    propio |= Q(**{f'{panel.ruta}__isnull': True})
                esperado = set(proxy._meta.proxy_for_model._default_manager.filter(propio)
                               .values_list('pk', flat=True))
                self.assertEqual(set(panel.get_queryset(self.peticion).values_list('pk', flat=True)),
                                 esperado)

    def test_la_lista_de_un_tipo_no_muestra_expedientes_de_otro(self):
        from django.urls import reverse

        from apps.reservas.models.reservas import CatalogoActividadReserva

        CatalogoActividadReserva.objects.create(unidad=self.laboratorio, nombre='Practica de laboratorio')
        CatalogoActividadReserva.objects.create(unidad=self.planta, nombre='Practica de planta')
        self.client.force_login(self.autor)

        plantas = self.client.get(reverse('admin:plantas_piloto_catalogoactividadreserva_changelist'), {'todas': '1'})
        laboratorios = self.client.get(reverse('admin:laboratorios_catalogoactividadreserva_changelist'), {'todas': '1'})

        self.assertContains(plantas, 'Practica de planta')
        self.assertNotContains(plantas, 'Practica de laboratorio')
        self.assertContains(laboratorios, 'Practica de laboratorio')
        self.assertNotContains(laboratorios, 'Practica de planta')

    def test_al_crear_desde_un_tipo_solo_se_ofrecen_sus_unidades(self):
        """El selector de unidad de cada seccion no deja escapar el registro a otro tipo."""
        from django.forms import ModelChoiceField

        from apps.core.presentation.tipologias import codigos_por_base

        revisados = 0
        for proxy in self.secciones_de_funcion():
            panel = admin.site._registry[proxy]
            primero, _, resto = panel.ruta.partition('__')
            if not panel.has_add_permission(self.peticion):
                continue
            campo = panel.get_form(self.peticion)().fields.get(primero)
            if not isinstance(campo, ModelChoiceField):
                continue
            with self.subTest(seccion=proxy._meta.label):
                filtro = f'{resto}__dependencia' if resto else 'dependencia'
                ofrecidas = set(campo.queryset.values_list(filtro, flat=True))
                self.assertTrue(ofrecidas <= set(codigos_por_base(panel.base_tipologia)),
                                f'ofrece unidades ajenas: {ofrecidas}')
            revisados += 1
        self.assertGreater(revisados, 20)

    def test_todas_las_secciones_abren(self):
        """Ciento veintisiete listas: ninguna puede romperse por heredar un panel."""
        from django.urls import reverse

        self.client.force_login(self.autor)
        for proxy in self.secciones_de_funcion():
            with self.subTest(seccion=proxy._meta.label):
                url = reverse(f'admin:{proxy._meta.app_label}_{proxy._meta.model_name}_changelist')
                self.assertEqual(self.client.get(url).status_code, 200)

    def test_los_expedientes_heredados_salen_del_indice_pero_siguen_accesibles(self):
        """Volver a listar «Reservas» de todos los tipos es justo la mezcla que se evita."""
        from django.urls import reverse

        heredados_en_el_indice = {
            m['object_name'] for area in admin.site.get_app_list(self.peticion)
            for m in area['models'] if m.get('admin_url', '').startswith('/admin/webcitt/')}
        for heredado in ('Reserva', 'Consumible', 'Producto', 'UnidadEquipo', 'ReporteOperativoUnidad'):
            with self.subTest(heredado=heredado):
                self.assertNotIn(heredado, heredados_en_el_indice)
        self.client.force_login(self.autor)
        self.assertEqual(self.client.get(reverse('admin:reservas_reserva_changelist')).status_code, 200)

    def test_las_rutas_propias_del_panel_heredado_no_cambian_de_dueno(self):
        """Los reportes generales siguen siendo generales; cada seccion tiene los suyos."""
        from django.urls import reverse

        self.assertEqual(reverse('admin:reservas-estadisticas'), '/admin/reservas/reserva/estadisticas/')
        self.assertEqual(reverse('admin:plantas_piloto-reservas-estadisticas'),
                         '/admin/plantas_piloto/reserva/estadisticas/')


class RecursosDeCadaUnidadTests(TestCase):
    """Una unidad con cientos de equipos e insumos solo dispone de los suyos."""

    def setUp(self):
        from apps.recursos.models.consumibles import Consumible
        from apps.recursos.models.unidades import UnidadEquipo

        self.autor = get_user_model().objects.create_superuser('recursos.qa')
        self.client.force_login(self.autor)
        self.lab = Unidad.objects.create(nombre='Laboratorio de suelos', slug='lab-suelos',
                                         dependencia='laboratorios', fecha_inicio=date(2026, 1, 1))
        self.planta = Unidad.objects.create(nombre='Planta de lacteos', slug='planta-lacteos',
                                            dependencia='plantas_piloto', fecha_inicio=date(2026, 1, 1))
        catalogo = UnidadEquipo._meta.get_field('equipo').related_model
        for unidad, apodo in ((self.lab, 'suelos'), (self.planta, 'lacteos')):
            ficha = catalogo.objects.create(codigo=f'EQ-{apodo}', nombre=f'Equipo de {apodo}')
            UnidadEquipo.objects.create(laboratorio=unidad, equipo=ficha, codigo_unidad=f'UE-{apodo}', activa=True)
            Consumible.objects.create(unidad=unidad, codigo=f'INS-{apodo}', nombre=f'Insumo de {apodo}')
        self.sin_asignar = catalogo.objects.create(codigo='EQ-nuevo', nombre='Equipo sin asignar')

    def test_las_fichas_tecnicas_de_un_tipo_son_las_de_sus_unidades(self):
        """Setenta y nueve de ochenta fichas pertenecen a una sola unidad: van con su tipo."""
        from django.urls import reverse

        plantas = self.client.get(reverse('admin:plantas_piloto_equiposservicios_changelist'), {'todas': '1'})
        laboratorios = self.client.get(reverse('admin:laboratorios_equiposservicios_changelist'), {'todas': '1'})

        self.assertContains(plantas, 'Equipo de lacteos')
        self.assertNotContains(plantas, 'Equipo de suelos')
        self.assertContains(laboratorios, 'Equipo de suelos')
        self.assertNotContains(laboratorios, 'Equipo de lacteos')
        # Una ficha recien creada aun no tiene unidad: se ve hasta que se asigne.
        self.assertContains(plantas, 'Equipo sin asignar')
        self.assertContains(plantas, 'Fichas técnicas de equipos')

    def test_un_equipo_compartido_aparece_en_cada_tipo_que_lo_usa_sin_repetirse(self):
        import re

        from django.urls import reverse

        from apps.recursos.models.unidades import UnidadEquipo

        otro_lab = Unidad.objects.create(nombre='Laboratorio de aguas', slug='lab-aguas',
                                         dependencia='laboratorios', fecha_inicio=date(2026, 1, 1))
        compartido = self.sin_asignar
        for unidad, codigo in ((self.lab, 'UE-c1'), (otro_lab, 'UE-c2'), (self.planta, 'UE-c3')):
            UnidadEquipo.objects.create(laboratorio=unidad, equipo=compartido, codigo_unidad=codigo, activa=True)

        for ruta in ('admin:laboratorios_equiposservicios_changelist',
                     'admin:plantas_piloto_equiposservicios_changelist'):
            with self.subTest(ruta=ruta):
                pagina = self.client.get(reverse(ruta), {'todas': '1'})
                # Una fila (la etiqueta accesible de su casilla tambien lo nombra).
                self.assertEqual(len(re.findall(r'field-codigo"><a[^>]*>EQ-nuevo<', pagina.content.decode())), 1)

    def test_cada_unidad_enlaza_sus_propios_recursos_desde_su_fila(self):
        from django.urls import reverse

        lista = self.client.get(reverse('admin:plantas_piloto_plantapiloto_changelist'))

        self.assertContains(lista, 'Sus recursos')
        equipos = reverse('admin:plantas_piloto_unidadequipo_changelist')
        insumos = reverse('admin:plantas_piloto_consumible_changelist')
        self.assertContains(lista, f'href="{equipos}?laboratorio__id__exact={self.planta.pk}">1 equipos')
        self.assertContains(lista, f'href="{insumos}?unidad__id__exact={self.planta.pk}">1 insumos')
        # Y el enlace lleva a una lista con lo suyo y nada mas.
        propios = self.client.get(f'{equipos}?laboratorio__id__exact={self.planta.pk}')
        self.assertContains(propios, 'UE-lacteos')
        self.assertNotContains(propios, 'UE-suelos')

    def test_el_catalogo_de_categorias_sigue_compartido_en_catalogos(self):
        peticion = RequestFactory().get('/admin/')
        peticion.user = self.autor
        areas = {a['name']: a for a in admin.site.get_app_list(peticion)}
        self.assertNotIn('Equipos y recursos tecnológicos', areas)
        catalogos = {m['object_name'] for m in areas['Catálogos institucionales']['models']}
        self.assertIn('CategoriaEquipo', catalogos)
        self.assertNotIn('EquiposServicios', catalogos)


class PuertaPorUnidadTests(TestCase):
    """Con cuarenta laboratorios, un expediente se abre unidad por unidad."""

    def setUp(self):
        from apps.recursos.models.unidades import UnidadEquipo

        self.autor = get_user_model().objects.create_superuser('puerta.qa')
        self.client.force_login(self.autor)
        self.suelos = Unidad.objects.create(nombre='Laboratorio de suelos', slug='lab-suelos',
                                            dependencia='laboratorios', fecha_inicio=date(2026, 1, 1))
        self.aguas = Unidad.objects.create(nombre='Laboratorio de aguas', slug='lab-aguas',
                                           dependencia='laboratorios', fecha_inicio=date(2026, 1, 1))
        catalogo = UnidadEquipo._meta.get_field('equipo').related_model
        for unidad, apodo, cuantos in ((self.suelos, 'suelos', 2), (self.aguas, 'aguas', 1)):
            ficha = catalogo.objects.create(codigo=f'EQ-{apodo}', nombre=f'Equipo de {apodo}')
            for n in range(cuantos):
                UnidadEquipo.objects.create(laboratorio=unidad, equipo=ficha,
                                            codigo_unidad=f'UE-{apodo}-{n}', activa=True)
        self.suelto = catalogo.objects.create(codigo='EQ-suelto', nombre='Equipo suelto')

    def lista(self, ruta='admin:laboratorios_unidadequipo_changelist', **parametros):
        from django.urls import reverse

        return self.client.get(reverse(ruta), parametros)

    def test_sin_unidad_elegida_se_ofrecen_las_unidades_con_su_conteo(self):
        pagina = self.lista()

        self.assertEqual(pagina.status_code, 200)
        self.assertContains(pagina, 'ELIGE LA UNIDAD')
        self.assertContains(pagina, 'Laboratorio de suelos')
        self.assertContains(pagina, 'Laboratorio de aguas')
        filas = {f['unidad'].pk: f['total'] for f in pagina.context['unidades']}
        self.assertEqual(filas[self.suelos.pk], 2)
        self.assertEqual(filas[self.aguas.pk], 1)
        # Ninguna fila de equipo todavia: nada se mezcla.
        self.assertNotContains(pagina, 'UE-suelos-0')
        self.assertContains(pagina, f'?laboratorio__id__exact={self.suelos.pk}')

    def test_con_la_unidad_elegida_solo_salen_sus_filas(self):
        pagina = self.lista(laboratorio__id__exact=self.suelos.pk)

        self.assertNotContains(pagina, 'ELIGE LA UNIDAD')
        self.assertContains(pagina, 'UE-suelos-0')
        self.assertContains(pagina, 'UE-suelos-1')
        self.assertNotContains(pagina, 'UE-aguas-0')

    def test_buscar_o_pedir_todas_salta_la_puerta(self):
        self.assertContains(self.lista(q='UE-aguas'), 'UE-aguas-0')
        todas = self.lista(todas='1')
        self.assertContains(todas, 'UE-suelos-0')
        self.assertContains(todas, 'UE-aguas-0')

    def test_la_puerta_tambien_sirve_a_las_fichas_tecnicas_por_relacion_inversa(self):
        ruta = 'admin:laboratorios_equiposservicios_changelist'
        puerta = self.lista(ruta)

        self.assertContains(puerta, 'ELIGE LA UNIDAD')
        self.assertContains(puerta, 'Sin unidad asignada')
        self.assertEqual(puerta.context['sin_asignar']['total'], 1)
        propias = self.lista(ruta, unidades__laboratorio__id__exact=self.suelos.pk)
        self.assertEqual(propias.status_code, 200)
        self.assertContains(propias, 'EQ-suelos')
        self.assertNotContains(propias, 'EQ-aguas')
        sueltas = self.lista(ruta, unidades__laboratorio__isnull='True')
        self.assertContains(sueltas, 'EQ-suelto')
        self.assertNotContains(sueltas, 'EQ-suelos')

    def test_sin_permiso_de_lectura_la_puerta_tambien_cierra(self):
        personal = get_user_model().objects.create_user('lector.qa', is_staff=True)
        self.client.force_login(personal)

        self.assertEqual(self.lista().status_code, 403)


class AreaDeReportesTests(TestCase):
    """Todos los reportes del administrador, en un solo sitio y segun permiso."""

    def setUp(self):
        self.superusuario = get_user_model().objects.create_superuser('reportes.qa')

    def area(self, usuario):
        peticion = RequestFactory().get('/admin/')
        peticion.user = usuario
        return next((a for a in admin.site.get_app_list(peticion) if a['slug'] == 'reportes'), None)

    def test_el_area_reune_sus_reportes_y_cada_uno_abre(self):
        from django.urls import reverse

        area = self.area(self.superusuario)
        self.assertIsNotNone(area)
        self.assertEqual([m['name'] for m in area['models']], [
            'Alertas de uso de equipos', 'Traspasos de equipos', 'Transparencia en el uso de equipos',
            'Reportes de Centros I+D',
            'Reporte institucional',
            'Reportes operativos por unidad',
            'Cumplimiento del expediente por unidad',
            'Resumen anual de entregas', 'Necesidades de compras por centro de costo', 'Remisión y seguimiento de mejora',
            'Estadísticas de reservas',
            'Reporte de uso por carreras y usuarios', 'Listado de solicitudes de reserva',
            'Equipamiento institucional', 'Lector de equipos'])
        por_nombre = {modelo['name']: modelo['admin_url'] for modelo in area['models']}
        self.assertEqual(por_nombre['Reportes de Centros I+D'], reverse('reportes_centros_id'))
        self.assertEqual(por_nombre['Remisión y seguimiento de mejora'], reverse('admin:documentos_informemejora_changelist'))
        self.assertEqual(por_nombre['Estadísticas de reservas'], reverse('admin:reservas-estadisticas'))
        menu = area['menu_reportes']
        self.assertEqual([seccion['codigo'] for seccion in menu['secciones']], ['unidades', 'centros_id'])
        unidades, centros = menu['secciones']
        principal = unidades['principal']
        self.assertEqual(principal['name'], 'Cumplimiento del expediente por unidad')
        self.assertEqual(principal['admin_url'], reverse('admin:reportes-cumplimiento-expediente'))
        self.assertTrue(principal['es_evaluacion'])
        self.assertEqual(centros['principal']['admin_url'], reverse('reportes_centros_id'))
        self.assertEqual(centros['categorias'], [])
        self.assertEqual([grupo['codigo'] for grupo in unidades['categorias'][:3]],
                         ['evaluacion', 'compras_equipos', 'actividad'])
        accesos = [seccion['principal'] for seccion in menu['secciones'] if seccion['principal']]
        accesos += [modelo for seccion in menu['secciones'] for categoria in seccion['categorias']
                    for subcategoria in categoria['subcategorias'] for modelo in subcategoria['models']]
        self.assertCountEqual([modelo['object_name'] for modelo in accesos],
                              [modelo['object_name'] for modelo in area['models']])
        self.assertEqual(len({modelo['object_name'] for modelo in accesos}), len(accesos))
        self.client.force_login(self.superusuario)
        for tarjeta in area['models']:
            with self.subTest(reporte=tarjeta['name']):
                if tarjeta['name'] == 'Reportes de Centros I+D':
                    # Este contrato comprueba la entrada y su renderizado. El
                    # cálculo científico usa la base separada `centros`, que
                    # tiene su propia integración y no pertenece a este caso.
                    reporte_cientifico = dict(title='Reportes de Centros I+D', scope='Centros autorizados',
                        categories=[], filters={}, center_options=[], metrics=[], notes=[], macro=True,
                        sections=[dict(titulo='Centros', headers=['Centro'], rows=[])],
                        pagination=dict(previous=None, next=None, number=1, num_pages=1, count=0))
                    with patch('apps.centros_id.informes.construir_reporte_centros',
                               return_value=reporte_cientifico) as construir:
                        respuesta = self.client.get(tarjeta['admin_url'])
                    construir.assert_called_once()
                    self.assertTemplateUsed(respuesta, 'centros_id/informes.html')
                else:
                    respuesta = self.client.get(tarjeta['admin_url'])
                self.assertEqual(respuesta.status_code, 200)
                if tarjeta['name'] == 'Cumplimiento del expediente por unidad':
                    self.assertContains(respuesta, '<h1>Cumplimiento del expediente por unidad</h1>', html=True)

    @patch('apps.centros_id.informes.puede_reportar_centros', return_value=False)
    def test_sin_permiso_de_lectura_el_reporte_no_aparece(self, _sin_asignacion_cientifica):
        from django.contrib.auth.models import Permission

        # La pertenencia a centros científicos se comprueba en su base
        # separada; aquí se aísla ese dominio para probar los permisos de
        # documentos y reservas, y que el menú no los amplíe.
        personal = get_user_model().objects.create_user('lector.reportes', is_staff=True)
        self.assertIsNone(self.area(personal))
        personal.user_permissions.add(Permission.objects.get(codename='view_reserva',
                                                             content_type__app_label='reservas'))
        personal = get_user_model().objects.get(pk=personal.pk)
        area = self.area(personal)
        self.assertEqual([m['name'] for m in area['models']], [
            'Estadísticas de reservas', 'Reporte de uso por carreras y usuarios',
            'Listado de solicitudes de reserva'])
        secciones = area['menu_reportes']['secciones']
        self.assertEqual([seccion['codigo'] for seccion in secciones], ['unidades'])
        self.assertIsNone(secciones[0]['principal'])
        self.assertEqual([grupo['codigo'] for grupo in secciones[0]['categorias']], ['actividad'])
        visibles = [modelo for categoria in secciones[0]['categorias']
            for subcategoria in categoria['subcategorias'] for modelo in subcategoria['models']]
        self.assertEqual([modelo['name'] for modelo in visibles], [modelo['name'] for modelo in area['models']])

    def test_las_tarjetas_de_reportes_muestran_su_descripcion_propia(self):
        self.client.force_login(self.superusuario)
        from django.urls import reverse

        indice = self.client.get(reverse('admin:index'))
        self.assertContains(indice, 'Reportes e indicadores')
        self.assertContains(indice, 'Compara las reservas por estado, unidad y fecha para conocer su demanda.')
