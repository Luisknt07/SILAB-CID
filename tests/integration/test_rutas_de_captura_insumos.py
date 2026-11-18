"""Ruta de captura de insumos y existencias: lo que la cuenta de la unidad registra en su panel llega a sus documentos.

Cada prueba recorre la pantalla con el cliente HTTP y una cuenta que administra la unidad (no superusuario), y envía
lo que enviaría el formulario real: los datos se leen del formulario que dibuja el panel, con sus valores por omisión,
y de los atributos `data-field-*` del botón que lo abre. Cubre:

- los decimales llegan a los formularios con punto (con coma, el campo numérico quedaba vacío y no dejaba guardar);
- crear un insumo con lo mínimo y editarlo sin perder valores, incluida la marca de sustancia sujeta a control;
- recibir existencias en un paso: código generado, bodega y costo por omisión, una o varias presentaciones;
- abrir una presentación, consumir y ajustar el saldo;
- anexo 3 (tablas 3.4 Reactivos, 3.5 Insumos y materiales, 3.6 Movimientos del período) y el documento de respaldo
  «Sustancias sujetas a control»;
- pedir en una reserva un insumo con existencias, y qué se responde cuando está agotado.
"""
import json
from datetime import date, timedelta
from decimal import Decimal
from html.parser import HTMLParser
from io import BytesIO, StringIO
from tempfile import TemporaryDirectory

from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from django.core.management import call_command
from django.test import TestCase, override_settings
from django.urls import reverse
from django.utils import timezone
from pypdf import PdfReader

from apps.directorio_unidades.models.core import Unidad
from apps.formacion.models.practicas import RegistroAuditoriaUnidad
from apps.integraciones.management.commands.auditar_plantillas import campos_decimales, decimales_localizados
from apps.recursos.models.consumibles import Consumible, EntradaInventario, LoteConsumible
from apps.recursos.models.equipos import EquiposServicios
from apps.recursos.models.unidades import UnidadEquipo
from apps.reservas.models.reservas import Reserva
from tests.integration.utiles import identificar, pdf_legible_prueba, verificar_pertenencia


class _Formulario(HTMLParser):
    """Un formulario del panel tal como lo enviaría el navegador sin tocar nada.

    `datos` lleva cada control con su valor por omisión; `obligatorios`, los que el navegador exige;
    `clases`, si el control es casilla o lista múltiple (para aplicar los `data-field-*` como lo hace el panel).
    """

    def __init__(self, nombre):
        super().__init__()
        self.nombre, self.dentro, self.encontrado = nombre, False, False
        self.datos, self.obligatorios, self.clases = {}, set(), {}
        self._lista = self._area = None

    def handle_starttag(self, etiqueta, atributos):
        atributos = dict(atributos)
        if etiqueta == 'form':
            self.dentro = atributos.get('data-agenda-operation-form') == self.nombre
            self.encontrado = self.encontrado or self.dentro
            return
        if not self.dentro:
            return
        nombre = atributos.get('name')
        if nombre and 'required' in atributos:
            self.obligatorios.add(nombre)
        if etiqueta == 'input' and nombre:
            tipo = atributos.get('type', 'text')
            if tipo == 'checkbox':
                self.clases[nombre] = 'casilla'
                if 'checked' in atributos:
                    self.datos[nombre] = atributos.get('value') or 'on'
            elif tipo not in ('file', 'submit', 'button'):
                self.datos[nombre] = atributos.get('value') or ''
        elif etiqueta == 'select' and nombre:
            self._lista = [nombre, 'multiple' in atributos, False]
            if self._lista[1]:
                self.clases[nombre] = 'multiple'
        elif etiqueta == 'option' and self._lista:
            nombre, multiple, elegido = self._lista
            if not multiple and (not elegido or 'selected' in atributos):
                self.datos[nombre] = atributos.get('value') or ''
                self._lista[2] = True
        elif etiqueta == 'textarea' and nombre:
            self._area = nombre
            self.datos[nombre] = ''

    def handle_data(self, texto):
        if self.dentro and self._area:
            self.datos[self._area] += texto

    def handle_endtag(self, etiqueta):
        if etiqueta == 'form':
            self.dentro = False
        elif etiqueta == 'select':
            self._lista = None
        elif etiqueta == 'textarea':
            self._area = None


class _Botones(HTMLParser):
    """Los botones que abren un formulario del panel, con sus atributos."""

    def __init__(self, formulario):
        super().__init__()
        self.formulario, self.hallados = formulario, []

    def handle_starttag(self, etiqueta, atributos):
        atributos = dict(atributos)
        if etiqueta == 'button' and atributos.get('data-agenda-operation-open') == self.formulario:
            self.hallados.append(atributos)


def _texto_del_pdf(contenido):
    """El texto del PDF en una sola línea, para buscar frases que la celda parte en renglones."""
    return ' '.join(' '.join(pagina.extract_text() or '' for pagina in PdfReader(BytesIO(contenido)).pages).split())


@override_settings(MEDICION_METAS_HABILITADA=True, MEDICION_SOLO_DEMO=False)
class RutaDeCapturaDeInsumosTests(TestCase):
    databases = {'default', 'centros'}

    @classmethod
    def setUpTestData(cls):
        usuarios = get_user_model().objects
        # La cuenta de la unidad: administra su laboratorio y no es superusuario.
        cls.gestor = usuarios.create_user('admin.lab-captura-insumos', password='clave-de-prueba',
                                          first_name='Gabriela', last_name='Gestora')
        identificar(cls.gestor, tipo_usuario='administrativo', carrera='')
        cls.solicitante = usuarios.create_user('estudiante.captura-insumos', password='clave-de-prueba',
                                               first_name='Saúl', last_name='Solicitante',
                                               email='saul.captura-insumos@upec.edu.ec')
        identificar(cls.solicitante, tipo_usuario='estudiante')
        verificar_pertenencia(cls.solicitante)
        cls.lab = Unidad.objects.create(
            nombre='Laboratorio ficticio de captura de insumos', slug='lab-captura-insumos', dependencia='laboratorios',
            descripcion='Unidad ficticia para probar la captura de insumos.', fecha_inicio=date(2025, 1, 1),
            administrador=cls.gestor, activo=True)
        modelo = EquiposServicios.objects.create(codigo='MOD-CAP-INS-01', nombre='Agitador ficticio de captura')
        cls.equipo = UnidadEquipo.objects.create(codigo_unidad='EQ-CAP-INS-01', equipo=modelo, laboratorio=cls.lab,
                                                 estado_unidad='disponible', activa=True)
        cls.accion = reverse('gestion_operacion_accion', args=[cls.lab.slug])
        cls.panel_url = reverse('gestion_unidad', args=[cls.lab.slug])

    def setUp(self):
        self.assertFalse(self.gestor.is_superuser)
        carpeta = TemporaryDirectory(prefix='captura-insumos-')
        self.addCleanup(carpeta.cleanup)
        medios = override_settings(MEDIA_ROOT=carpeta.name)
        medios.enable()
        self.addCleanup(medios.disable)
        self.client.force_login(self.gestor)

    # ---- ayudas: la pantalla como la usa la persona ------------------------------------------------------

    def panel(self, modo):
        respuesta = self.client.get(self.panel_url, {'view': 'recursos', 'modo_recursos': modo})
        self.assertEqual(respuesta.status_code, 200)
        return respuesta.content.decode('utf-8')

    def formulario(self, html, nombre):
        lector = _Formulario(nombre)
        lector.feed(html)
        self.assertTrue(lector.encontrado, f'El panel no dibuja el formulario «{nombre}».')
        return lector

    def botones(self, html, formulario, **con):
        lector = _Botones(formulario)
        lector.feed(html)
        return [b for b in lector.hallados
                if all(b.get('data-field-' + campo) == str(valor) for campo, valor in con.items())]

    def abrir(self, html, formulario, boton=None, /, **escrito):
        """Lo que se envía al guardar: el formulario con sus valores por omisión, los datos que le pasa el botón que
        lo abre (como hace el panel con los `data-field-*`) y lo que la persona escribe."""
        lector = self.formulario(html, formulario)
        datos = dict(lector.datos)
        for atributo, valor in (boton or {}).items():
            campo = atributo[len('data-field-'):]
            if not atributo.startswith('data-field-') or (campo not in lector.datos and campo not in lector.clases):
                continue
            if lector.clases.get(campo) == 'casilla':
                datos.pop(campo, None)
                if valor in ('true', '1'):
                    datos[campo] = 'on'
            elif lector.clases.get(campo) == 'multiple':
                datos[campo] = [parte for parte in valor.split(',') if parte]
            else:
                datos[campo] = valor
        datos.update(escrito)
        if 'catalogos_remotos' in datos:
            # El panel marca que las listas remotas terminaron de cargar antes de permitir guardar.
            datos['catalogos_seleccion_cargada'] = '1'
        datos['accion'] = 'guardar'
        return datos

    def guardar(self, datos, espera=200):
        respuesta = self.client.post(self.accion, datos)
        self.assertEqual(respuesta.status_code, espera, respuesta.content.decode('utf-8'))
        return respuesta.json()

    def crear_insumo(self, codigo, nombre, **escrito):
        """«Nuevo insumo» en Recursos e inventario → Insumos y materiales."""
        html = self.panel('insumos')
        nuevo = [b for b in self.botones(html, 'consumible') if 'data-field-registro_id' not in b]
        self.assertTrue(nuevo, 'El panel no ofrece «Nuevo insumo».')
        datos = self.abrir(html, 'consumible', nuevo[0], codigo=codigo, nombre=nombre,
                           **({'unidad_medida': 'g', 'cantidad_por_presentacion': '1000'} | escrito))
        self.guardar(datos)
        return Consumible.objects.get(codigo=codigo)

    def recibir(self, insumo, modo='insumos', espera=200, **escrito):
        """«Recibir existencias» desde la tarjeta del insumo."""
        html = self.panel(modo)
        boton = [b for b in self.botones(html, 'lote_consumible', consumible_id=insumo.pk)
                 if 'data-field-registro_id' not in b]
        self.assertTrue(boton, f'El panel ({modo}) no ofrece «Recibir existencias» para {insumo.codigo}.')
        return self.guardar(self.abrir(html, 'lote_consumible', boton[0], **escrito), espera)

    def anexo_de_inventario(self):
        """El anexo 3 con los registros al día, como lo abre el Centro de reportes."""
        respuesta = self.client.get(reverse('gestion_expediente_unidad', args=[self.lab.slug]),
                                    {'gestionar': 'INFORME-SEMESTRAL', 'anexo': 'INVENTARIO-CORTE', 'borrador': '1'})
        self.assertEqual(respuesta.status_code, 200)
        self.assertEqual(respuesta['Content-Type'], 'application/pdf')
        return _texto_del_pdf(respuesta.content)

    # ---- decimales ----------------------------------------------------------------------------------------

    def test_el_panel_entrega_los_decimales_con_punto_a_sus_formularios(self):
        """Con coma («1000,000»), el campo numérico quedaba vacío y, por obligatorio, el navegador no dejaba guardar."""
        insumo = Consumible.objects.create(
            unidad=self.lab, codigo='DEC-CAP-01', nombre='Agar ficticio decimal', unidad_medida='g',
            presentacion='Envase de 1 kg', cantidad_por_presentacion=Decimal('1000.000'), minimo=Decimal('250.500'),
            stock_seguridad=Decimal('100.250'), stock_objetivo=Decimal('2000.000'), precio_unitario=Decimal('0.0350'))
        self.recibir(insumo)
        lote = LoteConsumible.objects.get(consumible=insumo)

        for modo in ('insumos', 'inventario'):
            with self.subTest(modo=modo):
                html = self.panel(modo)
                editar = self.botones(html, 'consumible', registro_id=insumo.pk)
                self.assertTrue(editar, 'Falta el botón de editar el insumo.')
                self.assertEqual(
                    {campo: editar[0]['data-field-' + campo] for campo in (
                        'cantidad_por_presentacion', 'minimo', 'stock_seguridad', 'stock_objetivo', 'precio_unitario')},
                    {'cantidad_por_presentacion': '1000.000', 'minimo': '250.500', 'stock_seguridad': '100.250',
                     'stock_objetivo': '2000.000', 'precio_unitario': '0.0350'})
                # La recepción calcula el total con el contenido de la presentación.
                self.assertIn('data-presentation-size="1000.000"', html)
                self.assertNotIn('data-presentation-size="1000,000"', html)
                self.assertNotIn('="1000,000"', html)
                self.assertNotIn('="250,500"', html)
        # En «Existencias y consumo» el lote también pasa sus cantidades y su costo sin formato local.
        html = self.panel('inventario')
        self.assertIn('data-lot-quantity="1000.000"', html)
        self.assertIn('data-unit-cost="0.0350"', html)
        ubicar = self.botones(html, 'lote_consumible', registro_id=lote.pk)
        self.assertEqual({b['data-field-cantidad_inicial'] for b in ubicar}, {'1000.000'})
        self.assertEqual({b['data-field-costo_unitario'] for b in ubicar}, {'0.0350'})

    def test_la_auditoria_de_plantillas_vigila_los_decimales_del_panel(self):
        decimales = campos_decimales()
        self.assertIn('cantidad_por_presentacion', decimales)
        # Un atributo del panel con un campo decimal sin `unlocalize` es un hallazgo; con él, no.
        self.assertEqual(
            decimales_localizados('<button data-field-minimo="{{ item.minimo }}" data-field-nombre="{{ item.nombre }}">',
                                  decimales),
            ['data-field-minimo="{{ item.minimo }}"'])
        self.assertEqual(decimales_localizados(
            '<button data-field-minimo="{{ item.minimo|unlocalize }}"'
            " data-x=\"{{ lote.costo_unitario|default_if_none:''|unlocalize }}\""
            " data-y=\"{{ receta.cantidad_base|floatformat:'-3u' }}\">", decimales), [])
        # `floatformat` sin la «u» también imprime coma; en un campo de texto, `value` no se vigila.
        self.assertEqual(len(decimales_localizados(
            "<input type=\"number\" name=\"monto\" value=\"{{ movimiento.monto|floatformat:'2' }}\">", decimales)), 1)
        self.assertEqual(decimales_localizados('<input type="text" name="monto" value="{{ fila.monto }}">', decimales),
                         [])
        # Las plantillas del proyecto pasan la regla.
        call_command('auditar_plantillas', stdout=StringIO())

    # ---- ficha del insumo ---------------------------------------------------------------------------------

    def test_un_insumo_nuevo_se_crea_con_codigo_nombre_unidad_base_y_contenido(self):
        html = self.panel('insumos')
        self.assertEqual(self.formulario(html, 'consumible').obligatorios,
                         {'codigo', 'nombre', 'unidad_medida', 'cantidad_por_presentacion'})
        insumo = self.crear_insumo('MIN-CAP-01', 'Guantes ficticios de nitrilo', unidad_medida='par',
                                   cantidad_por_presentacion='50')
        self.assertEqual(
            (insumo.unidad_id, insumo.clasificacion, insumo.unidad_medida, insumo.cantidad_por_presentacion,
             insumo.stock_total, insumo.minimo, insumo.stock_seguridad, insumo.stock_objetivo,
             insumo.plazo_reposicion_dias, insumo.precio_unitario, insumo.activo, insumo.visible_en_reservas),
            (self.lab.pk, 'insumo', 'par', Decimal('50.000'), Decimal('0'), Decimal('0'), Decimal('0'), Decimal('0'),
             0, None, True, True))
        self.assertTrue(RegistroAuditoriaUnidad.objects.filter(
            unidad=self.lab, entidad='recursos.Consumible', objeto_id=str(insumo.pk), accion='crear').exists())
        # Un código repetido se rechaza diciendo cuál es el problema.
        html = self.panel('insumos')
        nuevo = [b for b in self.botones(html, 'consumible') if 'data-field-registro_id' not in b][0]
        error = self.guardar(self.abrir(html, 'consumible', nuevo, codigo='MIN-CAP-01', nombre='Otro',
                                        unidad_medida='par', cantidad_por_presentacion='1'), 400)['error']
        self.assertIn('MIN-CAP-01', error)
        self.assertIn('otro código', error)

    def test_guardar_la_ficha_sin_tocar_nada_no_cambia_ningun_valor(self):
        insumo = Consumible.objects.create(
            unidad=self.lab, codigo='EDI-CAP-01', nombre='Etanol ficticio al 96 %', clasificacion='reactivo',
            familia='Solventes', variante='Grado analítico', color='Incoloro', marca='Marca ficticia',
            presentacion='Botella de 1 L', cantidad_por_presentacion=Decimal('1000.000'), unidad_medida='ml',
            descripcion='Solvente de prueba.', especificacion_tecnica='Pureza ficticia 96 %.',
            instrucciones_solicitud='Pide los mililitros de la guía.', minimo=Decimal('500.500'),
            stock_seguridad=Decimal('250.250'), stock_objetivo=Decimal('4000.000'), plazo_reposicion_dias=20,
            precio_unitario=Decimal('0.0125'), origen_abastecimiento='proyecto',
            proveedor_referencia='Proveedor ficticio', ubicacion='Armario de solventes', lote='L-FICTICIO-01',
            fecha_vencimiento=date(2099, 12, 31))
        insumo.equipos_compatibles.add(self.equipo.equipo)
        insumo.refresh_from_db()
        campos = [campo.name for campo in Consumible._meta.concrete_fields if campo.name != 'fecha_actualizacion']
        antes = {campo: getattr(insumo, campo) for campo in campos}

        for modo in ('insumos', 'inventario'):
            with self.subTest(modo=modo):
                html = self.panel(modo)
                editar = self.botones(html, 'consumible', registro_id=insumo.pk)
                self.assertTrue(editar)
                self.guardar(self.abrir(html, 'consumible', editar[0]))
                insumo.refresh_from_db()
                self.assertEqual({campo: getattr(insumo, campo) for campo in campos}, antes)
                self.assertEqual(list(insumo.equipos_compatibles.all()), [self.equipo.equipo])

        # La marca de sustancia sujeta a control y su autorización se guardan desde la misma ficha.
        html = self.panel('insumos')
        editar = self.botones(html, 'consumible', registro_id=insumo.pk)[0]
        self.assertEqual(editar['data-field-sustancia_controlada'], 'false')
        self.guardar(self.abrir(html, 'consumible', editar, sustancia_controlada='true',
                                autorizacion_control='Licencia ficticia 2026-001'))
        insumo.refresh_from_db()
        self.assertTrue(insumo.sustancia_controlada)
        self.assertEqual(insumo.autorizacion_control, 'Licencia ficticia 2026-001')
        editar = self.botones(self.panel('insumos'), 'consumible', registro_id=insumo.pk)[0]
        self.assertEqual((editar['data-field-sustancia_controlada'], editar['data-field-autorizacion_control']),
                         ('true', 'Licencia ficticia 2026-001'))

    # ---- recepción de existencias -------------------------------------------------------------------------

    def test_recibir_existencias_pide_solo_el_insumo_y_cuantas_presentaciones(self):
        insumo = self.crear_insumo('REC-CAP-01', 'Agarosa ficticia', ubicacion='Estante ficticio B2',
                                   precio_unitario='0.0450')
        html = self.panel('insumos')
        formulario = self.formulario(html, 'lote_consumible')
        self.assertEqual(formulario.obligatorios, {'consumible_id', 'numero_presentaciones'})
        self.assertEqual(formulario.datos['numero_presentaciones'], '1')
        self.assertEqual((formulario.datos['codigo'], formulario.datos['bodega'], formulario.datos['estado']),
                         ('', '', 'bodega'))
        self.assertEqual(formulario.datos['fecha_ingreso'], timezone.localdate().isoformat())
        self.assertIn('Más datos (opcional)', html)
        self.assertNotIn('data-inventory-calculated-quantity', html)

        hoy = timezone.localdate()
        self.recibir(insumo)
        lote = LoteConsumible.objects.get(consumible=insumo)
        insumo.refresh_from_db()
        self.assertEqual(
            (lote.codigo, lote.estado, lote.bodega, lote.fecha_ingreso, lote.cantidad_inicial, lote.cantidad_actual,
             lote.costo_unitario, lote.creado_por),
            (f'REC-CAP-01-{hoy:%Y%m%d}-01', 'bodega', 'Estante ficticio B2', hoy, Decimal('1000.000'),
             Decimal('1000.000'), Decimal('0.0450'), self.gestor))
        self.assertEqual(insumo.stock_total, Decimal('1000.000'))
        # El ingreso es un movimiento trazable, con su saldo y su rastro de auditoría.
        movimiento = EntradaInventario.objects.get(consumible=insumo)
        self.assertEqual(
            (movimiento.tipo, movimiento.motivo, movimiento.cantidad, movimiento.saldo_resultante,
             movimiento.lote_inventario, movimiento.usuario, movimiento.costo_unitario),
            ('ingreso', 'recepcion', Decimal('1000.000'), Decimal('1000.000'), lote, self.gestor, Decimal('0.0450')))
        for entidad, objeto in (('recursos.LoteConsumible', lote), ('recursos.EntradaInventario', movimiento)):
            self.assertTrue(RegistroAuditoriaUnidad.objects.filter(
                unidad=self.lab, entidad=entidad, objeto_id=str(objeto.pk), accion='crear').exists(), entidad)
        # La tarjeta deja de decir «Agotado».
        tarjeta = [b for b in self.panel('insumos').split('<article') if 'REC-CAP-01' in b][0].split('</article>')[0]
        self.assertNotIn('Agotado', tarjeta)
        self.assertIn('1000 g', tarjeta)

    def test_varias_presentaciones_reciben_codigos_consecutivos_y_un_movimiento_cada_una(self):
        insumo = self.crear_insumo('VAR-CAP-01', 'Filamento ficticio PLA')
        hoy = timezone.localdate()
        self.recibir(insumo)
        mensaje = self.recibir(insumo, modo='inventario', numero_presentaciones='3')['message']
        self.assertIn('3 presentaciones recibidas', mensaje)
        lotes = list(LoteConsumible.objects.filter(consumible=insumo).order_by('codigo'))
        self.assertEqual([lote.codigo for lote in lotes],
                         [f'VAR-CAP-01-{hoy:%Y%m%d}-{numero:02d}' for numero in (1, 2, 3, 4)])
        self.assertTrue(all(lote.cantidad_actual == Decimal('1000.000') and lote.estado == 'bodega' for lote in lotes))
        # Sin ubicación en la ficha, la bodega por omisión es la unidad.
        self.assertEqual({lote.bodega for lote in lotes}, {self.lab.nombre})
        insumo.refresh_from_db()
        self.assertEqual(insumo.stock_total, Decimal('4000.000'))
        self.assertEqual(
            sorted(EntradaInventario.objects.filter(consumible=insumo).values_list('lote_inventario__codigo', flat=True)),
            [lote.codigo for lote in lotes])
        self.assertEqual(list(EntradaInventario.objects.filter(consumible=insumo).order_by('pk')
                              .values_list('saldo_resultante', flat=True)),
                         [Decimal('1000.000'), Decimal('2000.000'), Decimal('3000.000'), Decimal('4000.000')])

    def test_los_datos_opcionales_de_la_recepcion_se_respetan_y_los_errores_dicen_que_falta(self):
        insumo = self.crear_insumo('OPC-CAP-01', 'Resina ficticia', ubicacion='Estante ficticio')
        self.recibir(insumo, codigo='LOTE-PROPIO-01', numero_presentaciones='2', bodega='Bodega ficticia norte',
                     estanteria='E4', posicion='Nivel 1', fecha_vencimiento='2099-06-30', costo_unitario='0.0200',
                     documento_recepcion='ACTA-FICTICIA-01')
        lotes = list(LoteConsumible.objects.filter(consumible=insumo).order_by('codigo'))
        self.assertEqual([lote.codigo for lote in lotes], ['LOTE-PROPIO-01', 'LOTE-PROPIO-01-02'])
        self.assertEqual({(lote.bodega, lote.estanteria, lote.posicion, lote.fecha_vencimiento, lote.costo_unitario,
                           lote.documento_recepcion) for lote in lotes},
                         {('Bodega ficticia norte', 'E4', 'Nivel 1', date(2099, 6, 30), Decimal('0.0200'),
                           'ACTA-FICTICIA-01')})

        # Código repetido: se dice cuál y cómo resolverlo, y no ingresa nada.
        error = self.recibir(insumo, espera=400, codigo='LOTE-PROPIO-01')['error']
        self.assertIn('ya tiene un lote con el código «LOTE-PROPIO-01»', error)
        self.assertIn('Deja vacío', error)
        # «En uso» sin equipo, en un insumo con equipos compatibles definidos: el mensaje nombra el campo.
        insumo.equipos_compatibles.add(self.equipo.equipo)
        error = self.recibir(insumo, modo='inventario', espera=400, estado='en_uso')['error']
        self.assertIn('«Equipo donde está en uso»', error)
        # Sin insumo elegido.
        html = self.panel('inventario')
        general = [b for b in self.botones(html, 'lote_consumible') if 'data-field-consumible_id' not in b]
        self.assertTrue(general, 'Falta el botón general «Recibir existencias».')
        error = self.guardar(self.abrir(html, 'lote_consumible', general[0]), 400)['error']
        self.assertIn('«Insumo o material»', error)
        # Presentaciones no enteras.
        error = self.recibir(insumo, espera=400, numero_presentaciones='1.5')['error']
        self.assertIn('entero', error)
        insumo.refresh_from_db()
        self.assertEqual((LoteConsumible.objects.filter(consumible=insumo).count(), insumo.stock_total),
                         (2, Decimal('2000.000')))

    # ---- usar lo recibido ---------------------------------------------------------------------------------

    def test_lo_recibido_se_pone_en_uso_se_consume_y_se_ajusta(self):
        insumo = self.crear_insumo('USO-CAP-01', 'Buffer ficticio', unidad_medida='ml', cantidad_por_presentacion='500')
        # Con equipos compatibles definidos el lote se abre y se consume en un equipo.
        insumo.equipos_compatibles.add(self.equipo.equipo)
        self.recibir(insumo, numero_presentaciones='2')
        primero, segundo = LoteConsumible.objects.filter(consumible=insumo).order_by('codigo')

        # «Poner en uso»: el botón del lote abre el formulario con el estado ya puesto; solo se elige el equipo.
        html = self.panel('inventario')
        poner = [b for b in self.botones(html, 'lote_consumible', registro_id=primero.pk)
                 if b.get('data-field-estado') == 'en_uso']
        self.assertEqual(len(poner), 1, 'El lote en bodega debe ofrecer «Poner en uso».')
        self.assertIn('Poner en uso', html)
        self.guardar(self.abrir(html, 'lote_consumible', poner[0], equipo_en_uso_id=str(self.equipo.pk)))
        primero.refresh_from_db()
        self.assertEqual((primero.estado, primero.equipo_en_uso, primero.fecha_apertura, primero.cantidad_actual),
                         ('en_uso', self.equipo, timezone.localdate(), Decimal('500.000')))

        # Salida por consumo de la presentación abierta.
        html = self.panel('inventario')
        consumo = [b for b in self.botones(html, 'inventario', consumible_id=insumo.pk)
                   if b.get('data-field-tipo') == 'salida']
        self.assertTrue(consumo, 'El insumo debe ofrecer «Consumo o salida» ya en salida.')
        self.assertNotIn('nota', self.formulario(html, 'inventario').obligatorios)
        salida = self.guardar(self.abrir(html, 'inventario', consumo[0], motivo='consumo_practica', cantidad='120.5',
                                         lote_inventario_id=str(primero.pk)))
        movimiento = EntradaInventario.objects.get(pk=salida['registro']['id'])
        primero.refresh_from_db()
        insumo.refresh_from_db()
        self.assertEqual(
            (movimiento.tipo, movimiento.motivo, movimiento.cantidad, movimiento.saldo_resultante, movimiento.equipo,
             primero.cantidad_actual, insumo.stock_total),
            ('salida', 'consumo_practica', Decimal('120.500'), Decimal('879.500'), self.equipo, Decimal('379.500'),
             Decimal('879.500')))

        # Consumir de una presentación cerrada la abre en el mismo paso (el panel envía la marca y el equipo).
        cerrada = self.abrir(html, 'inventario', consumo[0], motivo='consumo_practica', cantidad='50',
                             lote_inventario_id=str(segundo.pk))
        self.assertEqual(cerrada['abrir_presentacion'], '')
        error = self.guardar(cerrada, 400)['error']
        self.assertIn('sigue cerrada en bodega', error)
        error = self.guardar(cerrada | {'abrir_presentacion': '1'}, 400)['error']
        self.assertIn('«Equipo relacionado»', error)
        self.guardar(cerrada | {'abrir_presentacion': '1', 'equipo_id': str(self.equipo.pk)})
        segundo.refresh_from_db()
        self.assertEqual((segundo.estado, segundo.equipo_en_uso, segundo.cantidad_actual),
                         ('en_uso', self.equipo, Decimal('450.000')))
        self.assertTrue(RegistroAuditoriaUnidad.objects.filter(
            unidad=self.lab, entidad='recursos.LoteConsumible', objeto_id=str(segundo.pk), accion='actualizar',
            descripcion__icontains='puesta en uso').exists())

        # Ajuste al saldo contado del lote: queda como movimiento de ajuste, no como edición del saldo.
        ajuste = self.guardar(self.abrir(html, 'inventario', consumo[0], tipo='ajuste', cantidad='300',
                                         lote_inventario_id=str(primero.pk), nota='Conteo físico ficticio.'))
        movimiento = EntradaInventario.objects.get(pk=ajuste['registro']['id'])
        primero.refresh_from_db()
        insumo.refresh_from_db()
        self.assertEqual((movimiento.tipo, movimiento.motivo, movimiento.cantidad, primero.cantidad_actual,
                          insumo.stock_total),
                         ('salida', 'ajuste_negativo', Decimal('79.500'), Decimal('300.000'), Decimal('750.000')))

    def test_un_insumo_sin_equipos_compatibles_se_abre_y_se_consume_sin_asignar_equipo(self):
        insumo = self.crear_insumo('GEN-CAP-01', 'Etanol ficticio de uso general', unidad_medida='ml',
                                   cantidad_por_presentacion='500')
        self.recibir(insumo, numero_presentaciones='2')
        primero, segundo = LoteConsumible.objects.filter(consumible=insumo).order_by('codigo')
        html = self.panel('inventario')
        # El panel marca qué insumo exige equipo: este no, así que el selector no se pide.
        self.assertIn(f'value="{insumo.pk}" data-compatible-equipment-ids="{self.equipo.pk}" data-requires-equipment=""',
                      html)

        # Desde bodega: el consumo abre la presentación hoy y la deja «En uso» sin equipo, en el mismo paso.
        consumo = [b for b in self.botones(html, 'inventario', consumible_id=insumo.pk)
                   if b.get('data-field-tipo') == 'salida'][0]
        salida = self.guardar(self.abrir(html, 'inventario', consumo, motivo='consumo_practica', cantidad='40',
                                         lote_inventario_id=str(primero.pk)))
        movimiento = EntradaInventario.objects.get(pk=salida['registro']['id'])
        primero.refresh_from_db()
        self.assertEqual((primero.estado, primero.equipo_en_uso, primero.fecha_apertura, primero.cantidad_actual),
                         ('en_uso', None, timezone.localdate(), Decimal('460.000')))
        self.assertEqual((movimiento.lote_inventario, movimiento.cantidad, movimiento.motivo, movimiento.usuario,
                          movimiento.equipo, movimiento.saldo_resultante),
                         (primero, Decimal('40.000'), 'consumo_practica', self.gestor, None, Decimal('960.000')))
        self.assertTrue(RegistroAuditoriaUnidad.objects.filter(
            unidad=self.lab, entidad='recursos.LoteConsumible', objeto_id=str(primero.pk),
            descripcion__icontains='puesta en uso').exists())

        # Desde «En uso»: se sigue descontando de la presentación abierta, también sin equipo.
        self.guardar(self.abrir(html, 'inventario', consumo, motivo='desperdicio_calidad', cantidad='10',
                                lote_inventario_id=str(primero.pk)))
        primero.refresh_from_db()
        self.assertEqual(primero.cantidad_actual, Decimal('450.000'))

        # «Poner en uso» desde la lista de lotes tampoco pide equipo.
        poner = [b for b in self.botones(html, 'lote_consumible', registro_id=segundo.pk)
                 if b.get('data-field-estado') == 'en_uso'][0]
        self.guardar(self.abrir(html, 'lote_consumible', poner, equipo_en_uso_id=''))
        segundo.refresh_from_db()
        self.assertEqual((segundo.estado, segundo.equipo_en_uso), ('en_uso', None))
        insumo.refresh_from_db()
        self.assertEqual(insumo.stock_total, Decimal('950.000'))

    def test_un_insumo_con_equipos_compatibles_sigue_exigiendo_el_equipo_al_consumir_de_bodega(self):
        insumo = self.crear_insumo('FIL-CAP-01', 'Filamento ficticio', unidad_medida='g',
                                   cantidad_por_presentacion='1000')
        insumo.equipos_compatibles.add(self.equipo.equipo)
        self.recibir(insumo)
        lote = LoteConsumible.objects.get(consumible=insumo)
        html = self.panel('inventario')
        self.assertIn(f'value="{insumo.pk}" data-compatible-equipment-ids="{self.equipo.pk}" data-requires-equipment="1"',
                      html)
        consumo = [b for b in self.botones(html, 'inventario', consumible_id=insumo.pk)
                   if b.get('data-field-tipo') == 'salida'][0]
        error = self.guardar(self.abrir(html, 'inventario', consumo, motivo='consumo_practica', cantidad='5',
                                        lote_inventario_id=str(lote.pk), abrir_presentacion='1'), 400)['error']
        self.assertIn('equipos compatibles definidos', error)
        lote.refresh_from_db()
        self.assertEqual((lote.estado, lote.cantidad_actual), ('bodega', Decimal('1000.000')))

    # ---- documentos ---------------------------------------------------------------------------------------

    def test_tabla_3_4_reactivos_trae_el_lote_recibido_en_el_panel(self):
        html = self.panel('insumos')
        nuevo = [b for b in self.botones(html, 'consumible') if 'data-field-registro_id' not in b][0]
        datos = self.abrir(html, 'consumible', nuevo, codigo='REA-CAP-01', nombre='Ácido ficticio diluido',
                           clasificacion='reactivo', unidad_medida='ml', cantidad_por_presentacion='250',
                           presentacion='Frasco de 250 ml', marca='Marca ficticia R')
        datos['ficha_tecnica'] = SimpleUploadedFile('ficha-seguridad-ficticia.pdf', pdf_legible_prueba(
            'Ficha de seguridad ficticia del reactivo de prueba.'), content_type='application/pdf')
        self.guardar(datos)
        reactivo = Consumible.objects.get(codigo='REA-CAP-01')
        self.assertTrue(reactivo.ficha_tecnica)
        self.recibir(reactivo, bodega='Armario ficticio de reactivos', estanteria='R1', posicion='P2',
                     fecha_vencimiento='2099-03-31')
        lote = LoteConsumible.objects.get(consumible=reactivo)

        texto = self.anexo_de_inventario()
        self.assertIn('3.4 REACTIVOS', texto)
        for esperado in ('REA-CAP-01', 'Ácido ficticio diluido', 'Frasco de 250 ml', 'Marca ficticia R', lote.codigo,
                         '250 ml', '31/03/2099', 'Armario ficticio de reactivos · R1 · P2', 'En bodega'):
            self.assertIn(esperado, texto)
        self.assertIn('Total: 1 reactivo · lotes: 1', texto)

    def test_tabla_3_5_insumos_y_materiales_trae_la_ficha_y_su_existencia(self):
        insumo = self.crear_insumo('INS-CAP-01', 'Puntas ficticias de pipeta', clasificacion='material',
                                   unidad_medida='unidad', cantidad_por_presentacion='96', minimo='96',
                                   stock_objetivo='480', ubicacion='Cajonera ficticia 3',
                                   origen_abastecimiento='donacion')
        self.recibir(insumo, numero_presentaciones='2', fecha_vencimiento='2099-09-30')

        texto = self.anexo_de_inventario()
        self.assertIn('3.5 INSUMOS Y MATERIALES', texto)
        for esperado in ('INS-CAP-01', 'Puntas ficticias de pipeta', 'Material', '192 unidad', '96 unidad',
                         '480 unidad', '30/09/2099', 'Cajonera ficticia 3'):
            self.assertIn(esperado, texto)
        self.assertIn('Total: 1 artículo · bajo el mínimo: 0 · sin lotes localizables: 0', texto)

    def test_tabla_3_6_movimientos_del_periodo_trae_el_ingreso_y_el_consumo(self):
        insumo = self.crear_insumo('MOV-CAP-01', 'Alcohol ficticio de limpieza', unidad_medida='ml',
                                   cantidad_por_presentacion='1000')
        self.recibir(insumo, documento_recepcion='ACTA-MOV-FICTICIA')
        lote = LoteConsumible.objects.get(consumible=insumo)
        html = self.panel('inventario')
        consumo = [b for b in self.botones(html, 'inventario', consumible_id=insumo.pk)
                   if b.get('data-field-tipo') == 'salida'][0]
        self.guardar(self.abrir(html, 'inventario', consumo, motivo='consumo_practica', cantidad='150',
                                lote_inventario_id=str(lote.pk), abrir_presentacion='1',
                                equipo_id=str(self.equipo.pk), referencia='PRACTICA-FICTICIA-07'))

        texto = self.anexo_de_inventario()
        self.assertIn('3.6 MOVIMIENTOS DEL PERÍODO', texto)
        for esperado in ('MOV-CAP-01', 'Recepción o compra', 'Consumo en práctica o docencia', '1.000 ml', '150 ml',
                         '850 ml', lote.codigo, 'ACTA-MOV-FICTICIA', 'PRACTICA-FICTICIA-07', 'Gabriela Gestora'):
            self.assertIn(esperado, texto)
        self.assertIn('Total: 2 movimientos · ingresos: 1 · salidas: 1', texto)

    def test_sustancias_sujetas_a_control_trae_la_marca_la_autorizacion_y_el_lote(self):
        sustancia = self.crear_insumo('SUS-CAP-01', 'Acetona ficticia', clasificacion='reactivo', unidad_medida='ml',
                                      cantidad_por_presentacion='500', sustancia_controlada='true',
                                      autorizacion_control='Licencia ficticia de control 77')
        self.assertTrue(sustancia.sustancia_controlada)
        self.recibir(sustancia, fecha_vencimiento='2099-01-31', bodega='Armario ficticio con llave')
        lote = LoteConsumible.objects.get(consumible=sustancia)
        self.crear_insumo('SUS-CAP-02', 'Agua destilada ficticia', clasificacion='reactivo', unidad_medida='ml')

        ruta = reverse('gestion_reporte_unidad', args=[self.lab.slug])
        hoy = timezone.localdate()
        filtros = {'categoria_reporte': 'sustancias', 'desde': date(hoy.year, 1, 1).isoformat(),
                   'hasta': hoy.isoformat()}
        pantalla = self.client.get(ruta, filtros)
        self.assertEqual(pantalla.status_code, 200)
        pdf = self.client.get(ruta, filtros | {'formato': 'pdf'})
        self.assertEqual(pdf.status_code, 200)
        for nombre, contenido in (('pantalla', pantalla.content.decode('utf-8')), ('pdf', _texto_del_pdf(pdf.content))):
            with self.subTest(formato=nombre):
                for esperado in ('Sustancias sujetas a control', 'SUS-CAP-01', 'Acetona ficticia',
                                 'Licencia ficticia de control 77', '500 ml', lote.codigo, '31/01/2099',
                                 'Armario ficticio con llave'):
                    self.assertIn(esperado, contenido)
                self.assertNotIn('Agua destilada ficticia', contenido)

    # ---- reserva con insumos ------------------------------------------------------------------------------

    def _reserva(self, **extra):
        # Cada solicitud va en una semana distinta: el mismo equipo no admite dos reservas a la misma hora.
        self._semanas = getattr(self, '_semanas', 1) + 1
        dia = timezone.localdate() + timedelta(days=7 * self._semanas)
        dia += timedelta(days=(7 - dia.weekday()) % 7)  # El lunes siguiente: un día hábil.
        datos = {
            'unidad_id': self.lab.pk,
            'fecha_inicio': f'{dia.isoformat()}T09:00',
            'fecha_fin': f'{dia.isoformat()}T11:00',
            'horas_seleccionadas': json.dumps([9, 10]),
            'proposito': 'Docencia',
            'descripcion_proyecto': 'Reserva ficticia para comprobar la solicitud de insumos.',
            'participantes_seleccionados': '[]',
            'aceptar_terminos': 'on',
            'modalidad_servicio': 'modelo_listo',
            'unidades_seleccionadas': json.dumps([{'id': self.equipo.pk}]),
        }
        return self.client.post(reverse('crear_reserva'), datos | extra)

    def test_la_reserva_pide_un_insumo_con_existencias_y_no_se_bloquea_por_los_agotados(self):
        con_existencias = self.crear_insumo('RES-CAP-01', 'Filamento ficticio con existencias')
        agotado = self.crear_insumo('RES-CAP-02', 'Filamento ficticio agotado')
        self.recibir(con_existencias)

        # El asistente de reservas ofrece el que tiene existencias y marca el agotado como no disponible.
        pagina = self.client.get(self.lab.get_absolute_url()).content.decode('utf-8')
        entradas = {}
        for bloque in pagina.split('<input class="form-control reservation-consumable__quantity"')[1:]:
            etiqueta = bloque.split('>', 1)[0]
            for insumo in (con_existencias, agotado):
                if f'data-consumible-id="{insumo.pk}"' in etiqueta:
                    entradas[insumo.codigo] = etiqueta
        self.assertIn('data-stock-available="true"', entradas['RES-CAP-01'])
        self.assertIn('max="1000.000"', entradas['RES-CAP-01'])
        self.assertIn('data-stock-available="false"', entradas['RES-CAP-02'])

        self.client.force_login(self.solicitante)

        def pedir(insumo, cantidad):
            return self._reserva(provision_consumibles='unidad', consumibles_seleccionados=json.dumps(
                [{'id': insumo.pk, 'cantidad': cantidad, 'metodo_estimacion': 'estimacion'}]))

        # Pide 250 g del insumo recibido: la reserva se crea con su cantidad.
        respuesta = pedir(con_existencias, '250.5')
        self.assertEqual(respuesta.status_code, 200, respuesta.content.decode('utf-8'))
        reserva = Reserva.objects.get(pk=respuesta.json()['reserva_id'])
        solicitado = reserva.consumibles_solicitados.get()
        self.assertEqual((solicitado.consumible, solicitado.cantidad_solicitada),
                         (con_existencias, Decimal('250.500')))

        # Pide más de lo que hay: el mensaje dice cuánto queda.
        respuesta = pedir(con_existencias, '5000')
        self.assertEqual(respuesta.status_code, 400)
        self.assertIn('supera la existencia disponible (1000 g)', respuesta.json()['error'])

        # Pide el agotado: se le dice que lo quite y que puede reservar sin insumos.
        respuesta = pedir(agotado, '10')
        self.assertEqual(respuesta.status_code, 400)
        error = respuesta.json()['error']
        self.assertIn('Filamento ficticio agotado está agotado', error)
        self.assertIn('puede enviarse sin insumos', error)

        # Sin pedir insumos, la reserva se crea aunque haya insumos agotados en la unidad.
        respuesta = self._reserva()
        self.assertEqual(respuesta.status_code, 200, respuesta.content.decode('utf-8'))
        self.assertFalse(Reserva.objects.get(pk=respuesta.json()['reserva_id']).consumibles_solicitados.exists())

    def test_con_todo_agotado_la_reserva_sin_insumos_se_crea(self):
        self.crear_insumo('RES-CAP-03', 'Resina ficticia sin existencias')
        self.assertFalse(Consumible.objects.filter(unidad=self.lab, stock_total__gt=0).exists())
        self.client.force_login(self.solicitante)
        respuesta = self._reserva()
        self.assertEqual(respuesta.status_code, 200, respuesta.content.decode('utf-8'))
        self.assertEqual(Reserva.objects.get(pk=respuesta.json()['reserva_id']).laboratorio, self.lab)
