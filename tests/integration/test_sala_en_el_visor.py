"""El aula se abre dentro del visor de la ficha de la unidad: la pantalla para conectar el servicio sale a la página
completa y admite el marco del propio sitio, y el sitio conserva cámara y micrófono para cedérselos a la sala aunque
esté dentro de ese marco."""
from datetime import date
from pathlib import Path

from django.conf import settings
from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from apps.formacion.presentation.clases_en_vivo import olvidar_origen
from apps.core.middleware.security import politica_de_permisos
from apps.formacion.models.cursos import Curso, LeccionCurso, ModuloCurso, ServidorClasesEnVivo
from apps.directorio_unidades.models.core import Unidad


class SalaDentroDelVisorTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.admin = get_user_model().objects.create_superuser('admin-visor', 'a@example.org', 'clave')
        cls.lab = Unidad.objects.create(nombre='Laboratorio visor', slug='lab-visor', dependencia='laboratorios',
                                        descripcion='.', fecha_inicio=date(2026, 1, 1))
        cls.curso = Curso.objects.create(unidad=cls.lab, codigo='VIS-CUR-001', nombre='Diseño 2D', publicado=True)
        modulo = ModuloCurso.objects.create(curso=cls.curso, orden=1, titulo='Inicio')
        cls.clase = LeccionCurso.objects.create(modulo=modulo, orden=1, titulo='Diseño 2D CAD', tipo='en_vivo',
                                                sala='plataforma')

    def setUp(self):
        olvidar_origen()
        self.addCleanup(olvidar_origen)

    def test_conectar_el_servicio_sale_del_visor_y_la_pantalla_admite_el_marco_del_sitio(self):
        self.client.force_login(self.admin)
        sala = self.client.get(reverse('clase_en_vivo', args=[self.lab.slug, self.curso.codigo, self.clase.pk]))
        self.assertContains(sala, 'target="_top"')
        servidor = self.client.get(reverse('servidor_clases_en_vivo'))
        self.assertEqual(servidor['X-Frame-Options'], 'SAMEORIGIN')

    def test_el_sitio_conserva_camara_y_microfono_para_cederlos_a_la_sala(self):
        ServidorClasesEnVivo.objects.create(proveedor='daily', daily_api_key='k', daily_dominio='upec.daily.co')
        politica = politica_de_permisos()
        for permiso in ('camera', 'microphone', 'display-capture'):
            self.assertIn(f'{permiso}=(self "https://upec.daily.co")', politica)

    def test_el_visor_cede_camara_y_microfono_a_lo_que_abre(self):
        guion = Path(settings.BASE_DIR, 'apps/gestion_unidades/static/portal/js/pages/unidades/detalle/gestor_contenido.js')
        self.assertIn("'camera; microphone; display-capture", guion.read_text(encoding='utf-8'))
