"""Cada equipo se identifica con el código oficial de bodega y se le sigue la pista a todo lo que le pasa.

El código del bien es único y se lee con o sin prefijo institucional; el QR lleva a la ficha vigente
aunque el equipo cambie de unidad; el lector registra lo nuevo sin duplicar, y la historia guarda
transferencias, áreas, custodios y códigos.
"""
from datetime import date
from io import StringIO
from pathlib import Path
from tempfile import TemporaryDirectory

from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.core.management import CommandError, call_command
from django.test import TestCase
from django.urls import reverse

from apps.recursos.presentation.codigos_equipo import buscar_equipo, codigo_leido, limpiar_codigo_bien
from apps.recursos.management.commands.importar_reporte_bienes import leer as leer_reporte
from apps.gestion_unidades.management.fichas_area.fablab import FICHAS as FICHAS_FABLAB
from apps.recursos.models.unidades import AliasCodigoUnidadEquipo, UnidadEquipo
from apps.recursos.models.equipos import EquiposServicios
from apps.gestion_unidades.models.espacios import EspacioReservable
from apps.recursos.models.mantenimiento import EventoCicloVidaEquipo
from apps.directorio_unidades.models.core import Unidad
from tests.integration.utiles import identificar


class CodigosDeEquipoTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.gestor = get_user_model().objects.create_user('gestor-codigos', password='clave-segura')
        identificar(cls.gestor, tipo_usuario='administrativo', carrera='')
        cls.unidad = Unidad.objects.create(nombre='Laboratorio de códigos', slug='laboratorio-codigos',
                                           dependencia='laboratorios', descripcion='.', fecha_inicio=date(2020, 1, 1),
                                           administrador=cls.gestor)
        cls.otra = Unidad.objects.create(nombre='Otra unidad', slug='otra-unidad', dependencia='laboratorios',
                                         descripcion='.', fecha_inicio=date(2020, 1, 1))
        cls.area = EspacioReservable.objects.create(unidad=cls.unidad, codigo='COD-AREA', nombre='Área de códigos', capacidad=4)
        cls.tipo = EquiposServicios.objects.create(codigo='COD-GAFAS', nombre='Visor de realidad virtual autónomo')
        cls.equipo = UnidadEquipo.objects.create(codigo_unidad='COD-VR-01', equipo=cls.tipo, laboratorio=cls.unidad,
                                                 numero_serie='SN-VR-01')
        cls.sin_codigo = UnidadEquipo.objects.create(codigo_unidad='COD-VR-02', equipo=cls.tipo, laboratorio=cls.unidad)

    def test_el_codigo_del_bien_se_guarda_sin_prefijo_y_no_se_repite(self):
        self.assertEqual(limpiar_codigo_bien('23300000000-37881242'), '37881242')
        self.assertEqual(codigo_leido('https://citt.upec.edu.ec/equipos/codigo/COD-VR-01/'), 'COD-VR-01')
        self.equipo.codigo_bien = '23300000000-39830957'
        self.equipo.save()
        self.equipo.refresh_from_db()
        self.assertEqual(self.equipo.codigo_bien, '39830957')
        self.assertEqual(self.equipo.codigo_etiqueta, '23300000000-39830957')
        self.sin_codigo.codigo_bien = '39830957'
        with self.assertRaises(ValidationError):
            self.sin_codigo.save()
        # Sin código no ocupa el lugar único: varios equipos pueden estar pendientes a la vez.
        self.sin_codigo.codigo_bien = ''
        self.sin_codigo.save()
        self.assertIsNone(UnidadEquipo.objects.get(pk=self.sin_codigo.pk).codigo_bien)

    def test_se_encuentra_con_cualquier_codigo_y_la_direccion_universal_sigue_al_equipo(self):
        UnidadEquipo.objects.filter(pk=self.equipo.pk).update(codigo_bien='40530521')
        AliasCodigoUnidadEquipo.objects.create(codigo='VIEJO-01', unidad_equipo=self.equipo)
        for lectura in ('23300000000-40530521', '40530521', 'cod-vr-01', 'VIEJO-01', 'SN-VR-01',
                        'http://x/equipos/codigo/COD-VR-01/'):
            with self.subTest(lectura=lectura):
                self.assertEqual(buscar_equipo(lectura), self.equipo)
        self.assertIsNone(buscar_equipo('99999999'))
        self.equipo.refresh_from_db()
        self.equipo.laboratorio = self.otra
        self.equipo.save()
        destino = self.client.get(reverse('equipo_por_codigo', args=['40530521']))
        self.assertRedirects(destino, reverse('ficha_equipo_publica', args=[self.otra.slug, 'COD-VR-01']),
                             fetch_redirect_response=False)

    def test_codigo_de_barras_qr_y_hoja_de_etiquetas(self):
        url = reverse('identificador_equipo', args=[self.unidad.slug, 'COD-VR-01'])
        ficha_url = reverse('ficha_equipo_publica', args=[self.unidad.slug, 'COD-VR-01'])
        # El público ve los códigos como texto; las etiquetas para imprimir son de quien gestiona.
        self.assertEqual(self.client.get(url).status_code, 404)
        publica = self.client.get(ficha_url)
        self.assertContains(publica, 'COD-VR-01')
        self.assertNotContains(publica, url)
        self.assertNotContains(publica, 'Código de barras y QR')
        hoja = reverse('etiquetas_equipos', args=[self.unidad.slug])
        self.assertEqual(self.client.get(hoja).status_code, 404)
        self.client.force_login(self.gestor)
        self.assertEqual(self.client.get(url)['Content-Type'], 'image/svg+xml')
        descarga = self.client.get(url, {'tipo': 'barra', 'descargar': '1'})
        self.assertIn('attachment', descarga['Content-Disposition'])
        respuesta = self.client.get(hoja, {'area': ''})
        self.assertEqual(respuesta['Content-Type'], 'application/pdf')
        ficha = self.client.get(reverse('ficha_equipo_publica', args=[self.unidad.slug, 'COD-VR-01']))
        self.assertContains(ficha, url)
        self.assertContains(ficha, 'Historia del equipo')

    def test_la_historia_guarda_transferencias_areas_custodios_y_codigos(self):
        self.area.equipos_asociados.add(self.equipo)
        self.equipo.custodio = 'Responsable A'
        self.equipo.codigo_unidad = 'COD-VR-01B'
        self.equipo.laboratorio = self.otra
        self.equipo.save()
        eventos = {evento.tipo: evento.descripcion for evento in EventoCicloVidaEquipo.objects.filter(equipo=self.equipo)}
        self.assertIn('Área de códigos', eventos['cambio_area'])
        self.assertIn('Responsable A', eventos['cambio_custodio'])
        self.assertIn('COD-VR-01B', eventos['cambio_codigo'])
        self.assertIn(f'de {self.unidad.nombre} a {self.otra.nombre}', eventos['transferencia'])
        # El código anterior sigue llevando al equipo: las etiquetas impresas no se rompen.
        self.assertEqual(buscar_equipo('COD-VR-01'), self.equipo)

    def test_el_lector_busca_asigna_y_registra_sin_duplicar(self):
        buscar = reverse('lector_buscar_equipo')
        registrar = reverse('lector_registrar_equipo')
        self.assertEqual(self.client.get(buscar, {'codigo': 'COD-VR-01'}).status_code, 302)
        self.client.force_login(self.gestor)
        self.assertEqual(self.client.get(reverse('lector_equipos')).status_code, 200)
        self.assertTrue(self.client.get(buscar, {'codigo': 'COD-VR-01'}).json()['encontrado'])
        self.assertFalse(self.client.get(buscar, {'codigo': '23300000000-111'}).json()['encontrado'])
        candidatos = self.client.get(reverse('lector_sugerencias'), {'unidad': self.unidad.slug, 'nombre': 'gafas de realidad virtual'}).json()
        self.assertIn(self.sin_codigo.pk, [equipo['id'] for equipo in candidatos['equipos']])
        enlazado = self.client.post(registrar, {'modo': 'enlazar', 'codigo': '23300000000-111', 'equipo_id': self.sin_codigo.pk,
                                                'custodio': 'Custodia B'}, content_type='application/json')
        self.assertEqual(enlazado.status_code, 200)
        self.sin_codigo.refresh_from_db()
        self.assertEqual((self.sin_codigo.codigo_bien, self.sin_codigo.custodio), ('111', 'Custodia B'))
        repetido = self.client.post(registrar, {'codigo': '111', 'equipo_id': self.equipo.pk}, content_type='application/json')
        self.assertEqual(repetido.status_code, 409)
        libre = self.client.get(buscar, {'codigo': '23300000000-222'}).json()
        self.assertEqual((libre['encontrado'], libre['valido']), (False, True))
        sin_equipo = self.client.post(registrar, {'codigo': '222', 'modo': 'nuevo'}, content_type='application/json')
        self.assertEqual(sin_equipo.status_code, 400)
        alta = self.client.post(reverse('gestion_operacion_accion', args=[self.unidad.slug]), {
            'modulo': 'recursos', 'entidad': 'equipo', 'codigo_catalogo': 'COD-MIC', 'nombre_catalogo': 'Microscopio digital con pantalla',
            'marca': 'Andonstar', 'codigo_unidad': '', 'codigo_bien': '222', 'tipo_bien': 'BLD',
            'estado_unidad': 'disponible', 'espacios_asociados': [self.area.pk], 'activa': 'on'})
        self.assertEqual(alta.status_code, 200, alta.content)
        creado = UnidadEquipo.objects.get(codigo_bien='222')
        # Sin código del sistema, el estándar UNIDAD-ÁREA-MODELO-N.º según el área elegida.
        self.assertEqual(creado.codigo_unidad, 'COD-AREA-01-01')
        self.assertTrue(creado.espacios_asociados.filter(pk=self.area.pk).exists())
        self.assertIsNotNone(creado.equipo.familia, 'La familia se deduce del nombre del modelo nuevo.')
        ajeno = UnidadEquipo.objects.create(codigo_unidad='COD-AJENO', equipo=self.tipo, laboratorio=self.otra)
        ajena = self.client.post(registrar, {'codigo': '333', 'equipo_id': ajeno.pk}, content_type='application/json')
        self.assertEqual(ajena.status_code, 403)
        pagina = self.client.get(reverse('lector_equipos'), {'unidad': self.unidad.slug})
        self.assertEqual(pagina.context['unidad_actual'], self.unidad)
        self.assertIn('view=recursos', pagina.context['volver_url'])

    def test_el_importador_propone_y_solo_enlaza_con_confirmacion(self):
        with TemporaryDirectory() as carpeta:
            archivo = Path(carpeta) / 'bienes.csv'
            archivo.write_text(
                'Código del Bien;(BLD) o (BCA);Serie/ Identificación;Modelo/ Características;Marca/ Otros;Color;Material;'
                'Dimensiones;Ubicación de Bodega;Custodio Actual;Fecha de Ingreso;Valor Contable\n'
                '39830957;BLD;GAFAS DE REALIDAD VIRTUAL;;META;BLANCO;METALICO;;PROYECTOS;CUSTODIA C;28/4/2025;1500\n'
                '40530524;BLD;HORNO DE SOLDADURA;T-962;PUHUI;GRIS;MIXTO;SN:T-962-FW-OX541;PROYECTOS;CUSTODIA C;27/10/2025;1850\n',
                encoding='utf-8')
            salida = StringIO()
            call_command('importar_reporte_bienes', str(archivo), '--unidad', self.unidad.slug, stdout=salida)
            self.assertIn('propuesto, sin enlazar', salida.getvalue())
            self.assertFalse(UnidadEquipo.objects.filter(codigo_bien='39830957').exists())
            horno = UnidadEquipo.objects.get(codigo_bien='40530524')
            self.assertEqual((horno.numero_serie, horno.custodio, horno.valor_contable), ('T-962-FW-OX541', 'CUSTODIA C', 1850))
            call_command('importar_reporte_bienes', str(archivo), '--unidad', self.unidad.slug, '--enlazar-por-nombre',
                         stdout=StringIO())
            gafas = UnidadEquipo.objects.get(codigo_bien='39830957')
            self.assertEqual(gafas.equipo, self.tipo)
            self.assertEqual(UnidadEquipo.objects.filter(codigo_bien='40530524').count(), 1)

    def test_el_importador_concilia_a_mano_y_confirma_lo_de_referencia(self):
        referencia = UnidadEquipo.objects.create(
            codigo_unidad='COD-VR-03', equipo=self.tipo, laboratorio=self.unidad, estado_unidad='no_disponible',
            observaciones='Registrado desde la ficha del área Área de códigos. Confirmar marca, modelo y número de serie.')
        self.area.equipos_asociados.add(referencia)
        with TemporaryDirectory() as carpeta:
            archivo = Path(carpeta) / 'bienes.csv'
            archivo.write_text(
                'Código del Bien;(BLD) o (BCA);Serie/ Identificación;Modelo/ Características;Marca/ Otros;Color;Material;'
                'Dimensiones;Ubicación de Bodega;Custodio Actual;Fecha de Ingreso;Valor Contable;codigo_sistema;nombre_equipo\n'
                '501;BLD;GAFAS DE REALIDAD VIRTUAL;;META;BLANCO;;;;;;;COD-VR-03;\n'
                '502;BLD;GAFAS DE REALIDAD VIRTUAL;;META;BLANCO;;;;;;;;\n'
                '503;BLD;MAQUINA LASER DE ESCRITORIO;FALCON 2 PRO;CREALITY;PLOMO;;;;;;;nuevo;Grabadora láser de diodo de escritorio\n',
                encoding='utf-8')
            call_command('importar_reporte_bienes', str(archivo), '--unidad', self.unidad.slug, '--area', 'COD-AREA',
                         '--enlazar-por-nombre', stdout=StringIO())
        referencia.refresh_from_db()
        self.assertEqual((referencia.codigo_bien, referencia.estado_unidad), ('501', 'disponible'))
        self.assertIn('Confirmado con el reporte de bienes', referencia.observaciones)
        # Sin pareja libre, el bien queda como otra unidad del mismo tipo, no como un tipo nuevo.
        self.assertEqual(UnidadEquipo.objects.get(codigo_bien='502').equipo, self.tipo)
        laser = UnidadEquipo.objects.get(codigo_bien='503')
        self.assertEqual(laser.equipo.nombre, 'Grabadora láser de diodo de escritorio')
        self.assertEqual(laser.equipo.familia.nombre, 'Grabadoras láser de diodo')
        self.assertTrue(laser.espacios_asociados.filter(pk=self.area.pk).exists())

    def test_el_lector_ubica_al_equipo_entre_sus_hermanos_y_su_familia(self):
        from apps.recursos.models.equipos import FamiliaEquipo

        visores = FamiliaEquipo.objects.create(nombre='Visores de prueba', slug='visores-de-prueba')
        EquiposServicios.objects.filter(pk=self.tipo.pk).update(familia=visores)
        otro_modelo = EquiposServicios.objects.create(codigo='COD-GAFAS-2', nombre='Gafas de realidad mixta', familia=visores)
        UnidadEquipo.objects.create(codigo_unidad='COD-OTRA-VR', equipo=self.tipo, laboratorio=self.otra)
        UnidadEquipo.objects.create(codigo_unidad='COD-OTRA-MX', equipo=otro_modelo, laboratorio=self.otra)
        UnidadEquipo.objects.create(codigo_unidad='COD-RET', equipo=self.tipo, laboratorio=self.unidad, activa=False)
        self.equipo.custodio = 'Funcionaria C'
        self.equipo.save()
        self.client.force_login(self.gestor)
        datos = self.client.get(reverse('lector_buscar_equipo'), {'codigo': 'COD-VR-01'}).json()
        parentela = datos['parentela']
        self.assertEqual([item['codigo'] for item in parentela['hermanos']], ['COD-VR-02'])
        self.assertEqual([item['codigo'] for item in parentela['mismo_modelo']], ['COD-OTRA-VR'])
        familia = parentela['familia']
        self.assertEqual(familia['total'], 4)
        self.assertEqual({fila['unidad']: fila['total'] for fila in familia['unidades']}, {self.unidad.nombre: 2, self.otra.nombre: 2})
        self.assertEqual([item['codigo'] for item in familia['parientes']], ['COD-OTRA-MX'])
        self.assertEqual(datos['recorrido'][0]['unidad'], self.unidad.nombre)
        self.assertIn('editar_equipo', datos['editar_url'])
        self.assertTrue(any('Funcionaria C' in hito['detalle'] for hito in datos['historia']))
        # El personal de otra unidad lo ubica, pero no ve custodios ni valores ni puede editarlo.
        personal = get_user_model().objects.create_user('personal-otra', password='clave', is_staff=True)
        self.client.force_login(personal)
        ajeno = self.client.get(reverse('lector_buscar_equipo'), {'codigo': 'COD-VR-01'}).json()
        self.assertEqual((ajeno['custodio'], ajeno['editar_url'], ajeno['ficha_interna_url']), ('', '', ''))
        self.assertFalse(any('Funcionaria C' in hito['detalle'] for hito in ajeno['historia']))
        self.assertEqual(ajeno['parentela']['familia']['total'], 4)

    def test_con_el_nombre_el_lector_sugiere_solo_lo_relacionado(self):
        resina = EquiposServicios.objects.create(codigo='COD-RESINA', nombre='Impresora 3D de resina')
        filamento = EquiposServicios.objects.create(codigo='COD-FDM', nombre='Impresora 3D FDM de filamento')
        sin_codigo_resina = UnidadEquipo.objects.create(codigo_unidad='COD-RES-01', equipo=resina, laboratorio=self.unidad)
        UnidadEquipo.objects.create(codigo_unidad='COD-FDM-01', equipo=filamento, laboratorio=self.unidad)
        UnidadEquipo.objects.create(codigo_unidad='COD-RES-OTRA', equipo=resina, laboratorio=self.otra)
        otra_area = EspacioReservable.objects.create(unidad=self.unidad, codigo='COD-AREA-3D', nombre='Impresión 3D', capacidad=4)
        otra_area.equipos_asociados.add(sin_codigo_resina)
        self.area.equipos_asociados.add(self.sin_codigo)
        UnidadEquipo.objects.filter(pk=self.equipo.pk).update(codigo_bien='880009')
        url = reverse('lector_sugerencias')
        self.client.force_login(self.gestor)

        visores = self.client.get(url, {'unidad': self.unidad.slug, 'nombre': 'gafas de realidad virtual', 'codigo': '444'}).json()
        self.assertEqual([equipo['id'] for equipo in visores['equipos']], [self.sin_codigo.pk])
        self.assertEqual([modelo['id'] for modelo in visores['modelos']], [self.tipo.pk])
        self.assertEqual([area['id'] for area in visores['areas'] if area['sugerida']], [self.area.pk])

        impresoras = self.client.get(url, {'unidad': self.unidad.slug, 'nombre': 'impresora 3d de resina'}).json()
        modelos = {modelo['id']: modelo for modelo in impresoras['modelos']}
        # Resina y filamento son tecnologías distintas: la de filamento no se sugiere.
        self.assertIn(resina.pk, modelos)
        self.assertNotIn(filamento.pk, modelos)
        self.assertNotIn(self.tipo.pk, modelos)
        self.assertEqual({lugar['unidad'] for lugar in modelos[resina.pk]['presencia']}, {self.unidad.nombre, self.otra.nombre})
        self.assertEqual([equipo['id'] for equipo in impresoras['equipos']], [sin_codigo_resina.pk])
        self.assertEqual(impresoras['areas'][0]['id'], otra_area.pk)
        self.assertEqual(self.client.get(url, {'unidad': self.otra.slug, 'nombre': 'visor'}).status_code, 403)

    def test_un_codigo_nuevo_llega_con_lo_que_dice_el_reporte_de_bodega(self):
        from unittest import mock

        from apps.recursos.presentation import reportes_bodega

        with TemporaryDirectory() as carpeta:
            Path(carpeta, self.unidad.slug).mkdir()
            Path(carpeta, self.unidad.slug, 'COD-AREA.csv').write_text(
                'codigo_bien;tipo_bien;descripcion;modelo;marca;dimensiones;custodio;fecha_ingreso;valor_contable\n'
                '777001;BLD;GAFAS DE REALIDAD VIRTUAL;QUEST 3;META;SN:QX12345;Funcionaria D;27/10/2025;650,50\n',
                encoding='utf-8')
            with mock.patch.object(reportes_bodega, 'CARPETA', Path(carpeta)):
                self.client.force_login(self.gestor)
                datos = self.client.get(reverse('lector_buscar_equipo'), {'codigo': '23300000000-777001'}).json()
                personal = get_user_model().objects.create_user('personal-bodega', password='clave', is_staff=True)
                self.client.force_login(personal)
                ajeno = self.client.get(reverse('lector_buscar_equipo'), {'codigo': '777001'}).json()
        bodega = datos['bodega']
        self.assertFalse(datos['encontrado'])
        self.assertEqual((bodega['nombre'], bodega['marca'], bodega['modelo'], bodega['serie']),
                         ('Gafas de realidad virtual', 'Meta', 'QUEST 3', 'QX12345'))
        self.assertEqual((bodega['unidad'], bodega['area']), (self.unidad.slug, self.area.pk))
        self.assertEqual((bodega['custodio'], bodega['fecha_ingreso_bodega'], bodega['valor_contable']),
                         ('Funcionaria D', '2025-10-27', '650.50'))
        # El custodio y el valor solo van a quien gestiona la unidad del bien.
        self.assertEqual(ajeno['bodega']['nombre'], 'Gafas de realidad virtual')
        self.assertNotIn('custodio', ajeno['bodega'])
        self.assertNotIn('valor_contable', ajeno['bodega'])

    def test_el_escaner_de_la_unidad_lleva_al_equipo_o_dice_que_no_existe(self):
        UnidadEquipo.objects.filter(pk=self.equipo.pk).update(codigo_bien='880001', custodio='Funcionaria E')
        UnidadEquipo.objects.create(codigo_unidad='COD-RETIRADO-2', codigo_bien='880002', equipo=self.tipo,
                                    laboratorio=self.unidad, activa=False)
        self.assertEqual(self.client.get(reverse('escaner_unidad', args=[self.unidad.slug])).status_code, 200)
        propia = self.client.get(reverse('escaner_buscar', args=[self.unidad.slug]), {'codigo': '23300000000-880001'}).json()
        self.assertTrue(propia['encontrado'] and propia['misma_unidad'])
        self.assertEqual(propia['ficha_url'], reverse('ficha_equipo_publica', args=[self.unidad.slug, 'COD-VR-01']))
        self.assertNotIn('Funcionaria E', str(propia))
        ajena = self.client.get(reverse('escaner_buscar', args=[self.otra.slug]), {'codigo': 'COD-VR-01'}).json()
        self.assertTrue(ajena['encontrado'])
        self.assertFalse(ajena['misma_unidad'])
        self.assertEqual(ajena['unidad'], self.unidad.nombre)
        self.assertIn('?abrir=', ajena['unidad_url'])
        for codigo in ('880002', '99999999', ''):
            with self.subTest(codigo=codigo):
                self.assertFalse(self.client.get(reverse('escaner_buscar', args=[self.unidad.slug]), {'codigo': codigo}).json()['encontrado'])

    def test_solo_el_prefijo_de_la_universidad_se_reconoce_como_bien(self):
        self.assertEqual(limpiar_codigo_bien('23300000000-37881242'), '37881242')
        self.assertEqual(limpiar_codigo_bien('99999999-37881242'), '99999999-37881242')
        self.client.force_login(self.gestor)
        ajena = self.client.post(reverse('lector_registrar_equipo'),
                                 {'modo': 'nuevo', 'codigo': '99999999-444', 'unidad': self.unidad.slug, 'nombre': 'X'},
                                 content_type='application/json')
        self.assertEqual(ajena.status_code, 400)
        self.assertIn('23300000000', ajena.json()['error'])
        self.assertFalse(UnidadEquipo.objects.filter(codigo_bien__contains='444').exists())

    def test_el_importador_lee_una_carpeta_con_un_csv_por_area(self):
        with TemporaryDirectory() as carpeta:
            Path(carpeta, 'COD-AREA.csv').write_text(
                'codigo_bien;tipo_bien;descripcion;modelo;marca;codigo_sistema;nombre_equipo\n'
                '601;BLD;MAQUINA LASER DE ESCRITORIO;FALCON 2 PRO;CREALITY;nuevo;Grabadora láser de diodo de escritorio\n',
                encoding='utf-8')
            with self.assertRaisesMessage(CommandError, 'no uses --area'):
                call_command('importar_reporte_bienes', carpeta, '--unidad', self.unidad.slug, '--area', 'COD-AREA',
                             stdout=StringIO())
            call_command('importar_reporte_bienes', carpeta, '--unidad', self.unidad.slug, stdout=StringIO())
            Path(carpeta, 'COD-AREA.csv').rename(Path(carpeta, 'NO-EXISTE.csv'))
            with self.assertRaisesMessage(CommandError, 'NO-EXISTE'):
                call_command('importar_reporte_bienes', carpeta, '--unidad', self.unidad.slug, stdout=StringIO())
        self.assertTrue(UnidadEquipo.objects.get(codigo_bien='601').espacios_asociados.filter(pk=self.area.pk).exists())

    def test_los_reportes_de_bodega_guardados_estan_conciliados_por_area(self):
        carpeta = Path(__file__).resolve().parents[2] / 'apps' / 'recursos' / 'management' / 'bienes_bodega' / 'laboratorio-fabricacion-digital-prototipado'
        from apps.recursos.presentation.reportes_bodega import CARPETA
        self.assertEqual(carpeta.parent, CARPETA)
        areas = FICHAS_FABLAB['laboratorio-fabricacion-digital-prototipado']
        codigos = []
        for archivo in sorted(carpeta.glob('*.csv')):
            with self.subTest(area=archivo.stem):
                self.assertIn(archivo.stem, areas)
                bienes = list(leer_reporte(archivo))
                self.assertTrue(bienes)
                self.assertTrue(all(bien['codigo_bien'].isdigit() for bien in bienes))
                codigos += [bien['codigo_bien'] for bien in bienes]
        self.assertEqual(len(codigos), 26)
        self.assertEqual(len(set(codigos)), 26)

    def test_los_ejemplos_de_inventario_solo_en_desarrollo_y_se_eliminan(self):
        from django.core.management.base import CommandError
        from django.test import override_settings

        from apps.recursos.models.equipos import EquiposServicios as Tipo

        with self.assertRaises(CommandError):
            call_command('cargar_ejemplos_inventario', '--unidad', self.unidad.slug, '--destino', self.otra.slug,
                         stdout=StringIO())
        for nombre in ('Portátil de préstamo', 'Impresora 3D FDM', 'Fresadora CNC', 'Cortadora láser', 'Secador de filamento'):
            tipo = Tipo.objects.create(codigo=f'EJ-{nombre[:8]}', nombre=nombre)
            fisica = UnidadEquipo.objects.create(codigo_unidad=f'BASE-{nombre[:6]}', equipo=tipo, laboratorio=self.unidad)
            self.area.equipos_asociados.add(fisica)
        with override_settings(DEBUG=True):
            salida = StringIO()
            call_command('cargar_ejemplos_inventario', '--unidad', self.unidad.slug, '--destino', self.otra.slug, stdout=salida)
            marca = '[Ejemplo de inventario]'
            prestado = UnidadEquipo.objects.get(observaciones__startswith=f'{marca} Equipo prestado')
            # Los ejemplos nacen con el código estándar de su unidad y su área.
            self.assertTrue(prestado.codigo_unidad.startswith('COD-AREA-'), prestado.codigo_unidad)
            self.assertIn(prestado.codigo_unidad, salida.getvalue())
            self.assertEqual(prestado.estado_unidad, 'prestado')
            viajero = UnidadEquipo.objects.get(observaciones__startswith=f'{marca} Equipo transferido')
            self.assertEqual(viajero.laboratorio, self.otra)
            anterior = viajero.codigos_anteriores.get().codigo
            self.assertTrue(anterior.startswith('COD-AREA-'))
            self.assertEqual(buscar_equipo(anterior), viajero)
            call_command('cargar_ejemplos_inventario', '--eliminar', stdout=StringIO())
        self.assertFalse(UnidadEquipo.objects.filter(observaciones__startswith='[Ejemplo de inventario]').exists())

    def test_lo_retirado_y_los_datos_malformados_no_rompen_ni_se_filtran(self):
        estudiante = get_user_model().objects.create_user('estudiante-codigos', password='clave')
        identificar(estudiante, tipo_usuario='estudiante')
        # El PDF de un equipo sin textos públicos se genera igual.
        pdf = self.client.get(reverse('ficha_equipo_publica', args=[self.unidad.slug, 'COD-VR-02']), {'formato': 'pdf'})
        self.assertEqual(pdf.status_code, 200)
        retirado = UnidadEquipo.objects.create(codigo_unidad='COD-RETIRADO', equipo=self.tipo, laboratorio=self.unidad,
                                               activa=False, codigo_bien='777')
        self.assertEqual(self.client.get(reverse('ficha_equipo_publica', args=[self.unidad.slug, 'COD-RETIRADO'])).status_code, 404)
        self.assertEqual(self.client.get(reverse('identificador_equipo', args=[self.unidad.slug, 'COD-RETIRADO'])).status_code, 404)
        self.client.force_login(estudiante)
        # El lector es para el personal: un estudiante no lo usa.
        self.assertEqual(self.client.get(reverse('lector_buscar_equipo'), {'codigo': '777'}).status_code, 403)
        personal = get_user_model().objects.create_user('personal-codigos', password='clave', is_staff=True)
        self.client.force_login(personal)
        self.assertFalse(self.client.get(reverse('lector_buscar_equipo'), {'codigo': '777'}).json()['encontrado'])
        for cuerpo in ('[]', '{"codigo": 123}', '{"codigo": "888", "modo": "enlazar", "equipo_id": "abc"}'):
            with self.subTest(cuerpo=cuerpo):
                respuesta = self.client.post(reverse('lector_registrar_equipo'), cuerpo, content_type='application/json')
                self.assertIn(respuesta.status_code, (400, 403))
        self.client.force_login(self.gestor)
        self.assertTrue(self.client.get(reverse('lector_buscar_equipo'), {'codigo': '777'}).json()['encontrado'])
        self.assertEqual(self.client.get(reverse('ficha_equipo_publica', args=[self.unidad.slug, retirado.codigo_unidad])).status_code, 200)
        malo = self.client.post(reverse('lector_registrar_equipo'), '{"codigo": "888", "modo": "enlazar", "equipo_id": "abc"}',
                                content_type='application/json')
        self.assertEqual(malo.status_code, 400)
