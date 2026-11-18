"""Dos simplificaciones que conservan la trazabilidad.

1. Un insumo sin equipos compatibles definidos se abre y se consume sin asignar equipo (las rutas por pantalla están
   en tests/integration/test_rutas_de_captura_insumos.py); con equipos compatibles, el equipo se sigue exigiendo.
2. Los traspasos de equipos: la unidad que entrega los propone en su lista de equipos, la que recibe los acepta o
   rechaza en su panel, la Dirección (con designación) los aprueba con un clic en Administración y la unidad que
   recibe registra la recepción física. Cada paso deja su auditoría; nadie aprueba su propia propuesta; un equipo con
   un traspaso en curso no admite otro ni una baja; el anexo 3 (bajas y traspasos) lo muestra.
"""
import re
from datetime import timedelta
from decimal import Decimal
from tempfile import TemporaryDirectory

from django.contrib.auth import get_user_model
from django.contrib.auth.models import Permission
from django.core.exceptions import PermissionDenied, ValidationError
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase, override_settings
from django.urls import reverse
from django.utils import timezone

from apps.core.roles import MODULOS_OPERATIVOS
from apps.directorio_unidades.models.core import Unidad
from apps.documentos.presentation.anexos_evidencia import constructor_de, contexto_del_anexo
from apps.documentos.presentation.expediente import anexos_del, construir_expediente, tramo_del_documento
from apps.formacion.models.practicas import RegistroAuditoriaUnidad
from apps.gestion_unidades.models.espacios import EspacioReservable, ResponsableUnidad
from apps.recursos.models.consumibles import Consumible, LoteConsumible
from apps.recursos.models.equipos import EquiposServicios
from apps.recursos.models.redistribucion import TraspasoEquipo
from apps.recursos.models.unidades import AliasCodigoUnidadEquipo, UnidadEquipo
from apps.recursos.presentation.traspasos import resolver_traspaso, responder_traspaso, solicitar_traspaso
from tests.integration.test_seguimiento_gobernanza import designar
from tests.integration.utiles import identificar, pdf_legible_prueba

ENTIDAD = 'recursos.TraspasoEquipo'


def _errores(respuesta):
    """Los errores que dibuja la pantalla, para leer por qué no avanzó."""
    return re.findall(r'errorlist.*?</ul>|role="alert">.*?</p>', respuesta.content.decode(), re.S) or respuesta.status_code


class ConsumoSinEquipoTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        hoy = timezone.localdate()
        cls.unidad = Unidad.objects.create(nombre='Laboratorio ficticio K2 de insumos', slug='lab-k2-insumos',
                                           dependencia='laboratorios', descripcion='Unidad ficticia.',
                                           fecha_inicio=hoy.replace(year=hoy.year - 1, day=1))
        cls.modelo = EquiposServicios.objects.create(codigo='MOD-K2-IMP', nombre='Impresora ficticia K2')
        cls.equipo = UnidadEquipo.objects.create(codigo_unidad='K2-IMP-01', equipo=cls.modelo, laboratorio=cls.unidad,
                                                 estado_unidad='disponible', activa=True)

    def lote(self, codigo):
        insumo = Consumible.objects.create(unidad=self.unidad, codigo=codigo, nombre=f'Insumo ficticio {codigo}',
                                           unidad_medida='g', cantidad_por_presentacion=Decimal('100'))
        return LoteConsumible(consumible=insumo, codigo=f'{codigo}-L1', cantidad_inicial=Decimal('100'),
                              cantidad_actual=Decimal('100'), estado='en_uso')

    def test_un_lote_de_un_insumo_sin_equipos_compatibles_queda_en_uso_sin_equipo(self):
        lote = self.lote('K2-GEN')
        self.assertFalse(lote.consumible.requiere_equipo)
        lote.full_clean()

    def test_un_lote_de_un_insumo_con_equipos_compatibles_sigue_exigiendo_el_equipo(self):
        lote = self.lote('K2-FIL')
        lote.consumible.equipos_compatibles.add(self.modelo)
        lote.consumible = Consumible.objects.get(pk=lote.consumible.pk)
        with self.assertRaises(ValidationError) as error:
            lote.full_clean()
        self.assertIn('equipo_en_uso', error.exception.message_dict)
        lote.equipo_en_uso = self.equipo
        lote.full_clean()


@override_settings(MEDICION_METAS_HABILITADA=True, MEDICION_SOLO_DEMO=False)
class TraspasoQueProponeLaUnidadTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.hoy = timezone.localdate()
        usuarios = get_user_model().objects
        inicio = cls.hoy.replace(year=cls.hoy.year - 1, day=1)
        cls.cuenta_origen = usuarios.create_user('admin.lab-k2-entrega', password='clave-ficticia',
                                                 first_name='Olga', last_name='Origen')
        cls.cuenta_destino = usuarios.create_user('admin.lab-k2-recibe', password='clave-ficticia',
                                                  first_name='Diego', last_name='Destino')
        for cuenta in (cls.cuenta_origen, cls.cuenta_destino):
            identificar(cuenta, tipo_usuario='administrativo', carrera='')
        cls.origen = Unidad.objects.create(nombre='Laboratorio ficticio K2 que entrega', slug='lab-k2-entrega',
                                           dependencia='laboratorios', descripcion='Unidad ficticia.',
                                           fecha_inicio=inicio, administrador=cls.cuenta_origen, activo=True)
        cls.destino = Unidad.objects.create(nombre='Laboratorio ficticio K2 que recibe', slug='lab-k2-recibe',
                                            dependencia='laboratorios', descripcion='Unidad ficticia.',
                                            fecha_inicio=inicio, administrador=cls.cuenta_destino, activo=True)
        cls.area = EspacioReservable.objects.create(unidad=cls.destino, codigo='K2R-AREA-MET', nombre='Metrología',
                                                    capacidad=4)
        # La Dirección: designación vigente y el permiso de aprobar traspasos en Administración.
        cls.direccion = usuarios.create_user('direccion.k2', password='clave-ficticia', is_staff=True,
                                             first_name='Dora', last_name='Dirección')
        cls.direccion.user_permissions.add(*Permission.objects.filter(
            codename__in=('aprobar_traspasoequipo', 'view_traspasoequipo', 'change_traspasoequipo')))
        designar(cls.direccion)
        modelo = EquiposServicios.objects.create(codigo='MOD-K2-BAL', nombre='Balanza ficticia K2')
        cls.equipo = UnidadEquipo.objects.create(
            codigo_unidad='K2E-BAL-01', equipo=modelo, laboratorio=cls.origen, estado_unidad='disponible', activa=True,
            codigo_bien='BIEN-K2-0001', custodio='Custodio ficticio que entrega', ubicacion_especifica='Mesa ficticia 3')

    def setUp(self):
        carpeta = TemporaryDirectory(prefix='traspasos-k2-')
        self.addCleanup(carpeta.cleanup)
        medios = override_settings(MEDIA_ROOT=carpeta.name)
        medios.enable()
        self.addCleanup(medios.disable)

    # ---- las pantallas ----------------------------------------------------------------------------------

    def panel(self, unidad):
        respuesta = self.client.get(reverse('gestion_unidad', args=[unidad.slug]),
                                    {'view': 'recursos', 'modo_recursos': 'activos'})
        self.assertEqual(respuesta.status_code, 200)
        return respuesta.content.decode()

    def proponer(self, cuenta, espera=302, **datos):
        self.client.force_login(cuenta)
        ruta = reverse('proponer_traspaso_equipo', args=[self.origen.slug, self.equipo.pk])
        respuesta = self.client.post(ruta, {'destino': self.destino.pk, 'motivo': 'necesidad',
                                            'justificacion': 'La unidad ficticia que recibe lo usará en metrología.',
                                            **datos})
        self.assertEqual(respuesta.status_code, espera, _errores(respuesta))
        return TraspasoEquipo.objects.order_by('-pk').first()

    def responder(self, cuenta, traspaso, espera=302, unidad=None, **datos):
        self.client.force_login(cuenta)
        respuesta = self.client.post(reverse('traspaso_equipo_unidad',
                                             args=[(unidad or self.destino).slug, traspaso.codigo]), datos)
        self.assertEqual(respuesta.status_code, espera, _errores(respuesta))
        traspaso.refresh_from_db()
        return respuesta

    def accion_direccion(self, accion, traspaso):
        self.client.force_login(self.direccion)
        respuesta = self.client.post(reverse('admin:recursos_traspasoequipo_changelist'),
                                     {'action': accion, '_selected_action': [traspaso.pk]}, follow=True)
        self.assertEqual(respuesta.status_code, 200)
        traspaso.refresh_from_db()
        return respuesta.content.decode()

    def auditoria(self, unidad, traspaso):
        return list(RegistroAuditoriaUnidad.objects.filter(unidad=unidad, entidad=ENTIDAD, objeto_id=str(traspaso.pk))
                    .order_by('creado_en', 'pk').values_list('accion', 'usuario__username', 'datos_anteriores__etapa',
                                                             'datos_nuevos__etapa'))

    def bajas_y_traspasos(self, unidad):
        documentos = construir_expediente(unidad, self.hoy.year, hoy=self.hoy)
        informe = next(d for d in documentos if d.exigido.codigo == 'INFORME-SEMESTRAL'
                       and tramo_del_documento(d)[0] <= self.hoy <= tramo_del_documento(d)[1])
        anexo = next(a for a in anexos_del(informe, incluir_no_aplica=True) if a.exigido.codigo == 'INVENTARIO-CORTE')
        registro = next(r for r in constructor_de('INVENTARIO-CORTE')(contexto_del_anexo(anexo, *tramo_del_documento(anexo)))
                        if r.titulo == 'Bajas y traspasos del período')
        return [str(fila) for fila in registro.filas]

    # ---- el circuito completo ---------------------------------------------------------------------------

    def test_el_traspaso_lo_propone_el_origen_lo_acepta_el_destino_lo_aprueba_la_direccion_y_lo_recibe_el_destino(self):
        # 1. La unidad que entrega lo propone desde la fila del equipo.
        self.client.force_login(self.cuenta_origen)
        ruta = reverse('proponer_traspaso_equipo', args=[self.origen.slug, self.equipo.pk])
        self.assertIn(ruta, self.panel(self.origen))
        pagina = self.client.get(ruta).content.decode()
        self.assertIn(self.destino.nombre, pagina)
        self.assertNotIn(f'<option value="{self.origen.pk}">', pagina)
        traspaso = self.proponer(self.cuenta_origen)
        self.assertEqual((traspaso.estado, traspaso.solicitado_por, traspaso.unidad_origen, traspaso.unidad_destino,
                          traspaso.entrega_nombre), ('solicitado', self.cuenta_origen, self.origen, self.destino,
                                                     'Olga Origen'))
        self.assertEqual(self.auditoria(self.origen, traspaso), [('crear', 'admin.lab-k2-entrega', '', 'propuesto')])
        # El equipo ya no ofrece otra propuesta ni admite otra ni una baja mientras siga en curso.
        self.assertNotIn(ruta, self.panel(self.origen))
        self.assertIn('no admite otro', self.client.get(ruta).content.decode())
        self.proponer(self.cuenta_origen, espera=200)
        self.assertEqual(TraspasoEquipo.objects.count(), 1)
        equipo = UnidadEquipo.objects.get(pk=self.equipo.pk)
        equipo.fecha_baja, equipo.motivo_baja = self.hoy, 'dano_irreparable'
        equipo.observacion_baja = 'Informe técnico ficticio de baja.'
        with self.assertRaisesMessage(ValidationError, traspaso.codigo):
            equipo.save()

        # La Dirección todavía no puede aprobar: falta la aceptación de la unidad que recibe.
        self.assertIn('todavía no acepta', self.accion_direccion('aprobar', traspaso))
        self.assertEqual(traspaso.estado, 'solicitado')

        # 2. La unidad que recibe lo ve en «Traspasos por recibir» y lo acepta.
        self.client.force_login(self.cuenta_destino)
        panel = self.panel(self.destino)
        self.assertIn('Traspasos por recibir', panel)
        self.assertIn(f'data-traspaso-por-recibir="{traspaso.codigo}"', panel)
        self.assertIn('Aceptar o rechazar', panel)
        self.responder(self.cuenta_destino, traspaso, accion='aceptar')
        self.assertEqual(traspaso.estado, 'solicitado')
        self.assertEqual(self.auditoria(self.destino, traspaso),
                         [('aprobar', 'admin.lab-k2-recibe', 'propuesto', 'aceptado')])

        # 3. La Dirección lo aprueba con un clic.
        self.accion_direccion('aprobar', traspaso)
        self.assertEqual((traspaso.estado, traspaso.aprobado_por), ('aprobado', self.direccion))
        self.assertIn(('aprobar', 'direccion.k2', 'aceptado', 'aprobado'), self.auditoria(self.origen, traspaso))

        # 4. La unidad que recibe registra la recepción física con su acta.
        self.client.force_login(self.cuenta_destino)
        self.assertIn('Registrar la recepción', self.panel(self.destino))
        acta = SimpleUploadedFile('acta-traspaso-k2.pdf', pdf_legible_prueba(
            'Acta ficticia de traspaso K2: entrega, recepción, custodio y estado del equipo ficticio.'),
                                  content_type='application/pdf')
        self.responder(self.cuenta_destino, traspaso, accion='recibir', fecha=self.hoy.isoformat(), area=self.area.pk,
                       custodio='Custodio ficticio que recibe', acta=acta,
                       observaciones='Llegó con su estuche ficticio.')
        self.assertEqual((traspaso.estado, traspaso.ejecutado_por, traspaso.recibe_nombre, traspaso.entrega_nombre),
                         ('ejecutado', self.cuenta_destino, 'Diego Destino', 'Olga Origen'))
        self.assertTrue(traspaso.acta_firmada.name)
        equipo = UnidadEquipo.objects.get(pk=self.equipo.pk)
        self.assertEqual((equipo.laboratorio, equipo.custodio, equipo.ubicacion_especifica, equipo.codigo_bien),
                         (self.destino, 'Custodio ficticio que recibe', '', 'BIEN-K2-0001'))
        self.assertEqual(list(equipo.espacios_asociados.all()), [self.area])
        self.assertNotEqual(equipo.codigo_unidad, 'K2E-BAL-01')
        self.assertTrue(AliasCodigoUnidadEquipo.objects.filter(codigo='K2E-BAL-01', unidad_equipo=equipo).exists())
        self.assertEqual(traspaso.equipos.get().codigo_nuevo, equipo.codigo_unidad)
        self.assertIn(('actualizar', 'admin.lab-k2-recibe', 'aprobado', 'ejecutado'),
                      self.auditoria(self.destino, traspaso))
        self.assertIn(('actualizar', 'admin.lab-k2-recibe', 'aprobado', 'ejecutado'),
                      self.auditoria(self.origen, traspaso))
        self.assertNotIn(f'data-traspaso-por-recibir="{traspaso.codigo}"', self.panel(self.destino))

        # El anexo 3 (bajas y traspasos) lo presenta en las dos unidades.
        entrega = [fila for fila in self.bajas_y_traspasos(self.origen) if traspaso.codigo in fila]
        recibe = [fila for fila in self.bajas_y_traspasos(self.destino) if traspaso.codigo in fila]
        self.assertEqual(len(entrega), 1)
        self.assertEqual(len(recibe), 1)
        self.assertIn('Traspaso entregado', entrega[0])
        self.assertIn('Traspaso recibido', recibe[0])
        self.assertIn(self.hoy.strftime('%d/%m/%Y'), recibe[0])

    # ---- los rechazos -----------------------------------------------------------------------------------

    def test_la_unidad_que_recibe_rechaza_con_motivo_y_el_equipo_queda_libre(self):
        traspaso = self.proponer(self.cuenta_origen)
        respuesta = self.responder(self.cuenta_destino, traspaso, espera=400, accion='rechazar', motivo='')
        self.assertIn('Indica por qué', respuesta.content.decode())
        self.responder(self.cuenta_destino, traspaso, accion='rechazar', motivo='No hay espacio ficticio en el área.')
        self.assertEqual(traspaso.estado, 'rechazado')
        self.assertIn('No hay espacio ficticio en el área.', traspaso.observacion_direccion)
        self.assertEqual(self.auditoria(self.destino, traspaso)[-1],
                         ('observar', 'admin.lab-k2-recibe', 'propuesto', 'rechazado'))
        self.assertEqual(UnidadEquipo.objects.get(pk=self.equipo.pk).laboratorio, self.origen)
        # Ya no está en curso: admite otra propuesta.
        self.assertNotEqual(self.proponer(self.cuenta_origen).pk, traspaso.pk)

    def test_la_direccion_rechaza_un_traspaso_aceptado(self):
        traspaso = self.proponer(self.cuenta_origen)
        self.responder(self.cuenta_destino, traspaso, accion='aceptar')
        self.accion_direccion('rechazar', traspaso)
        self.assertEqual((traspaso.estado, traspaso.aprobado_por), ('rechazado', self.direccion))
        self.assertEqual(UnidadEquipo.objects.get(pk=self.equipo.pk).laboratorio, self.origen)

    def test_solo_la_unidad_que_recibe_acepta_y_registra_la_recepcion(self):
        traspaso = self.proponer(self.cuenta_origen)
        # La unidad que entrega ve el traspaso, pero no lo acepta por la otra.
        self.client.force_login(self.cuenta_origen)
        self.assertEqual(self.client.get(reverse('traspaso_equipo_unidad', args=[self.origen.slug, traspaso.codigo]))
                         .status_code, 200)
        self.responder(self.cuenta_origen, traspaso, espera=403, unidad=self.origen, accion='aceptar')
        # Una cuenta ajena no lo ve.
        ajena = get_user_model().objects.create_user('ajena.k2', password='clave-ficticia')
        identificar(ajena, tipo_usuario='estudiante')
        self.responder(ajena, traspaso, espera=403, accion='aceptar')
        self.assertEqual(self.auditoria(self.destino, traspaso), [])
        # Sin aprobar no se recibe.
        self.responder(self.cuenta_destino, traspaso, accion='aceptar')
        respuesta = self.responder(self.cuenta_destino, traspaso, espera=400, accion='recibir',
                                   fecha=self.hoy.isoformat(), custodio='Custodio ficticio')
        self.assertIn('aprobado por la Dirección', respuesta.content.decode())
        self.assertEqual(UnidadEquipo.objects.get(pk=self.equipo.pk).laboratorio, self.origen)

    # ---- la independencia -------------------------------------------------------------------------------

    def test_quien_propone_no_acepta_en_destino_aunque_tambien_pertenezca_a_ella(self):
        ResponsableUnidad.objects.create(unidad=self.destino, usuario=self.cuenta_origen, nombre='Olga Origen',
                                         rol='coordinacion', activo=True,
                                         permisos_operativos={modulo: True for modulo in MODULOS_OPERATIVOS})
        traspaso = self.proponer(self.cuenta_origen)
        self.client.force_login(self.cuenta_origen)
        self.assertIn('lo acepta o lo rechaza otra persona', self.client.get(
            reverse('traspaso_equipo_unidad', args=[self.destino.slug, traspaso.codigo])).content.decode())
        respuesta = self.responder(self.cuenta_origen, traspaso, espera=400, accion='aceptar')
        self.assertIn('Quien propone el traspaso no puede aceptarlo', respuesta.content.decode())
        self.assertEqual(self.auditoria(self.destino, traspaso), [])
        self.responder(self.cuenta_destino, traspaso, accion='aceptar')
        self.assertEqual(self.auditoria(self.destino, traspaso)[-1][1], 'admin.lab-k2-recibe')

    def test_la_direccion_que_propuso_no_aprueba_su_propia_propuesta(self):
        traspaso = solicitar_traspaso(self.direccion, [self.equipo], self.destino, 'Reorganización ficticia.',
                                      motivo='reorganizacion')
        responder_traspaso(traspaso, self.cuenta_destino, True)
        with self.assertRaises(PermissionDenied):
            resolver_traspaso(traspaso, self.direccion, True)
        self.assertIn('Quien propuso el traspaso no puede aprobarlo', self.accion_direccion('aprobar', traspaso))
        self.assertEqual(traspaso.estado, 'solicitado')
        otra = get_user_model().objects.create_user('direccion.k2-segunda', password='clave-ficticia')
        otra.user_permissions.add(Permission.objects.get(codename='aprobar_traspasoequipo'))
        resolver_traspaso(traspaso, get_user_model().objects.get(pk=otra.pk), True)
        traspaso.refresh_from_db()
        self.assertEqual(traspaso.estado, 'aprobado')

    def test_la_recepcion_no_admite_una_fecha_futura(self):
        traspaso = self.proponer(self.cuenta_origen)
        self.responder(self.cuenta_destino, traspaso, accion='aceptar')
        self.accion_direccion('aprobar', traspaso)
        respuesta = self.responder(self.cuenta_destino, traspaso, espera=400, accion='recibir',
                                   fecha=(self.hoy + timedelta(days=2)).isoformat(), custodio='Custodio ficticio')
        self.assertIn('fecha real de la recepción', respuesta.content.decode())
        self.assertEqual(traspaso.estado, 'aprobado')
