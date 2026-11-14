"""Un centro experimental es una finca que produce y experimenta: su ficha tiene su propio mapa de seis pestañas y su
trabajo se organiza en ejes productivos, cada uno con su página como el área de un laboratorio. Se cargan con su
contenido documentado (cifras con fuente, fotos con crédito, videos verificados) sin pisar lo que el centro edita,
y cada eje lleva su gestión productiva: ciclos con meta y registros del día."""
from datetime import date
from decimal import Decimal
from io import StringIO
from tempfile import TemporaryDirectory

from django.contrib import admin
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.core.management import call_command
from django.test import RequestFactory, TestCase, override_settings
from django.urls import reverse

from apps.centros_experimentales.operacion.presentation.centro_experimental import ROLES
from apps.centros_experimentales.operacion.presentation.centro_simuladores import simuladores_de
from apps.gestion_unidades.presentation.portadas import EXPLICACIONES_CENTRO, portadas_de
from apps.plantas_piloto.operacion.presentation.secciones_plantas import MAPA_CENTRO, mapa_de
from apps.centros_experimentales.operacion.management.centros.contenidos import AT, EJES, SF, VIDEOS
from apps.reservas.models.reservas import CatalogoActividadReserva
from apps.centros_experimentales.operacion.models.centros import CicloProductivo, EjeProductivo, RegistroProduccion
from apps.gestion_unidades.models.operaciones import ConfiguracionOperativaUnidad
from apps.formacion.models.cursos import Curso
from apps.gestion_unidades.models.espacios import EspacioReservable
from apps.directorio_unidades.models.relaciones import RelacionUnidad
from apps.reservas.models.seguridad import RequisitoAcceso
from apps.directorio_unidades.models.core import Unidad
from apps.recursos.models.recursos import DEFAULT_MODULES_BY_DEPENDENCIA


def unidad(slug, dependencia, nombre):
    return Unidad.objects.create(nombre=nombre, slug=slug, dependencia=dependencia, descripcion='Unidad de prueba.',
                                 fecha_inicio=date(2026, 1, 1))


class MapaDelCentroTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.centro = unidad(SF, 'centro_experimental', 'Centro Experimental San Francisco')

    def test_el_mapa_sigue_las_seis_pestanas_del_centro(self):
        self.assertIs(mapa_de(self.centro), MAPA_CENTRO)
        self.assertEqual(list(MAPA_CENTRO.pestanas),
                         [clave for clave, *_ in DEFAULT_MODULES_BY_DEPENDENCIA['centro_experimental']])
        self.assertEqual(MAPA_CENTRO.modulo_reservas, 'visitas-servicios')
        self.assertEqual([MAPA_CENTRO.numero(clave) for clave in ('funcionamiento', 'ejes', 'destino', 'areas_equipos',
                                                                   'temas_investigacion', 'como_reservar', 'reservar',
                                                                   'visitas')],
                         ['1.4', '2.1', '3.4', '4.1', '5.1', '6.1', '6.2', '6.6'])
        # Lo que un centro no tiene no aparece en su mapa.
        self.assertEqual((MAPA_CENTRO.numero('haccp'), MAPA_CENTRO.numero('indicadores')), ('', ''))

    def test_las_pestanas_explican_lo_suyo_y_no_lo_del_observatorio(self):
        portadas = {p['clave']: p for p in portadas_de(self.centro, self.centro.modulos_contenido.all())}
        self.assertEqual(portadas['areas-productivas']['entrada'], EXPLICACIONES_CENTRO['areas-productivas']['entrada'])
        self.assertNotIn('encuestas', portadas['investigacion-vinculacion']['entrada'])

    def test_un_eje_solo_es_de_un_centro_experimental(self):
        laboratorio = unidad('laboratorio-ejes', 'laboratorios', 'Laboratorio de prueba')
        with self.assertRaises(ValidationError):
            EjeProductivo(unidad=laboratorio, codigo='leche', titulo='Leche', resumen='.', que_produce='.').full_clean()


class CargaDeEjesTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.sf = unidad(SF, 'centro_experimental', 'Centro Experimental San Francisco')
        cls.lactea = EspacioReservable.objects.create(unidad=cls.sf, codigo='CESF-LACTEA', nombre='Producción láctea')
        cls.parcelas = EspacioReservable.objects.create(unidad=cls.sf, codigo='CESF-PARCELAS', nombre='Parcelas')

    def setUp(self):
        media = TemporaryDirectory(ignore_cleanup_errors=True)
        self.addCleanup(media.cleanup)
        self.enterContext(override_settings(MEDIA_ROOT=media.name))

    def cargar(self, *opciones):
        salida = StringIO()
        call_command('cargar_ejes_centros', *opciones, stdout=salida)
        return salida.getvalue()

    def test_carga_los_ejes_con_sus_areas_fotos_y_videos_y_omite_el_centro_que_falta(self):
        salida = self.cargar()
        self.assertIn(f'{AT}: no existe todavía', salida)
        self.assertEqual(self.sf.ejes_productivos.count(), len(EJES[SF]))
        leche = self.sf.ejes_productivos.get(codigo='leche')
        self.assertEqual(list(leche.espacios.all()), [self.lactea])
        self.assertEqual(len(leche.lista_videos), len(VIDEOS[(SF, 'leche')].splitlines()))
        self.assertTrue(leche.imagenes.exists())
        self.assertTrue(all(imagen.credito for imagen in leche.imagenes.all()))
        self.assertEqual(leche.destinos[0][0], 'Planta piloto de lácteos')

    def test_cargar_de_nuevo_no_duplica_ni_pisa_lo_editado(self):
        self.cargar('--sin-fotos')
        EjeProductivo.objects.filter(unidad=self.sf, codigo='leche').update(resumen='Resumen del centro')
        self.assertIn('al día', self.cargar('--sin-fotos'))
        self.assertEqual(self.sf.ejes_productivos.get(codigo='leche').resumen, 'Resumen del centro')
        self.cargar('--sin-fotos', '--reescribir')
        self.assertNotEqual(self.sf.ejes_productivos.get(codigo='leche').resumen, 'Resumen del centro')
        self.assertEqual(self.sf.ejes_productivos.count(), len(EJES[SF]))


class FichaDelCentroTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.sf = unidad(SF, 'centro_experimental', 'Centro Experimental San Francisco')
        cls.lacteos = unidad('planta-piloto-lacteos-ejes', 'plantas_piloto', 'Planta Piloto de Lácteos')
        RelacionUnidad.objects.create(origen=cls.sf, tipo='abastece', destino=cls.lacteos,
                                      que_fluye='Leche cruda del hato del centro')
        call_command('cargar_ejes_centros', '--sin-fotos', stdout=StringIO())
        cls.admin = get_user_model().objects.create_superuser('centro.admin', 'c@example.org', 'clave')

    def ruta(self, nombre, *args):
        return reverse(nombre, args=[SF, *args])

    def test_la_ficha_ofrece_las_secciones_del_centro_numeradas(self):
        ficha = self.client.get(self.sf.get_absolute_url())
        self.assertEqual(ficha.status_code, 200)
        for texto in ('Áreas y sistemas productivos', 'Cómo funciona el centro', self.ruta('ejes_centro'),
                      self.ruta('eje_centro', 'leche'), self.ruta('destino_centro'), self.ruta('calendario_centro')):
            with self.subTest(texto=texto):
                self.assertContains(ficha, texto)

    def test_cada_seccion_responde_con_su_contenido(self):
        for nombre, args, texto in (
                ('funcionamiento_centro', (), 'Familias cuidadoras'),
                ('ejes_centro', (), 'Ganadería de leche'),
                ('calendario_centro', (), 'Época lluviosa'),
                ('destino_centro', (), 'Leche cruda del hato del centro'),
                ('temas_centro', (), 'Mezclas forrajeras para clima frío'),
                ('eje_centro', ('leche',), 'Cómo trabaja el eje')):
            with self.subTest(seccion=nombre):
                self.assertContains(self.client.get(self.ruta(nombre, *args)), texto)

    def test_la_ficha_nombra_roles_y_no_personas(self):
        pagina = self.client.get(self.ruta('funcionamiento_centro'))
        for _icono, rol, _que in ROLES:
            self.assertContains(pagina, rol)

    def test_un_eje_retirado_no_se_publica(self):
        EjeProductivo.objects.filter(unidad=self.sf, codigo='cuyes').update(publicado=False)
        self.assertEqual(self.client.get(self.ruta('eje_centro', 'cuyes')).status_code, 404)
        self.assertNotContains(self.client.get(self.ruta('ejes_centro')), 'Galpón para 500 cuyes')
        self.assertEqual(self.client.get(reverse('ejes_centro', args=[self.lacteos.slug])).status_code, 404)

    def test_quien_gestiona_edita_el_eje_desde_su_pagina(self):
        self.assertNotContains(self.client.get(self.ruta('eje_centro', 'leche')), 'Editar el eje')
        self.client.force_login(self.admin)
        self.assertContains(self.client.get(self.ruta('eje_centro', 'leche')), 'Editar el eje')

    def test_el_administrador_del_centro_tiene_su_produccion_agropecuaria(self):
        peticion = RequestFactory().get('/admin/')
        peticion.user = self.admin
        areas = {area['name']: area for area in admin.site.get_app_list(peticion)}
        modelos = {m['object_name'] for m in areas['Centros experimentales']['models']}
        self.assertIn('EjeProductivo', modelos)
        for otro in ('Laboratorios', 'Plantas piloto', 'Observatorios'):
            self.assertNotIn('EjeProductivo', {m['object_name'] for m in areas[otro]['models']})


class GestionProductivaTests(TestCase):
    """Cada eje planifica ciclos con su meta y registra el mismo día lo que produce: el centro compara lo real con lo
    planificado. El público ve los totales; los registros uno a uno, quien gestiona la producción."""

    @classmethod
    def setUpTestData(cls):
        cls.sf = unidad(SF, 'centro_experimental', 'Centro Experimental San Francisco')
        cls.lote = EspacioReservable.objects.create(unidad=cls.sf, codigo='CESF-PARCELAS', nombre='Parcelas')
        call_command('cargar_ejes_centros', '--sin-fotos', stdout=StringIO())
        cls.eje = cls.sf.ejes_productivos.get(codigo='cultivos-andinos')
        cls.ciclo = CicloProductivo.objects.create(
            eje=cls.eje, nombre='Papa Superchola 2026-B', rubro='Papa', lugar=cls.lote, inicio=date(2026, 3, 1),
            fin_previsto=date(2026, 9, 1), superficie_ha=Decimal('0.5'), meta=Decimal('10000'), unidad_medida='kg',
            estado='en_curso')
        cls.admin = get_user_model().objects.create_superuser('produccion.admin', 'p@example.org', 'clave')

    def registro(self, **campos):
        datos = {'ciclo': self.ciclo, 'fecha': date(2026, 8, 20), 'tipo': 'cosecha', 'cantidad': Decimal('4000'),
                 'unidad_medida': 'kg'}
        datos.update(campos)
        return RegistroProduccion(**datos)

    def test_lo_producido_suma_cosechas_de_la_misma_unidad_frente_a_la_meta(self):
        self.registro().save()
        self.registro(cantidad=Decimal('1000')).save()
        self.registro(tipo='labor', cantidad=None, unidad_medida='', detalle='Aporque').save()
        self.registro(tipo='entrega', destino='planta', cantidad=Decimal('3000')).save()
        self.assertEqual(self.ciclo.producido, Decimal('5000'))
        self.assertEqual(self.ciclo.cumplimiento, 50)

    def test_las_reglas_del_ciclo_y_del_registro(self):
        otro = unidad('centro-experimental-otro', 'centro_experimental', 'Otro centro')
        ajeno = EspacioReservable.objects.create(unidad=otro, codigo='OTRO-LOTE', nombre='Lote ajeno')
        for cambios in ({'fin_previsto': date(2026, 1, 1)}, {'lugar': ajeno}, {'estado': 'cerrado'}):
            with self.subTest(cambios=cambios), self.assertRaises(ValidationError):
                CicloProductivo(**{**{f.name: getattr(self.ciclo, f.name) for f in CicloProductivo._meta.fields
                                      if f.name != 'id'}, **cambios}).full_clean()
        for cambios in ({'cantidad': None}, {'tipo': 'entrega', 'destino': ''}, {'fecha': date(2026, 1, 1)},
                        {'unidad_medida': ''}):
            with self.subTest(cambios=cambios), self.assertRaises(ValidationError):
                self.registro(**cambios).full_clean()

    def test_el_publico_ve_los_totales_y_no_los_registros_ni_quien_los_anoto(self):
        self.registro(detalle='Bloque 7, surco norte', registrado_por=self.admin).save()
        pagina = self.client.get(reverse('produccion_centro', args=[SF]))
        self.assertContains(pagina, 'Papa Superchola 2026-B')
        self.assertContains(pagina, '40 %')
        self.assertContains(pagina, 'ESPAC 2024')
        self.assertNotContains(pagina, 'Bloque 7, surco norte')
        self.assertNotContains(pagina, 'produccion.admin')
        self.assertEqual(self.client.post(reverse('produccion_centro', args=[SF]), {}).status_code, 403)
        self.assertEqual(self.client.get(reverse('produccion_csv_centro', args=[SF])).status_code, 403)

    def test_quien_gestiona_registra_desde_la_pagina_y_descarga_el_csv(self):
        self.client.force_login(self.admin)
        respuesta = self.client.post(reverse('produccion_centro', args=[SF]), {
            'ciclo': self.ciclo.pk, 'fecha': '2026-08-21', 'tipo': 'cosecha', 'cantidad': '1200', 'unidad_medida': 'kg',
            'destino': '', 'detalle': 'Primera cosecha'})
        self.assertRedirects(respuesta, reverse('produccion_centro', args=[SF]) + '#registrar',
                             fetch_redirect_response=False)
        registro = RegistroProduccion.objects.get(detalle='Primera cosecha')
        self.assertEqual(registro.registrado_por, self.admin)
        pagina = self.client.get(reverse('produccion_centro', args=[SF]))
        self.assertContains(pagina, 'Primera cosecha')
        self.assertContains(pagina, 'Planificar un ciclo')
        csv = self.client.get(reverse('produccion_csv_centro', args=[SF]))
        self.assertEqual(csv.status_code, 200)
        self.assertIn('Papa Superchola 2026-B', csv.content.decode('utf-8-sig'))

    def test_la_ficha_ofrece_la_seccion_con_las_referencias_aunque_no_haya_ciclos(self):
        CicloProductivo.objects.all().delete()
        ficha = self.client.get(self.sf.get_absolute_url())
        self.assertContains(ficha, reverse('produccion_centro', args=[SF]))
        self.assertContains(ficha, 'Referencias para planificar')


class SimuladoresYCursosTests(TestCase):
    """Los simuladores parten de rendimientos con fuente y cada centro ve los que aplican a sus ejes; cada centro tiene
    al menos un curso armado en el aula y la lista de los que debería dictar."""

    @classmethod
    def setUpTestData(cls):
        cls.sf = unidad(SF, 'centro_experimental', 'Centro Experimental San Francisco')
        cls.at = unidad(AT, 'centro_experimental', 'Centro Experimental Alonso Tadeo')
        call_command('cargar_ejes_centros', '--sin-fotos', stdout=StringIO())

    def resultado(self, slug, clave, **parametros):
        pagina = self.client.get(reverse('simuladores_centro', args=[slug]), parametros)
        simulador = next(s for s in pagina.context['simuladores'] if s['clave'] == clave)
        return {nombre: valor for nombre, valor, _unidad in simulador['resultado']}

    def test_cada_centro_ve_los_simuladores_de_sus_ejes(self):
        claves = lambda slug: [s['clave'] for s in simuladores_de(Unidad.objects.get(slug=slug))]  # noqa: E731
        self.assertEqual(claves(SF), ['leche', 'cosecha'])
        self.assertEqual(claves(AT), ['cosecha', 'postura', 'cafe'])

    def test_los_calculos_parten_de_las_referencias_y_se_pueden_cambiar(self):
        self.assertEqual(self.resultado(SF, 'leche')['Leche al día'], Decimal('20') * Decimal('7.9'))
        cafe = self.resultado(AT, 'cafe', **{'cafe-cereza': '350'})
        self.assertEqual((cafe['Café pergamino seco'], cafe['Café verde (almendra)']), (Decimal('70.00'), Decimal('56.0000')))
        self.assertEqual(round(cafe['Café tostado'], 2), Decimal('47.32'))
        cosecha = self.resultado(SF, 'cosecha', **{'cosecha-cultivo': 'tomate-arbol', 'cosecha-superficie': '1',
                                                   'cosecha-perdida': '0'})
        self.assertEqual(cosecha['Cosecha esperada'], Decimal('15200'))
        # Lo que no es un número o se sale de sus límites vuelve al valor de partida.
        self.assertEqual(self.resultado(AT, 'postura', **{'postura-postura': '180', 'postura-gallinas': 'muchas'})
                         ['Huevos al día'], Decimal('80'))

    def test_cada_centro_tiene_su_curso_armado_y_los_recomendados(self):
        for curso, slug in (('ordeno-calidad-leche', SF), ('cafe-cereza-taza', AT)):
            call_command('cargar_curso_precargado', curso, stdout=StringIO())
            armado = Curso.objects.get(unidad__slug=slug)
            self.assertFalse(armado.publicado)
            self.assertTrue(armado.modulos.exists())
            pagina = self.client.get(reverse('cursos_centro', args=[slug]))
            self.assertContains(pagina, armado.nombre)
            self.assertNotContains(pagina, 'se publica cuando el centro lo revise')
            self.assertNotContains(pagina, reverse('curso_unidad', args=[slug, armado.codigo]))
            self.assertContains(pagina, 'Pedirlo al centro')
        self.assertContains(self.client.get(self.sf.get_absolute_url()), reverse('cursos_centro', args=[SF]))
        self.assertContains(self.client.get(self.at.get_absolute_url()), reverse('simuladores_centro', args=[AT]))


class ReservasDelCentroTests(TestCase):
    """Cada centro dice qué se reserva en cada eje y cómo; el comando abre los recorridos por las áreas visitables y
    registra una práctica y un ensayo por eje en el catálogo, sin imponer requisitos obligatorios."""

    @classmethod
    def setUpTestData(cls):
        cls.sf = unidad(SF, 'centro_experimental', 'Centro Experimental San Francisco')
        for codigo, nombre, capacidad in (('CESF-LACTEA', 'Producción láctea', 10), ('CESF-CUYES', 'Galpón de cuyes', 6),
                                          ('CESF-AGROECOLOGIA', 'Agroecología', 10)):
            EspacioReservable.objects.create(unidad=cls.sf, codigo=codigo, nombre=nombre, capacidad=capacidad)
        call_command('cargar_ejes_centros', '--sin-fotos', stdout=StringIO())

    def configurar(self):
        salida = StringIO()
        call_command('configurar_reservas_centros', stdout=salida)
        return salida.getvalue()

    def test_abre_recorridos_y_registra_las_actividades_sin_requisitos_obligatorios(self):
        salida = self.configurar()
        self.assertIn(f'{AT}: no existe todavía', salida)
        configuracion = ConfiguracionOperativaUnidad.objects.get(unidad=self.sf)
        self.assertTrue(configuracion.acepta_visitas)
        self.assertIn('herbario', configuracion.visitas_texto)
        self.assertEqual(set(self.sf.espacios_reservables.filter(visitable=True).values_list('codigo', flat=True)),
                         {'CESF-LACTEA', 'CESF-CUYES'})
        actividades = CatalogoActividadReserva.objects.filter(unidad=self.sf)
        self.assertEqual(actividades.count(), 2 * len(EJES[SF]) + 1)
        self.assertTrue(actividades.filter(codigo='CESF-PRAC-LECHE', proposito_codigo='docencia_practica').exists())
        self.assertFalse(RequisitoAcceso.objects.filter(unidad=self.sf).exists())
        self.assertIn('al día', self.configurar())

    def test_la_pagina_explica_que_se_reserva_en_cada_eje_y_los_recorridos(self):
        self.configurar()
        pagina = self.client.get(reverse('como_reservar_centro', args=[SF]))
        for texto in ('Práctica de campo', 'Ensayo de investigación o tesis', 'Recorrido o visita técnica',
                      'Ganadería de leche', 'Se visita', 'Recorridos guiados', 'pediluvio'):
            with self.subTest(texto=texto):
                self.assertContains(pagina, texto)
        self.assertContains(self.client.get(self.sf.get_absolute_url()), reverse('como_reservar_centro', args=[SF]))


class RecomendacionesPublicasFormacionTests(TestCase):
    def test_recomendaciones_solo_enlazan_cursos_publicados_y_activos(self):
        from unittest.mock import patch

        from apps.centros_experimentales.operacion.presentation.centro_experimental import cursos_recomendados

        centro = unidad('centro-recomendacion-publica', 'centro_experimental', 'Centro de prueba')
        visible = Curso.objects.create(unidad=centro, codigo='REC-VISIBLE', nombre='Curso visible', publicado=True)
        borrador = Curso.objects.create(unidad=centro, codigo='REC-BORRADOR', nombre='Curso en revisión')
        inactivo = Curso.objects.create(
            unidad=centro, codigo='REC-INACTIVO', nombre='Curso desactivado', publicado=True, activo=False,
        )
        propuestas = {centro.slug: [
            (curso.nombre, 'eje', 20, 'Estudiantes', 'Aplicación práctica')
            for curso in (visible, borrador, inactivo)
        ]}
        with patch('apps.centros_experimentales.operacion.management.centros.contenidos.CURSOS_RECOMENDADOS', propuestas):
            filas = cursos_recomendados(centro)
        self.assertEqual([fila['curso'] for fila in filas], [visible, None, None])
