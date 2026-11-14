"""El modal tiene gestión propia, permisos por centro y decisiones de reserva validadas."""
from datetime import datetime, time, timedelta
from urllib.parse import urlencode

from django.contrib.auth import get_user_model
from django.test import Client, TestCase, override_settings
from django.urls import reverse
from django.utils import timezone

from apps.centros_id.areas import opciones_areas
from apps.centros_id.gestion_catalogo import PANELES, REGISTROS
from apps.centros_id.models import (
    CentroID, Componente, HorarioRecurso, Integrante, Novedad, RegistroSolicitud, SolicitudCentro, Zona,
)


class GestionCentroTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        usuario = get_user_model()
        cls.gestor = usuario.objects.create_user('gestor.modal')  # No necesita acceso al admin.
        cls.otro_usuario = usuario.objects.create_user('ajeno.modal', is_staff=True)
        cls.solicitante = usuario.objects.create_user('solicitante.modal')
        cls.centro = CentroID.objects.create(nombre='Centro del modal', sigla='CM', slug='centro-modal',
            area=opciones_areas()[0][0], proposito='Investigación aplicada', responsable=cls.gestor)
        cls.otro = CentroID.objects.create(nombre='Otro centro privado', slug='otro-modal',
            area=opciones_areas()[0][0], proposito='Otra agenda')
        cls.area = Componente.objects.create(centro=cls.centro, nombre='Área técnica', codigo='tecnica',
            tipo='laboratorio', resumen='Validación', descripcion='Validación técnica')
        cls.persona = Integrante.objects.create(centro=cls.centro, nombre='Técnico del centro', rol='tecnico')
        cls.ajena = Integrante.objects.create(centro=cls.otro, nombre='Técnica ajena', rol='tecnico')
        cls.zona = Zona.objects.create(centro=cls.centro, nombre='Sala de pruebas', codigo='SALA',
            reservable=True, estado_acceso='disponible', aforo=8, area_m2=25)
        cls.dia = timezone.localdate() + timedelta(days=3)
        cls.inicio = timezone.make_aware(datetime.combine(cls.dia, time(10)))
        for dia in range(7):
            HorarioRecurso.objects.create(centro=cls.centro, zona=cls.zona, dia=dia, abre=time(8), cierra=time(18))
        cls.solicitud = SolicitudCentro.objects.create(centro=cls.centro, usuario=cls.solicitante,
            tipo='uso', titulo='Ensayo de material', problema='Validar resistencia', resultado_esperado='Informe',
            zona=cls.zona, participantes=2, inicio_preferido=cls.inicio, fin_preferido=cls.inicio+timedelta(hours=1))
        cls.privada = SolicitudCentro.objects.create(centro=cls.otro, usuario=cls.solicitante,
            titulo='Solicitud del otro centro', problema='Reservada', resultado_esperado='Resultado')

    def setUp(self):
        self.client.force_login(self.gestor)

    def url(self, panel='resumen', tipo='', editar='', centro=None, **extras):
        return reverse('gestion_centro_id', args=[(centro or self.centro).slug]) + '?' + urlencode(
            dict(panel=panel, tipo=tipo, editar=editar, fragment=1) | extras)

    def datos(self, url, **cambios):
        formulario = self.client.get(url).context['formulario']
        datos = {}
        for nombre, campo in formulario.fields.items():
            valor = formulario[nombre].value()
            if getattr(campo.widget, 'input_type', '') == 'file':
                continue
            if isinstance(valor, bool):
                if valor:
                    datos[nombre] = 'on'
            else:
                datos[nombre] = '' if valor is None else valor
        datos.update(cambios)
        return datos

    def test_modal_solo_para_gestores_y_sin_enlace_admin(self):
        ficha = reverse('centro_id', args=[self.centro.slug])
        pagina = self.client.get(ficha)
        self.assertContains(pagina, 'id="cidGestionModal"')
        self.assertContains(pagina, 'data-cid-gestion-abrir')
        contenido = pagina.content.decode().split('id="cidFicha"', 1)[1]
        self.assertNotIn('/admin/', contenido)
        self.client.logout()
        self.assertNotContains(self.client.get(ficha), 'id="cidGestionModal"')

    def test_permisos_incluyen_gestor_sin_staff_y_excluyen_staff_ajeno(self):
        self.assertContains(self.client.get(self.url()), 'data-cid-gestion-panel')
        self.client.force_login(self.otro_usuario)
        self.assertEqual(self.client.get(self.url()).status_code, 403)
        self.assertEqual(self.client.post(self.url('configuracion'), {}).status_code, 403)
        self.client.logout()
        self.assertEqual(self.client.get(self.url()).status_code, 302)

    def test_no_lee_otro_centro_ni_sus_expedientes(self):
        self.assertEqual(self.client.get(self.url(centro=self.otro)).status_code, 403)
        self.assertEqual(self.client.get(self.url('solicitudes', 'solicitudes', self.privada.pk)).status_code, 404)
        self.assertEqual(self.client.post(self.url('solicitudes', 'solicitudes', self.privada.pk), {}).status_code, 404)
        self.assertNotContains(self.client.get(self.url('solicitudes', 'solicitudes')), self.privada.titulo)

    def test_paneles_y_todos_los_formularios_nuevos_se_renderizan(self):
        for panel, _, _ in PANELES:
            with self.subTest(panel=panel):
                self.assertContains(self.client.get(self.url(panel)), 'data-cid-gestion-panel')
        for tipo, spec in REGISTROS.items():
            if tipo == 'solicitudes':
                continue
            with self.subTest(tipo=tipo):
                self.assertContains(self.client.get(self.url(spec[0], tipo, 'nuevo')), 'data-gestion-formulario')

    def test_rutas_y_tipos_no_permitidos(self):
        for url in (self.url('inexistente'), self.url('equipo', 'solicitudes'),
                    self.url('resumen', editar='1'), self.url('solicitudes', 'solicitudes', 'nuevo')):
            self.assertEqual(self.client.get(url).status_code, 404)

    def test_avanza_solicitud_y_conserva_actor_e_historial(self):
        url = self.url('solicitudes', 'solicitudes', self.solicitud.pk)
        respuesta = self.client.post(url, self.datos(url, estado='evaluacion', motivo='Revisión técnica iniciada'), follow=True)
        self.assertContains(respuesta, 'Cambios guardados.')
        self.solicitud.refresh_from_db()
        self.assertEqual(self.solicitud.estado, 'evaluacion')
        movimiento = self.solicitud.historial.latest('fecha')
        self.assertEqual(movimiento.autor_id, self.gestor.pk)
        self.assertEqual(movimiento.detalle, 'Revisión técnica iniciada')
        self.assertEqual(movimiento.estado_anterior, 'recibida')

    def test_no_salta_estados_ni_acepta_persona_ajena(self):
        url = self.url('solicitudes', 'solicitudes', self.solicitud.pk)
        for cambios in ({'estado': 'cerrada'}, {'responsable_atencion': self.ajena.pk}):
            with self.subTest(cambios=cambios):
                respuesta = self.client.post(url, self.datos(url, **cambios))
                self.assertTrue(respuesta.context['formulario'].errors)
                self.solicitud.refresh_from_db()
                self.assertEqual(self.solicitud.estado, 'recibida')

    def test_confirma_reserva_y_rechaza_solapamiento(self):
        self.solicitud.avanzar('evaluacion')
        self.solicitud.save(actor=self.gestor)
        url = self.url('solicitudes', 'solicitudes', self.solicitud.pk)
        datos = self.datos(url, estado='aprobada', requisitos_validados='on', evidencia_requisitos='Inducción verificada',
            inicio_reservado=timezone.localtime(self.inicio).strftime('%Y-%m-%dT%H:%M'),
            fin_reservado=timezone.localtime(self.inicio+timedelta(hours=1)).strftime('%Y-%m-%dT%H:%M'))
        self.assertEqual(self.client.post(url, datos).status_code, 302)
        self.solicitud.refresh_from_db()
        self.assertEqual(self.solicitud.estado, 'aprobada')
        self.assertContains(self.client.get(self.url('agenda')), self.solicitud.titulo)
        segunda = SolicitudCentro.objects.create(centro=self.centro, usuario=self.solicitante, tipo='uso',
            titulo='Segundo ensayo', problema='Colisión', resultado_esperado='Informe', estado='evaluacion',
            zona=self.zona, participantes=2)
        url2 = self.url('solicitudes', 'solicitudes', segunda.pk)
        datos['revision'] = self.datos(url2)['revision']
        respuesta = self.client.post(url2, datos)
        self.assertContains(respuesta, 'El recurso ya está asignado')
        segunda.refresh_from_db()
        self.assertEqual(segunda.estado, 'evaluacion')

    def test_no_confirma_acceso_sin_comprobar_requisitos(self):
        self.solicitud.avanzar('evaluacion')
        self.solicitud.save(actor=self.gestor)
        url = self.url('solicitudes', 'solicitudes', self.solicitud.pk)
        respuesta = self.client.post(url, self.datos(url, estado='aprobada',
            inicio_reservado=timezone.localtime(self.inicio).strftime('%Y-%m-%dT%H:%M'),
            fin_reservado=timezone.localtime(self.inicio+timedelta(hours=1)).strftime('%Y-%m-%dT%H:%M')))
        self.assertContains(respuesta, 'Compruebe y documente los requisitos')
        self.solicitud.refresh_from_db()
        self.assertEqual(self.solicitud.estado, 'evaluacion')

    def test_conflicto_de_edicion_no_sobrescribe_otro_cambio(self):
        url = self.url('solicitudes', 'solicitudes', self.solicitud.pk)
        datos = self.datos(url, respuesta='Respuesta anterior')
        self.solicitud.respuesta = 'Respuesta de otra persona'
        self.solicitud.save(actor=self.gestor)
        respuesta = self.client.post(url, datos)
        self.assertContains(respuesta, 'cambió mientras lo editabas')
        self.solicitud.refresh_from_db()
        self.assertEqual(self.solicitud.respuesta, 'Respuesta de otra persona')

    def test_csrf_obligatorio_y_respuesta_privada_no_cacheable(self):
        cliente = Client(enforce_csrf_checks=True)
        cliente.force_login(self.gestor)
        self.assertEqual(cliente.post(self.url('configuracion'), {}).status_code, 403)
        respuesta = self.client.get(self.url())
        self.assertIn('no-store', respuesta['Cache-Control'])

    def test_guardado_de_contenido_no_altera_procedencia_ni_privilegios(self):
        novedad = Novedad.objects.create(centro=self.centro, titulo='Noticia de prueba', resumen='Detalle', es_muestra=True, fecha=timezone.localdate())
        url = self.url('contenidos', 'novedades', novedad.pk)
        datos = self.datos(url, titulo='Noticia corregida', es_muestra='', centro=self.otro.pk,
            validado_por=self.gestor.pk, responsable=self.otro_usuario.pk)
        self.assertEqual(self.client.post(url, datos).status_code, 302)
        novedad.refresh_from_db()
        self.centro.refresh_from_db()
        self.assertEqual(novedad.titulo, 'Noticia corregida')
        self.assertTrue(novedad.es_muestra)
        self.assertEqual(novedad.centro, self.centro)
        self.assertIsNone(novedad.validado_por)
        self.assertEqual(self.centro.responsable_id, self.gestor.pk)

    @override_settings(DEBUG=True, CENTROS_ID_ESCENARIOS_OPERATIVOS=('centro-modal',))
    def test_nuevo_contenido_del_escenario_conserva_su_condicion(self):
        url = self.url('contenidos', 'novedades', 'nuevo')
        respuesta = self.client.post(url, self.datos(url, titulo='Actividad local', resumen='Actividad',
            tipo='noticia', fecha=timezone.localdate().isoformat(), publicada='on'))
        self.assertEqual(respuesta.status_code, 302)
        self.assertTrue(Novedad.objects.get(titulo='Actividad local').es_muestra)

    def test_formulario_vacio_con_relaciones_obligatorias_muestra_errores(self):
        for tipo in ('sesiones', 'hitos', 'habilitaciones', 'equipos', 'archivos'):
            with self.subTest(tipo=tipo):
                respuesta = self.client.post(self.url(REGISTROS[tipo][0], tipo, 'nuevo'), {})
                self.assertEqual(respuesta.status_code, 200)
                self.assertTrue(respuesta.context['formulario'].errors)

    def test_edicion_desde_secciones_usa_panel_propio(self):
        for clave in ('presentacion', 'solicitar', 'documentos'):
            pagina = self.client.get(reverse('seccion_centro_id', args=[self.centro.slug, clave]))
            self.assertNotContains(pagina, '/admin/')
        url = self.url('contenidos', 'carpetas', 'nuevo', pestana='investigacion', seccion='proyectos')
        form = self.client.get(url).context['formulario']
        self.assertEqual(form['pestana'].value(), 'investigacion')
        self.assertEqual(form['seccion'].value(), 'proyectos')

    def test_filtros_paginacion_y_configuracion_completa_fuera_de_modal(self):
        for n in range(28):
            Novedad.objects.create(centro=self.centro, titulo=f'Noticia {n}', resumen='Detalle', fecha=timezone.localdate())
        pagina = self.client.get(self.url('contenidos', 'novedades'))
        self.assertEqual(len(pagina.context['filas']), 25)
        self.assertTrue(pagina.context['siguiente_url'])
        filtrada = self.client.get(self.url('contenidos', 'novedades', q='Noticia 27'))
        self.assertEqual(filtrada.context['pagina'].paginator.count, 1)
        completa = self.client.get(reverse('gestion_centro_id', args=[self.centro.slug]))
        self.assertContains(completa, 'data-cid-gestion-pagina')
        self.assertNotIn('/admin/', completa.content.decode().split('data-cid-gestion-pagina', 1)[1])
        self.assertEqual(RegistroSolicitud.objects.filter(solicitud=self.privada).count(), 1)

    def test_configuracion_se_guarda_sin_reasignar_gestores_y_valida_solo_por_accion(self):
        url = self.url('configuracion')
        datos = self.datos(url, lema='Atención tecnológica', adscripcion='Universidad', mision='Investigar',
            vision='Transferir', fuente_identidad='Resolución oficial', responsable=self.otro_usuario.pk)
        self.assertEqual(self.client.post(url, datos).status_code, 302)
        self.centro.refresh_from_db()
        self.assertEqual(self.centro.lema, 'Atención tecnológica')
        self.assertEqual(self.centro.responsable_id, self.gestor.pk)
        self.assertIsNone(self.centro.identidad_validada_en)
        datos = self.datos(url, accion='validar_identidad')
        self.assertEqual(self.client.post(url, datos).status_code, 302)
        self.centro.refresh_from_db()
        self.assertTrue(self.centro.identidad_validada)
        self.assertEqual(self.centro.identidad_validada_por_id, self.gestor.pk)

    def test_no_aplica_validacion_incompleta_ni_decisiones_fuera_de_configuracion(self):
        url = self.url('configuracion')
        original = self.centro.lema
        respuesta = self.client.post(url, self.datos(url, lema='No se guarda', accion='validar_estado'))
        self.assertContains(respuesta, 'Registre el respaldo institucional')
        self.centro.refresh_from_db()
        self.assertEqual(self.centro.lema, original)
        url = self.url('solicitudes', 'solicitudes', self.solicitud.pk)
        respuesta = self.client.post(url, self.datos(url, accion='validar_estado', estado='evaluacion'))
        self.assertContains(respuesta, 'Acción no reconocida')
        self.solicitud.refresh_from_db()
        self.assertEqual(self.solicitud.estado, 'recibida')
