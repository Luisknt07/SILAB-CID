"""Recursos propios, atención privada y accesos canónicos a formación."""
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, time, timedelta
from threading import Barrier

from django.contrib import admin
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.db import close_old_connections, connection
from django.test import RequestFactory, TestCase, TransactionTestCase, skipUnlessDBFeature
from django.urls import reverse
from django.utils import timezone

from apps.centros_id.carga import Cargador
from apps.centros_id.contenido import cidt
from apps.centros_id.formularios import SolicitudForm
from apps.centros_id.models import (
    BloqueoRecurso, CentroID, EquipoCentro, HabilitacionEquipo, HerramientaCentro, HorarioRecurso, Integrante,
    RegistroSolicitud, SesionAcompanamiento, SolicitudCentro, TareaSolicitud, Zona,
)
from apps.centros_id.operaciones import disponibilidad


class OperacionesCentroTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.centro = Cargador(cidt).cargar()
        cls.otro = CentroID.objects.create(nombre='Otro centro', slug='otro-operativo', sigla='OTRO')
        cls.usuario = get_user_model().objects.create_user('operacion.usuario')
        cls.ajeno = get_user_model().objects.create_user('operacion.ajeno')
        cls.gestor = get_user_model().objects.create_user('operacion.gestor', is_staff=True)
        cls.centro.gestores.add(cls.gestor)
        cls.persona = Integrante.objects.create(centro=cls.centro, nombre='Responsable técnico', rol='tecnico')
        cls.area = cls.centro.componentes.first()
        cls.zona = cls.centro.zonas.filter(reservable=True).first()
        cls.zona.estado_acceso, cls.zona.aforo = 'disponible', 8
        cls.zona.save()
        cls.equipo = EquipoCentro.objects.create(componente=cls.area, nombre='Activo individual', categoria='Pruebas',
            es_activo_individual=True, codigo='ACT-01', cantidad=1, reservable=True, requiere_supervision=False)
        cls.servicio = cls.centro.servicios.first()
        cls.dia = timezone.localdate() + timedelta(days=2)
        cls.inicio = timezone.make_aware(datetime.combine(cls.dia, time(10)))
        cls.fin = cls.inicio + timedelta(hours=1)
        for recurso in (cls.zona, cls.equipo):
            for dia in range(7):
                HorarioRecurso.objects.create(centro=cls.centro, dia=dia, abre=time(8), cierra=time(18),
                    **({'zona': recurso} if isinstance(recurso, Zona) else {'equipo': recurso}))

    def solicitud(self, **extras):
        datos = dict(centro=self.centro, usuario=self.usuario, titulo='Solicitud confidencial de empresa',
            problema='Proceso reservado', resultado_esperado='Validación', tipo='uso', estado='evaluacion',
            zona=self.zona, inicio_reservado=self.inicio, fin_reservado=self.fin, participantes=2,
            requisitos_validados=True, evidencia_requisitos='Verificación interna')
        return SolicitudCentro.objects.create(**(datos | extras))

    def detalle(self, solicitud):
        return reverse('solicitud_detalle_centro_id', args=[self.centro.slug, solicitud.pk])

    def recursos(self, **parametros):
        return self.client.get(reverse('seccion_centro_id', args=[self.centro.slug, 'recursos']), parametros)

    def confirmar(self, solicitud):
        solicitud.avanzar('aprobada')
        solicitud.save(actor=self.gestor)

    def test_servicio_explica_entradas_metodo_entrega_y_condiciones(self):
        self.servicio.alcance, self.servicio.entradas = 'Alcance definido', 'Muestra identificada'
        self.servicio.metodo, self.servicio.aceptacion = 'Método técnico', 'Tolerancia acordada'
        self.servicio.formato_entrega, self.servicio.plazo = 'Informe firmado', 'Plazo desde recepción conforme'
        self.servicio.save()
        pagina = self.client.get(reverse('fragmento_centro_id', args=[self.centro.slug, 'servicio', self.servicio.pk]))
        for texto in (self.servicio.alcance, self.servicio.entradas, self.servicio.metodo, self.servicio.aceptacion,
                      self.servicio.formato_entrega, self.servicio.plazo):
            self.assertContains(pagina, texto)

    def test_tarifa_no_se_publica_sin_respaldo_y_vigencia(self):
        self.servicio.tarifa = 'USD 987.65 por ensayo'
        self.servicio.save()
        for url in (reverse('seccion_centro_id', args=[self.centro.slug, 'portafolio']),
                    reverse('fragmento_centro_id', args=[self.centro.slug, 'servicio', self.servicio.pk])):
            self.assertNotContains(self.client.get(url), self.servicio.tarifa)
        self.servicio.tarifa_fuente = 'Resolución de tarifas'
        self.servicio.tarifa_fecha, self.servicio.tarifa_hasta = self.dia - timedelta(days=3), self.dia
        self.servicio.save()
        self.assertTrue(self.servicio.tarifa_documentada)
        self.assertContains(self.client.get(reverse('fragmento_centro_id',
            args=[self.centro.slug, 'servicio', self.servicio.pk])), self.servicio.tarifa)
        self.servicio.tarifa_hasta = timezone.localdate() - timedelta(days=1)
        self.assertFalse(self.servicio.tarifa_documentada)

    def test_servicio_suspendido_se_informa_pero_no_se_pide(self):
        self.servicio.estado_oferta = 'suspendido'
        self.servicio.save()
        pagina = self.client.get(reverse('fragmento_centro_id', args=[self.centro.slug, 'servicio', self.servicio.pk]))
        self.assertContains(pagina, 'Temporalmente suspendido')
        self.assertNotContains(pagina, 'Consultar servicio')
        self.assertNotContains(pagina, 'Solicitar servicio')
        datos = dict(tipo='servicio', perfil='externo', titulo='Ensayo', problema='Necesidad',
                     resultado_esperado='Informe', servicio=self.servicio.pk)
        form = SolicitudForm(datos, centro=self.centro)
        self.assertFalse(form.is_valid())
        self.assertIn('servicio', form.errors)

    def test_formularios_no_muestran_campos_de_otras_operaciones(self):
        reto = SolicitudForm(centro=self.centro, initial={'tipo': 'reto'})
        uso = SolicitudForm(centro=self.centro, initial={'tipo': 'uso'})
        asesoria = SolicitudForm(centro=self.centro, initial={'tipo': 'asesoria'})
        self.assertNotIn('zona', reto.fields)
        self.assertNotIn('servicio', uso.fields)
        self.assertIn('equipo', uso.fields)
        self.assertTrue(uso.fields['inicio_preferido'].required)
        self.assertNotIn('zona', asesoria.fields)
        self.assertNotIn('participantes', asesoria.fields)

    def test_pedir_uso_no_confirma_ni_ocupa_ventana(self):
        self.client.force_login(self.usuario)
        url = reverse('solicitar_centro_id', args=[self.centro.slug])
        respuesta = self.client.post(url, dict(tipo='uso', perfil='interno', titulo='Usar activo', problema='Práctica',
            resultado_esperado='Registro', equipo=self.equipo.pk, inicio_preferido=self.inicio.strftime('%Y-%m-%dT%H:%M'),
            fin_preferido=self.fin.strftime('%Y-%m-%dT%H:%M'), participantes=1))
        self.assertEqual(respuesta.status_code, 302)
        solicitud = SolicitudCentro.objects.get(usuario=self.usuario)
        self.assertEqual(solicitud.estado, 'recibida')
        self.assertIsNone(solicitud.inicio_reservado)
        self.assertEqual(len(disponibilidad(self.equipo, self.dia)), 1)
        self.assertEqual(solicitud.historial.first().autor_id, self.usuario.pk)

    def test_familia_no_se_puede_convertir_en_reserva_sin_individualizar(self):
        self.equipo.es_activo_individual = False
        with self.assertRaises(ValidationError):
            self.equipo.full_clean()
        self.equipo.save()
        solicitud = self.solicitud(zona=None, equipo=self.equipo)
        with self.assertRaises(ValidationError):
            self.confirmar(solicitud)

    def test_recurso_bloqueado_o_en_mantenimiento_no_se_confirma(self):
        solicitud = self.solicitud(zona=None, equipo=self.equipo)
        self.equipo.estado = 'mantenimiento'
        self.equipo.save()
        with self.assertRaises(ValidationError):
            self.confirmar(solicitud)
        self.equipo.estado = 'operativo'
        self.equipo.save()
        BloqueoRecurso.objects.create(centro=self.centro, equipo=self.equipo, inicio=self.inicio,
                                      fin=self.fin, motivo='Diagnóstico interno privado')
        with self.assertRaises(ValidationError):
            solicitud.save()

    def test_confirmacion_exige_horario_y_no_inventa_disponibilidad(self):
        solicitud = self.solicitud()
        self.zona.horarios.all().delete()
        with self.assertRaises(ValidationError):
            self.confirmar(solicitud)
        self.assertEqual(disponibilidad(self.zona, self.dia), [])

    def test_confirmacion_respeta_aforo_y_comprobacion_de_requisitos(self):
        for campos in ({'participantes': 9}, {'requisitos_validados': False}, {'evidencia_requisitos': ''}):
            solicitud = self.solicitud(**campos)
            with self.assertRaises(ValidationError):
                self.confirmar(solicitud)

    def test_intervalos_contiguos_se_permiten_sin_margen(self):
        uno = self.solicitud()
        self.confirmar(uno)
        dos = self.solicitud(inicio_reservado=self.fin, fin_reservado=self.fin + timedelta(hours=1))
        self.confirmar(dos)
        self.assertEqual(SolicitudCentro.objects.filter(estado='aprobada').count(), 2)

    def test_preparacion_y_cierre_impiden_contiguedad_y_salida_del_horario(self):
        self.zona.margen_minutos = 15
        self.zona.save()
        uno = self.solicitud()
        self.confirmar(uno)
        dos = self.solicitud(inicio_reservado=self.fin, fin_reservado=self.fin + timedelta(hours=1))
        with self.assertRaises(ValidationError):
            self.confirmar(dos)
        fuera = self.solicitud(inicio_reservado=self.inicio.replace(hour=8), fin_reservado=self.inicio.replace(hour=9))
        with self.assertRaises(ValidationError):
            self.confirmar(fuera)

    def test_habilitacion_se_consulta_por_equipo_usuario_fecha_y_revocacion(self):
        self.equipo.requiere_induccion = True
        self.equipo.save()
        solicitud = self.solicitud(zona=None, equipo=self.equipo)
        with self.assertRaises(ValidationError):
            self.confirmar(solicitud)
        habilitacion = HabilitacionEquipo.objects.create(equipo=self.equipo, usuario=self.usuario,
            desde=self.dia, hasta=self.dia, evidencia='Evaluación práctica', verificador=self.gestor)
        solicitud.save(actor=self.gestor)
        habilitacion.revocada = True
        habilitacion.save()
        solicitud.avanzar('ejecucion')
        with self.assertRaises(ValidationError):
            solicitud.save(actor=self.gestor)

    def test_equipo_supervisado_necesita_persona_disponible(self):
        self.equipo.requiere_supervision = True
        self.equipo.save()
        solicitud = self.solicitud(zona=None, equipo=self.equipo)
        with self.assertRaises(ValidationError):
            self.confirmar(solicitud)
        solicitud.supervisor = self.persona
        solicitud.save(actor=self.gestor)
        otro = self.solicitud(supervisor=self.persona)
        with self.assertRaises(ValidationError):
            self.confirmar(otro)

    def test_calendario_publico_no_divulga_identidades_ni_motivos(self):
        solicitud = self.solicitud()
        self.confirmar(solicitud)
        BloqueoRecurso.objects.create(centro=self.centro, zona=self.zona, inicio=self.fin + timedelta(hours=1),
                                      fin=self.fin + timedelta(hours=2), motivo='Incidencia confidencial')
        pagina = self.recursos(zona=self.zona.pk, fecha=self.dia.isoformat())
        self.assertEqual(pagina.status_code, 200)
        for texto in (solicitud.titulo, solicitud.problema, self.usuario.username, 'Incidencia confidencial'):
            self.assertNotContains(pagina, texto)
        self.assertEqual([(v['inicio'].hour, v['fin'].hour) for v in pagina.context['ventanas']], [(8, 10), (11, 12), (13, 18)])

    def test_recurso_ajeno_o_de_area_no_publicada_no_se_consulta(self):
        ajeno = Zona.objects.create(centro=self.otro, nombre='Espacio privado', codigo='X', nivel='1', area_m2=10, reservable=True)
        self.assertEqual(self.recursos(zona=ajeno.pk).status_code, 404)
        self.area.publicado = False
        self.area.save()
        self.assertEqual(self.recursos(equipo=self.equipo.pk).status_code, 404)

    def test_disponibilidad_rechaza_fecha_invalida_o_fuera_del_horizonte(self):
        for fecha in ('no-fecha', (self.dia + timedelta(days=91)).isoformat()):
            pagina = self.recursos(zona=self.zona.pk, fecha=fecha)
            self.assertTrue(pagina.context['disponibilidad_form'].errors)
            self.assertIsNone(pagina.context['ventanas'])

    def test_confirmar_espacio_y_equipo_es_una_sola_transaccion(self):
        ocupada = self.solicitud(zona=None, equipo=self.equipo)
        self.confirmar(ocupada)
        conjunta = self.solicitud(equipo=self.equipo)
        with self.assertRaises(ValidationError):
            self.confirmar(conjunta)
        conjunta.refresh_from_db()
        self.assertEqual(conjunta.estado, 'evaluacion')
        libre = self.solicitud()
        self.confirmar(libre)

    def test_historial_registra_autor_estado_y_reprogramacion(self):
        solicitud = self.solicitud()
        self.confirmar(solicitud)
        solicitud.inicio_reservado += timedelta(hours=2)
        solicitud.fin_reservado += timedelta(hours=2)
        solicitud.save(actor=self.gestor, motivo='Fecha acordada con el solicitante')
        self.assertEqual(solicitud.historial.count(), 3)
        ultimo = solicitud.historial.last()
        self.assertEqual(ultimo.autor_id, self.gestor.pk)
        self.assertIn('Fecha acordada', ultimo.detalle)
        self.assertIn('Horario:', ultimo.detalle)

    def test_guardado_rechaza_saltos_y_reasignar_propietario(self):
        solicitud = self.solicitud()
        solicitud.estado = 'cerrada'
        with self.assertRaises(ValidationError):
            solicitud.save(actor=self.gestor)
        solicitud.refresh_from_db()
        solicitud.usuario = self.ajeno
        with self.assertRaises(ValidationError):
            solicitud.save(actor=self.gestor)

    def test_expediente_solo_lo_ve_titular_o_gestion_del_centro(self):
        solicitud = self.solicitud(notas_internas='NOTA INTERNA SECRETA', evidencia_requisitos='EVIDENCIA PRIVADA')
        url = self.detalle(solicitud)
        self.assertEqual(self.client.get(url).status_code, 302)
        self.client.force_login(self.ajeno)
        self.assertEqual(self.client.get(url).status_code, 404)
        for usuario in (self.usuario, self.gestor):
            self.client.force_login(usuario)
            pagina = self.client.get(url)
            self.assertContains(pagina, solicitud.referencia)
            self.assertNotContains(pagina, 'NOTA INTERNA SECRETA')
            self.assertNotContains(pagina, 'EVIDENCIA PRIVADA')

    def test_cancelacion_del_titular_conserva_historial_y_libera_recurso(self):
        solicitud = self.solicitud()
        self.confirmar(solicitud)
        self.client.force_login(self.usuario)
        respuesta = self.client.post(self.detalle(solicitud), {'accion': 'cancelar', 'detalle': 'Cambio de actividad'})
        self.assertEqual(respuesta.status_code, 302)
        solicitud.refresh_from_db()
        self.assertEqual(solicitud.estado, 'cancelada')
        self.assertIsNotNone(solicitud.cerrada_en)
        self.assertEqual(solicitud.historial.last().autor_id, self.usuario.pk)
        self.assertEqual(len(disponibilidad(self.zona, self.dia)), 1)
        self.client.post(self.detalle(solicitud), {'accion': 'cancelar', 'detalle': 'Reintento'})
        self.assertEqual(solicitud.historial.count(), 3)

    def test_get_no_cancela_y_ajeno_no_puede_aportar_informacion(self):
        solicitud = self.solicitud()
        self.client.force_login(self.usuario)
        self.client.get(self.detalle(solicitud), {'accion': 'cancelar', 'detalle': 'No aplicar'})
        solicitud.refresh_from_db()
        self.assertEqual(solicitud.estado, 'evaluacion')
        self.client.force_login(self.ajeno)
        self.assertEqual(self.client.post(self.detalle(solicitud), {'detalle': 'Interferencia'}).status_code, 404)

    def test_acompanamiento_aprobado_exige_responsable_diagnostico_y_plan(self):
        solicitud = self.solicitud(tipo='asesoria', zona=None)
        with self.assertRaises(ValidationError):
            self.confirmar(solicitud)
        solicitud.responsable_atencion, solicitud.diagnostico, solicitud.plan = self.persona, 'Diagnóstico', 'Plan acordado'
        solicitud.save(actor=self.gestor)
        self.client.force_login(self.usuario)
        self.assertContains(self.client.get(self.detalle(solicitud)), 'Plan acordado')

    def test_sesiones_evitan_doble_asignacion_del_especialista(self):
        solicitud = self.solicitud(tipo='asesoria', zona=None, responsable_atencion=self.persona,
                                    diagnostico='Necesidad', plan='Dos sesiones')
        self.confirmar(solicitud)
        SesionAcompanamiento.objects.create(solicitud=solicitud, responsable=self.persona, inicio=self.inicio,
                                            fin=self.fin, modalidad='Presencial', notas_internas='Nota reservada')
        with self.assertRaises(ValidationError):
            SesionAcompanamiento.objects.create(solicitud=solicitud, responsable=self.persona,
                inicio=self.inicio + timedelta(minutes=30), fin=self.fin + timedelta(hours=1), modalidad='Virtual')
        uso = self.solicitud(supervisor=self.persona)
        with self.assertRaises(ValidationError):
            self.confirmar(uso)
        self.client.force_login(self.usuario)
        self.assertNotContains(self.client.get(self.detalle(solicitud)), 'Nota reservada')

    def test_cancelar_atencion_cancela_sesiones_futuras_sin_borrarlas(self):
        solicitud = self.solicitud(tipo='asesoria', zona=None, responsable_atencion=self.persona,
                                    diagnostico='Necesidad', plan='Plan')
        self.confirmar(solicitud)
        sesion = SesionAcompanamiento.objects.create(solicitud=solicitud, responsable=self.persona,
            inicio=self.inicio, fin=self.fin, modalidad='Virtual')
        solicitud.avanzar('cancelada')
        solicitud.save(actor=self.gestor, motivo='Atención reorientada')
        sesion.refresh_from_db()
        self.assertEqual(sesion.estado, 'cancelada')

    def test_compromiso_cumplido_requiere_evidencia_y_se_comparte_en_expediente(self):
        solicitud = self.solicitud()
        tarea = TareaSolicitud(solicitud=solicitud, titulo='Aportar datos', a_cargo='solicitante', plazo=self.dia, completada=True)
        with self.assertRaises(ValidationError):
            tarea.save()
        tarea.evidencia = 'Datos recibidos y revisados'
        tarea.save()
        self.client.force_login(self.usuario)
        self.assertContains(self.client.get(self.detalle(solicitud)), tarea.evidencia)

    def test_herramienta_solo_publica_despues_de_revisar_metodo_y_version(self):
        h = HerramientaCentro.objects.create(centro=self.centro, nombre='Modelo de prueba', tipo='educativa',
            objetivo='Aprender', entradas='Masa en kg; de 1 a 10', metodo='Conservación de masa', salidas='kg de producto',
            supuestos='Sin pérdidas', limites='Solo educativo', version='1', enlace='https://example.org/modelo', publicado=True)
        self.assertNotContains(self.recursos(), h.nombre)
        h.validar(self.gestor)
        self.assertContains(self.recursos(), h.nombre)
        h.version = '2'
        h.save(update_fields=['version'])
        self.assertNotContains(self.recursos(), h.nombre)
        with self.assertRaises(ValidationError):
            h.validar(self.ajeno)

    def test_admin_acota_las_opciones_de_centro_al_gestor(self):
        panel = admin.site._registry[HorarioRecurso]
        request = RequestFactory().get('/')
        request.user = self.gestor
        campo = panel.formfield_for_foreignkey(HorarioRecurso._meta.get_field('centro'), request)
        self.assertEqual(list(campo.queryset), [self.centro])

    def test_cancelacion_con_guardado_parcial_conserva_fecha_y_historial(self):
        solicitud = self.solicitud()
        solicitud.avanzar('cancelada')
        solicitud.save(actor=self.usuario, motivo='Cambio de necesidad', update_fields=['estado'])
        solicitud.refresh_from_db()
        self.assertIsNotNone(solicitud.cerrada_en)
        self.assertEqual(solicitud.historial.last().estado_nuevo, 'cancelada')

    def test_calibracion_debe_cubrir_el_dia_reservado(self):
        self.equipo.calibracion_requerida = True
        self.equipo.calibracion_hasta = self.dia - timedelta(days=1)
        self.equipo.calibracion_evidencia = 'Certificado técnico vigente hoy'
        self.equipo.save()
        solicitud = self.solicitud(zona=None, equipo=self.equipo)
        with self.assertRaises(ValidationError):
            self.confirmar(solicitud)
        self.assertEqual(disponibilidad(self.equipo, self.dia), [])
        self.equipo.calibracion_hasta = self.dia
        self.equipo.save()
        solicitud.save(actor=self.gestor)
        self.assertEqual(solicitud.estado, 'aprobada')

    def test_bloqueo_no_invalida_silenciosamente_una_confirmacion_existente(self):
        solicitud = self.solicitud()
        self.confirmar(solicitud)
        with self.assertRaises(ValidationError):
            BloqueoRecurso.objects.create(centro=self.centro, zona=self.zona, inicio=self.inicio,
                                          fin=self.fin, motivo='Mantenimiento previsto')
        self.assertEqual(BloqueoRecurso.objects.count(), 0)

    def test_horarios_no_se_cruzan_ni_apuntan_a_recursos_ajenos(self):
        with self.assertRaises(ValidationError):
            HorarioRecurso.objects.create(centro=self.centro, zona=self.zona, dia=self.dia.weekday(),
                                          abre=time(9), cierra=time(12))
        with self.assertRaises(ValidationError):
            HorarioRecurso.objects.create(centro=self.otro, equipo=self.equipo, dia=1, abre=time(18), cierra=time(19))

    def test_usuario_no_puede_aprobar_su_propia_solicitud(self):
        solicitud = self.solicitud()
        solicitud.avanzar('aprobada')
        with self.assertRaises(ValidationError):
            solicitud.save(actor=self.usuario)
        solicitud.refresh_from_db()
        self.assertEqual(solicitud.estado, 'evaluacion')

    def test_habilitacion_no_se_emite_sin_verificador_autorizado(self):
        with self.assertRaises(ValidationError):
            HabilitacionEquipo.objects.create(equipo=self.equipo, usuario=self.usuario,
                desde=self.dia, hasta=self.dia, evidencia='Curso aprobado', verificador=self.ajeno)

    def test_contexto_del_equipo_se_conserva_al_autenticarse(self):
        from urllib.parse import parse_qs, urlsplit
        pagina = self.client.get(reverse('solicitar_centro_id', args=[self.centro.slug]),
                                {'tipo': 'uso', 'equipo': self.equipo.pk})
        destino = parse_qs(urlsplit(pagina.context['entrar_url']).query)['next'][0]
        self.client.force_login(self.usuario)
        pagina = self.client.get(destino)
        self.assertEqual(pagina.context['formulario'].initial['equipo'], self.equipo.pk)

    def test_solicitud_de_recurso_no_admite_intervalo_pasado_ni_cero_participantes(self):
        form = SolicitudForm(dict(tipo='uso', perfil='interno', titulo='Uso', problema='Práctica', resultado_esperado='Registro',
            equipo=self.equipo.pk, inicio_preferido='2020-01-01T10:00', fin_preferido='2020-01-01T11:00',
            participantes=0), centro=self.centro)
        self.assertFalse(form.is_valid())
        self.assertIn('inicio_preferido', form.errors)
        self.assertIn('participantes', form.errors)


    def test_un_centro_sin_oferta_abre_retos_y_no_ofrece_formularios_imposibles(self):
        self.client.force_login(self.usuario)
        url = reverse('solicitar_centro_id', args=[self.otro.slug])
        pagina = self.client.get(url)
        self.assertEqual(pagina.context['tipo_seleccionado'], 'reto')
        self.assertEqual(pagina.context['formulario'].initial['tipo'], 'reto')
        self.assertNotIn('servicio', dict(pagina.context['tipos_solicitud']))
        self.assertNotIn('uso', dict(pagina.context['tipos_solicitud']))
        for tipo in ('servicio', 'uso'):
            with self.subTest(tipo=tipo):
                pagina = self.client.get(url, {'tipo': tipo})
                self.assertIsNone(pagina.context['formulario'])
                self.assertContains(pagina, 'Plantear una necesidad')
                self.assertContains(pagina, 'Mis solicitudes a este centro')
                self.client.post(url, {'tipo': tipo, 'titulo': 'Intento sin oferta'})
        self.assertFalse(self.otro.solicitudes.exists())

    def test_servicio_elegido_se_valida_antes_de_autenticarse(self):
        url = reverse('solicitar_centro_id', args=[self.otro.slug])
        self.assertEqual(self.client.get(url, {'tipo': 'servicio', 'servicio': self.servicio.pk}).status_code, 404)
        url = reverse('solicitar_centro_id', args=[self.centro.slug])
        pagina = self.client.get(url, {'tipo': 'servicio', 'servicio': self.servicio.pk})
        self.assertContains(pagina, self.servicio.nombre)
        self.servicio.estado_oferta = 'suspendido'
        self.servicio.save()
        self.assertEqual(self.client.get(url, {'tipo': 'servicio', 'servicio': self.servicio.pk}).status_code, 404)

    def test_tipo_invalido_en_post_muestra_el_error_del_campo_oculto(self):
        self.client.force_login(self.usuario)
        url = reverse('solicitar_centro_id', args=[self.centro.slug])
        self.assertEqual(self.client.get(url, {'tipo': 'inexistente'}).status_code, 404)
        pagina = self.client.post(url, {'tipo': 'inexistente', 'perfil': 'interno', 'titulo': 'Propuesta',
                                      'problema': 'Necesidad', 'resultado_esperado': 'Informe'})
        self.assertContains(pagina, str(pagina.context['formulario']['tipo'].errors), html=True)
        self.assertFalse(SolicitudCentro.objects.filter(usuario=self.usuario).exists())

    def test_formulario_solo_ofrece_recursos_habilitados(self):
        self.zona.estado_acceso = 'bloqueado'
        self.zona.save()
        self.equipo.calibracion_requerida = True
        self.equipo.calibracion_hasta = timezone.localdate() - timedelta(days=1)
        self.equipo.save()
        formulario = SolicitudForm(centro=self.centro, initial={'tipo': 'uso'})
        self.assertNotIn(self.zona, formulario.fields['zona'].queryset)
        self.assertNotIn(self.equipo, formulario.fields['equipo'].queryset)

    def test_equipo_muestra_induccion_supervision_y_vigencia_sin_fuente_privada(self):
        self.equipo.requiere_induccion = self.equipo.requiere_supervision = self.equipo.calibracion_requerida = True
        self.equipo.calibracion_hasta, self.equipo.calibracion_evidencia = self.dia, 'Referencia privada de calibración'
        self.equipo.save()
        pagina = self.recursos(equipo=self.equipo.pk)
        self.assertContains(pagina, 'Requiere inducción y habilitación vigente')
        self.assertContains(pagina, 'El uso requiere supervisión')
        self.assertContains(pagina, self.dia.strftime('%d/%m/%Y'))
        self.assertNotContains(pagina, self.equipo.calibracion_evidencia)

    def test_oferta_sujeta_a_evaluacion_y_suspension_tienen_acciones_coherentes(self):
        url = reverse('fragmento_centro_id', args=[self.centro.slug, 'servicio', self.servicio.pk])
        self.assertContains(self.client.get(url), 'Consultar servicio')
        self.servicio.estado_oferta = 'disponible'
        self.servicio.save()
        self.assertContains(self.client.get(url), 'Solicitar servicio')
        self.centro.servicios.update(estado_oferta='suspendido')
        pagina = self.client.get(reverse('seccion_centro_id', args=[self.centro.slug, 'portafolio']))
        self.assertNotContains(pagina, 'Solicitar un servicio')
        self.assertNotContains(pagina, '?tipo=servicio')
        self.assertContains(pagina, 'Temporalmente suspendido')


class ConfirmacionesConcurrentesTests(TransactionTestCase):
    @skipUnlessDBFeature('has_select_for_update')
    def test_dos_confirmaciones_simultaneas_de_espacio(self):
        self._comprobar_concurrencia('zona')

    @skipUnlessDBFeature('has_select_for_update')
    def test_dos_confirmaciones_simultaneas_de_equipo(self):
        self._comprobar_concurrencia('equipo')

    def _comprobar_concurrencia(self, tipo):
        centro = Cargador(cidt).cargar()
        usuario = get_user_model().objects.create_user('concurrencia.usuario')
        gestor = get_user_model().objects.create_user('concurrencia.gestor')
        centro.gestores.add(gestor)
        zona = centro.zonas.filter(reservable=True).first()
        zona.estado_acceso, zona.aforo = 'disponible', 5
        zona.save()
        dia = timezone.localdate() + timedelta(days=3)
        inicio = timezone.make_aware(datetime.combine(dia, time(10)))
        recurso = zona if tipo == 'zona' else EquipoCentro.objects.create(componente=centro.componentes.first(),
            nombre='Activo concurrente', codigo='CON-01', cantidad=1, es_activo_individual=True, reservable=True,
            requiere_supervision=False)
        HorarioRecurso.objects.create(centro=centro, dia=dia.weekday(), abre=time(8), cierra=time(18), **{tipo: recurso})
        solicitudes = [SolicitudCentro.objects.create(centro=centro, usuario=usuario, **{tipo: recurso}, tipo='uso',
            titulo=f'Competidora {i}', problema='Necesidad', resultado_esperado='Uso', estado='evaluacion',
            participantes=1, requisitos_validados=True, evidencia_requisitos='Revisión',
            inicio_reservado=inicio, fin_reservado=inicio + timedelta(hours=1)) for i in range(2)]
        barrera = Barrier(2)

        def confirmar(pk):
            close_old_connections()
            try:
                if not connection.settings_dict['NAME'].startswith('test_'):
                    raise RuntimeError('La concurrencia solo se prueba en la base aislada.')
                s = SolicitudCentro.objects.get(pk=pk)
                actor = get_user_model().objects.get(pk=gestor.pk)
                s.avanzar('aprobada')
                barrera.wait(timeout=10)
                try:
                    s.save(actor=actor)
                    return 'confirmada'
                except ValidationError:
                    return 'ocupada'
            finally:
                close_old_connections()

        with ThreadPoolExecutor(max_workers=2) as executor:
            resultados = list(executor.map(confirmar, [s.pk for s in solicitudes]))
        self.assertCountEqual(resultados, ['confirmada', 'ocupada'])
        self.assertEqual(SolicitudCentro.objects.filter(**{tipo: recurso}, estado='aprobada').count(), 1)
        self.assertEqual(RegistroSolicitud.objects.filter(estado_nuevo='aprobada').count(), 1)
