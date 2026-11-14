"""Inscripción a los cursos: gratis, pagando con verificación de la unidad, con código de descuento (al 100 %, sin pagar)
y por matrícula de la unidad, individual o en grupo, por usuario o por correo."""
import shutil
import tempfile
from datetime import date, timedelta
from decimal import Decimal

from allauth.account.models import EmailAddress
from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase, override_settings
from django.urls import reverse
from django.utils import timezone

from apps.formacion.models.cursos_inscripcion import CodigoDescuento, InvitacionCurso, PagoInscripcion
from apps.formacion.models.cursos import Curso, EdicionCurso, InscripcionCurso
from apps.directorio_unidades.models.core import Unidad

MEDIOS = tempfile.mkdtemp(prefix='citt-pagos-')


def comprobante():
    return SimpleUploadedFile('pago.pdf', b'%PDF-1.4 pago', content_type='application/pdf')


@override_settings(MEDIA_ROOT=MEDIOS)
class InscripcionDeCursosTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        usuarios = get_user_model()
        cls.admin = usuarios.objects.create_superuser('admin-pago', 'a@example.org', 'clave')
        cls.ana = usuarios.objects.create_user('ana-pago', 'ana@example.org', 'clave', first_name='Ana', last_name='Ríos')
        cls.luis = usuarios.objects.create_user('luis-pago', 'luis@example.org', 'clave')
        EmailAddress.objects.create(user=cls.ana, email=cls.ana.email, verified=True, primary=True)
        cls.lab = Unidad.objects.create(nombre='Laboratorio con pagos', slug='lab-pago', dependencia='laboratorios',
                                        descripcion='.', fecha_inicio=date(2026, 1, 1))
        cls.curso = Curso.objects.create(
            unidad=cls.lab, codigo='LP-CUR-001', nombre='Fusion avanzado', publicado=True, inscripcion='abierta',
            costo=Decimal('40.00'), pago_transferencia=True, pago_enlace=True, enlace_pago='https://pagos.example.org/curso',
            datos_pago='Cuenta corriente 123456 · Banco del Pacífico')
        hoy = timezone.localdate()
        cls.edicion = EdicionCurso.objects.create(curso=cls.curso, nombre='2026-II', anio=hoy.year,
                                                  inicio=hoy + timedelta(days=10), cupo=10)

    @classmethod
    def tearDownClass(cls):
        super().tearDownClass()
        shutil.rmtree(MEDIOS, ignore_errors=True)

    def url(self, nombre, *extra):
        return reverse(nombre, args=[self.lab.slug, self.curso.codigo, *extra])

    def pagar(self, datos):
        usuario = get_user_model().objects.get(pk=self.client.session['_auth_user_id'])
        identidad = {'edicion': self.edicion.pk, 'nombres_completos': usuario.get_full_name() or 'Luis Torres',
                     'documento': 'DOC-ANA' if usuario.pk == self.ana.pk else 'DOC-LUIS'}
        return self.client.post(self.url('pagar_curso'), {**identidad, **datos})

    def test_curso_con_costo_se_inscribe_con_comprobante_y_la_unidad_verifica(self):
        self.client.force_login(self.ana)
        self.assertContains(self.client.get(self.url('curso_unidad')), self.url('pagar_curso'))
        formulario = self.client.get(self.url('pagar_curso') + f'?edicion={self.edicion.pk}')
        self.assertContains(formulario, 'Banco del Pacífico')
        self.assertContains(formulario, 'https://pagos.example.org/curso')
        self.assertContains(self.pagar({'medio': 'transferencia'}),
                            'Adjunta el comprobante o escribe el número de la transacción.')
        self.pagar({'medio': 'transferencia', 'comprobante': comprobante()})
        pago = PagoInscripcion.objects.get()
        self.assertEqual((pago.estado, pago.monto, pago.inscripcion.estado), ('pendiente', Decimal('40.00'), 'pendiente'))
        self.assertTrue(self.client.get(self.url('aula_curso')).context['libre'])
        self.client.force_login(self.luis)
        self.assertEqual(self.client.get(self.url('comprobante_pago', pago.pk)).status_code, 403)
        self.assertEqual(self.client.get('/media/' + pago.comprobante.name).status_code, 404)
        self.client.force_login(self.admin)
        self.assertEqual(self.client.get(self.url('comprobante_pago', pago.pk)).status_code, 200)
        self.client.post(self.url('inscritos_curso'), {'accion': 'verificar_pago', 'pago': pago.pk})
        pago.refresh_from_db()
        self.assertEqual((pago.estado, pago.inscripcion.estado, pago.verificado_por), ('verificado', 'aceptada', self.admin))
        self.client.force_login(self.ana)
        self.assertEqual(self.client.get(self.url('aula_curso')).status_code, 200)

    def test_un_pago_rechazado_se_puede_volver_a_enviar(self):
        self.client.force_login(self.ana)
        self.pagar({'medio': 'transferencia', 'referencia': 'TX-1'})
        pago = PagoInscripcion.objects.get()
        self.client.force_login(self.admin)
        self.client.post(self.url('inscritos_curso'), {'accion': 'rechazar_pago', 'pago': pago.pk,
                                                       'observacion': 'El número no coincide.'})
        self.client.force_login(self.ana)
        self.assertContains(self.client.get(self.url('pagar_curso') + f'?edicion={self.edicion.pk}'), 'no pudo verificar tu pago anterior')
        self.pagar({'medio': 'transferencia', 'referencia': 'TX-2'})
        pago.refresh_from_db()
        self.assertEqual((pago.estado, pago.referencia, pago.inscripcion.estado), ('pendiente', 'TX-2', 'pendiente'))

    def test_codigos_de_descuento(self):
        CodigoDescuento.objects.create(curso=self.curso, codigo='mitad', porcentaje=50)
        CodigoDescuento.objects.create(curso=self.curso, codigo='BECA', porcentaje=100, usos_maximos=1)
        CodigoDescuento.objects.create(curso=self.curso, codigo='VIEJO', porcentaje=30, vigente_hasta=date(2020, 1, 1))
        self.client.force_login(self.ana)
        # Vencido o inexistente dan el mismo mensaje: no se puede saber qué códigos existen.
        self.assertContains(self.pagar({'codigo': 'viejo'}), 'Ese código no es válido')
        self.assertContains(self.pagar({'codigo': 'NADA'}), 'Ese código no es válido')
        self.pagar({'codigo': 'beca'})
        inscripcion = InscripcionCurso.objects.get(usuario=self.ana)
        self.assertEqual((inscripcion.estado, inscripcion.pago.estado, inscripcion.pago.monto), ('aceptada', 'exonerado', Decimal('0.00')))
        self.client.force_login(self.luis)
        self.assertContains(self.pagar({'codigo': 'BECA'}), 'Ese código no es válido')
        self.pagar({'codigo': 'MITAD', 'medio': 'transferencia', 'referencia': 'TX-9'})
        self.assertEqual(PagoInscripcion.objects.get(inscripcion__usuario=self.luis).monto, Decimal('20.00'))

    def test_la_unidad_matricula_personas_y_grupos_por_usuario_o_correo(self):
        self.client.force_login(self.admin)
        self.client.post(self.url('inscritos_curso'), {
            'accion': 'matricular', 'edicion': self.edicion.pk,
            'personas': 'ana@example.org, luis-pago\nnueva@upec.edu.ec; no-es-correo'})
        self.assertEqual(set(InscripcionCurso.objects.values_list('usuario__username', 'estado')),
                         {('ana-pago', 'aceptada'), ('luis-pago', 'aceptada')})
        self.assertTrue(all(pago.estado == 'exonerado' for pago in PagoInscripcion.objects.all()))
        self.assertEqual(list(InvitacionCurso.objects.filter(inscripcion__isnull=True).values_list('correo', flat=True)), ['nueva@upec.edu.ec'])
        # Quien solo escribe ese correo en su perfil no se queda con la matrícula: hace falta tenerlo verificado.
        intruso = get_user_model().objects.create_user('intruso', 'nueva@upec.edu.ec', 'clave')
        self.client.force_login(intruso)
        self.client.get(reverse('mis_cursos', args=[self.lab.slug]))
        self.assertFalse(InscripcionCurso.objects.filter(usuario=intruso).exists())
        nueva = get_user_model().objects.create_user('nueva', 'Nueva@upec.edu.ec', 'clave')
        EmailAddress.objects.create(user=nueva, email='Nueva@upec.edu.ec', verified=True, primary=True)
        self.client.force_login(nueva)
        self.client.get(reverse('mis_cursos', args=[self.lab.slug]))
        self.assertEqual(InscripcionCurso.objects.get(usuario=nueva).estado, 'aceptada')
        self.assertIsNotNone(InvitacionCurso.objects.get(correo='nueva@upec.edu.ec').inscripcion)

    def test_un_curso_gratuito_exige_grupo_y_los_codigos_se_crean_en_la_pagina(self):
        Curso.objects.filter(pk=self.curso.pk).update(costo=None)
        self.client.force_login(self.ana)
        self.assertEqual(self.client.get(self.url('pagar_curso') + f'?edicion={self.edicion.pk}').status_code, 404)
        self.client.post(self.url('inscribirse_curso'), {'edicion': self.edicion.pk,
                                                           'nombres_completos': 'Ana Ríos', 'documento': 'DOC-ANA'})
        self.assertEqual(InscripcionCurso.objects.get().estado, 'aceptada')
        self.client.force_login(self.admin)
        nuevo = reverse('editar_registro', args=[self.lab.slug, 'codigo_descuento', 'nuevo'])
        self.client.post(nuevo, {'padre': self.curso.pk, 'registro-codigo': 'docentes', 'registro-porcentaje': '25',
                                 'registro-activo': 'on'}, HTTP_X_REQUESTED_WITH='fetch')
        self.assertEqual(CodigoDescuento.objects.get().codigo, 'DOCENTES')
