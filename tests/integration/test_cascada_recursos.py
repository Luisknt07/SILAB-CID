"""Reglas de la seleccion guiada de recursos (espacio -> equipos -> software).

El asistente guia en el navegador, pero el servidor debe exigir lo mismo:
- en la ruta de recursos el espacio es obligatorio cuando la unidad publica areas;
- la unidad completa solo se reserva para actividades docentes;
- el software "adicional" no exige estar instalado en el equipo elegido, pero
  queda registrado como requisito para que el laboratorio lo habilite.
"""

import json
import os
from datetime import date

from django.conf import settings
from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse
from tests.integration.utiles import verificar_pertenencia

from apps.recursos.models.equipos import EquiposServicios
from apps.gestion_unidades.models.espacios import EspacioReservable
from apps.reservas.models.reservas import Reserva
from apps.recursos.models.software import SoftwareDisponible
from apps.directorio_unidades.models.core import Unidad
from apps.recursos.models.unidades import UnidadEquipo


class CascadaRecursosTests(TestCase):
    databases = {'default', 'centros'}

    @classmethod
    def setUpTestData(cls):
        User = get_user_model()
        cls.docente = User.objects.create_user(
            'docente-cascada', password='clave-segura', email='cascada@upec.edu.ec',
            first_name='Docente', last_name='Cascada',
        )
        perfil = cls.docente.profile
        perfil.tipo_usuario = 'docente'
        perfil.facultad = 'agropecuarias_ambientales'
        perfil.carrera = 'computacion'
        perfil.institucion = 'UPEC'
        perfil.save()
        verificar_pertenencia(cls.docente)
        cls.unidad = Unidad.objects.create(
            nombre='Laboratorio de cascada',
            descripcion='Unidad para validar la seleccion guiada.',
            fecha_inicio=date(2026, 1, 1),
            dependencia='laboratorios',
            slug='laboratorio-cascada',
        )
        cls.catalogo = EquiposServicios.objects.create(
            codigo='EQ-CASC-001', nombre='Impresora de cascada',
        )
        cls.equipo = UnidadEquipo.objects.create(
            codigo_unidad='UE-CASC-001',
            equipo=cls.catalogo,
            laboratorio=cls.unidad,
            estado_unidad='disponible',
            activa=True,
        )
        cls.area = EspacioReservable.objects.create(
            unidad=cls.unidad,
            codigo='AREA-CASC',
            nombre='Área técnica de cascada',
            tipo='area',
            politica_reserva='tecnico',
            capacidad=6,
            reservable=True,
            activo=True,
        )
        cls.area.equipos_asociados.add(cls.equipo)
        cls.sala = EspacioReservable.objects.create(
            unidad=cls.unidad,
            codigo='SALA-CASC',
            nombre='Sala de cascada',
            tipo='sala',
            politica_reserva='general',
            capacidad=20,
            reservable=True,
            activo=True,
        )
        cls.instalado = SoftwareDisponible.objects.create(
            unidad=cls.unidad, codigo='SW-CASC-IN', nombre='CAD instalado',
            version='2026', tipo_acceso='instalacion', licencias_totales=5,
            licencias_disponibles=5, requiere_reserva=True, activo=True,
        )
        cls.instalado.equipos_instalados.add(cls.equipo)
        cls.no_instalado = SoftwareDisponible.objects.create(
            unidad=cls.unidad, codigo='SW-CASC-EX', nombre='Simulador adicional',
            version='2026', tipo_acceso='licencia', licencias_totales=5,
            licencias_disponibles=5, requiere_reserva=True, activo=True,
        )
        # Instalado en otro equipo: elegirlo sin marcarlo como adicional debe
        # exigir ese equipo, igual que antes de la cascada.
        cls.otro_equipo = UnidadEquipo.objects.create(
            codigo_unidad='UE-CASC-002',
            equipo=cls.catalogo,
            laboratorio=cls.unidad,
            estado_unidad='disponible',
            activa=True,
        )
        cls.no_instalado.equipos_instalados.add(cls.otro_equipo)
        # Programa propio del equipo: se incluye siempre que se reserva la impresora.
        cls.propio = SoftwareDisponible.objects.create(
            unidad=cls.unidad, codigo='SW-CASC-PROPIO', nombre='Laminador de la impresora',
            version='3', tipo_acceso='instalacion', licencias_totales=1,
            licencias_disponibles=1, requiere_reserva=True, activo=True,
            uso_en_equipo='obligatorio',
        )
        cls.propio.equipos_instalados.add(cls.equipo)

    def setUp(self):
        self.client.force_login(self.docente)

    def _payload(self, **overrides):
        payload = {
            'unidad_id': self.unidad.pk,
            'tipo_solicitud': 'recursos',
            'fecha_inicio': '2026-11-19T09:00',
            'fecha_fin': '2026-11-19T11:00',
            'horas_seleccionadas': json.dumps([9, 10]),
            'proposito_codigo': 'investigacion_innovacion',
            'subtipo_actividad': 'proyecto_investigacion',
            'alcance_beneficiario': 'perfil_solicitante',
            'vinculacion_actividad': 'independiente',
            'referencia_actividad': 'Proyecto de cascada',
            'participantes_seleccionados': '[]',
            'aceptar_terminos': 'on',
            'incluye_espacio': 'true',
            'solicito_espacio': 'true',
            'solicito_equipo': 'true',
            'alcance_espacio': 'areas',
            'espacios_solicitados': [str(self.area.pk)],
            'unidades_seleccionadas': json.dumps([{'id': self.equipo.pk}]),
            'provision_consumibles': 'ninguno',
        }
        payload.update(overrides)
        return payload

    def test_el_espacio_es_obligatorio_en_la_ruta_de_recursos(self):
        respuesta = self.client.post(
            reverse('crear_reserva'),
            self._payload(espacios_solicitados=[], incluye_espacio='false', solicito_espacio='false'),
        )

        self.assertEqual(respuesta.status_code, 400, respuesta.content)
        self.assertIn('áreas', respuesta.json()['error'])

    def test_un_area_tecnica_exige_un_equipo(self):
        respuesta = self.client.post(
            reverse('crear_reserva'),
            self._payload(unidades_seleccionadas='[]', solicito_equipo='false'),
        )

        self.assertEqual(respuesta.status_code, 400, respuesta.content)
        self.assertIn('equipo', respuesta.json()['error'].lower())

    def test_una_sala_general_se_reserva_sola_con_su_mobiliario(self):
        respuesta = self.client.post(
            reverse('crear_reserva'),
            self._payload(
                espacios_solicitados=[str(self.sala.pk)],
                unidades_seleccionadas='[]',
                solicito_equipo='false',
            ),
        )

        self.assertEqual(respuesta.status_code, 200, respuesta.content)
        reserva = Reserva.objects.get(pk=respuesta.json()['reserva_id'])
        self.assertEqual(list(reserva.espacios_solicitados.values_list('pk', flat=True)), [self.sala.pk])
        self.assertEqual(reserva.alcance_espacio, 'areas')

    def test_la_unidad_completa_solo_se_reserva_para_docencia(self):
        rechazada = self.client.post(
            reverse('crear_reserva'),
            self._payload(alcance_espacio='unidad_completa', espacios_solicitados=[]),
        )
        self.assertEqual(rechazada.status_code, 400, rechazada.content)
        self.assertIn('actividades docentes', rechazada.json()['error'])

        aceptada = self.client.post(
            reverse('crear_reserva'),
            self._payload(
                alcance_espacio='unidad_completa',
                espacios_solicitados=[],
                proposito_codigo='docencia_practica',
                subtipo_actividad='simulacion_demostracion',
                referencia_actividad='Demostración de cascada',
                origen_programacion='adicional',
                # Toda docencia exige guia: se crea con la reserva.
                vinculacion_actividad='manual',
                guia_confirmada_solicitante='1',
                guia_asignatura='Fabricación digital',
                guia_resultado_aprendizaje='Reconoce el flujo de fabricación digital.',
                guia_objetivos='Observar la demostración.',
                guia_formato_procedimiento='numerado',
                guia_procedimiento='Presentar\nDemostrar\nRegistrar',
            ),
        )
        self.assertEqual(aceptada.status_code, 200, aceptada.content)
        reserva = Reserva.objects.get(pk=aceptada.json()['reserva_id'])
        self.assertEqual(reserva.alcance_espacio, 'unidad_completa')

    def test_el_software_adicional_no_exige_equipo_y_queda_como_requisito(self):
        sin_marca = self.client.post(
            reverse('crear_reserva'),
            self._payload(
                software_solicitado=[str(self.no_instalado.pk)],
                solicito_software='true',
            ),
        )
        self.assertEqual(sin_marca.status_code, 400, sin_marca.content)
        self.assertIn('Selecciona un equipo donde esté disponible', sin_marca.json()['error'])

        marcado = self.client.post(
            reverse('crear_reserva'),
            self._payload(
                software_solicitado=[str(self.instalado.pk), str(self.no_instalado.pk)],
                software_adicional=json.dumps([self.no_instalado.pk]),
                software_adicional_texto='Plugin de simulación térmica',
                solicito_software='true',
            ),
        )
        self.assertEqual(marcado.status_code, 200, marcado.content)
        reserva = Reserva.objects.get(pk=marcado.json()['reserva_id'])
        # El programa propio de la impresora viaja siempre con ella.
        self.assertEqual(
            set(reserva.software_solicitado.values_list('pk', flat=True)),
            {self.instalado.pk, self.no_instalado.pk, self.propio.pk},
        )
        self.assertIn('Software adicional por habilitar: Simulador adicional', reserva.requisitos_especiales)
        self.assertIn('otro: Plugin de simulación térmica', reserva.requisitos_especiales)

    def test_el_software_propio_del_equipo_se_incluye_aunque_no_se_marque(self):
        sin_marcar = self.client.post(reverse('crear_reserva'), self._payload())
        self.assertEqual(sin_marcar.status_code, 200, sin_marcar.content)
        reserva = Reserva.objects.get(pk=sin_marcar.json()['reserva_id'])
        self.assertEqual(list(reserva.software_solicitado.values_list('pk', flat=True)), [self.propio.pk])

        # Con otro equipo el programa propio no aplica; lo opcional sigue siendo decision de la persona.
        otro = self.client.post(
            reverse('crear_reserva'),
            self._payload(
                espacios_solicitados=[str(self.sala.pk)],
                unidades_seleccionadas=json.dumps([{'id': self.otro_equipo.pk}]),
                fecha_inicio='2026-11-20T09:00', fecha_fin='2026-11-20T11:00',
            ),
        )
        self.assertEqual(otro.status_code, 200, otro.content)
        self.assertFalse(Reserva.objects.get(pk=otro.json()['reserva_id']).software_solicitado.exists())

    def test_el_asistente_publica_la_cascada(self):
        pagina = self.client.get(self.unidad.get_absolute_url())

        self.assertEqual(pagina.status_code, 200)
        self.assertContains(pagina, 'Elige dónde trabajarás')
        # Sin medios propios no se ofrece orientación: nunca se muestran los de otra unidad.
        self.assertNotContains(pagina, 'data-space-orientation')
        self.assertNotContains(pagina, 'plano-fablab-demostrativo')
        self.assertNotContains(pagina, 'img/360/lacteos1')
        # Con los medios de la unidad, la orientación abre diálogos amplios; los iframes cargan al abrirlos.
        self.unidad.recorrido_espacios_youtube_url = 'https://www.youtube.com/watch?v=Vcxz9ss2MAs'
        self.unidad.recorrido_360_ruta = 'https://recorridos.example.edu/unidad/index.html'
        self.unidad.save(update_fields=['recorrido_espacios_youtube_url', 'recorrido_360_ruta'])
        pagina = self.client.get(self.unidad.get_absolute_url())
        self.assertContains(pagina, '¿No conoces el laboratorio?')
        for destino in ('orientacionVideo', 'orientacion360'):
            self.assertContains(pagina, f'data-orientation-open="{destino}"')
            self.assertContains(pagina, f'<template id="{destino}">')
        self.assertNotContains(pagina, 'orientacionPlano')
        self.assertContains(pagina, '<iframe data-src="', count=2)
        self.assertNotContains(pagina, 'reservation-space-tour')
        # Equipos en tarjetas agrupadas por categoria; no disponibles en un plegable aparte.
        self.assertContains(pagina, 'class="reservation-equipment-list" id="unidadesTableBody"')
        self.assertContains(pagina, 'id="equiposNoDisponibles"')
        self.assertNotContains(pagina, 'id="filtroEstado"')
        self.assertNotContains(pagina, 'selectAllUnidades')
        self.assertContains(pagina, 'data-software-access=')
        self.assertContains(pagina, 'data-software-usage="obligatorio"')
        self.assertContains(pagina, '<b>Versión instalada</b>')
        self.assertContains(pagina, 'class="reservation-software-item__details"')
        # Icono, nombre y detalles son hijos directos de la etiqueta: misma fila.
        self.assertNotContains(pagina, 'reservation-software-item__row')
        # Flujo de servicios: detalles del trabajo, materiales por servicio y
        # urgencia con propuesta de fecha; sin simulaciones comparables.
        self.assertContains(pagina, 'id="trabajoServicioReserva"')
        self.assertContains(pagina, 'name="urgencia_servicio"')
        self.assertContains(pagina, 'id="proponerEntregaServicio"')
        self.assertContains(pagina, "data-service-schedule-url=")
        self.assertNotContains(pagina, 'data-quote-simulations')
        # Flujo directo: sin filtro de categoria (las areas ya filtran), sin
        # etiquetas de apoyo (nota fija), sin opciones de provision de insumos
        # y sin descripcion opcional (la descripcion obligatoria la reemplaza).
        self.assertNotContains(pagina, 'id="filtroEquipo"')
        self.assertContains(pagina, 'id="apoyoLaboratorioNota"')
        self.assertNotContains(pagina, 'id="requisitosEspecialesOpciones"')
        self.assertContains(pagina, 'id="provisionConsumibles"')
        self.assertNotContains(pagina, 'id="provisionConsumiblesOpciones"')
        self.assertNotContains(pagina, 'id="descripcionActividadCampo"')
        # Sin boton de simulacion ni metodo de calculo: la cantidad basta y el
        # valor se calcula solo; el pago vive en su propia seccion del paso 4.
        self.assertNotContains(pagina, 'id="calcularCotizacionServicio"')
        self.assertNotContains(pagina, 'reservation-consumable__method')
        self.assertContains(pagina, 'id="pagoServicioSeccion"')
        # La cantidad se escribe por sesion y el total lo calcula el asistente,
        # asi que ya no se pregunta por el alcance de las cantidades.
        self.assertNotContains(pagina, 'id="alcanceCantidadesOpciones"')
        # La reserva pregunta las piezas de la practica, como el servicio.
        self.assertContains(pagina, 'id="piezasPorSesionReserva"')
        # Servicios: finalidad breve en lugar de clasificacion y participantes.
        self.assertContains(pagina, 'id="finalidadServicioReserva"')
        self.assertContains(pagina, 'data-software-usage="opcional"')
        # La version concreta la valida la prueba del contrato versionado; aqui
        # solo importa que el asistente publique su build.
        self.assertRegex(pagina.content.decode(), r'data-reservation-build="\d{8}-[a-z-]+v\d+"')

    def test_la_api_de_unidades_publica_la_categoria_para_agrupar(self):
        respuesta = self.client.get(reverse('obtener_unidades_laboratorio', args=[self.unidad.pk]))
        self.assertEqual(respuesta.status_code, 200)
        unidades = {item['codigo']: item for item in respuesta.json()['unidades']}
        self.assertEqual(unidades['UE-CASC-001']['categoria'], 'Impresión 3D')
        self.assertIn('video_url', unidades['UE-CASC-001'])
        self.assertIs(unidades['UE-CASC-001']['admite_software_adicional'], False)

    def test_el_asistente_integra_software_e_insumos_en_cada_equipo(self):
        base = os.path.join(settings.BASE_DIR, 'apps', 'reservas', 'static', 'portal', 'js', 'pages', 'unidades', 'reservas')
        with open(os.path.join(base, 'reservation_wizard.js'), encoding='utf-8') as archivo:
            asistente = archivo.read()
        with open(os.path.join(base, 'modal_reserva_equipos.js'), encoding='utf-8') as archivo:
            heredado = archivo.read()
        self.assertIn('function integrateResourcesIntoEquipment()', asistente)
        self.assertIn('function openEquipmentSheet(', asistente)
        # Programa propio: se marca y bloquea con el equipo; programas por
        # instalar: pregunta dentro de la tarjeta del equipo que lo admite.
        self.assertIn("input.dataset.rwRequired = 'true';", asistente)
        self.assertIn('function syncSoftwareAdicionalTexto()', asistente)
        self.assertNotIn('rw-software-extra__other', asistente)
        self.assertIn('data-equipment-extra-software-input', heredado)
        self.assertIn('data-admite-software-adicional=', heredado)
        # Una fila por equipo: software e insumos siempre visibles con su cantidad,
        # unidades con nombre claro (el codigo queda en la ficha).
        self.assertIn('<b data-count>0</b>', heredado)
        self.assertIn("`Unidad ${indice}`", heredado)
        self.assertNotIn("(unidad.codigo || 'Unidad')", heredado)
        # Los controles de insumos se toman de todo el formulario (la cascada los mueve).
        self.assertIn("form.querySelectorAll('.reservation-consumable__check')", asistente)
        # Flujo directo: sin cabeceras numeradas de la cascada ni simulaciones;
        # la provision se deduce de los insumos marcados; la presentacion del
        # procedimiento se elige en la barra del editor; la descripcion se
        # redacta junto a la ayuda visible.
        self.assertNotIn('function cascadeHeading(', asistente)
        self.assertNotIn('function renderSimulations()', asistente)
        self.assertIn('function syncProvision()', asistente)
        self.assertIn("guideEditor.on('formato'", asistente)
        self.assertIn('reservation-intent__grid', asistente)
        # La descripcion cambia con el proposito: solo docencia alimenta la guia,
        # y el ejemplo que se ofrece es el que publica la unidad reservada.
        self.assertIn("state.type === 'servicio' ? 'servicio' : selectedPurpose()", asistente)
        self.assertIn('INTENT_COPY[clave] || INTENT_COPY.docencia_practica', asistente)
        self.assertIn('EJEMPLOS_UNIDAD[clave]', asistente)
        self.assertIn('function briefIntent(title, sample)', asistente)
        self.assertNotIn('reservation-intent__help"><summary', asistente)
        # Calendario: la hora de almuerzo se muestra bloqueada y no se selecciona.
        self.assertIn('if (esHoraDeAlmuerzo(hora)) continue;', heredado)
        self.assertNotIn('function filtrarPorEquipo()', heredado)
        # El panel de horas del dia se retiro: la agenda semanal es la unica
        # superficie y su barra es la que muestra el aviso de seleccion.
        self.assertNotIn('function renderDayHours()', heredado)
        self.assertNotIn('function filasHorarioDia(value)', heredado)
        self.assertNotIn("getElementById('hourList')", heredado)
        self.assertNotIn("getElementById('selSummary')", heredado)
        self.assertIn('[data-calendar-selection-summary]', asistente)
        # Expediente del solicitante: pestañas, recorrido y lector de PDF.
        with open(os.path.join(base, 'modal_mis_reservas.js'), encoding='utf-8') as archivo:
            historial = archivo.read()
        self.assertIn('function renderizarExpedienteReserva()', historial)
        self.assertIn('function lineaTiempoReservaHtml(reserva)', historial)
        self.assertIn('function mostrarDocumentoReserva(clave, disparador)', historial)
        # Los PDF delegan en el visor compartido y devuelven el foco al botón
        # del expediente al cerrarlo; la guía y el comprobante conservan su URL.
        self.assertIn('window.visorPdfModal.abrir(enlace,', historial)
        self.assertIn('enlace.href = url;', historial)
        self.assertIn('disparador?.isConnected', historial)
        self.assertIn('mostrarDocumentoReserva(boton.dataset.verDocumento, boton)', historial)
        self.assertIn('function panelDocumentosReserva(reserva)', historial)
        # El expediente se abre como ventana sobre la agenda, no embebido.
        self.assertIn("classList.add('has-open-record')", historial)
        self.assertIn('function cerrarExpedienteReserva()', historial)
        # Solo equipos ligados a las areas marcadas; los sin area y la lista de
        # no disponibles siguen el mismo filtro.
        self.assertIn('(locations.length > 0 && locations.some((spaceId) => selectedSpaceIds.has(spaceId)))', asistente)
        self.assertIn("unavailable.querySelectorAll('[data-unavailable-list] li[data-unit-id]')", asistente)
        self.assertIn('<li data-unit-id="${escapeHtml(String(unidad.id))}">', heredado)
        # Detalles desplegables (uno abierto por lista), existencia controlada y
        # cantidades editables en la cotizacion del servicio.
        self.assertIn('function toggleItemDetails(item, open)', asistente)
        self.assertIn('function checkConsumableStock(input)', asistente)
        self.assertIn("serviceConsumablesInput.name = 'consumibles_servicio'", asistente)
        self.assertIn('function renderServiceWork()', asistente)
        self.assertIn('async function requestDeliveryProposal()', asistente)
        self.assertIn('function applyDeliveryProposal(proposal)', asistente)
        self.assertIn('function scheduleServiceQuote()', asistente)
        # Insumos bloqueados hasta marcar el equipo de su tarjeta (tambien en espejos).
        self.assertIn("check.dataset.rwBaseEnabled = baseEnabled ? 'true' : 'false';", asistente)
        self.assertIn("target.disabled = source.dataset.rwBaseEnabled !== 'true' || !mirrorUnlocked;", asistente)
        # Tabla unificada de seis columnas con IVA opcional; un servicio por solicitud.
        self.assertIn('function quoteTable(quote)', asistente)
        self.assertIn("taxApplies: modal.dataset.taxApplies === 'true'", asistente)
        self.assertIn('desmarca los demas', asistente)
        # Programaciones semanales: cantidades por sesion o totales y costo del programa.
        self.assertIn('function estimatedSessions()', asistente)
        self.assertIn("if (purposeSection) purposeSection.hidden = isService;", asistente)
        # Guia FT04: el dialogo vive dentro del modal (foco) y la bibliografia
        # se pega como BibTeX ya listo, sin plantillas de codigo.
        self.assertIn('form.appendChild(guidePreview);', asistente)
        self.assertNotIn('document.body.appendChild(guidePreview);', asistente)
        self.assertNotIn('data-bibtex-template', asistente)
        self.assertIn('Pega aquí tus entradas BibTeX ya listas', asistente)
        self.assertIn("if (state.type === 'servicio') return validateIntent();", asistente)
        # Descripcion obligatoria (50-200 palabras) en ambas rutas, con ejemplo redactado,
        # que alimenta las sugerencias de la guia.
        self.assertIn('name="intencion_solicitud"', asistente)
        self.assertIn('function intentSummary(maxSentences = 2)', asistente)
        self.assertIn('Usar el ejemplo redactado', asistente)
        # La cantidad escrita es la de una sesion o la de una pieza; el total
        # lo calcula el asistente y no se edita.
        self.assertIn('function updateConsumableTotals()', asistente)
        self.assertIn('function resourceWorkUnits(card)', asistente)
        # Cada equipo declara sus piezas y su detalle en su propia tarjeta.
        self.assertIn('function syncEquipmentWorkUnits(groups)', asistente)
        # Reservar solo el espacio se declara y se confirma, ya no se bloquea.
        self.assertIn('function spaceOnlySelection()', asistente)
        self.assertNotIn('function validateSpaceEquipmentSelection', asistente)
        self.assertNotIn('Selecciona un equipo o software asociado a', asistente)
        self.assertIn('function syncEquipmentWorkSummary()', asistente)
        self.assertIn('function materialTotalQuantity(row)', asistente)
        self.assertNotIn('alcance_cantidades', asistente)
        self.assertIn("resources.insertBefore(serviceQuote, responsibleCatalog || null);", asistente)
        self.assertNotIn('reservation-consumable__method', asistente)
        self.assertIn("url.searchParams.set('seleccion', JSON.stringify(selectedIds));", asistente)
        self.assertIn('Compromiso de uso.', asistente)
        self.assertNotIn('function openSoftwareSheet', asistente)
        # Sin seccion de software de uso general ni "software adicional" por ids.
        self.assertNotIn('Software de uso general', asistente)
        self.assertNotIn("softwareAdicionalInput.name = 'software_adicional'", asistente)
        self.assertNotIn('rw-software-extra', asistente)
        # Insumos compartidos: la tarjeta original en el primer equipo compatible
        # y un espejo sincronizado en cada uno de los demas.
        self.assertIn("groups.filter((item) => ids.includes(Number.parseInt(item.dataset.equipoId, 10)))", asistente)
        # Con «diseño con asesoría» el equipo muestra su software y explica que
        # los materiales del trabajo se eligen junto a las piezas.
        self.assertIn("const eligeInsumos = state.type === 'recursos';", asistente)
        self.assertIn("if ((!eligeInsumos && !isAssistedService()) || !groups.length) {", asistente)
        self.assertIn('function describeEquipmentConsumables(section, count, eligeInsumos)', asistente)
        self.assertIn("syncConsumableMirrors(card, others);", asistente)
        self.assertIn("form.addEventListener('input', relayMirrorEvent);", asistente)
        self.assertNotIn("'Marca el equipo para usarlo'", asistente)
        self.assertNotIn('function openConsumableSheet', asistente)
        self.assertNotIn("requirementsGrid.querySelectorAll('.reservation-consumable__check')", asistente)
        self.assertNotIn("'#unidadesTableBody tr'", asistente)
        self.assertIn('function renderGrupoEquipo(', heredado)
        self.assertIn('function renderNoDisponibles(', heredado)
        self.assertIn('window.reservationAfterUnitsRender', heredado)
        self.assertNotIn('toggleAllUnidades', heredado)
