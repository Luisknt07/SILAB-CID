"""Los laboratorios nuevos, probados como los usaría la Universidad.

El FabLab ya cubre la fabricación. Aquí se prueba lo que aquel no toca: una
sala de cómputo con licencias concurrentes y reservas sin material, un
laboratorio húmedo con reactivos por lote, áreas técnicas y prácticas
docentes, un laboratorio de emprendimiento cuya oferta son salas, mentorías
y licencias en la nube, con atención hasta las 20:00, y una planta piloto de
lácteos que produce lotes en líneas de proceso.
"""

import json
import re
from datetime import date, time, timedelta
from importlib import import_module
from pathlib import Path

from tests.historia import registro_anterior

from decimal import Decimal

from django.contrib.auth import get_user_model
from django.core.management import call_command
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from apps.reservas.models.reservas import CatalogoActividadReserva, EjemploSolicitudUnidad, GuiaActividadReserva, Reserva
from apps.recursos.models.consumibles import Consumible, LoteConsumible
from apps.gestion_unidades.models.espacios import EspacioReservable, ResponsableUnidad
from apps.laboratorios.operacion.models.fablab import FablabService, SolicitudFabricacion
from apps.recursos.models.software import SoftwareDisponible
from apps.directorio_unidades.models.core import Unidad
from apps.recursos.models.unidades import UnidadEquipo
from tests.integration.utiles import identificar, verificar_pertenencia

CLAVE_OPERATIVA = 'Laboratorio-2026'


def _dia_habil(referencia):
    """Un martes cualquiera: evita el fin de semana, que es de la administración."""
    fecha = referencia
    while fecha.weekday() >= 5:
        fecha += timedelta(days=1)
    return fecha


class BaseLaboratorioCargado(TestCase):
    """Crea la unidad vacía y la deja operativa con el cargador institucional."""

    slug = ''
    nombre = ''
    laboratorio = ''

    @classmethod
    def setUpTestData(cls):
        cls.unidad = Unidad.objects.create(
            nombre=cls.nombre,
            descripcion=f'Unidad de prueba para {cls.nombre}.',
            fecha_inicio=date(2026, 1, 1),
            dependencia='laboratorios',
            slug=cls.slug,
        )
        call_command(
            'cargar_laboratorios_institucionales',
            laboratorio=cls.laboratorio,
            password=CLAVE_OPERATIVA,
        )
        cls.unidad.refresh_from_db()
        cls.configuracion = cls.unidad.configuracion_operativa
        cls.fecha = _dia_habil(timezone.localdate() + timedelta(days=3))

        Usuario = get_user_model()
        cls.estudiante = Usuario.objects.create_user(
            username=f'estudiante.{cls.laboratorio}',
            password='Clave-Estudiante-2026',
            email=f'estudiante.{cls.laboratorio}@upec.edu.ec',
        )
        identificar(cls.estudiante, tipo_usuario='estudiante')
        verificar_pertenencia(cls.estudiante)
        cls.docente = Usuario.objects.create_user(
            username=f'docente.{cls.laboratorio}',
            password='Clave-Docente-2026',
            email=f'docente.{cls.laboratorio}@upec.edu.ec',
        )
        identificar(cls.docente, tipo_usuario='docente')
        verificar_pertenencia(cls.docente)

    def _payload(self, **extra):
        """Solicitud mínima de recursos; cada prueba añade lo suyo."""
        datos = {
            'unidad_id': self.unidad.pk,
            'fecha_inicio': f'{self.fecha.isoformat()}T09:00',
            'fecha_fin': f'{self.fecha.isoformat()}T11:00',
            'horas_seleccionadas': json.dumps([9, 10]),
            'proposito': 'Investigación',
            'proposito_codigo': 'investigacion_innovacion',
            'subtipo_actividad': 'proyecto_investigacion',
            'alcance_beneficiario': 'perfil_solicitante',
            'vinculacion_actividad': 'manual',
            'referencia_actividad': 'Prueba funcional del laboratorio',
            'descripcion_proyecto': 'Validación funcional de la unidad recién cargada.',
            'participantes_seleccionados': '[]',
            'aceptar_terminos': 'on',
            'tipo_solicitud': 'recursos',
            'provision_consumibles': 'ninguno',
            'unidades_seleccionadas': '[]',
        }
        datos.update(extra)
        return datos

    def _unidad_equipo(self, codigo):
        return UnidadEquipo.objects.get(codigo_unidad=codigo)

    def _seleccion(self, *codigos):
        return json.dumps([
            {
                'id': self._unidad_equipo(codigo).pk,
                'codigo': codigo,
                'equipo_nombre': self._unidad_equipo(codigo).equipo.nombre,
            }
            for codigo in codigos
        ])


class LaboratorioIADatosTests(BaseLaboratorioCargado):
    """Sala de cómputo: licencias concurrentes, cupo y reservas sin material."""

    slug = 'laboratorio-inteligencia-artificial-ciencia-datos'
    nombre = 'Laboratorio IA y Ciencia de Datos'
    laboratorio = 'ia'

    def test_la_carga_deja_el_laboratorio_listo_para_reservar(self):
        self.assertEqual(UnidadEquipo.objects.filter(laboratorio=self.unidad).count(), 9)
        self.assertEqual(EspacioReservable.objects.filter(unidad=self.unidad).count(), 2)
        self.assertEqual(FablabService.objects.filter(unidad=self.unidad).count(), 2)
        self.assertEqual(Consumible.objects.filter(unidad=self.unidad).count(), 3)

        # El horario declarado es el que verá quien reserve.
        self.assertEqual(self.configuracion.hora_apertura_atencion, time(8, 0))
        self.assertEqual(self.configuracion.hora_cierre_atencion, time(18, 0))
        # Una sala de cómputo corre ensayos, no fabrica piezas.
        self.assertEqual(self.configuracion.unidad_de_trabajo, 'ensayos')
        self.assertEqual(self.configuracion.palabras_trabajo, ('ensayo', 'ensayos'))
        pagina = self.client.get(self.unidad.get_absolute_url())
        self.assertContains(pagina, 'data-trabajo-plural="ensayos"')
        self.assertContains(pagina, 'Cantidad por ensayo')

        # Las licencias son concurrentes y el entorno propio viene incluido.
        matlab = SoftwareDisponible.objects.get(unidad=self.unidad, codigo='IA-SW-MATLAB')
        entorno = SoftwareDisponible.objects.get(unidad=self.unidad, codigo='IA-SW-PYTHON')
        self.assertEqual(matlab.licencias_totales, 5)
        self.assertEqual(matlab.uso_en_equipo, 'opcional')
        self.assertEqual(entorno.uso_en_equipo, 'obligatorio')

        # El laboratorio tiene quién lo atienda, con cuenta y permisos.
        cuentas = ResponsableUnidad.objects.filter(
            unidad=self.unidad, usuario__isnull=False, activo=True
        )
        self.assertEqual(cuentas.count(), 2)
        coordinacion = cuentas.get(rol='coordinacion')
        self.assertTrue(coordinacion.permisos_operativos['reservas'])
        self.assertTrue(coordinacion.recibe_reservas)

        # Los tres artículos son de uso general: ninguno cuelga de un equipo.
        marcador = Consumible.objects.get(codigo='IA-MAT-MARCADOR')
        self.assertFalse(marcador.equipos_compatibles.exists())

    def test_una_practica_reserva_puesto_licencia_y_sala(self):
        self.client.force_login(self.estudiante)
        estacion = self._unidad_equipo('IA-UNIT-GPU-01')
        sala = EspacioReservable.objects.get(codigo='IA-SALA-COMPUTO')
        matlab = SoftwareDisponible.objects.get(codigo='IA-SW-MATLAB')

        respuesta = self.client.post(reverse('crear_reserva'), self._payload(
            unidades_seleccionadas=self._seleccion('IA-UNIT-GPU-01'),
            espacios_solicitados=[str(sala.pk)],
            software_solicitado=[str(matlab.pk)],
            incluye_espacio='1',
        ))

        self.assertEqual(respuesta.status_code, 200, respuesta.content)
        reserva = Reserva.objects.get(pk=respuesta.json()['reserva_id'])
        self.assertEqual(reserva.laboratorio, self.unidad)
        # El entorno del laboratorio viene incluido con el puesto; MATLAB se eligió.
        solicitado = set(reserva.software_solicitado.values_list('codigo', flat=True))
        self.assertEqual(solicitado, {'IA-SW-MATLAB', 'IA-SW-PYTHON'})
        self.assertIn(matlab.codigo, solicitado)
        self.assertEqual(list(reserva.espacios_solicitados.all()), [sala])
        self.assertIn(estacion.codigo_unidad, reserva.unidades_seleccionadas)
        # Una sala de cómputo no consume inventario.
        self.assertFalse(reserva.consumibles_solicitados.exists())

    def test_las_licencias_concurrentes_limitan_la_ultima_reserva(self):
        """SPSS tiene tres licencias: la cuarta persona a la misma hora no entra."""
        spss = SoftwareDisponible.objects.get(codigo='IA-SW-SPSS')
        sala = EspacioReservable.objects.get(codigo='IA-SALA-COMPUTO')
        Usuario = get_user_model()
        puestos = ['IA-UNIT-ETQ-01', 'IA-UNIT-ETQ-02', 'IA-UNIT-ETQ-03', 'IA-UNIT-ETQ-04']
        for numero, codigo in enumerate(puestos, start=1):
            usuario = Usuario.objects.create_user(
                username=f'analista{numero}',
                password='Clave-Analista-2026',
                email=f'analista{numero}@upec.edu.ec',
            )
            identificar(usuario, tipo_usuario='docente')
            self.client.force_login(usuario)
            respuesta = self.client.post(reverse('crear_reserva'), self._payload(
                unidades_seleccionadas=self._seleccion(codigo),
                software_solicitado=[str(spss.pk)],
                espacios_solicitados=[str(sala.pk)],
                incluye_espacio='1',
            ))
            if numero <= spss.licencias_totales:
                self.assertEqual(respuesta.status_code, 200, respuesta.content)
            else:
                self.assertEqual(respuesta.status_code, 400, respuesta.content)
                self.assertIn(
                    'no quedan accesos concurrentes',
                    respuesta.json()['error'].lower(),
                )

    def test_la_sala_de_analitica_se_reserva_sola(self):
        """Una sala de uso general no exige equipo ni software."""
        self.client.force_login(self.docente)
        sala = EspacioReservable.objects.get(codigo='IA-SALA-ANALITICA')

        respuesta = self.client.post(reverse('crear_reserva'), self._payload(
            espacios_solicitados=[str(sala.pk)],
            incluye_espacio='1',
        ))

        self.assertEqual(respuesta.status_code, 200, respuesta.content)
        reserva = Reserva.objects.get(pk=respuesta.json()['reserva_id'])
        self.assertEqual(list(reserva.espacios_solicitados.all()), [sala])
        self.assertFalse(reserva.software_solicitado.exists())

    def test_fuera_del_horario_declarado_no_se_reserva(self):
        """Este laboratorio atiende hasta las 18:00 y no antes de las 08:00."""
        self.client.force_login(self.estudiante)
        tarde = self.client.post(reverse('crear_reserva'), self._payload(
            fecha_inicio=f'{self.fecha.isoformat()}T18:00',
            fecha_fin=f'{self.fecha.isoformat()}T20:00',
            horas_seleccionadas=json.dumps([18, 19]),
            unidades_seleccionadas=self._seleccion('IA-UNIT-GPU-01'),
        ))
        self.assertEqual(tarde.status_code, 400)
        self.assertIn('18:00', tarde.json()['error'])

        temprano = self.client.post(reverse('crear_reserva'), self._payload(
            fecha_inicio=f'{self.fecha.isoformat()}T07:00',
            fecha_fin=f'{self.fecha.isoformat()}T09:00',
            horas_seleccionadas=json.dumps([7, 8]),
            unidades_seleccionadas=self._seleccion('IA-UNIT-GPU-01'),
        ))
        self.assertEqual(temprano.status_code, 400)
        self.assertIn('08:00', temprano.json()['error'])


class LaboratorioBiotecnologiaTests(BaseLaboratorioCargado):
    """Laboratorio húmedo: reactivos por lote, áreas técnicas y docencia."""

    slug = 'laboratorio-microbiologia-biotecnologia-aplicada'
    nombre = 'Laboratorio de Biotecnología Aplicada'
    laboratorio = 'biotecnologia'

    def test_la_carga_deja_el_inventario_con_lotes_y_vencimiento(self):
        # Siete equipos principales y dos auxiliares: la balanza y el pH-metro.
        self.assertEqual(UnidadEquipo.objects.filter(laboratorio=self.unidad).count(), 9)
        areas = EspacioReservable.objects.filter(unidad=self.unidad)
        self.assertEqual(areas.count(), 3)
        self.assertEqual(
            set(areas.values_list('politica_reserva', flat=True)),
            {'tecnico', 'mixto'},
        )

        # Los reactivos se manejan por lote: vencen y se abren en un equipo.
        lotes = LoteConsumible.objects.filter(consumible__unidad=self.unidad)
        self.assertEqual(lotes.count(), 9)
        self.assertTrue(all(lote.fecha_vencimiento for lote in lotes))
        abiertos = lotes.filter(estado='en_uso')
        self.assertEqual(abiertos.count(), 4)
        self.assertTrue(all(lote.equipo_en_uso_id for lote in abiertos))

        # El horario abre antes que el de una sala de cómputo.
        self.assertEqual(self.configuracion.hora_apertura_atencion, time(7, 0))
        self.assertEqual(self.configuracion.hora_cierre_atencion, time(18, 0))
        # Un laboratorio húmedo procesa muestras: el asistente lo dice así.
        self.assertEqual(self.configuracion.palabras_trabajo, ('muestra', 'muestras'))
        pagina = self.client.get(self.unidad.get_absolute_url())
        self.assertContains(pagina, 'Cantidad por muestra')
        self.assertContains(pagina, 'Número de muestras')

    def test_una_practica_docente_pide_area_equipo_y_reactivos(self):
        self.client.force_login(self.docente)
        actividad = CatalogoActividadReserva.objects.get(codigo='BIO-ACT-MOLECULAR')
        # Toda práctica docente del catálogo exige su guía aprobada y vigente.
        GuiaActividadReserva.objects.create(
            actividad=actividad,
            titulo='Guía de la práctica de biología molecular',
            codigo_guia='BIO-GUIA-MOL-01',
            numero_version=1,
            es_estructurada=True,
            es_vigente=True,
            contenido={'laboratorio': self.unidad.nombre},
            visibilidad='unidad',
            estado_publicacion='publicada',
            subido_por=self.docente,
        )
        area = EspacioReservable.objects.get(codigo='BIO-AREA-MOLECULAR')
        agarosa = Consumible.objects.get(codigo='BIO-REA-AGAROSA')
        puntas = Consumible.objects.get(codigo='BIO-MAT-PUNTAS')

        respuesta = self.client.post(reverse('crear_reserva'), self._payload(
            proposito='Docencia',
            proposito_codigo='docencia_practica',
            subtipo_actividad='practica_curricular',
            vinculacion_actividad='catalogo',
            actividad_catalogo=str(actividad.pk),
            origen_programacion='programada',
            referencia_actividad='',
            unidades_seleccionadas=self._seleccion('BIO-UNIT-PCR-01'),
            espacios_solicitados=[str(area.pk)],
            incluye_espacio='1',
            provision_consumibles='unidad',
            # Ocho muestras: el asistente ya envía el consumo de la sesión.
            piezas_por_sesion='8',
            consumibles_seleccionados=json.dumps([
                {'id': agarosa.pk, 'cantidad': '8.000', 'metodo_estimacion': 'estimacion'},
                {'id': puntas.pk, 'cantidad': '96.000', 'metodo_estimacion': 'estimacion'},
            ]),
        ))

        self.assertEqual(respuesta.status_code, 200, respuesta.content)
        reserva = Reserva.objects.get(pk=respuesta.json()['reserva_id'])
        self.assertEqual(reserva.actividad_catalogo, actividad)
        self.assertEqual(reserva.cantidad_piezas, 8)
        pedidos = {
            item.consumible.codigo: item.cantidad_solicitada
            for item in reserva.consumibles_solicitados.all()
        }
        self.assertEqual(pedidos['BIO-REA-AGAROSA'], Decimal('8.000'))
        self.assertEqual(pedidos['BIO-MAT-PUNTAS'], Decimal('96.000'))

    def test_el_servicio_de_extraccion_cobra_segun_el_segmento(self):
        self.client.force_login(self.estudiante)
        servicio = FablabService.objects.get(code='BIO-SRV-EXTRACCION')
        kit = Consumible.objects.get(codigo='BIO-REA-KIT-ADN')
        entrega = _dia_habil(self.fecha + timedelta(days=4))

        respuesta = self.client.post(reverse('crear_reserva'), self._payload(
            tipo_solicitud='servicio',
            modalidad_servicio='modelo_listo',
            servicios_solicitados=[str(servicio.pk)],
            cantidad_piezas='4',
            urgencia_servicio='normal',
            detalle_trabajo='Cuatro muestras de suelo del proyecto de titulación.',
            fecha_entrega_prevista=entrega.isoformat(),
            materiales_seleccionados=json.dumps([kit.pk]),
            consumibles_servicio=json.dumps({str(kit.pk): '4.000'}),
            cotizacion_aceptada='true',
            metodo_pago='transferencia',
        ))

        self.assertEqual(respuesta.status_code, 200, respuesta.content)
        reserva = Reserva.objects.get(pk=respuesta.json()['reserva_id'])
        self.assertEqual(reserva.tipo_solicitud, 'servicio')
        self.assertEqual(reserva.cantidad_piezas, 4)
        # El servicio suma sus materiales obligatorios aunque se marque uno solo.
        pedidos = {
            item.consumible.codigo: item.cantidad_solicitada
            for item in reserva.consumibles_solicitados.all()
        }
        self.assertEqual(pedidos['BIO-REA-KIT-ADN'], Decimal('4.000'))
        self.assertIn('BIO-MAT-PUNTAS', pedidos)
        self.assertIn('BIO-MAT-TUBOS', pedidos)
        # El servicio deja su orden de trabajo, que es donde vive el comprobante.
        self.assertTrue(SolicitudFabricacion.objects.filter(reserva=reserva).exists())
        # Una estudiante recibe el descuento de su segmento sobre lo que se cobra.
        self.assertGreater(reserva.costo_estimado, Decimal('0'))
        conceptos = reserva.desglose_cotizacion['conceptos'][0]['componentes']
        descuentos = [c for c in conceptos if c.get('aporte_institucional')]
        self.assertTrue(descuentos)

    def test_el_cierre_descuenta_del_lote_abierto(self):
        """La atención se cierra desde el panel y el inventario lo refleja."""
        self.client.force_login(self.docente)
        area = EspacioReservable.objects.get(codigo='BIO-AREA-MOLECULAR')
        agarosa = Consumible.objects.get(codigo='BIO-REA-AGAROSA')
        lote = LoteConsumible.objects.filter(consumible=agarosa).first()
        lote.estado = 'en_uso'
        lote.equipo_en_uso = self._unidad_equipo('BIO-UNIT-PCR-01')
        lote.save(update_fields=['estado', 'equipo_en_uso'])
        saldo_inicial = lote.cantidad_actual

        ayer = _dia_habil(timezone.localdate() - timedelta(days=4))
        creacion = self.client.post(reverse('crear_reserva'), self._payload(
            fecha_inicio=f'{ayer.isoformat()}T09:00',
            fecha_fin=f'{ayer.isoformat()}T11:00',
            unidades_seleccionadas=self._seleccion('BIO-UNIT-PCR-01'),
            espacios_solicitados=[str(area.pk)],
            incluye_espacio='1',
            provision_consumibles='unidad',
            piezas_por_sesion='2',
            consumibles_seleccionados=json.dumps([
                {'id': agarosa.pk, 'cantidad': '10.000', 'metodo_estimacion': 'estimacion'},
            ]),
        ))
        self.assertEqual(creacion.status_code, 200, creacion.content)
        reserva = Reserva.objects.get(pk=creacion.json()['reserva_id'])
        reserva.estado = 'confirmada'
        reserva.save(update_fields=['estado'])

        coordinacion = ResponsableUnidad.objects.get(
            unidad=self.unidad, rol='coordinacion', usuario__isnull=False
        )
        self.client.force_login(coordinacion.usuario)
        pedido = reserva.consumibles_solicitados.get()
        cierre = self.client.post(
            reverse('gestion_reserva_accion', args=[self.unidad.slug, reserva.pk]),
            {
                'accion': 'completar',
                'ejecucion_registrada': '1',
                'participantes_seleccionados': '[]',
                'asistencia_solicitante': 'asistio',
                'ejecucion_hora_inicio': '09:00',
                'ejecucion_hora_fin': '11:00',
                'ejecucion_asistentes_total': '1',
                'ejecucion_piezas': '2',
                'ejecucion_cumplimiento': 'si',
                'ejecucion_equipos_ids': [str(self._unidad_equipo('BIO-UNIT-PCR-01').pk)],
                'ejecucion_consumibles_json': json.dumps([{
                    'reserva_consumible_id': pedido.pk,
                    'consumida': '9',
                    'desperdiciada': '1',
                    'lote_id': lote.pk,
                    'equipo_id': self._unidad_equipo('BIO-UNIT-PCR-01').pk,
                    'motivo_desperdicio': 'desperdicio_calidad',
                    'piezas': 2,
                    'modo_cantidad': 'distintas',
                    'detalle_piezas': ['5', '4'],
                }]),
                'ejecucion_observaciones': 'Gel preparado y documentado sin novedad.',
            },
        )

        self.assertEqual(cierre.status_code, 200, cierre.content)
        reserva.refresh_from_db()
        lote.refresh_from_db()
        self.assertEqual(reserva.estado, 'completada')
        self.assertEqual(lote.cantidad_actual, saldo_inicial - Decimal('10'))
        consumo = reserva.detalle_ejecucion['consumibles'][0]
        self.assertEqual(consumo['detalle_piezas'], ['5.000', '4.000'])
        self.assertEqual(reserva.detalle_ejecucion['piezas_producidas'], 2)

    def test_a_las_siete_se_reserva_porque_este_laboratorio_abre_antes(self):
        self.client.force_login(self.docente)
        area = EspacioReservable.objects.get(codigo='BIO-MESON-PREPARACION')

        respuesta = self.client.post(reverse('crear_reserva'), self._payload(
            fecha_inicio=f'{self.fecha.isoformat()}T07:00',
            fecha_fin=f'{self.fecha.isoformat()}T09:00',
            horas_seleccionadas=json.dumps([7, 8]),
            espacios_solicitados=[str(area.pk)],
            incluye_espacio='1',
        ))

        self.assertEqual(respuesta.status_code, 200, respuesta.content)
        reserva = Reserva.objects.get(pk=respuesta.json()['reserva_id'])
        self.assertEqual(reserva.hora_inicio, time(7, 0))


class LaboratorioEmprendimientoTests(BaseLaboratorioCargado):
    """Carreras administrativas: salas, mentoría y jornada hasta las 20:00."""

    slug = 'laboratorio-emprendimiento-innovacion-empresarial'
    nombre = 'Laboratorio de Emprendimiento e Innovación Empresarial'
    laboratorio = 'emprendimiento'

    def test_la_carga_crea_la_unidad_y_la_deja_lista_para_reservar(self):
        self.assertEqual(UnidadEquipo.objects.filter(laboratorio=self.unidad).count(), 12)
        self.assertEqual(EspacioReservable.objects.filter(unidad=self.unidad).count(), 4)
        self.assertEqual(FablabService.objects.filter(unidad=self.unidad).count(), 4)
        self.assertEqual(Consumible.objects.filter(unidad=self.unidad).count(), 6)

        # Atiende en jornada extendida, que es lo suyo: sus usuarios trabajan.
        self.assertEqual(self.configuracion.hora_apertura_atencion, time(8, 0))
        self.assertEqual(self.configuracion.hora_cierre_atencion, time(20, 0))
        # Un emprendimiento no fabrica piezas ni procesa muestras: arma prototipos.
        self.assertEqual(self.configuracion.unidad_de_trabajo, 'prototipos')
        self.assertEqual(self.configuracion.palabras_trabajo, ('prototipo', 'prototipos'))
        pagina = self.client.get(self.unidad.get_absolute_url())
        self.assertContains(pagina, 'data-trabajo-plural="prototipos"')
        self.assertContains(pagina, 'Cantidad por prototipo')

        # La oferta principal son espacios, y uno de ellos es una cabina.
        cabina = EspacioReservable.objects.get(codigo='EMP-CABINA-PITCH')
        self.assertEqual(cabina.tipo, 'cabina')
        self.assertTrue(cabina.reservable)

        # El material de la impresora cuelga de ella; el de taller no.
        papel = Consumible.objects.get(codigo='EMP-MAT-PAPEL-A1')
        canvas = Consumible.objects.get(codigo='EMP-MAT-CANVAS')
        self.assertTrue(papel.equipos_compatibles.exists())
        self.assertFalse(canvas.equipos_compatibles.exists())

        # El papel llega en rollos y no vence; la tinta sí.
        rollo = LoteConsumible.objects.get(codigo='EMP-PAPEL-R1')
        tinta = LoteConsumible.objects.get(codigo='EMP-TINTA-C1')
        self.assertIsNone(rollo.fecha_vencimiento)
        self.assertIsNotNone(tinta.fecha_vencimiento)

        # El laboratorio tiene quién lo atienda desde su propio panel.
        cuentas = ResponsableUnidad.objects.filter(
            unidad=self.unidad, usuario__isnull=False, activo=True
        )
        self.assertEqual(cuentas.count(), 2)
        self.assertTrue(cuentas.get(rol='coordinacion').permisos_operativos['reservas'])

    def test_la_sala_de_coworking_se_reserva_sola(self):
        """Un equipo emprendedor solo necesita la mesa: ni máquina ni programa."""
        self.client.force_login(self.estudiante)
        sala = EspacioReservable.objects.get(codigo='EMP-SALA-COWORK')

        respuesta = self.client.post(reverse('crear_reserva'), self._payload(
            espacios_solicitados=[str(sala.pk)],
            incluye_espacio='1',
        ))

        self.assertEqual(respuesta.status_code, 200, respuesta.content)
        reserva = Reserva.objects.get(pk=respuesta.json()['reserva_id'])
        self.assertEqual(list(reserva.espacios_solicitados.all()), [sala])
        self.assertFalse(reserva.software_solicitado.exists())
        self.assertFalse(reserva.consumibles_solicitados.exists())

    def test_a_las_diecinueve_se_reserva_y_a_las_veinte_ya_no(self):
        """Este laboratorio cierra a las 20:00, no a las 18:00 del resto."""
        self.client.force_login(self.estudiante)
        cabina = EspacioReservable.objects.get(codigo='EMP-CABINA-PITCH')

        tarde = self.client.post(reverse('crear_reserva'), self._payload(
            fecha_inicio=f'{self.fecha.isoformat()}T18:00',
            fecha_fin=f'{self.fecha.isoformat()}T20:00',
            horas_seleccionadas=json.dumps([18, 19]),
            espacios_solicitados=[str(cabina.pk)],
            incluye_espacio='1',
        ))
        self.assertEqual(tarde.status_code, 200, tarde.content)
        self.assertEqual(
            Reserva.objects.get(pk=tarde.json()['reserva_id']).hora_inicio,
            time(18, 0),
        )

        pasada = self.client.post(reverse('crear_reserva'), self._payload(
            fecha_inicio=f'{self.fecha.isoformat()}T20:00',
            fecha_fin=f'{self.fecha.isoformat()}T21:00',
            horas_seleccionadas=json.dumps([20]),
            espacios_solicitados=[str(cabina.pk)],
            incluye_espacio='1',
        ))
        self.assertEqual(pasada.status_code, 400)
        self.assertIn('20:00', pasada.json()['error'])

    def test_los_tres_accesos_a_la_plataforma_de_encuestas_se_agotan(self):
        """La licencia en la nube tiene tres accesos: el cuarto equipo espera."""
        encuestas = SoftwareDisponible.objects.get(codigo='EMP-SW-ENCUESTAS')
        sala = EspacioReservable.objects.get(codigo='EMP-SALA-COWORK')
        Usuario = get_user_model()
        for numero in range(1, 5):
            usuario = Usuario.objects.create_user(
                username=f'emprendedor{numero}',
                password='Clave-Emprende-2026',
                email=f'emprendedor{numero}@upec.edu.ec',
            )
            identificar(usuario, tipo_usuario='estudiante')
            self.client.force_login(usuario)
            respuesta = self.client.post(reverse('crear_reserva'), self._payload(
                espacios_solicitados=[str(sala.pk)],
                incluye_espacio='1',
                software_solicitado=[str(encuestas.pk)],
            ))
            if numero <= encuestas.licencias_totales:
                self.assertEqual(respuesta.status_code, 200, respuesta.content)
            else:
                self.assertEqual(respuesta.status_code, 400)
                self.assertIn('concurrentes', respuesta.json()['error'])

    def test_la_mentoria_no_le_cuesta_nada_a_quien_la_pide(self):
        """Una asesoría es tiempo de una persona: la Universidad lo asume."""
        self.client.force_login(self.estudiante)
        servicio = FablabService.objects.get(code='EMP-SRV-MENTORIA')
        entrega = _dia_habil(self.fecha + timedelta(days=4))

        respuesta = self.client.post(reverse('crear_reserva'), self._payload(
            tipo_solicitud='servicio',
            modalidad_servicio='modelo_listo',
            servicios_solicitados=[str(servicio.pk)],
            cantidad_piezas='1',
            urgencia_servicio='normal',
            detalle_trabajo='Revisión del modelo de negocio de una tienda de abarrotes.',
            fecha_entrega_prevista=entrega.isoformat(),
            materiales_seleccionados='[]',
            consumibles_servicio='{}',
            cotizacion_aceptada='true',
            metodo_pago='transferencia',
        ))

        self.assertEqual(respuesta.status_code, 200, respuesta.content)
        reserva = Reserva.objects.get(pk=respuesta.json()['reserva_id'])
        self.assertEqual(reserva.tipo_solicitud, 'servicio')
        self.assertFalse(reserva.consumibles_solicitados.exists())
        # Aun sin material, la asesoría deja su orden de trabajo y su cotización.
        self.assertTrue(SolicitudFabricacion.objects.filter(reserva=reserva).exists())
        # La hora del mentor se cotiza, pero como aporte de la Universidad.
        self.assertEqual(reserva.costo_estimado, Decimal('0.00'))
        componentes = reserva.desglose_cotizacion['conceptos'][0]['componentes']
        mano_obra = next(c for c in componentes if c['clave'] == 'mano_obra')
        self.assertEqual(mano_obra['valor'], '16.00')
        self.assertFalse(mano_obra['cobrado'])
        self.assertEqual(mano_obra['aporte_institucional'], '16.00')
        self.assertEqual(mano_obra['valor_usuario'], '0.00')

    def test_una_licencia_del_navegador_no_exige_equipo(self):
        """La plataforma de encuestas no vive en ninguna máquina del laboratorio."""
        self.client.force_login(self.estudiante)
        encuestas = SoftwareDisponible.objects.get(codigo='EMP-SW-ENCUESTAS')
        self.assertEqual(encuestas.tipo_acceso, 'remoto')
        self.assertFalse(encuestas.equipos_instalados.exists())

        sala = EspacioReservable.objects.get(codigo='EMP-SALA-COWORK')

        respuesta = self.client.post(reverse('crear_reserva'), self._payload(
            espacios_solicitados=[str(sala.pk)],
            incluye_espacio='1',
            software_solicitado=[str(encuestas.pk)],
        ))

        self.assertEqual(respuesta.status_code, 200, respuesta.content)
        reserva = Reserva.objects.get(pk=respuesta.json()['reserva_id'])
        self.assertEqual(list(reserva.software_solicitado.all()), [encuestas])
        # Sin ninguna máquina reservada: eso es lo que antes quedaba bloqueado.
        self.assertEqual(json.loads(reserva.unidades_seleccionadas or '[]'), [])

    def test_el_simulador_instalado_si_exige_su_equipo(self):
        """El que sí vive en el portátil obliga a reservarlo."""
        self.client.force_login(self.estudiante)
        simulador = SoftwareDisponible.objects.get(codigo='EMP-SW-FINANZAS')

        sala = EspacioReservable.objects.get(codigo='EMP-SALA-COWORK')

        respuesta = self.client.post(reverse('crear_reserva'), self._payload(
            espacios_solicitados=[str(sala.pk)],
            incluye_espacio='1',
            software_solicitado=[str(simulador.pk)],
        ))

        self.assertEqual(respuesta.status_code, 400)
        self.assertIn(simulador.nombre, respuesta.json()['error'])

    def test_el_cierre_reparte_el_papel_entre_los_prototipos(self):
        """Tres tableros impresos, cada uno con su consumo declarado."""
        self.client.force_login(self.docente)
        area = EspacioReservable.objects.get(codigo='EMP-AREA-PROTOTIPO')
        papel = Consumible.objects.get(codigo='EMP-MAT-PAPEL-A1')
        rollo = LoteConsumible.objects.get(codigo='EMP-PAPEL-R1')
        saldo_inicial = rollo.cantidad_actual

        ayer = _dia_habil(timezone.localdate() - timedelta(days=4))
        creacion = self.client.post(reverse('crear_reserva'), self._payload(
            fecha_inicio=f'{ayer.isoformat()}T09:00',
            fecha_fin=f'{ayer.isoformat()}T11:00',
            unidades_seleccionadas=self._seleccion('EMP-UNIT-PLOT-01'),
            espacios_solicitados=[str(area.pk)],
            incluye_espacio='1',
            provision_consumibles='unidad',
            piezas_por_sesion='3',
            consumibles_seleccionados=json.dumps([
                {'id': papel.pk, 'cantidad': '3.000', 'metodo_estimacion': 'estimacion'},
            ]),
        ))
        self.assertEqual(creacion.status_code, 200, creacion.content)
        reserva = Reserva.objects.get(pk=creacion.json()['reserva_id'])
        self.assertEqual(reserva.cantidad_piezas, 3)
        reserva.estado = 'confirmada'
        reserva.save(update_fields=['estado'])

        coordinacion = ResponsableUnidad.objects.get(
            unidad=self.unidad, rol='coordinacion', usuario__isnull=False
        )
        self.client.force_login(coordinacion.usuario)
        pedido = reserva.consumibles_solicitados.get()
        cierre = self.client.post(
            reverse('gestion_reserva_accion', args=[self.unidad.slug, reserva.pk]),
            {
                'accion': 'completar',
                'ejecucion_registrada': '1',
                'participantes_seleccionados': '[]',
                'asistencia_solicitante': 'asistio',
                'ejecucion_hora_inicio': '09:00',
                'ejecucion_hora_fin': '11:00',
                'ejecucion_asistentes_total': '3',
                'ejecucion_piezas': '3',
                'ejecucion_cumplimiento': 'si',
                'ejecucion_equipos_ids': [str(self._unidad_equipo('EMP-UNIT-PLOT-01').pk)],
                'ejecucion_consumibles_json': json.dumps([{
                    'reserva_consumible_id': pedido.pk,
                    'consumida': '2.8',
                    'desperdiciada': '0.2',
                    'lote_id': rollo.pk,
                    'equipo_id': self._unidad_equipo('EMP-UNIT-PLOT-01').pk,
                    'motivo_desperdicio': 'desperdicio_calidad',
                    'piezas': 3,
                    'modo_cantidad': 'distintas',
                    'detalle_piezas': ['1', '0.9', '0.9'],
                }]),
                'ejecucion_observaciones': 'Tres tableros impresos; uno se repitió por color.',
            },
        )

        self.assertEqual(cierre.status_code, 200, cierre.content)
        reserva.refresh_from_db()
        rollo.refresh_from_db()
        self.assertEqual(reserva.estado, 'completada')
        self.assertEqual(rollo.cantidad_actual, saldo_inicial - Decimal('3'))
        consumo = reserva.detalle_ejecucion['consumibles'][0]
        self.assertEqual(consumo['detalle_piezas'], ['1.000', '0.900', '0.900'])
        self.assertEqual(reserva.detalle_ejecucion['piezas_producidas'], 3)


class PlantaPilotoLacteosTests(BaseLaboratorioCargado):
    """La primera planta: lotes, líneas de proceso, leche con tres días de vida."""

    slug = 'planta-piloto-lacteos'
    nombre = 'Planta Piloto de Lácteos'
    laboratorio = 'lacteos'

    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()
        # La unidad nace del cargador con su ficha de planta piloto; la base
        # de prueba la creó como laboratorio y el cargador respeta lo que
        # existe, así que aquí se corrige a mano lo que en la vida real trae
        # la ficha institucional.
        cls.unidad.dependencia = 'plantas_piloto'
        cls.unidad.clasificacion_funcional = 'planta_piloto'
        cls.unidad.save(update_fields=['dependencia', 'clasificacion_funcional'])

    def test_la_carga_deja_la_planta_lista_para_producir(self):
        self.assertEqual(UnidadEquipo.objects.filter(laboratorio=self.unidad).count(), 19)
        self.assertEqual(EspacioReservable.objects.filter(unidad=self.unidad).count(), 7)
        self.assertEqual(FablabService.objects.filter(unidad=self.unidad).count(), 4)
        self.assertEqual(Consumible.objects.filter(unidad=self.unidad).count(), 35)

        # La leche llega de madrugada: la planta abre a las 07:00 y cierra a las 17:00.
        self.assertEqual(self.configuracion.hora_apertura_atencion, time(7, 0))
        self.assertEqual(self.configuracion.hora_cierre_atencion, time(17, 0))
        # Una planta produce lotes, en masculino.
        self.assertEqual(self.configuracion.unidad_de_trabajo, 'lotes')
        self.assertEqual(self.configuracion.formas_trabajo['cuantos'], 'cuántos')
        pagina = self.client.get(self.unidad.get_absolute_url())
        self.assertEqual(pagina.status_code, 200)
        self.assertIn('/planta-piloto/', self.unidad.get_absolute_url())
        self.assertContains(pagina, 'data-trabajo-plural="lotes"')
        self.assertContains(pagina, '¿Cuántos lotes harás en este equipo?')
        # Los espacios de una planta tienen su propio tipo.
        self.assertContains(pagina, 'Línea de proceso')
        self.assertContains(pagina, 'Cámara de frío o almacén')
        # El inventario distingue todo lo que fluye por una planta.
        for clase in ('insumo', 'reactivo', 'material', 'empaque', 'proteccion', 'limpieza'):
            with self.subTest(clase=clase):
                self.assertContains(pagina, f'data-inventory-type="{clase}"')
        # La leche cruda vence a los tres días; el cuajo, al año.
        leche = LoteConsumible.objects.get(codigo='LAC-LECHE-L1')
        self.assertEqual(leche.fecha_vencimiento, timezone.localdate() + timedelta(days=3))
        self.assertEqual(leche.equipo_en_uso.codigo_unidad, 'LAC-EQP-TANQ-01')

    def test_los_auxiliares_acompanan_a_la_linea_y_no_se_reservan(self):
        respuesta = self.client.get(reverse('obtener_unidades_laboratorio', args=[self.unidad.pk]))
        unidades = {item['codigo']: item for item in respuesta.json()['unidades']}
        for auxiliar in ('LAC-EQP-CALD-01', 'LAC-EQP-BAL-01', 'LAC-EQP-PH-01', 'LAC-EQP-LACT-01'):
            self.assertNotIn(auxiliar, unidades)
        self.assertEqual(unidades['LAC-EQP-PAST-01']['auxiliares'], ['Caldera de vapor'])
        self.assertEqual(unidades['LAC-EQP-PAST-01']['categoria'], 'Proceso térmico')
        self.assertEqual(
            unidades['LAC-EQP-TANQ-01']['auxiliares'],
            ['Balanza de plataforma', 'Termolactodensímetro'],
        )

    def test_a_las_siete_se_reserva_la_sala_de_capacitacion_sola(self):
        self.client.force_login(self.estudiante)
        sala = EspacioReservable.objects.get(codigo='LAC-SALA-CAPACITACION')
        respuesta = self.client.post(reverse('crear_reserva'), self._payload(
            fecha_inicio=f'{self.fecha.isoformat()}T07:00',
            fecha_fin=f'{self.fecha.isoformat()}T09:00',
            horas_seleccionadas=json.dumps([7, 8]),
            espacios_solicitados=[str(sala.pk)],
            incluye_espacio='1',
        ))
        self.assertEqual(respuesta.status_code, 200, respuesta.content)
        reserva = Reserva.objects.get(pk=respuesta.json()['reserva_id'])
        self.assertEqual(reserva.hora_inicio, time(7, 0))
        self.assertFalse(reserva.consumibles_solicitados.exists())

        tarde = self.client.post(reverse('crear_reserva'), self._payload(
            fecha_inicio=f'{self.fecha.isoformat()}T17:00',
            fecha_fin=f'{self.fecha.isoformat()}T18:00',
            horas_seleccionadas=json.dumps([17]),
            espacios_solicitados=[str(sala.pk)],
            incluye_espacio='1',
        ))
        self.assertEqual(tarde.status_code, 400)
        self.assertIn('17:00', tarde.json()['error'])

    def test_una_practica_de_queso_pide_la_tina_la_queseria_y_sus_insumos(self):
        self.client.force_login(self.docente)
        queseria = EspacioReservable.objects.get(codigo='LAC-AREA-QUESERIA')
        leche = Consumible.objects.get(codigo='LAC-INS-LECHE')
        cuajo = Consumible.objects.get(codigo='LAC-INS-CUAJO')
        respuesta = self.client.post(reverse('crear_reserva'), self._payload(
            fecha_inicio=f'{self.fecha.isoformat()}T08:00',
            fecha_fin=f'{self.fecha.isoformat()}T12:00',
            horas_seleccionadas=json.dumps([8, 9, 10, 11]),
            unidades_seleccionadas=self._seleccion('LAC-EQP-TINA-01', 'LAC-EQP-PREN-01'),
            espacios_solicitados=[str(queseria.pk)],
            incluye_espacio='1',
            provision_consumibles='unidad',
            piezas_por_sesion='2',
            consumibles_seleccionados=json.dumps([
                {'id': leche.pk, 'cantidad': '100.000', 'metodo_estimacion': 'estimacion'},
                {'id': cuajo.pk, 'cantidad': '10.000', 'metodo_estimacion': 'estimacion'},
            ]),
        ))
        self.assertEqual(respuesta.status_code, 200, respuesta.content)
        reserva = Reserva.objects.get(pk=respuesta.json()['reserva_id'])
        self.assertEqual(reserva.cantidad_piezas, 2)
        pedidos = {
            item.consumible.codigo: item.cantidad_solicitada
            for item in reserva.consumibles_solicitados.all()
        }
        self.assertEqual(pedidos['LAC-INS-LECHE'], Decimal('100.000'))
        self.assertEqual(pedidos['LAC-INS-CUAJO'], Decimal('10.000'))
        # La caldera que calienta la tina no ocupa una tarjeta ni una fila.
        self.assertNotIn('LAC-EQP-CALD-01', reserva.unidades_seleccionadas)

    def test_la_maquila_de_yogur_suma_cultivo_azucar_y_envases(self):
        self.client.force_login(self.docente)
        maquila = FablabService.objects.get(code='LAC-SRV-MAQUILA')
        self.assertEqual(maquila.tipo_servicio, 'maquila_academica')
        cultivo = Consumible.objects.get(codigo='LAC-INS-CULTIVO-YOG')
        entrega = _dia_habil(self.fecha + timedelta(days=4))
        respuesta = self.client.post(reverse('crear_reserva'), self._payload(
            tipo_solicitud='servicio',
            modalidad_servicio='modelo_listo',
            servicios_solicitados=[str(maquila.pk)],
            cantidad_piezas='2',
            urgencia_servicio='normal',
            detalle_trabajo='Dos lotes de cien litros de yogur de mora para la feria.',
            fecha_entrega_prevista=entrega.isoformat(),
            materiales_seleccionados=json.dumps([cultivo.pk]),
            consumibles_servicio=json.dumps({str(cultivo.pk): '2.000'}),
            cotizacion_aceptada='true',
            metodo_pago='transferencia',
        ))
        self.assertEqual(respuesta.status_code, 200, respuesta.content)
        reserva = Reserva.objects.get(pk=respuesta.json()['reserva_id'])
        pedidos = {
            item.consumible.codigo: item.cantidad_solicitada
            for item in reserva.consumibles_solicitados.all()
        }
        self.assertEqual(pedidos['LAC-INS-CULTIVO-YOG'], Decimal('2.000'))
        for obligatorio in ('LAC-INS-AZUCAR', 'LAC-EMP-ENVASE-1L', 'LAC-EMP-ETIQUETA'):
            with self.subTest(material=obligatorio):
                self.assertIn(obligatorio, pedidos)
        self.assertTrue(SolicitudFabricacion.objects.filter(reserva=reserva).exists())
        self.assertGreater(reserva.costo_estimado, Decimal('0'))

    def test_el_cierre_descuenta_la_leche_del_tanque_por_lote_producido(self):
        """La leche sale del lote abierto en el tanque, aunque la práctica reservó la tina."""
        self.client.force_login(self.docente)
        queseria = EspacioReservable.objects.get(codigo='LAC-AREA-QUESERIA')
        leche = Consumible.objects.get(codigo='LAC-INS-LECHE')
        lote = LoteConsumible.objects.get(codigo='LAC-LECHE-L1')
        saldo_inicial = lote.cantidad_actual

        ayer = _dia_habil(timezone.localdate() - timedelta(days=4))
        creacion = self.client.post(reverse('crear_reserva'), self._payload(
            fecha_inicio=f'{ayer.isoformat()}T08:00',
            fecha_fin=f'{ayer.isoformat()}T12:00',
            horas_seleccionadas=json.dumps([8, 9, 10, 11]),
            unidades_seleccionadas=self._seleccion('LAC-EQP-TINA-01'),
            espacios_solicitados=[str(queseria.pk)],
            incluye_espacio='1',
            provision_consumibles='unidad',
            piezas_por_sesion='2',
            consumibles_seleccionados=json.dumps([
                {'id': leche.pk, 'cantidad': '100.000', 'metodo_estimacion': 'estimacion'},
            ]),
        ))
        self.assertEqual(creacion.status_code, 200, creacion.content)
        reserva = Reserva.objects.get(pk=creacion.json()['reserva_id'])
        reserva.estado = 'confirmada'
        reserva.save(update_fields=['estado'])

        coordinacion = ResponsableUnidad.objects.get(
            unidad=self.unidad, rol='coordinacion', usuario__isnull=False
        )
        self.client.force_login(coordinacion.usuario)
        pedido = reserva.consumibles_solicitados.get()
        tanque = self._unidad_equipo('LAC-EQP-TANQ-01')
        cierre = self.client.post(
            reverse('gestion_reserva_accion', args=[self.unidad.slug, reserva.pk]),
            {
                'accion': 'completar',
                'ejecucion_registrada': '1',
                'participantes_seleccionados': '[]',
                'asistencia_solicitante': 'asistio',
                'ejecucion_hora_inicio': '08:00',
                'ejecucion_hora_fin': '12:00',
                'ejecucion_asistentes_total': '10',
                'ejecucion_piezas': '2',
                'ejecucion_cumplimiento': 'si',
                'ejecucion_equipos_ids': [
                    str(self._unidad_equipo('LAC-EQP-TINA-01').pk), str(tanque.pk),
                ],
                'ejecucion_consumibles_json': json.dumps([{
                    'reserva_consumible_id': pedido.pk,
                    'consumida': '98',
                    'desperdiciada': '2',
                    'lote_id': lote.pk,
                    'equipo_id': tanque.pk,
                    'motivo_desperdicio': 'desperdicio_calidad',
                    'piezas': 2,
                    'modo_cantidad': 'distintas',
                    'detalle_piezas': ['50', '48'],
                }]),
                'ejecucion_observaciones': 'Dos lotes de queso fresco; dos litros se perdieron al desuerar.',
            },
        )
        self.assertEqual(cierre.status_code, 200, cierre.content)
        reserva.refresh_from_db()
        lote.refresh_from_db()
        self.assertEqual(reserva.estado, 'completada')
        self.assertEqual(lote.cantidad_actual, saldo_inicial - Decimal('100'))
        consumo = reserva.detalle_ejecucion['consumibles'][0]
        self.assertEqual(consumo['detalle_piezas'], ['50.000', '48.000'])
        self.assertEqual(reserva.detalle_ejecucion['piezas_producidas'], 2)


class EjemploDeRedaccionPorUnidadTests(TestCase):
    """El asistente propone el ejemplo del laboratorio que se está reservando."""

    @classmethod
    def setUpTestData(cls):
        cls.unidades = {}
        for slug, nombre, laboratorio in (
            ('laboratorio-inteligencia-artificial-ciencia-datos', 'Laboratorio IA y Ciencia de Datos', 'ia'),
            (
                'laboratorio-microbiologia-biotecnologia-aplicada',
                'Laboratorio de Biotecnología Aplicada',
                'biotecnologia',
            ),
        ):
            cls.unidades[laboratorio] = Unidad.objects.create(
                nombre=nombre,
                descripcion=f'Unidad de prueba para {nombre}.',
                fecha_inicio=date(2026, 1, 1),
                dependencia='laboratorios',
                slug=slug,
            )
            call_command('cargar_laboratorios_institucionales', laboratorio=laboratorio)
        # Una unidad sin ejemplos propios: comprueba el respaldo neutro.
        cls.sin_ejemplos = Unidad.objects.create(
            nombre='Unidad sin ejemplos propios',
            descripcion='Unidad recién creada que todavía no redactó los suyos.',
            fecha_inicio=date(2026, 1, 1),
            dependencia='laboratorios',
            slug='unidad-sin-ejemplos-prueba',
        )

    def _ejemplos_publicados(self, unidad):
        respuesta = self.client.get(unidad.get_absolute_url())
        self.assertEqual(respuesta.status_code, 200)
        return json.loads(
            re.search(
                r'id="ejemplosSolicitudReserva"[^>]*>(.*?)</script>',
                respuesta.content.decode(),
                re.S,
            ).group(1)
        )

    def test_cada_laboratorio_propone_su_propio_ejemplo(self):
        ia = self._ejemplos_publicados(self.unidades['ia'])
        bio = self._ejemplos_publicados(self.unidades['biotecnologia'])

        self.assertIn('matriz de confusión', ia['servicio']['ejemplo'])
        self.assertIn('ADN', bio['servicio']['ejemplo'])
        # Ninguno habla del trabajo del otro.
        self.assertNotIn('ADN', ia['servicio']['ejemplo'])
        self.assertNotIn('matriz de confusión', bio['servicio']['ejemplo'])

    def test_una_unidad_sin_ejemplos_no_hereda_los_de_nadie(self):
        self.assertEqual(self._ejemplos_publicados(self.sin_ejemplos), {})
        # El asistente guarda un ejemplo neutro para ese caso: no nombra
        # material, técnica ni equipo de ninguna disciplina.
        guion = (
            Path('apps/reservas/static/portal/js/pages/unidades/reservas/reservation_wizard.js')
            .read_text(encoding='utf-8')
        )
        for palabra in ('PLA', 'STL', 'agarosa', 'termociclador'):
            self.assertNotIn(f"sample: '{palabra}", guion)
        self.assertIn(
            "sample: 'Necesito que el laboratorio realice este trabajo",
            guion,
        )

    def test_el_ejemplo_propio_reemplaza_al_neutro_y_la_lista_es_opcional(self):
        unidad = self.unidades['ia']
        fila = EjemploSolicitudUnidad.objects.get(
            unidad=unidad, proposito_codigo='titulacion'
        )
        self.assertEqual(fila.checklist, [])

        fila.checklist = ['Qué conjunto de datos traes y de dónde salió.']
        fila.full_clean()
        fila.save()

        publicado = self._ejemplos_publicados(unidad)['titulacion']
        self.assertEqual(
            publicado['checklist'], ['Qué conjunto de datos traes y de dónde salió.']
        )
        self.assertIn('GPU', publicado['ejemplo'])

    def test_el_fablab_conserva_los_ejemplos_que_ya_mostraba(self):
        """La migración los guardó como filas suyas, no se perdieron."""
        migracion = import_module('apps.historial_modelos.migrations.0165_ejemplos_del_fablab')
        fablab = Unidad.objects.create(
            nombre='Laboratorio de Manufactura Digital y Prototipado',
            descripcion='El FabLab, que escribió los ejemplos originales.',
            fecha_inicio=date(2026, 1, 1),
            dependencia='laboratorios',
            slug=migracion.SLUG,
        )
        migracion.cargar(registro_anterior(), None)

        propios = EjemploSolicitudUnidad.publicados(fablab)
        self.assertIn('STL', propios['servicio']['ejemplo'])
        self.assertIn('filamento PLA', propios['docencia_practica']['ejemplo'])
        self.assertIn(
            'Material, color y acabado deseados; tolerancias si importan.',
            propios['servicio']['checklist'],
        )
        # Repetirla no duplica ni cambia nada: la migración es idempotente.
        migracion.cargar(registro_anterior(), None)
        self.assertEqual(
            EjemploSolicitudUnidad.objects.filter(unidad=fablab).count(),
            len(migracion.EJEMPLOS),
        )


class LenguajeDelServicioTests(TestCase):
    """El encargo se describe con las palabras de lo que el servicio hace."""

    asistente = Path(
        'apps/reservas/static/portal/js/pages/unidades/reservas/reservation_wizard.js'
    )
    plantilla = Path(
        'apps/gestion_unidades/templates/portal/pages/unidades/detalle/modales/reserva_equipos.html'
    )

    def setUp(self):
        self.guion = self.asistente.read_text(encoding='utf-8')
        self.marcado = self.plantilla.read_text(encoding='utf-8')

    def test_cada_tipo_de_servicio_tiene_sus_palabras(self):
        """Salvo «otro», que es justamente el que usa el texto neutro."""
        tipos = [
            codigo
            for codigo, _ in FablabService._meta.get_field('tipo_servicio').choices
            if codigo != 'otro'
        ]
        self.assertTrue(tipos)
        for codigo in tipos:
            with self.subTest(tipo=codigo):
                self.assertIn(f'      {codigo}: {{', self.guion)
        self.assertIn('PALABRAS_SERVICIO_NEUTRAS', self.guion)

    def test_el_encabezado_del_encargo_ya_no_habla_de_fabricar(self):
        self.assertNotIn('<h3>¿Qué vas a fabricar', self.marcado)
        self.assertIn('data-service-work-title', self.marcado)
        # La palabra de fabricar sigue existiendo, pero solo para quien fabrica.
        self.assertIn("titulo: '¿Qué vas a fabricar y con qué material?'", self.guion)

    def test_el_servicio_declara_su_tipo_para_que_el_asistente_lo_lea(self):
        self.assertIn('data-tipo-servicio="{{ servicio.tipo_servicio }}"', self.marcado)
        for atributo in ('data-mode-title', 'data-mode-hint'):
            with self.subTest(atributo=atributo):
                self.assertIn(atributo, self.marcado)

    def test_las_modalidades_de_la_plantilla_nacen_neutras(self):
        """Sin servicio elegido todavía, nadie ve vocabulario de otro oficio."""
        for palabra in ('Entrego el modelo listo', 'Diseño con asesoría'):
            with self.subTest(palabra=palabra):
                self.assertNotIn(f'<strong data-mode-title>{palabra}<', self.marcado)
                self.assertNotIn(f'<strong data-mode-title>{{% translate "{palabra}" %}}<', self.marcado)
        self.assertIn('<strong data-mode-title>{% translate "Entrego el trabajo listo" %}<', self.marcado)
