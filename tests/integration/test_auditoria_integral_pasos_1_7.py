"""Cuatro recorridos integrales para la arquitectura de Plantas Piloto.

La auditoria no repite pruebas unitarias de cada pantalla. Recorre los enlaces
entre catalogo, aula, reservas, produccion y repositorio para detectar roturas
que solo aparecen cuando los siete pasos trabajan juntos.
"""

import json
from datetime import timedelta
from decimal import Decimal

from django.core.exceptions import ValidationError
from django.core.management import call_command
from django.urls import reverse
from django.utils import timezone

from apps.plantas_piloto.operacion.presentation.gestion_produccion import orden_de_practica
from apps.reservas.presentation.proceso import seleccion_por_proceso
from apps.reservas.presentation.reservas_publicas import agenda_publica
from apps.plantas_piloto.operacion.presentation.secciones_plantas import PESTANAS_PLANTA, SECCIONES_PLANTA
from apps.plantas_piloto.operacion.management.plantas.taxonomia import PRODUCTOS_TAXONOMIA, TAXONOMIA_FAMILIAS
from apps.gestion_unidades.models.repositorio import ArtefactoExterno
from apps.recursos.models.recursos import CarpetaRecurso, Recurso
from apps.reservas.models.reservas import GuiaActividadReserva, Reserva
from apps.plantas_piloto.operacion.models.produccion import OrdenProduccion, Producto, Receta
from apps.formacion.models.practicas import PlanificacionPractica
from apps.directorio_unidades.models.core import Unidad
from tests.integration.test_reserva_por_proceso import BasePracticaPorProceso


class AuditoriaIntegralPasosUnoASieteTests(BasePracticaPorProceso):
    """Casos representativos de visitante, estudiante, docente y gestor."""

    databases = {'default', 'centros'}

    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()
        for planta in ('carnicos', 'panificacion', 'hortofruticola', 'almidones'):
            call_command('cargar_laboratorios_institucionales', laboratorio=planta)

    def test_caso_1_visitante_consulta_las_cinco_plantas_sin_alterar_laboratorios(self):
        plantas = list(
            Unidad.objects.filter(dependencia='plantas_piloto').order_by('slug')
        )
        self.assertEqual(len(plantas), 5)
        self.assertEqual(len(PESTANAS_PLANTA), 6)
        self.assertEqual(len(SECCIONES_PLANTA), 34)

        for unidad in plantas:
            with self.subTest(planta=unidad.slug):
                prefijo = unidad.familias_producto.order_by('orden').first().codigo.split('-F', 1)[0]
                self.assertEqual(
                    list(unidad.familias_producto.values_list('nombre', flat=True)),
                    list(TAXONOMIA_FAMILIAS[prefijo]),
                )
                esperados = {
                    nombre
                    for familia in PRODUCTOS_TAXONOMIA[prefijo].values()
                    for nombre, _unidad_medida in familia
                }
                actuales = set(
                    Producto.objects.filter(unidad=unidad, activo=True, publico=True)
                    .values_list('nombre', flat=True)
                )
                self.assertTrue(esperados.issubset(actuales), esperados - actuales)
                self.assertEqual(unidad.modulos_contenido.filter(activo=True).count(), 6)
                pagina = self.client.get(unidad.get_absolute_url())
                self.assertEqual(pagina.status_code, 200)
                for titulo, _secciones in PESTANAS_PLANTA.values():
                    self.assertContains(pagina, titulo)
                for receta in Receta.objects.filter(unidad=unidad, activa=True):
                    self.assertEqual(seleccion_por_proceso(receta, Decimal('1'))['faltantes'], [])

        laboratorio = Unidad.objects.create(
            nombre='Laboratorio de regresion', descripcion='Unidad sin produccion.',
            fecha_inicio='2026-01-01', dependencia='laboratorios',
            slug='laboratorio-regresion-arquitectura',
        )
        self.assertEqual(
            set(laboratorio.modulos_contenido.values_list('clave', flat=True)),
            {
                'informacion-general', 'areas-equipos', 'procesos-productos',
                'docencia-capacitacion', 'reservas-servicios', 'investigacion-formativa',
            },
        )
        pagina_laboratorio = self.client.get(laboratorio.get_absolute_url())
        self.assertEqual(pagina_laboratorio.status_code, 200)
        self.assertContains(pagina_laboratorio, 'data-modulo="informacion-general"')
        self.assertNotContains(pagina_laboratorio, 'data-modulo="procesos-protocolos"')

    def test_caso_2_estudiante_mantiene_la_ruta_del_saber_hacer_y_exporta(self):
        receta = self.receta_queso
        producto = receta.producto
        rutas = {
            'producto': reverse('ficha_producto_publica', args=[self.unidad.slug, producto.pk]),
            'ficha': reverse('ficha_proceso_publica', args=[self.unidad.slug, receta.pk]),
            'documentacion': reverse('documentacion_proceso', args=[self.unidad.slug, receta.pk]),
            'balance': reverse('simulador_balance', args=[self.unidad.slug]) + f'?receta={receta.pk}',
            'linea': reverse('simulador_linea', args=[self.unidad.slug]) + f'?receta={receta.pk}',
        }
        enlaces_esperados = {
            reverse('ficha_producto_publica', args=[self.unidad.slug, producto.pk]),
            reverse('ficha_proceso_publica', args=[self.unidad.slug, receta.pk]),
            reverse('documentacion_proceso', args=[self.unidad.slug, receta.pk]),
        }
        for nombre, ruta in rutas.items():
            with self.subTest(vista=nombre):
                respuesta = self.client.get(ruta)
                self.assertEqual(respuesta.status_code, 200)
                self.assertEqual(respuesta['X-Frame-Options'], 'SAMEORIGIN')
                acciones = respuesta.context['acciones_proceso']
                self.assertTrue(enlaces_esperados.issubset({accion['url'] for accion in acciones}))

        ficha = self.client.get(rutas['ficha'])
        self.assertContains(ficha, 'Diagrama de flujo')
        self.assertContains(ficha, 'Diagrama sinóptico')
        saber = self.client.get(rutas['documentacion'])
        self.assertContains(saber, 'BASES PARA LEER Y CALCULAR EL PROCESO')
        self.assertContains(saber, 'saber-formula')
        csv = self.client.get(reverse(
            'datos_proceso_csv', args=[self.unidad.slug, receta.pk],
        ))
        self.assertEqual(csv.status_code, 200)
        self.assertTrue(csv.content.startswith('\ufeff'.encode('utf-8')))
        pdf = self.client.get(rutas['documentacion'] + '?formato=pdf')
        self.assertEqual(pdf.status_code, 200)
        self.assertEqual(pdf['Content-Type'], 'application/pdf')
        self.assertTrue(pdf.content.startswith(b'%PDF'))

    def test_caso_3_docente_reserva_un_proceso_y_la_guia_gobierna_la_aprobacion(self):
        seleccion = self.seleccion('1')
        respuesta = self.reservar(self.carga_docencia(seleccion))
        self.assertEqual(respuesta.status_code, 200, respuesta.content)
        reserva_id = respuesta.json()['reserva_id']
        reserva = Reserva.objects.get(pk=reserva_id)
        plan = PlanificacionPractica.objects.get(reserva=reserva)
        guia = GuiaActividadReserva.objects.get(actividad=plan.actividad, activo=True)
        contenido_completo = dict(guia.contenido)
        guia.contenido = {**contenido_completo, 'objetivos': ''}
        guia.estado_publicacion = 'borrador'
        guia.save(update_fields=['contenido', 'estado_publicacion', 'actualizado_en'])
        rechazada = self.aprobar(reserva)
        self.assertEqual(rechazada.status_code, 409)
        self.assertIn('guía', rechazada.json()['error'].lower())

        guia.contenido = contenido_completo
        guia.estado_publicacion = 'revision'
        guia.save(update_fields=['contenido', 'estado_publicacion', 'actualizado_en'])
        aprobada = self.aprobar(reserva)
        self.assertEqual(aprobada.status_code, 200, aprobada.content)
        orden = OrdenProduccion.objects.get(reserva=reserva)
        self.assertEqual(orden.receta, self.receta_queso)
        self.assertEqual(orden.factor, Decimal('1.000'))
        self.assertEqual(orden_de_practica(reserva, self.coordinacion), orden)
        self.assertEqual(OrdenProduccion.objects.filter(reserva=reserva).count(), 1)
        # Quien reservó ve la corrida de su práctica en el comprobante.
        self.client.force_login(self.docente)
        comprobante = self.client.get(reverse('comprobante_reserva', args=[reserva.pk]))
        self.assertContains(comprobante, f'Tu práctica en la planta · corrida {orden.codigo}')

        agenda = agenda_publica(self.unidad, desde=self.inicio, dias=1)
        serializada = json.dumps(agenda, ensure_ascii=False, default=str)
        self.assertNotIn(self.docente.username, serializada)
        self.assertNotIn(self.docente.email, serializada)
        estados = {slot['estado'] for dia in agenda for slot in dia['slots']}
        self.assertTrue(estados.issubset({'disponible', 'comprometido'}))
        self.assertIn('comprometido', estados)

    def test_caso_4_gestor_publica_adjuntos_y_conecta_un_artefacto_seguro(self):
        modulo = self.unidad.modulos_contenido.get(clave='informacion-general')
        carpeta = CarpetaRecurso.objects.create(
            nombre='Modelos validados', unidad=self.unidad, modulo_config=modulo,
            seccion_planta='1.5', visibilidad='publica',
        )
        inseguro = Recurso.objects.create(
            nombre='Archivo sin revisar', descripcion='Pendiente de antivirus.',
            unidad=self.unidad, carpeta=carpeta, url='https://example.test/inseguro.pdf',
            tipo_adjunto='artefacto', visibilidad='publica', seguridad_verificada=False,
        )
        with self.assertRaises(ValidationError):
            inseguro.full_clean()
        self.assertEqual(
            self.client.get(reverse('recurso_unidad', args=[inseguro.pk])).status_code,
            404,
        )

        evidencia = Recurso(
            nombre='Validacion del modelo', descripcion='Contraste con una corrida institucional.',
            unidad=self.unidad, carpeta=carpeta, url='https://example.test/validacion.pdf',
            tipo_adjunto='evidencia', autor='UPEC', licencia_uso='interna',
            visibilidad='publica', seguridad_verificada=True,
        )
        evidencia.full_clean()
        evidencia.save()
        artefacto = ArtefactoExterno.objects.create(
            codigo='LAC-SIM-AUDITORIA-01', nombre='Modelo conectado de auditoria',
            descripcion='Comprueba el contrato de datos de una receta.',
            tipo='hoja_calculo', nivel_integracion=2, unidad=self.unidad,
            receta=self.receta_queso, software_requerido='Lector XLSX',
            licencia_software='libre', requisitos_tecnicos='Formato XLSX.',
            instrucciones_uso='Exportar, calcular e importar el resultado.',
            entradas_esperadas=['Receta.codigo', 'Receta.cantidad_base'],
            salidas_devueltas=['masa_final'], formato_intercambio='xlsx',
            esquema={'masa_final': 'decimal'}, que_representa='Balance estacionario.',
            supuestos_simplificaciones='Sin acumulacion.', estado_verificacion='verificado',
            estado_validacion='datos', evidencia_validacion=evidencia,
            fuente_referencia='Acta UPEC LAC-AUD-2026-01.',
            responsable_validacion=self.coordinacion,
            vigente_desde=timezone.localdate() - timedelta(days=30),
            vigente_hasta=timezone.localdate() + timedelta(days=365),
            limitaciones_conocidas='No modela transitorios.', autor='UPEC',
            licencia_uso='Uso academico UPEC', estado='publicado', visibilidad='publica',
        )
        repositorio = self.client.get(reverse('repositorio_unidad', args=[self.unidad.slug]))
        self.assertContains(repositorio, evidencia.nombre)
        self.assertNotContains(repositorio, inseguro.nombre)
        ficha = self.client.get(reverse(
            'ficha_proceso_publica', args=[self.unidad.slug, self.receta_queso.pk],
        ))
        exportar = reverse(
            'exportar_paquete_artefacto', args=[self.unidad.slug, artefacto.codigo],
        )
        self.assertContains(ficha, f'Exportar datos · {artefacto.nombre}')
        self.assertContains(ficha, exportar)
        paquete = self.client.get(exportar)
        self.assertEqual(paquete.status_code, 200)
        self.assertTrue(paquete.content.startswith(b'PK'))

        etapa = self.receta_queso.etapas.first()
        etapa.duracion_min += 1
        etapa.save(update_fields=['duracion_min'])
        artefacto.refresh_from_db()
        self.assertTrue(artefacto.posiblemente_desactualizado)
