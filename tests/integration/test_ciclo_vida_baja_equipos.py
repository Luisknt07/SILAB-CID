"""El retiro técnico conserva activos y decisiones, sin autorizar la baja patrimonial."""

from datetime import date, timedelta
from io import BytesIO
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch

from django.contrib import admin
from django.contrib.auth import get_user_model
from django.core import signing
from django.core.exceptions import PermissionDenied, ValidationError
from django.core.files.uploadedfile import SimpleUploadedFile
from django.forms import modelform_factory
from django.test import RequestFactory, override_settings
from pypdf import PdfWriter

from apps.directorio_unidades.models.core import Unidad
from apps.core.roles import MODULOS_OPERATIVOS
from apps.formacion.models.practicas import RegistroAuditoriaUnidad
from apps.gestion_unidades.models.espacios import ResponsableUnidad
from apps.gestion_unidades.presentation.activacion import alternar_equipo
from apps.gestion_unidades.presentation.auditoria import instantanea
from apps.gestion_unidades.presentation.permisos import puede_operar_modulo_unidad
from apps.recursos.admin.equipos import UnidadEquipoAdmin
from apps.recursos.models.mantenimiento import EventoCicloVidaEquipo
from apps.recursos.models.unidades import UnidadEquipo
from apps.recursos.presentation.ciclo_vida_equipo import (
    ALCANCE_RETIRO, CAMPOS_CICLO, PREFIJO_CICLO, UnidadEquipoCicloVidaForm,
    SALT_CICLO, guardar_ciclo_vida,
)
from tests.integration.test_ficha_equipo import BaseDeFicha
from tests.integration.utiles import identificar


class CicloVidaBajaEquipoTests(BaseDeFicha):
    def retirar(self, equipo=None, **cambios):
        equipo = equipo or self.equipo
        equipo.fecha_baja = self.hoy
        equipo.motivo_baja = 'dano_irreparable'
        equipo.observacion_baja = 'Diagnóstico técnico 04: motor averiado; conservar en bodega hasta trámite patrimonial.'
        for campo, valor in cambios.items():
            setattr(equipo, campo, valor)
        return equipo

    def sustituto(self, codigo='FIC-SUS-01', unidad=None):
        return UnidadEquipo.objects.create(
            codigo_unidad=codigo, laboratorio=unidad or self.unidad, equipo=self.tipo,
            activa=True, estado_unidad='disponible', fecha_adquisicion=self.hoy,
        )

    def pdf(self):
        archivo = BytesIO()
        escritor = PdfWriter()
        escritor.add_blank_page(width=300, height=400)
        escritor.write(archivo)
        return SimpleUploadedFile('diagnostico.pdf', archivo.getvalue(), content_type='application/pdf')

    def formulario(self, datos, **kwargs):
        self.equipo.refresh_from_db()
        formulario = modelform_factory(UnidadEquipo, form=UnidadEquipoCicloVidaForm, fields=[
            'laboratorio', 'fecha_baja', 'motivo_baja', 'observacion_baja', 'reemplazado_por',
        ])
        if 'ciclo_version' not in datos:
            apertura = formulario(instance=self.equipo, usuario=self.coordinador)
            datos = {**datos, 'ciclo_version': apertura.initial['ciclo_version']}
        return formulario(datos, instance=self.equipo, usuario=self.coordinador, **kwargs)

    def datos_retiro(self, **cambios):
        return {'laboratorio': self.unidad.pk, 'fecha_baja': self.hoy.isoformat(),
                'motivo_baja': 'dano_irreparable', 'observacion_baja': 'Diagnóstico del motor y referencia TEC-04.',
                'reemplazado_por': '', **cambios}

    def test_el_uso_y_la_antiguedad_no_inventan_una_baja(self):
        self.equipo.fecha_adquisicion = date(2000, 1, 1)
        self.equipo.vida_util_anios = 3
        self.equipo.estado_unidad = 'obsoleto'
        self.equipo.save()
        self.equipo.refresh_from_db()
        self.assertIsNone(self.equipo.fecha_baja)
        self.assertFalse(self.equipo.eventos_ciclo_vida.filter(tipo='baja').exists())

    @override_settings(CITT_EXIGIR_EQUIPOS_VERIFICADOS=False)
    def test_el_retiro_no_borra_el_equipo_ni_permite_reservarlo_o_publicarlo(self):
        guardar_ciclo_vida(self.retirar(), self.coordinador)
        self.equipo.refresh_from_db()
        self.assertFalse(self.equipo.activa)
        self.assertEqual(self.equipo.estado_unidad, 'no_disponible')
        self.assertTrue(UnidadEquipo.objects.filter(pk=self.equipo.pk).exists())
        self.assertFalse(self.equipo.disponible_para_reserva)
        self.assertFalse(self.equipo.es_publico)
        self.assertFalse(UnidadEquipo.objects.publicos().filter(pk=self.equipo.pk).exists())
        # Incluso una importación que omitiera save no vuelve reservable un retirado.
        UnidadEquipo.objects.filter(pk=self.equipo.pk).update(activa=True, estado_unidad='disponible')
        self.equipo.refresh_from_db()
        self.assertFalse(self.equipo.disponible_para_reserva)
        self.assertFalse(self.equipo.es_publico)
        self.assertFalse(UnidadEquipo.objects.publicos().filter(pk=self.equipo.pk).exists())

    def test_el_evento_conserva_autor_justificacion_y_alcance_tecnico(self):
        guardar_ciclo_vida(self.retirar(), self.coordinador)
        evento = self.equipo.eventos_ciclo_vida.get(tipo='baja')
        self.assertEqual(evento.usuario, self.coordinador)
        self.assertEqual(evento.unidad, self.unidad)
        self.assertTrue(evento.descripcion.startswith(PREFIJO_CICLO))
        self.assertIn(self.equipo.observacion_baja, evento.descripcion)
        self.assertIn(ALCANCE_RETIRO, evento.descripcion)
        auditoria = RegistroAuditoriaUnidad.objects.get(entidad='recursos.UnidadEquipo', objeto_id=str(self.equipo.pk))
        self.assertEqual(auditoria.usuario, self.coordinador)
        self.assertEqual(auditoria.datos_nuevos['alcance'], ALCANCE_RETIRO)

    def test_el_respaldo_legible_se_adjunta_una_sola_vez(self):
        with TemporaryDirectory() as carpeta, override_settings(MEDIA_ROOT=carpeta):
            guardar_ciclo_vida(self.retirar(), self.coordinador, evidencia=self.pdf())
            evento = self.equipo.eventos_ciclo_vida.get(tipo='baja')
            self.assertTrue(evento.evidencia.storage.exists(evento.evidencia.name))
            self.assertEqual(len(list(Path(carpeta).rglob('*.pdf'))), 1)
            self.assertEqual(self.equipo.eventos_ciclo_vida.exclude(evidencia='').count(), 1)

    def test_una_falla_de_auditoria_revierte_retiro_evento_y_archivo_nuevo(self):
        with TemporaryDirectory() as carpeta, override_settings(MEDIA_ROOT=carpeta):
            with patch('apps.recursos.presentation.ciclo_vida_equipo.registrar_auditoria', side_effect=RuntimeError('fallo')):
                with self.assertRaises(RuntimeError):
                    guardar_ciclo_vida(self.retirar(), self.coordinador, evidencia=self.pdf())
            self.equipo.refresh_from_db()
            self.assertIsNone(self.equipo.fecha_baja)
            self.assertFalse(self.equipo.eventos_ciclo_vida.filter(tipo='baja').exists())
            self.assertEqual(list(Path(carpeta).rglob('*.pdf')), [])

    def test_no_se_acepta_un_archivo_renombrado_como_pdf(self):
        archivo = SimpleUploadedFile('respaldo.pdf', b'<html>contenido falso</html>')
        with self.assertRaises(ValidationError):
            guardar_ciclo_vida(self.retirar(), self.coordinador, evidencia=archivo)
        self.equipo.refresh_from_db()
        self.assertIsNone(self.equipo.fecha_baja)

    def test_un_respaldo_excesivo_no_se_guarda(self):
        archivo = self.pdf()
        archivo.size = 26 * 1024 * 1024
        with self.assertRaisesMessage(ValidationError, '25 MB'):
            guardar_ciclo_vida(self.retirar(), self.coordinador, evidencia=archivo)
        self.equipo.refresh_from_db()
        self.assertIsNone(self.equipo.fecha_baja)

    def test_un_usuario_sin_delegacion_no_puede_retirar(self):
        ajeno = get_user_model().objects.create_user('sin-permiso-baja', password='clave')
        with self.assertRaises(PermissionDenied):
            guardar_ciclo_vida(self.retirar(), ajeno)
        self.equipo.refresh_from_db()
        self.assertIsNone(self.equipo.fecha_baja)

    def test_fecha_motivo_y_justificacion_son_obligatorios_y_coherentes(self):
        casos = [({'fecha_baja': self.hoy + timedelta(days=1)}, 'fecha_baja'),
                 ({'fecha_baja': self.equipo.fecha_adquisicion - timedelta(days=1)}, 'fecha_baja'),
                 ({'motivo_baja': ''}, 'motivo_baja'), ({'observacion_baja': '  '}, 'observacion_baja'),
                 ({'fecha_baja': None}, 'fecha_baja')]
        for cambios, campo in casos:
            with self.subTest(cambios=cambios):
                self.equipo.refresh_from_db()
                with self.assertRaises(ValidationError) as error:
                    self.retirar(**cambios).save()
                self.assertIn(campo, error.exception.message_dict)

    def test_sustitucion_real_conserva_la_cadena_y_el_activo_original(self):
        sustituto = self.sustituto()
        guardar_ciclo_vida(self.retirar(reemplazado_por=sustituto), self.coordinador)
        tercero = self.sustituto('FIC-SUS-02')
        guardar_ciclo_vida(self.retirar(sustituto, reemplazado_por=tercero), self.coordinador)
        self.equipo.refresh_from_db()
        # Retirar después el sustituto no invalida una relación histórica anterior.
        self.equipo.save()
        self.assertEqual(self.equipo.reemplazado_por_id, sustituto.pk)
        self.assertEqual(sustituto.reemplazado_por_id, tercero.pk)
        self.assertEqual(UnidadEquipo.objects.filter(laboratorio=self.unidad).count(), 3)

    def test_no_se_permiten_autorreferencia_crossunit_ni_ciclos(self):
        otra = Unidad.objects.create(nombre='Unidad ajena', slug='unidad-ajena-baja', dependencia='laboratorios',
                                     administrador=self.coordinador, fecha_inicio=date(2020, 1, 1))
        ajeno = self.sustituto('AJENO-01', otra)
        for destino in (self.equipo, ajeno):
            with self.subTest(destino=destino.pk):
                with self.assertRaises(ValidationError) as error:
                    guardar_ciclo_vida(self.retirar(reemplazado_por=destino), self.coordinador)
                self.assertIn('reemplazado_por', error.exception.message_dict)
        segundo = self.sustituto()
        guardar_ciclo_vida(self.retirar(reemplazado_por=segundo), self.coordinador)
        with self.assertRaises(ValidationError) as error:
            guardar_ciclo_vida(self.retirar(segundo, reemplazado_por=self.equipo), self.coordinador)
        self.assertIn('ciclo', str(error.exception).lower())
        segundo.refresh_from_db()
        self.assertIsNone(segundo.fecha_baja)

    def test_un_sustituto_no_operativo_no_acredita_reemplazo(self):
        sustituto = self.sustituto()
        sustituto.estado_unidad = 'mantenimiento'
        sustituto.save()
        with self.assertRaises(ValidationError):
            guardar_ciclo_vida(self.retirar(reemplazado_por=sustituto), self.coordinador)

    def test_rectificar_exige_motivo_y_anade_historia_sin_reactivar(self):
        guardar_ciclo_vida(self.retirar(), self.coordinador)
        original = self.equipo.eventos_ciclo_vida.get(tipo='baja')
        self.equipo.fecha_baja = None
        self.equipo.motivo_baja = self.equipo.observacion_baja = ''
        with self.assertRaises(ValidationError):
            guardar_ciclo_vida(self.equipo, self.coordinador)
        guardar_ciclo_vida(self.equipo, self.coordinador, justificacion='Se confundió el número de serie; revisión TEC-05.')
        self.equipo.refresh_from_db()
        self.assertIsNone(self.equipo.fecha_baja)
        self.assertFalse(self.equipo.activa)
        original.refresh_from_db()
        nuevo = self.equipo.eventos_ciclo_vida.get(tipo='actualizacion')
        self.assertIn('TEC-05', nuevo.descripcion)
        self.assertIn('dano_irreparable', nuevo.descripcion)
        self.assertEqual(original.usuario, self.coordinador)

    def test_sustitucion_posterior_registra_evento_sin_reescribir_retiro(self):
        guardar_ciclo_vida(self.retirar(), self.coordinador)
        original = self.equipo.eventos_ciclo_vida.get(tipo='baja')
        texto = original.descripcion
        self.equipo.reemplazado_por = self.sustituto()
        guardar_ciclo_vida(self.equipo, self.coordinador)
        original.refresh_from_db()
        self.assertEqual(original.descripcion, texto)
        nuevo = self.equipo.eventos_ciclo_vida.get(tipo='actualizacion')
        self.assertIn(self.equipo.reemplazado_por.codigo_unidad, nuevo.descripcion)

    def test_una_edicion_concurrente_del_retiro_exige_recargar(self):
        esperados = instantanea(self.equipo, CAMPOS_CICLO)
        guardar_ciclo_vida(self.retirar(), self.coordinador)
        self.equipo.observacion_baja += ' Nota del formulario antiguo.'
        with self.assertRaisesMessage(ValidationError, 'cambió mientras editabas'):
            guardar_ciclo_vida(self.equipo, self.coordinador, esperados=esperados)

    def test_el_formulario_admin_pide_justificacion_al_rectificar(self):
        guardar_ciclo_vida(self.retirar(), self.coordinador)
        formulario = self.formulario(self.datos_retiro(observacion_baja='Cambio sin motivo de corrección.'))
        self.assertFalse(formulario.is_valid())
        self.assertIn('justificacion_rectificacion', formulario.errors)
        formulario = self.formulario(self.datos_retiro(
            observacion_baja='Diagnóstico corregido TEC-05.', justificacion_rectificacion='Se corrigió la referencia.'))
        self.assertTrue(formulario.is_valid(), formulario.errors)

    def test_el_admin_atribuye_el_retiro_al_usuario_del_formulario(self):
        formulario = self.formulario(self.datos_retiro())
        self.assertTrue(formulario.is_valid(), formulario.errors)
        instancia = formulario.save(commit=False)
        peticion = RequestFactory().post('/admin/')
        peticion.user = self.coordinador
        UnidadEquipoAdmin(UnidadEquipo, admin.site).save_model(peticion, instancia, formulario, change=True)
        self.assertEqual(self.equipo.eventos_ciclo_vida.get(tipo='baja').usuario, self.coordinador)

    def test_el_formulario_real_del_admin_incluye_respaldo_y_autor(self):
        peticion = RequestFactory().get('/admin/')
        peticion.user = self.coordinador
        peticion.user.is_superuser = True
        formulario = UnidadEquipoAdmin(UnidadEquipo, admin.site).get_form(peticion, self.equipo)(instance=self.equipo)
        self.assertIs(formulario.usuario, peticion.user)
        self.assertIn('respaldo_retiro', formulario.fields)
        self.assertIn('justificacion_rectificacion', formulario.fields)
        self.assertTrue(formulario.fields['ciclo_version'].widget.is_hidden)

    def test_el_token_del_get_impide_que_una_pantalla_antigua_pise_otra_decision(self):
        apertura = UnidadEquipoCicloVidaForm(instance=self.equipo, usuario=self.coordinador)
        token = apertura.initial['ciclo_version']
        guardar_ciclo_vida(self.retirar(), self.coordinador)
        self.equipo.refresh_from_db()
        formulario = self.formulario(self.datos_retiro(
            ciclo_version=token, observacion_baja='Cambio desde pestaña antigua.',
            justificacion_rectificacion='Aunque tenga un motivo, no puede sobrescribir otra decisión.'))
        self.assertFalse(formulario.is_valid())
        self.assertIn('desde que abriste', str(formulario.non_field_errors()))
        self.equipo.refresh_from_db()
        self.assertNotIn('pestaña antigua', self.equipo.observacion_baja)

    def test_el_token_es_obligatorio_y_no_se_acepta_si_fue_alterado(self):
        token = UnidadEquipoCicloVidaForm(instance=self.equipo, usuario=self.coordinador).initial['ciclo_version']
        for valor in ('', token + 'x'):
            with self.subTest(token=valor):
                formulario = self.formulario(self.datos_retiro(ciclo_version=valor))
                self.assertFalse(formulario.is_valid())
                self.assertIn('fue alterada', str(formulario.non_field_errors()))

    def test_el_token_esta_vinculado_al_actor_y_al_activo(self):
        ajeno = get_user_model().objects.create_user('actor-token-ajeno')
        otro_equipo = self.sustituto()
        tokens = [UnidadEquipoCicloVidaForm(instance=self.equipo, usuario=ajeno).initial['ciclo_version'],
                  UnidadEquipoCicloVidaForm(instance=otro_equipo, usuario=self.coordinador).initial['ciclo_version']]
        for token in tokens:
            with self.subTest(token=token):
                formulario = self.formulario(self.datos_retiro(ciclo_version=token))
                self.assertFalse(formulario.is_valid())
                self.assertIn('fue alterada', str(formulario.non_field_errors()))

    def test_la_firma_expirada_exige_recargar_la_ficha(self):
        with patch('django.core.signing.time.time', return_value=1):
            token = signing.dumps({'esquema': 1, 'equipo_id': self.equipo.pk, 'actor_id': self.coordinador.pk,
                                   'campos': instantanea(self.equipo, CAMPOS_CICLO)}, salt=SALT_CICLO)
        formulario = self.formulario(self.datos_retiro(ciclo_version=token))
        self.assertFalse(formulario.is_valid())
        self.assertIn('vigencia', str(formulario.non_field_errors()))

    def test_operador_solo_recursos_puede_reabrir_respaldo_pero_no_otros_adjuntos(self):
        operador = get_user_model().objects.create_user('actor-solo-recursos-baja', password='clave')
        identificar(operador, tipo_usuario='administrativo', carrera='')
        ResponsableUnidad.objects.create(unidad=self.unidad, usuario=operador, rol='otro', activo=True,
            permisos_operativos={modulo: modulo == 'recursos' for modulo in MODULOS_OPERATIVOS})
        self.assertTrue(puede_operar_modulo_unidad(operador, self.unidad, 'recursos'))
        self.assertFalse(puede_operar_modulo_unidad(operador, self.unidad, 'mantenimiento'))
        with TemporaryDirectory() as carpeta, override_settings(MEDIA_ROOT=carpeta):
            guardar_ciclo_vida(self.retirar(), operador, evidencia=self.pdf())
            retiro = self.equipo.eventos_ciclo_vida.get(tipo='baja')
            self.client.force_login(operador)
            respuesta = self.client.get(retiro.evidencia.url)
            self.assertEqual(respuesta.status_code, 200)
            self.assertTrue(b''.join(respuesta.streaming_content).startswith(b'%PDF'))
            firmware = EventoCicloVidaEquipo.objects.create(
                equipo=self.equipo, unidad=self.unidad, tipo='actualizacion', usuario=operador,
                descripcion='Actualización de firmware, sin retiro.', evidencia=self.pdf())
            self.assertEqual(self.client.get(firmware.evidencia.url).status_code, 404)
            ajeno = get_user_model().objects.create_user('lector-retiro-ajeno', password='clave')
            identificar(ajeno, tipo_usuario='administrativo', carrera='')
            self.client.force_login(ajeno)
            self.assertEqual(self.client.get(retiro.evidencia.url).status_code, 404)
            self.client.logout()
            self.assertEqual(self.client.get(retiro.evidencia.url).status_code, 404)

    def test_acciones_masivas_y_reactivacion_directa_no_abren_activos_retirados(self):
        guardar_ciclo_vida(self.retirar(), self.coordinador)
        normal = self.sustituto()
        administracion = UnidadEquipoAdmin(UnidadEquipo, admin.site)
        peticion = RequestFactory().post('/admin/')
        peticion.user = self.coordinador
        with patch.object(administracion, 'message_user'):
            administracion.marcar_disponible(peticion, UnidadEquipo.objects.filter(pk__in=[self.equipo.pk, normal.pk]))
            administracion.marcar_mantenimiento(peticion, UnidadEquipo.objects.filter(pk=self.equipo.pk))
        self.equipo.refresh_from_db()
        self.assertEqual(self.equipo.estado_unidad, 'no_disponible')
        with self.assertRaises(ValidationError):
            alternar_equipo(self.equipo)
        normal.refresh_from_db()
        self.assertEqual(normal.estado_unidad, 'disponible')

    def test_fecha_de_fin_conserva_el_dia_real_y_resuelve_bisiesto(self):
        self.equipo.fecha_adquisicion = date(2024, 3, 31)
        self.equipo.vida_util_anios = 1
        self.assertEqual(self.equipo.fin_vida_util, date(2025, 3, 31))
        self.equipo.fecha_adquisicion = date(2024, 2, 29)
        self.assertEqual(self.equipo.fin_vida_util, date(2025, 2, 28))
        self.equipo.vida_util_anios = 4
        self.assertEqual(self.equipo.fin_vida_util, date(2028, 2, 29))
        self.equipo.fecha_adquisicion = date(9999, 3, 31)
        self.assertIsNone(self.equipo.fin_vida_util)

    def test_el_registro_inicial_puede_conservar_un_retiro_documentado(self):
        nuevo = UnidadEquipo(codigo_unidad='HIST-01', laboratorio=self.unidad, equipo=self.tipo)
        guardar_ciclo_vida(self.retirar(nuevo), self.coordinador)
        self.assertEqual(set(nuevo.eventos_ciclo_vida.values_list('tipo', flat=True)), {'registro', 'baja'})
        self.assertFalse(nuevo.activa)
