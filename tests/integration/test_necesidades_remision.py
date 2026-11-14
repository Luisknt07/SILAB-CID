"""Capturas internas, permisos vigentes y conservación de la remisión anual."""
from copy import deepcopy
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.core.exceptions import PermissionDenied, ValidationError
from django.test import TestCase

from apps.directorio_unidades.models.core import DependenciaAcademica
from apps.documentos.models.necesidades import RemisionNecesidades, huella_contenido
from apps.documentos.presentation.necesidades_remision import (
    contenido_remision, puede_leer_remision, remitir_necesidades,
)


class RemisionNecesidadesTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        usuarios = get_user_model()
        cls.direccion = usuarios.objects.create_user('dir-necesidades', is_superuser=True, is_staff=True)
        cls.receptor = usuarios.objects.create_user('dec-necesidades', first_name='Decana')
        cls.gestor = usuarios.objects.create_user('unidad-necesidades')
        cls.nuevo_receptor = usuarios.objects.create_user('nuevo-dec-necesidades')
        cls.dependencia = DependenciaAcademica.objects.create(
            nombre='Dependencia con centro', centro_costo='Centro original')
        cls.dependencia.receptores.add(cls.receptor)

    def lectura(self, *, evaluadas=1, sin_compras=False):
        return dict(anio_preparacion=2026, anio_ejecucion=2027,
            resumen=dict(unidades_total=2, evaluadas=evaluadas, pendientes=2 - evaluadas,
                         con_compras=0 if sin_compras else evaluadas,
                         sin_compras=evaluadas if sin_compras else 0),
            unidades=[dict(id=11, nombre='Unidad revisada', dependencia_id=self.dependencia.pk,
                evaluado=bool(evaluadas), transferible=bool(evaluadas),
                centro_costo=self.dependencia.centro_costo,
                declaracion='sin_compras' if sin_compras else 'con_compras',
                sin_compras_justificacion='Los recursos disponibles cubren las actividades.' if sin_compras else '',
                necesidades=[] if sin_compras else [dict(item='Licencia de diseño', clase_bien='software',
                    cantidad='1', costo_unitario='125.00', mes_compra='2')]),
                dict(id=12, nombre='Unidad pendiente', dependencia_id=self.dependencia.pk,
                    evaluado=False, transferible=False, necesidades=[])] )

    def remitir(self, lectura=None, usuario=None):
        lectura = self.lectura() if lectura is None else lectura
        with patch('apps.documentos.presentation.necesidades_decanato.lectura_necesidades',
                   return_value=lectura) as fuente:
            remision = remitir_necesidades(2026, self.dependencia, usuario or self.direccion)
        fuente.assert_called_once_with(2026, usuario or self.direccion, dependencia=self.dependencia)
        return remision

    def test_solo_direccion_activa_puede_remitir_y_no_acepta_contenido_cliente(self):
        for usuario in (self.gestor, self.receptor):
            with self.assertRaises(PermissionDenied):
                remitir_necesidades(2026, self.dependencia, usuario)
        get_user_model().objects.filter(pk=self.direccion.pk).update(is_active=False)
        with self.assertRaises(PermissionDenied):
            remitir_necesidades(2026, self.dependencia, self.direccion)
        self.assertEqual(RemisionNecesidades.objects.count(), 0)

    def test_dependencia_activa_y_destinatarios_activos_obligatorios(self):
        self.dependencia.activa = False
        self.dependencia.save(update_fields=['activa'])
        with self.assertRaisesMessage(ValidationError, 'dependencia activa'):
            remitir_necesidades(2026, self.dependencia, self.direccion)
        self.dependencia.activa = True
        self.dependencia.save(update_fields=['activa'])
        get_user_model().objects.filter(pk=self.receptor.pk).update(is_active=False)
        with self.assertRaisesMessage(ValidationError, 'receptor activo'):
            remitir_necesidades(2026, self.dependencia, self.direccion)

    def test_no_remite_si_no_hay_evaluacion_de_direccion(self):
        with self.assertRaisesMessage(ValidationError, 'evaluadas por Dirección'):
            self.remitir(self.lectura(evaluadas=0))
        self.assertEqual(RemisionNecesidades.objects.count(), 0)

    def test_remision_parcial_conserva_pendientes_y_no_ejecuta_compras(self):
        remision = self.remitir()
        self.assertEqual(remision.anio_preparacion, 2026)
        self.assertEqual(remision.anio_ejecucion, 2027)
        self.assertEqual(remision.remitido_por_id, self.direccion.pk)
        self.assertEqual(remision.destinatarios, [{'id': self.receptor.pk, 'nombre': 'Decana'}])
        self.assertEqual(remision.contenido['resumen']['pendientes'], 1)
        self.assertEqual(remision.contenido['unidades'][1]['necesidades'], [])
        self.assertEqual(remision.sha256, huella_contenido(remision.contenido))

    def test_no_compras_justificadas_tambien_se_remiten(self):
        remision = self.remitir(self.lectura(sin_compras=True))
        self.assertEqual(remision.contenido['resumen']['sin_compras'], 1)
        self.assertEqual(remision.contenido['unidades'][0]['necesidades'], [])

    def test_misma_captura_es_idempotente_y_cambio_de_centro_produce_otro_antecedente(self):
        primera = self.remitir()
        segunda = self.remitir()
        self.assertEqual(primera.pk, segunda.pk)
        self.dependencia.centro_costo = 'Centro actualizado'
        self.dependencia.save(update_fields=['centro_costo'])
        tercera = self.remitir()
        self.assertNotEqual(primera.pk, tercera.pk)
        primera.refresh_from_db()
        self.assertEqual(primera.contenido['unidades'][0]['centro_costo'], 'Centro original')
        self.assertEqual(tercera.contenido['unidades'][0]['centro_costo'], 'Centro actualizado')

    def test_captura_no_admite_edicion_borrado_ni_reescritura_masiva(self):
        remision = self.remitir()
        remision.contenido['unidades'][0]['nombre'] = 'Cambio local'
        for operacion in (
            lambda: remision.save(), lambda: remision.delete(),
            lambda: RemisionNecesidades.objects.filter(pk=remision.pk).update(sha256='x' * 64),
            lambda: RemisionNecesidades.objects.filter(pk=remision.pk).delete(),
            lambda: RemisionNecesidades.objects.bulk_update([remision], ['contenido']),
        ):
            with self.assertRaises(ValidationError):
                operacion()
        remision.refresh_from_db()
        self.assertEqual(remision.contenido['unidades'][0]['nombre'], 'Unidad revisada')

    def test_acceso_receptor_vigente_y_revocacion_cierra_lectura(self):
        remision = self.remitir()
        self.assertTrue(puede_leer_remision(self.receptor, remision))
        self.assertFalse(puede_leer_remision(self.gestor, remision))
        self.dependencia.receptores.remove(self.receptor)
        self.dependencia.receptores.add(self.nuevo_receptor)
        self.assertFalse(puede_leer_remision(self.receptor, remision))
        self.assertTrue(puede_leer_remision(self.nuevo_receptor, remision))
        self.assertEqual(remision.destinatarios[0]['id'], self.receptor.pk)
        self.dependencia.activa = False
        self.dependencia.save(update_fields=['activa'])
        self.assertFalse(puede_leer_remision(self.nuevo_receptor, remision))
        self.assertTrue(puede_leer_remision(self.direccion, remision))

    def test_descarga_verifica_huella_y_devuelve_copia_independiente(self):
        remision = self.remitir()
        contenido = contenido_remision(remision)
        contenido['unidades'][0]['nombre'] = 'No cambia la captura'
        self.assertNotEqual(contenido, remision.contenido)
        remision.contenido = deepcopy(contenido)
        with self.assertRaisesMessage(ValidationError, 'huella'):
            contenido_remision(remision)

    def test_anios_invalidos_no_se_convierten_en_otro_ejercicio(self):
        for anio in ('2026.1', 2026.1, True, None, 2019, 2100, 'nan'):
            with self.subTest(anio=anio), self.assertRaises(ValidationError):
                remitir_necesidades(anio, self.dependencia, self.direccion)
