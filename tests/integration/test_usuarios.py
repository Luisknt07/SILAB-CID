from datetime import date, time, timedelta

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from apps.core.usuarios.vigencia import estado_perfil
from apps.core.models.periodos import PeriodoAcademico, VersionCalendarioAcademico, VinculacionUsuarioPeriodo
from apps.gestion_unidades.models.espacios import ResponsableUnidad
from apps.reservas.models.reservas import Reserva
from apps.directorio_unidades.models.core import Unidad
from tests.integration.utiles import identificar


class RegistroInstitucionalTests(TestCase):
    def test_registro_guarda_clasificacion_para_reportes(self):
        response = self.client.post(reverse('register'), {
            'username': 'nueva.estudiante',
            'first_name': 'María',
            'last_name': 'Paz',
            'email': 'maria.paz@upec.edu.ec',
            'password1': 'Clave-Institucional-2026',
            'password2': 'Clave-Institucional-2026',
            'tipo_usuario': 'estudiante',
            'facultad': 'agropecuarias_ambientales',
            'carrera': 'computacion',
            'nivel_academico': 'quinto_semestre',
            'cedula': '2026-0010',
            'institucion': '',
        })

        self.assertRedirects(response, reverse('profile'))
        perfil = get_user_model().objects.get(username='nueva.estudiante').profile
        self.assertEqual(perfil.tipo_usuario, 'estudiante')
        self.assertEqual(perfil.facultad, 'agropecuarias_ambientales')
        self.assertEqual(perfil.carrera, 'computacion')
        self.assertEqual(perfil.institucion, 'UPEC')
        self.assertTrue(perfil.perfil_reserva_completo)

    def test_usuario_externo_debe_indicar_institucion(self):
        response = self.client.post(reverse('register'), {
            'username': 'usuario.externo',
            'first_name': 'Usuario',
            'last_name': 'Externo',
            'email': 'externo@example.com',
            'password1': 'Clave-Externa-2026',
            'password2': 'Clave-Externa-2026',
            'tipo_usuario': 'externo',
            'facultad': '',
            'carrera': '',
            'nivel_academico': '',
            'cedula': '',
            'institucion': '',
        })

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Indica la institución')
        self.assertFalse(get_user_model().objects.filter(username='usuario.externo').exists())


class PerfilInstitucionalTests(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user(
            username='perfil.prueba',
            password='Clave-Perfil-2026',
            first_name='Ana',
            last_name='Paredes',
            email='ana.paredes@upec.edu.ec',
        )
        self.client.force_login(self.user)

    def datos_base(self, **overrides):
        data = {
            'first_name': 'Ana',
            'last_name': 'Paredes',
            'email': 'ana.paredes@upec.edu.ec',
            'telefono': '0999999999',
            'tipo_usuario': 'estudiante',
            'facultad': 'agropecuarias_ambientales',
            'carrera': 'computacion',
            'nivel_academico': 'quinto_semestre',
            'cedula': '2026-1001',
            'institucion': '',
            'cargo': '',
            'biografia': '',
        }
        data.update(overrides)
        return data

    def test_el_catalogo_ofrece_las_carreras_de_cada_facultad(self):
        """El selector filtra por facultad y no deja fuera ninguna carrera."""
        respuesta = self.client.get(reverse('profile'))

        carreras = {
            item['value']: item['facultad'] for item in respuesta.context['carreras_perfil']
        }
        self.assertEqual(carreras['turismo'], 'agropecuarias_ambientales')
        self.assertEqual(carreras['enfermeria'], 'salud_educacion')
        self.assertEqual(carreras['comercio_exterior'], 'comercio_administracion')
        # Cada carrera declara su facultad: el formulario las filtra con ese dato.
        self.assertTrue(all(carreras.values()))
        self.assertContains(respuesta, 'Carrera de Turismo')

    def test_perfil_muestra_carrera_junto_a_su_facultad(self):
        self.user.profile.tipo_usuario = 'administrativo'
        self.user.profile.facultad = 'administracion_central'
        self.user.profile.save()

        response = self.client.get(reverse('profile'))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'name="carrera"')
        self.assertContains(response, 'id="profileCarrera"')
        self.assertContains(
            response,
            'value="computacion" data-facultad="agropecuarias_ambientales"',
        )
        self.assertContains(response, 'Carrera o programa académico')

    def test_estudiante_actualiza_carrera_para_reportes(self):
        response = self.client.post(reverse('profile_edit'), self.datos_base())

        self.assertRedirects(response, reverse('profile'))
        self.user.refresh_from_db()
        self.user.profile.refresh_from_db()
        self.assertEqual(self.user.profile.facultad, 'agropecuarias_ambientales')
        self.assertEqual(self.user.profile.carrera, 'computacion')
        self.assertTrue(self.user.profile.perfil_reserva_completo)

    def test_carrera_incompatible_reabre_modal_y_conserva_datos(self):
        response = self.client.post(
            reverse('profile_edit'),
            self.datos_base(
                facultad='salud_educacion',
                carrera='computacion',
            ),
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'La facultad no corresponde a la carrera seleccionada.')
        self.assertContains(response, 'data-open-on-load="true"')
        self.assertContains(
            response,
            'value="computacion" data-facultad="agropecuarias_ambientales" selected',
        )
        self.user.profile.refresh_from_db()
        self.assertEqual(self.user.profile.carrera or '', '')

    def test_docente_debe_seleccionar_carrera(self):
        response = self.client.post(
            reverse('profile_edit'),
            self.datos_base(
                tipo_usuario='docente',
                carrera='',
                nivel_academico='',
                cedula='',
            ),
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Selecciona la carrera o programa académico')

    def test_personal_administrativo_puede_asociar_una_carrera(self):
        response = self.client.post(
            reverse('profile_edit'),
            self.datos_base(
                tipo_usuario='administrativo',
                nivel_academico='',
                cedula='',
            ),
        )

        self.assertRedirects(response, reverse('profile'))
        self.user.profile.refresh_from_db()
        self.assertEqual(self.user.profile.carrera, 'computacion')
        self.assertEqual(self.user.profile.nivel_academico or '', '')
        self.assertEqual(self.user.profile.cedula or '', '')

    def test_usuario_externo_limpia_vinculacion_upec(self):
        profile = self.user.profile
        profile.tipo_usuario = 'estudiante'
        profile.facultad = 'agropecuarias_ambientales'
        profile.carrera = 'computacion'
        profile.nivel_academico = 'quinto_semestre'
        profile.cedula = '2026-1001'
        profile.institucion = 'UPEC'
        profile.save()

        response = self.client.post(
            reverse('profile_edit'),
            self.datos_base(
                tipo_usuario='externo',
                facultad='',
                carrera='',
                nivel_academico='',
                cedula='',
                institucion='Fundación de Innovación del Carchi',
            ),
        )

        self.assertRedirects(response, reverse('profile'))
        profile.refresh_from_db()
        self.assertEqual(profile.facultad, 'externo')
        self.assertEqual(profile.carrera or '', '')
        self.assertEqual(profile.institucion, 'Fundación de Innovación del Carchi')


class AccesoInstitucionalTests(TestCase):
    """El acceso identifica a la unidad y respeta a dónde iba la persona."""

    def setUp(self):
        self.usuario = get_user_model().objects.create_user(
            username='acceso.prueba',
            password='Clave-Acceso-2026',
        )

    def test_el_acceso_se_presenta_con_la_unidad_y_sin_enlaces_muertos(self):
        respuesta = self.client.get(reverse('login'))

        self.assertEqual(respuesta.status_code, 200)
        self.assertContains(respuesta, 'Laboratorios y Centros de Investigación y Desarrollo')
        self.assertContains(respuesta, reverse('account_reset_password'))
        self.assertContains(respuesta, 'autocomplete="current-password"')
        # Restos de la plantilla comprada: inglés y enlace sin destino.
        self.assertNotContains(respuesta, 'MAGIC IS IN THE DETAILS')
        self.assertNotContains(respuesta, 'Forget password?')

    def test_recuperar_la_contrasena_usa_la_misma_cara_institucional(self):
        """La pantalla de allauth venía cruda, en inglés y con su propio menú."""
        respuesta = self.client.get(reverse('account_reset_password'))

        self.assertEqual(respuesta.status_code, 200)
        self.assertContains(respuesta, 'Recuperar la contraseña')
        self.assertContains(respuesta, 'Sistema de Laboratorios y Centros I+D')
        # La cabecera del portal, no el «Menú:» suelto de la plantilla original.
        self.assertContains(respuesta, 'Laboratorios y Unidades')
        self.assertNotContains(respuesta, 'Menú:')
        self.assertNotContains(respuesta, 'Forgotten your password')

    def test_entrar_devuelve_a_la_pagina_que_pidio_la_sesion(self):
        destino = reverse('profile')

        respuesta = self.client.post(
            f"{reverse('login')}?next={destino}",
            {'username': 'acceso.prueba', 'password': 'Clave-Acceso-2026'},
        )

        self.assertRedirects(respuesta, destino)

    def test_un_destino_ajeno_no_saca_a_la_persona_del_portal(self):
        respuesta = self.client.post(
            f"{reverse('login')}?next=https://sitio-ajeno.example/",
            {'username': 'acceso.prueba', 'password': 'Clave-Acceso-2026'},
        )

        self.assertRedirects(respuesta, reverse('home'))


class CierreDeSesionTests(TestCase):
    """Salir está a la vista y solo ocurre cuando la persona lo pide."""

    def setUp(self):
        self.usuario = get_user_model().objects.create_user(
            username='sesion.prueba',
            password='Clave-Sesion-2026',
        )
        self.client.force_login(self.usuario)

    def test_la_cabecera_y_el_perfil_ofrecen_cerrar_sesion(self):
        respuesta = self.client.get(reverse('profile'))

        self.assertContains(respuesta, f'action="{reverse("logout")}"')
        self.assertContains(respuesta, 'Cerrar sesión')
        # La sesion vive en la barra superior: usuario visible y cierre a la vista.
        self.assertContains(respuesta, 'data-home-session')
        self.assertContains(respuesta, 'sesion.prueba')

    def test_cerrar_sesion_exige_el_envio_de_la_persona(self):
        # Un GET ajeno (una imagen, un enlace) no puede sacar a nadie.
        self.assertEqual(self.client.get(reverse('logout')).status_code, 405)
        self.assertIn('_auth_user_id', self.client.session)

        respuesta = self.client.post(reverse('logout'))

        self.assertRedirects(respuesta, reverse('home'))
        self.assertNotIn('_auth_user_id', self.client.session)


class PerfilPorRolTests(TestCase):
    """El perfil resume lo que cada persona tiene en los laboratorios."""

    def setUp(self):
        User = get_user_model()
        self.responsable = User.objects.create_user(
            username='responsable.perfil',
            password='Clave-Perfil-2026',
            first_name='Luis',
            last_name='Chamorro',
            email='luis.chamorro@upec.edu.ec',
        )
        self.solicitante = User.objects.create_user(
            username='solicitante.perfil',
            password='Clave-Perfil-2026',
            first_name='Sara',
            last_name='Benítez',
            email='sara.benitez@upec.edu.ec',
        )
        self.unidad = Unidad.objects.create(
            nombre='Laboratorio del perfil',
            slug='laboratorio-del-perfil',
            dependencia='laboratorios',
            descripcion='Unidad para verificar el perfil por rol.',
            fecha_inicio=date(2026, 1, 1),
            administrador=self.responsable,
        )

    def _reserva(self, **extra):
        datos = {
            'laboratorio': self.unidad,
            'usuario': self.solicitante,
            'fecha': date(2026, 12, 10),
            'hora_inicio': time(9),
            'hora_fin': time(11),
            'equipo_codigo': 'EQ-PERFIL',
            'equipo_nombre': 'Equipo del perfil',
            'estado': 'pendiente',
        }
        datos.update(extra)
        return Reserva.objects.create(**datos)

    def test_quien_reserva_ve_su_seguimiento_y_entra_al_expediente(self):
        proxima = self._reserva()
        self._reserva(fecha=date(2026, 12, 17), estado='completada')
        self.client.force_login(self.solicitante)

        respuesta = self.client.get(reverse('profile'))

        self.assertEqual(respuesta.status_code, 200)
        resumen = respuesta.context['reservas_perfil']
        self.assertEqual(resumen['total'], 2)
        self.assertEqual(resumen['abiertas'], 1)
        self.assertEqual(resumen['proxima'], proxima)
        # El enlace es el mismo que usan los avisos y la lista de guías.
        self.assertContains(respuesta, proxima.url_seguimiento)
        self.assertContains(respuesta, 'Mis reservas')
        # Sin unidades a su cargo no se le ofrece el panel de gestión.
        self.assertEqual(respuesta.context['unidades_perfil'], [])
        self.assertNotContains(respuesta, 'Abrir el panel')
        # Nada de cifras inventadas ni interruptores que no guardan nada.
        self.assertNotContains(respuesta, 'Certificaciones')
        self.assertNotContains(respuesta, 'Modo oscuro')
        self.assertNotContains(respuesta, 'Sesiones Activas')

    def test_quien_atiende_la_unidad_llega_al_panel_desde_su_perfil(self):
        self._reserva()
        self.client.force_login(self.responsable)

        respuesta = self.client.get(reverse('profile'))

        self.assertEqual(respuesta.status_code, 200)
        unidades = respuesta.context['unidades_perfil']
        self.assertEqual(len(unidades), 1)
        self.assertEqual(unidades[0]['unidad'], self.unidad)
        self.assertEqual(unidades[0]['pendientes'], 1)
        self.assertContains(respuesta, reverse('gestion_unidad', args=[self.unidad.slug]))
        self.assertContains(respuesta, 'solicitud esperan tu decisión')
        self.assertContains(respuesta, 'se trabajan en el panel de cada unidad')
        self.assertIn('Personal de Laboratorio del perfil', respuesta.context['roles_perfil'])
        # El perfil no repite la bandeja de la campana ni el detalle del panel.
        self.assertNotContains(respuesta, 'Novedades de tus solicitudes')


class CedulaYPerfilProfesionalTests(TestCase):
    """La cédula identifica a cualquiera; el perfil profesional solo a quien lo publica."""

    def setUp(self):
        self.estudiante = get_user_model().objects.create_user(
            username='cedula.estudiante',
            password='Clave-Cedula-2026',
            first_name='Iván',
            last_name='Pozo',
            email='ivan.pozo@upec.edu.ec',
        )
        self.client.force_login(self.estudiante)

    def _datos(self, **extra):
        datos = {
            'first_name': 'Iván',
            'last_name': 'Pozo',
            'email': 'ivan.pozo@upec.edu.ec',
            'tipo_usuario': 'estudiante',
            'facultad': 'agropecuarias_ambientales',
            'carrera': 'computacion',
            'nivel_academico': 'quinto_semestre',
            # Cédula ecuatoriana válida (dígito verificador correcto).
            'cedula': '0401234562',
            'institucion': '',
            'telefono': '',
            'cargo': '',
            'biografia': '',
        }
        datos.update(extra)
        return datos

    def test_el_estudiante_registra_su_cedula_y_no_un_codigo(self):
        respuesta = self.client.get(reverse('profile'))

        self.assertContains(respuesta, 'Cédula o documento de identidad')
        self.assertNotContains(respuesta, 'Código de estudiante')
        # Sin cédula el perfil de un estudiante no está listo para reservar.
        perfil = self.estudiante.profile
        perfil.tipo_usuario = 'estudiante'
        perfil.facultad = 'agropecuarias_ambientales'
        perfil.carrera = 'computacion'
        perfil.nivel_academico = 'quinto_semestre'
        perfil.save()
        self.assertIn('cédula o documento de identidad', perfil.campos_faltantes_reserva())

    def test_una_cedula_ecuatoriana_mal_escrita_no_pasa(self):
        respuesta = self.client.post(reverse('profile_edit'), self._datos(cedula='0401234567'))

        self.assertEqual(respuesta.status_code, 200)
        self.assertContains(respuesta, 'La cédula no es válida')
        self.estudiante.profile.refresh_from_db()
        self.assertFalse(self.estudiante.profile.cedula)

    def test_un_pasaporte_extranjero_se_acepta_como_documento(self):
        respuesta = self.client.post(reverse('profile_edit'), self._datos(cedula='AB1234567'))

        self.assertRedirects(respuesta, reverse('profile'))
        self.estudiante.profile.refresh_from_db()
        self.assertEqual(self.estudiante.profile.cedula, 'AB1234567')

    def test_al_estudiante_no_se_le_pide_cargo_ni_biografia(self):
        respuesta = self.client.get(reverse('profile'))

        self.assertFalse(respuesta.context['perfil_publico'])
        self.assertNotContains(respuesta, 'Perfil profesional')

    def test_quien_atiende_una_unidad_publica_su_perfil_profesional(self):
        unidad = Unidad.objects.create(
            nombre='Laboratorio del equipo humano',
            slug='laboratorio-equipo-humano',
            dependencia='laboratorios',
            descripcion='Unidad para verificar la ficha del personal.',
            fecha_inicio=date(2026, 1, 1),
            administrador=self.estudiante,
        )
        responsable = ResponsableUnidad.objects.create(
            unidad=unidad,
            usuario=self.estudiante,
            rol='laboratorista',
        )

        respuesta = self.client.get(reverse('profile'))
        self.assertTrue(respuesta.context['perfil_publico'])
        self.assertContains(respuesta, 'Perfil profesional')

        guardado = self.client.post(reverse('profile_edit'), self._datos(
            tipo_usuario='administrativo',
            carrera='',
            nivel_academico='',
            cargo='Laboratorista de manufactura',
        ))
        self.assertRedirects(guardado, reverse('profile'))

        # Lo que escribe en su perfil describe su ficha si la unidad no lo hizo.
        responsable = ResponsableUnidad.objects.get(pk=responsable.pk)
        self.assertEqual(responsable.descripcion_publica, 'Laboratorista de manufactura')
        responsable.descripcion = 'Atiende impresión 3D y corte láser'
        responsable.save(update_fields=['descripcion'])
        self.assertEqual(responsable.descripcion_publica, 'Atiende impresión 3D y corte láser')


class DatosObligatoriosTests(TestCase):
    """Sin datos institucionales al día no se usan las funciones."""

    def setUp(self):
        self.usuario = get_user_model().objects.create_user(
            username='sin.datos',
            password='Clave-Datos-2026',
            first_name='Sin',
            last_name='Datos',
            email='sin.datos@upec.edu.ec',
        )
        self.client.force_login(self.usuario)

    def test_el_portal_se_lee_pero_las_funciones_esperan(self):
        # Leer el portal no exige nada: la cuenta incompleta navega.
        self.assertEqual(self.client.get(reverse('home')).status_code, 200)

        # El asistente recibe el aviso en JSON, que es lo que sabe mostrar.
        respuesta = self.client.get(reverse('obtener_reservas_usuario'))

        self.assertEqual(respuesta.status_code, 403)
        self.assertIn('Completa y confirma tus datos', respuesta.json()['error'])
        self.assertEqual(respuesta.json()['perfil_url'], reverse('profile'))

    def test_una_navegacion_vuelve_al_perfil_con_el_formulario_abierto(self):
        respuesta = self.client.get(
            reverse('obtener_reservas_usuario'), HTTP_ACCEPT='text/html'
        )

        self.assertRedirects(respuesta, f"{reverse('profile')}?completar=1")
        perfil = self.client.get(f"{reverse('profile')}?completar=1")
        self.assertContains(perfil, 'Completa tus datos para usar los laboratorios')
        self.assertContains(perfil, 'data-open-on-load="true"')

    def test_al_completar_el_perfil_se_abren_las_funciones(self):
        identificar(self.usuario, tipo_usuario='docente')

        respuesta = self.client.get(reverse('obtener_reservas_usuario'))

        self.assertEqual(respuesta.status_code, 200)


class SemestrePorPeriodoTests(TestCase):
    """El semestre avanza con el período y el irregular lo corrige."""

    def setUp(self):
        self.estudiante = get_user_model().objects.create_user(
            username='estudiante.periodo',
            password='Clave-Periodo-2026',
            first_name='Rosa',
            last_name='Andrade',
            email='rosa.andrade@upec.edu.ec',
        )
        identificar(
            self.estudiante,
            tipo_usuario='estudiante',
            nivel_academico='quinto_semestre',
        )
        self.anterior = self._periodo('2026-A', 'A', date(2026, 3, 2), date(2026, 7, 31))
        hoy = timezone.localdate()
        self.actual = self._periodo(
            '2026-B', 'B', hoy - timedelta(days=10), hoy + timedelta(days=60)
        )

    def _periodo(self, codigo, ciclo, inicio, fin):
        periodo = PeriodoAcademico.objects.create(
            codigo=codigo,
            anio_referencia=2026,
            ciclo=ciclo,
            tipo='ordinario',
            ambito='carreras_centros',
            estado='borrador',
        )
        VersionCalendarioAcademico.objects.create(
            periodo=periodo,
            numero=1,
            fecha_inicio_clases=inicio,
            fecha_fin_clases=fin,
            fecha_fin_periodo=fin,
            vigente=True,
        )
        periodo.estado = 'publicado'
        periodo.save(update_fields=['estado', 'actualizado_en'])
        return periodo

    def test_el_sistema_propone_el_semestre_siguiente_y_espera_confirmacion(self):
        VinculacionUsuarioPeriodo.objects.create(
            usuario=self.estudiante,
            periodo=self.anterior,
            tipo_usuario='estudiante',
            facultad='agropecuarias_ambientales',
            carrera='computacion',
            nivel_academico='quinto_semestre',
            institucion='UPEC',
        )

        estado = estado_perfil(self.estudiante)

        self.assertEqual(estado['periodo'], self.actual)
        self.assertEqual(estado['propuesta']['nivel_academico'], 'sexto_semestre')
        self.assertTrue(estado['propuesta']['avanzado'])
        # Hay algo que decidir: hasta confirmarlo no se usan las funciones.
        self.assertTrue(estado['requiere_confirmacion'])
        self.assertFalse(estado['vigente'])

        self.client.force_login(self.estudiante)
        bloqueada = self.client.get(reverse('obtener_reservas_usuario'))
        self.assertEqual(bloqueada.status_code, 403)

    def test_el_estudiante_irregular_corrige_lo_propuesto_al_confirmar(self):
        VinculacionUsuarioPeriodo.objects.create(
            usuario=self.estudiante,
            periodo=self.anterior,
            tipo_usuario='estudiante',
            facultad='agropecuarias_ambientales',
            carrera='computacion',
            nivel_academico='quinto_semestre',
            institucion='UPEC',
        )
        self.client.force_login(self.estudiante)

        # Repite quinto porque arrastra materias: confirma lo que corresponde.
        respuesta = self.client.post(reverse('profile_edit'), {
            'first_name': 'Rosa',
            'last_name': 'Andrade',
            'email': 'rosa.andrade@upec.edu.ec',
            'tipo_usuario': 'estudiante',
            'facultad': 'agropecuarias_ambientales',
            'carrera': 'computacion',
            'nivel_academico': 'quinto_semestre',
            'cedula': 'PRB-IRREGULAR',
            'institucion': '',
            'telefono': '',
            'cargo': '',
            'biografia': '',
        })

        self.assertRedirects(respuesta, reverse('profile'))
        vinculacion = VinculacionUsuarioPeriodo.objects.get(
            usuario=self.estudiante, periodo=self.actual
        )
        self.assertEqual(vinculacion.nivel_academico, 'quinto_semestre')
        self.assertTrue(estado_perfil(self.estudiante)['vigente'])
        self.assertEqual(self.client.get(reverse('obtener_reservas_usuario')).status_code, 200)

    def test_quien_no_cambia_de_semestre_se_vincula_sin_interrumpirse(self):
        docente = get_user_model().objects.create_user(
            username='docente.periodo',
            password='Clave-Periodo-2026',
            email='docente.periodo@upec.edu.ec',
        )
        identificar(docente, tipo_usuario='docente')

        estado = estado_perfil(docente)

        self.assertTrue(estado['vigente'])
        self.assertFalse(estado['requiere_confirmacion'])
        # La vinculación del período queda registrada igual, para los reportes.
        self.assertTrue(
            VinculacionUsuarioPeriodo.objects.filter(
                usuario=docente, periodo=self.actual, estado='activa'
            ).exists()
        )
