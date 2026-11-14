"""Consulta institucional y privacidad pública de certificados de eventos."""
from datetime import date
from urllib.parse import parse_qs, urlsplit

from django.contrib import admin
from django.contrib.auth import get_user_model
from django.test import RequestFactory, TestCase
from django.urls import reverse

from apps.formacion.admin.cursos import CertificadoCursoAdmin, UnidadCertificadoFilter, consultas_formacion_de_unidad
from apps.gestion_unidades.admin.tablero_unidad import tablero
from apps.formacion.models.cursos import CertificadoCurso, Curso, EdicionCurso, InscripcionCurso, ParticipanteEvento
from apps.formacion.models.cursos_certificacion import ConfiguracionCertificadoCurso
from apps.directorio_unidades.models.core import Unidad


class ConsultaCertificadosEventoTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.usuario = get_user_model().objects.create_user('consulta-evento', 'consulta@example.invalid', 'clave')
        cls.unidad = Unidad.objects.create(nombre='Laboratorio principal', slug='consulta-principal',
            dependencia='laboratorios', descripcion='.', fecha_inicio=date(2026, 1, 1))
        cls.otra = Unidad.objects.create(nombre='Otra unidad', slug='consulta-otra',
            dependencia='laboratorios', descripcion='.', fecha_inicio=date(2026, 1, 1))
        cls.autor = get_user_model().objects.create_superuser('consulta-admin')
        cls.certificados = []
        for numero, unidad in enumerate((cls.unidad, cls.unidad, cls.otra), start=1):
            curso = Curso.objects.create(unidad=unidad, codigo=f'CONSULTA-{numero}', nombre=f'Evento {numero}', duracion_horas=8)
            ConfiguracionCertificadoCurso.objects.get_or_create(curso=curso)
            edicion = EdicionCurso.objects.create(curso=curso, nombre='Edición 2026', anio=2026,
                inicio=date(2026, 10, 1), fin=date(2026, 10, 2))
            identidad = ({'inscripcion': InscripcionCurso.objects.create(edicion=edicion, usuario=cls.usuario, estado='aceptada')}
                if numero == 1 else {'participante_evento': ParticipanteEvento.objects.create(edicion=edicion,
                    documento=f'PRIVADO-{numero}234', nombres_completos=f'Participante externo {numero}')})
            cls.certificados.append(CertificadoCurso.objects.create(**identidad, codigo=f'CERT-CONSULTA-{numero}',
                nombre=f'Participante {numero}', documento=f'PRIVADO-{numero}234', tipo='asistencia',
                curso_nombre=curso.nombre, clasificacion='Seminario', categoria_evento='seminario',
                fecha_inicio=edicion.inicio, fecha_fin=edicion.fin, horas=8,
                edicion=edicion.nombre, unidad_nombre=unidad.nombre, motivo_emision='Registro privado de asistencia.'))

    def filtro(self, valor):
        request = RequestFactory().get('/admin/', {'unidad_certificado': valor})
        return UnidadCertificadoFilter(request, {'unidad_certificado': [valor]}, CertificadoCurso,
                                       CertificadoCursoAdmin(CertificadoCurso, admin.site))

    def test_filtro_por_unidad_incluye_inscritos_y_externos_sin_mezclar_unidades(self):
        filtro = self.filtro(str(self.unidad.pk))
        resultados = filtro.queryset(RequestFactory().get('/'), CertificadoCurso.objects.all())
        self.assertSetEqual(set(resultados.values_list('pk', flat=True)), {c.pk for c in self.certificados[:2]})
        self.assertSetEqual({pk for pk, _ in filtro.lookup_choices}, {self.unidad.pk, self.otra.pk})
        self.assertFalse(self.filtro('dato-invalido').queryset(RequestFactory().get('/'), CertificadoCurso.objects.all()).exists())

    def test_verificacion_publica_externo_muestra_estado_y_omite_identidad_privada(self):
        certificado = self.certificados[1]
        response = self.client.get(reverse('verificar_certificado', args=[certificado.codigo]))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, certificado.nombre)
        self.assertContains(response, 'Certificado auténtico y vigente')
        self.assertNotContains(response, certificado.documento)
        self.assertNotContains(response, certificado.motivo_emision)
        certificado.anulado = True
        certificado.motivo_anulacion = 'Documento reemplazado por corrección.'
        certificado.save(update_fields=['anulado', 'motivo_anulacion'])
        response = self.client.get(reverse('verificar_certificado', args=[certificado.codigo]))
        self.assertContains(response, 'Certificado anulado')
        self.assertNotContains(response, 'data-pdf-titulo="Certificado')

    def test_el_tablero_de_formacion_incluye_las_consultas_de_su_unidad(self):
        request = RequestFactory().get('/admin/')
        request.user = self.autor
        consultas = consultas_formacion_de_unidad(request, self.unidad)
        self.assertEqual(len(consultas), 3)
        cantidades = {urlsplit(fila['lista']).path: fila['total'] for fila in consultas}
        for modelo, total in ((ConfiguracionCertificadoCurso, 2), (ParticipanteEvento, 1), (CertificadoCurso, 2)):
            ruta = reverse(f'admin:{modelo._meta.app_label}_{modelo._meta.model_name}_changelist')
            self.assertEqual(cantidades[ruta], total)
        grupos = tablero(request, self.unidad, 'laboratorios')['operacion']
        enlaces = {fila['lista'] for grupo in grupos for fila in grupo['filas']}
        self.assertTrue({fila['lista'] for fila in consultas}.issubset(enlaces))
        self.assertTrue(all(not fila['nuevo'] for fila in consultas))

    def test_cada_enlace_del_tablero_abre_solo_registros_de_su_unidad(self):
        request = RequestFactory().get('/admin/')
        request.user = self.autor
        self.client.force_login(self.autor)
        for fila in consultas_formacion_de_unidad(request, self.unidad):
            with self.subTest(enlace=fila['lista']):
                pagina = self.client.get(fila['lista'])
                self.assertEqual(pagina.status_code, 200)
                listado = pagina.context['cl'].queryset
                self.assertEqual(listado.count(), fila['total'])
                modelo = listado.model
                if modelo is CertificadoCurso:
                    esperados = {c.pk for c in self.certificados[:2]}
                elif modelo is ConfiguracionCertificadoCurso:
                    esperados = set(modelo.objects.filter(curso__unidad=self.unidad).values_list('pk', flat=True))
                else:
                    esperados = set(modelo.objects.filter(edicion__curso__unidad=self.unidad).values_list('pk', flat=True))
                self.assertSetEqual(set(listado.values_list('pk', flat=True)), esperados)
                self.assertIn(str(self.unidad.pk), next(iter(parse_qs(urlsplit(fila['lista']).query).values())))
                self.assertNotContains(pagina, 'class="addlink"')

    def test_las_consultas_respetan_los_permisos_originales_del_administrador(self):
        request = RequestFactory().get('/admin/')
        request.user = self.usuario
        self.assertEqual(consultas_formacion_de_unidad(request, self.unidad), [])
        self.usuario.is_staff = True
        self.usuario.save(update_fields=['is_staff'])
        self.client.force_login(self.usuario)
        for modelo in (ConfiguracionCertificadoCurso, ParticipanteEvento, CertificadoCurso):
            with self.subTest(modelo=modelo.__name__):
                ruta = reverse(f'admin:{modelo._meta.app_label}_{modelo._meta.model_name}_changelist')
                self.assertEqual(self.client.get(ruta).status_code, 403)
