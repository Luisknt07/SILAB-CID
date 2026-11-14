"""Permisos académicos, tarifas nuevas y conservación de operaciones emitidas."""

from datetime import time, timedelta
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.contrib.auth.models import AnonymousUser
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone
from django.utils.translation import override

from apps.gestion_unidades.presentation.permisos import puede_crear_guias_unidad
from apps.reservas.presentation.cotizaciones import calcular_costo_referencial_recursos, calcular_cotizacion, calcular_liquidacion_real, clasificar_reserva, clasificar_usuario, recalcular_estimacion_reserva
from apps.reservas.presentation.forms import GuiaPracticaForm
from apps.reservas.presentation.guias import _puede_ver_guia, puede_editar_guia
from apps.reservas.presentation.views import _puede_crear_guia
from apps.core.usuarios.pertenencia import pertenencia_actual
from apps.core.usuarios.verificacion import estado_verificacion, registrar_revision
from apps.reservas.models.reservas import CatalogoActividadReserva, GuiaActividadReserva, Reserva
from apps.gestion_unidades.models.operaciones import ConfiguracionOperativaUnidad
from apps.laboratorios.operacion.models.fablab import FablabService
from apps.directorio_unidades.models.core import Unidad
from apps.core.models.usuarios_base import UserProfile
from tests.integration.utiles import identificar


class PertenenciaGestionTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        User = get_user_model()
        cls.revisor = User.objects.create_superuser('verificacion.gestion', password=None)
        cls.docente = User.objects.create_user('docente.gestion')
        cls.staff = User.objects.create_user('editor.gestion', is_staff=True)
        cls.estudiante = User.objects.create_user('estudiante.gestion')
        cls.externo = User.objects.create_user('externo.gestion')
        for usuario in [cls.docente, cls.staff]:
            identificar(usuario)
        identificar(cls.estudiante, tipo_usuario='estudiante')
        identificar(cls.externo, tipo_usuario='externo', facultad='externo',
                    carrera='', institucion='Organización externa')
        cls.unidad = Unidad.objects.create(
            nombre='Unidad de pertenencia', slug='unidad-pertenencia',
            dependencia='laboratorios', fecha_inicio=timezone.localdate(),
        )
        cls.otra = Unidad.objects.create(
            nombre='Otra unidad', slug='otra-pertenencia', dependencia='laboratorios',
            fecha_inicio=timezone.localdate(), administrador=cls.staff,
        )
        cls.configuracion, _ = ConfiguracionOperativaUnidad.objects.get_or_create(unidad=cls.unidad)
        cls.configuracion.tarifa_referencial_hora_espacio = Decimal('20')
        cls.configuracion.aporte_institucional_recursos_pct = Decimal('75')
        cls.configuracion.save()
        cls.actividad = CatalogoActividadReserva.objects.create(
            nombre='Actividad privada', unidad=cls.unidad, creado_por=cls.docente,
            proposito_codigo='docencia_practica', subtipo_actividad='practica_curricular',
            visibilidad='privada', estado_publicacion='borrador',
        )
        cls.guia = GuiaActividadReserva.objects.create(
            actividad=cls.actividad, titulo='Guía propia histórica', es_estructurada=True,
            estado_publicacion='borrador', visibilidad='privada',
        )
        cls.servicio = FablabService.objects.create(
            code='SRV-PERTENENCIA', nombre='Servicio de pertenencia', unidad=cls.unidad,
            costo_diseno_completo=Decimal('100'), descuento_estudiante=Decimal('50'),
            descuento_personal=Decimal('25'), descuento_externo=Decimal('0'),
        )

    def decidir(self, usuario, decision='aprobada', **extras):
        perfil = UserProfile.objects.select_related('user').get(user_id=usuario.pk)
        return registrar_revision(
            perfil_id=perfil.pk, revisor=self.revisor, decision=decision,
            fundamento='Registro sintético cotejado.', referencia='QA-PERTENENCIA-42',
            huella=estado_verificacion(perfil)['huella'], **extras,
        )

    def cotizar(self, usuario):
        return calcular_cotizacion([self.servicio], 'diseno_completo', usuario)

    def recursos(self, usuario):
        return calcular_costo_referencial_recursos(
            [], usuario, configuracion=self.configuracion, incluye_espacio=True, duracion_horas=2,
        )

    def reserva(self, cotizacion=None, tipo='docente'):
        reserva = Reserva.objects.create(
            laboratorio=self.unidad, usuario=self.docente, fecha=timezone.localdate(),
            hora_inicio=time(8), hora_fin=time(10), duracion=2, tipo_solicitud='recursos',
            incluye_espacio=True, tipo_usuario_solicitante=tipo,
            desglose_cotizacion=cotizacion or {},
        )
        reserva.refresh_from_db()
        return reserva

    def test_declaracion_staff_y_procedencia_no_conceden_privilegios(self):
        for usuario in [self.docente, self.estudiante, self.staff, self.externo, AnonymousUser(), None]:
            with self.subTest(usuario=getattr(usuario, 'pk', None)):
                self.assertEqual(clasificar_usuario(usuario)[0], 'externo')
                if usuario is not None:
                    self.assertFalse(puede_crear_guias_unidad(usuario, self.unidad))
        self.assertFalse(_puede_crear_guia(self.docente, self.unidad))
        self.assertEqual(self.cotizar(self.estudiante)['total'], '0.00')
        self.assertEqual(self.recursos(self.docente)['aporte_institucional'], '40.00')

    def test_aprobacion_habilita_autoria_y_tarifa_sin_asignar_roles(self):
        self.decidir(self.docente)
        self.decidir(self.estudiante)
        self.assertTrue(puede_crear_guias_unidad(self.docente, self.unidad))
        self.assertTrue(_puede_crear_guia(self.docente, self.unidad))
        self.assertFalse(puede_crear_guias_unidad(self.estudiante, self.unidad))
        cotizacion = self.cotizar(self.estudiante)
        self.assertEqual(cotizacion['segmento'], 'estudiante')
        self.assertEqual(cotizacion['total'], '0.00')
        self.assertEqual(self.recursos(self.docente)['aporte_institucional'], '40.00')
        resumen = cotizacion['pertenencia_tarifaria']
        self.assertEqual(resumen['estado'], 'aprobada')
        self.assertIsNotNone(resumen['revision_id'])
        self.assertNotIn('identidad_revisada', resumen)
        self.assertNotIn('fundamento', resumen)
        self.assertFalse(self.docente.is_staff)

    def test_externo_aprobado_no_recibe_tarifa_interna(self):
        self.decidir(self.externo)
        self.assertTrue(pertenencia_actual(self.externo)['aprobada'])
        self.assertEqual(clasificar_usuario(self.externo)[0], 'externo')
        self.assertFalse(puede_crear_guias_unidad(self.externo, self.unidad))

    def test_revocacion_conserva_documentos_propios_y_cotizacion(self):
        self.decidir(self.docente)
        original = self.recursos(self.docente)
        reserva = self.reserva(original)
        self.decidir(self.docente, 'revocada')
        self.assertFalse(puede_crear_guias_unidad(self.docente, self.unidad))
        self.assertTrue(puede_editar_guia(self.docente, self.guia))
        self.assertTrue(_puede_ver_guia(self.docente, self.guia))
        self.assertEqual(self.recursos(self.docente)['segmento'], 'externo')
        reserva.refresh_from_db()
        self.assertEqual(reserva.desglose_cotizacion, original)
        self.assertEqual(clasificar_reserva(reserva)[0], 'personal')
        actualizada = recalcular_estimacion_reserva(reserva)
        self.assertEqual(actualizada['segmento'], 'personal')
        self.assertEqual(actualizada['pertenencia_tarifaria'], original['pertenencia_tarifaria'])
        self.assertEqual(actualizada['aporte_institucional'], '40.00')

    def test_identidad_modificada_se_consulta_sin_cache(self):
        self.decidir(self.docente)
        self.assertEqual(clasificar_usuario(self.docente)[0], 'personal')
        UserProfile.objects.filter(user=self.docente).update(tipo_usuario='estudiante')
        self.assertEqual(clasificar_usuario(self.docente)[0], 'externo')
        self.assertFalse(puede_crear_guias_unidad(self.docente, self.unidad))
        self.assertEqual(self.cotizar(self.docente)['pertenencia_tarifaria']['estado'], 'datos_modificados')

    def test_vencimiento_y_cuenta_inactiva_se_respetan(self):
        self.decidir(self.docente, vigente_hasta=timezone.localdate())
        with self.settings():
            from unittest.mock import patch
            with patch('apps.core.usuarios.verificacion.timezone.localdate',
                       return_value=timezone.localdate() + timedelta(days=1)):
                self.assertEqual(clasificar_usuario(self.docente)[0], 'externo')
                self.assertFalse(puede_crear_guias_unidad(self.docente, self.unidad))
        get_user_model().objects.filter(pk=self.docente.pk).update(is_active=False)
        self.assertEqual(clasificar_usuario(self.docente)[0], 'externo')

    def test_staff_de_otra_unidad_no_lee_guia_o_fuentes_privadas(self):
        self.assertTrue(puede_crear_guias_unidad(self.staff, self.otra))
        self.assertFalse(_puede_ver_guia(self.staff, self.guia))
        self.assertFalse(puede_editar_guia(self.staff, self.guia))
        self.client.force_login(self.staff)
        self.assertEqual(self.client.get(reverse('ver_guia_actividad', args=[self.guia.pk])).status_code, 404)
        self.assertEqual(self.client.get(reverse('nueva_guia_practica', args=[self.unidad.slug])).status_code, 403)
        form = GuiaPracticaForm(unidad=self.unidad, usuario=self.staff)
        self.assertFalse(form.fields['actividad_existente'].queryset.filter(pk=self.actividad.pk).exists())
        lista = self.client.get(reverse('lista_guias_practica', args=[self.unidad.slug]))
        self.assertEqual(lista.status_code, 200)
        self.assertNotContains(lista, self.guia.titulo)
        detalle = self.client.get(self.unidad.get_absolute_url())
        self.assertNotContains(detalle, self.actividad.nombre)
        self.assertNotContains(detalle, self.guia.titulo)
        from apps.formacion.presentation.practicas import _actividades_para
        self.assertFalse(_actividades_para(self.staff, self.unidad).filter(pk=self.actividad.pk).exists())

    def test_segmento_emitido_prevalece_sobre_tipo_periodico_y_perfil(self):
        reserva = self.reserva({'segmento': 'externo', 'total': '40.00'}, tipo='docente')
        self.decidir(self.docente)
        self.assertEqual(clasificar_reserva(reserva)[0], 'externo')
        recalculada = recalcular_estimacion_reserva(reserva)
        self.assertEqual(recalculada['total'], '0.00')
        self.assertEqual(recalculada['pertenencia_tarifaria']['version'], 0)

    def test_legado_sin_cotizacion_usa_tipo_historico_sin_inferir_perfil_actual(self):
        self.decidir(self.docente)
        self.assertEqual(clasificar_reserva(self.reserva(tipo='estudiante'))[0], 'estudiante')
        self.assertEqual(clasificar_reserva(self.reserva(tipo=''))[0], 'externo')

    def test_liquidacion_conserva_segmento_emitido_tras_aprobar_perfil(self):
        reserva = self.reserva({'segmento': 'externo', 'total': '40.00'})
        self.decidir(self.docente)
        liquidacion = calcular_liquidacion_real(
            reserva, inicio=time(8), fin=time(10), recursos={}, consumos=[],
        )
        self.assertEqual(liquidacion['segmento'], 'externo')
        reserva.refresh_from_db()
        self.assertEqual(reserva.desglose_cotizacion, {'segmento': 'externo', 'total': '40.00'})

    def test_modal_y_lista_presentan_la_politica_es_en(self):
        self.client.force_login(self.docente)
        respuesta = self.client.get(self.unidad.get_absolute_url())
        self.assertContains(respuesta, 'data-tariff-segment="externo"')
        self.assertContains(respuesta, 'data-can-author-guides="false"')
        self.client.cookies['slcid_language'] = 'en'
        with override('en'):
            respuesta = self.client.get(reverse('lista_guias_practica', args=[self.unidad.slug]))
            self.assertContains(respuesta, 'valid verified faculty status')
            self.assertEqual(clasificar_usuario(self.docente)[1], 'External user')
