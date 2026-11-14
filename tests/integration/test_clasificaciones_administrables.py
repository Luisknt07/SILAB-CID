"""Subareas y modos de uso: codigo estable, archivado, alcance y proteccion."""
from datetime import date

from django.contrib import admin
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.test import RequestFactory, TestCase
from django.urls import reverse

from apps.directorio_unidades.models.core import Categoria, TipoLaboratorio, Unidad


class ClasificacionesAdministrablesTests(TestCase):
    def setUp(self):
        self.usuario = get_user_model().objects.create_superuser(
            username='admin-clasificaciones', email='clasificaciones@upec.edu.ec',
            password='clave-segura-pruebas',
        )
        self.client.force_login(self.usuario)
        self.laboratorio = Unidad.objects.create(
            nombre='Laboratorio de Microbiología', slug='laboratorio-microbiologia',
            dependencia='laboratorios', descripcion='x', fecha_inicio=date(2026, 1, 1),
        )
        self.planta = Unidad.objects.create(
            nombre='Planta de Lácteos', slug='planta-lacteos', dependencia='plantas_piloto',
            modo_operacion='lotes', descripcion='x', fecha_inicio=date(2026, 1, 1),
        )

    def formulario_unidad(self, instancia=None, **datos):
        peticion = RequestFactory().get('/')
        peticion.user = self.usuario
        registro = admin.site._registry[Unidad]
        base = {
            'nombre': 'Laboratorio nuevo', 'slug': 'laboratorio-nuevo', 'descripcion': 'x',
            'fecha_inicio': '2026-01-01', 'dependencia': 'laboratorios',
            'estado_catalogo': 'disponible', 'contacto_email': 'lab@upec.edu.ec',
            'visitas': 0, 'likes': 0,
        }
        base.update(datos)
        return registro.get_form(peticion, instancia)(data=base, instance=instancia)

    def test_el_codigo_se_genera_del_nombre_es_unico_y_no_cambia_al_renombrar(self):
        primera = Categoria.objects.create(nombre='Química Analítica')
        segunda = Categoria.objects.create(nombre='Quimica analitica')
        self.assertEqual(primera.codigo, 'quimica-analitica')
        self.assertEqual(segunda.codigo, 'quimica-analitica-2')
        primera.nombre = 'Química analítica e instrumental'
        primera.save()
        self.assertEqual(Categoria.objects.get(pk=primera.pk).codigo, 'quimica-analitica')

    def test_el_catalogo_filtra_por_codigo_y_acepta_el_nombre_historico(self):
        categoria = Categoria.objects.create(nombre='Biotecnología')
        self.laboratorio.categorias.add(categoria)
        otro = Unidad.objects.create(
            nombre='Laboratorio de Física', slug='laboratorio-fisica', dependencia='laboratorios',
            descripcion='x', fecha_inicio=date(2026, 1, 1),
        )
        for valor in ('biotecnologia', 'Biotecnología'):
            with self.subTest(valor=valor):
                respuesta = self.client.get(reverse('hublab'), {'categoria': valor})
                self.assertQuerySetEqual(respuesta.context['unidades'], [self.laboratorio])
                self.assertEqual(respuesta.context['categoria_seleccionada'], 'biotecnologia')
                self.assertContains(respuesta, '<option value="biotecnologia" selected>Biotecnología</option>', html=True)
        self.assertNotContains(self.client.get(reverse('hublab'), {'categoria': 'biotecnologia'}), otro.nombre)

    def test_archivar_retira_de_filtros_y_de_unidades_nuevas_pero_conserva_asignaciones(self):
        categoria = Categoria.objects.create(nombre='Docencia experimental')
        self.laboratorio.categorias.add(categoria)
        categoria.activa = False
        categoria.save()

        catalogo = self.client.get(reverse('hublab'))
        self.assertNotContains(catalogo, 'value="docencia-experimental"')
        self.assertContains(catalogo, '<span>Docencia experimental</span>', html=True)

        nuevo = self.formulario_unidad()
        self.assertNotIn(categoria, nuevo.fields['categorias'].queryset)
        existente = self.formulario_unidad(self.laboratorio, nombre=self.laboratorio.nombre,
                                           slug=self.laboratorio.slug)
        self.assertIn(categoria, existente.fields['categorias'].queryset)
        self.assertEqual(list(self.laboratorio.categorias.all()), [categoria])

    def test_una_clasificacion_acotada_a_una_tipologia_no_se_asigna_fuera_de_ella(self):
        exclusiva = TipoLaboratorio.objects.create(nombre='Maquila', tipologias=['plantas_piloto'])
        general = TipoLaboratorio.objects.create(nombre='Docencia')

        rechazado = self.formulario_unidad(tipos_laboratorio=[exclusiva.pk, general.pk])
        self.assertFalse(rechazado.is_valid())
        self.assertIn('tipos_laboratorio', rechazado.errors)
        aceptado = self.formulario_unidad(dependencia='plantas_piloto', modo_operacion='lotes',
                                          slug='planta-nueva', tipos_laboratorio=[exclusiva.pk, general.pk])
        self.assertTrue(aceptado.is_valid(), aceptado.errors)

        self.planta.tipos_laboratorio.add(exclusiva, general)
        plantas = self.client.get(reverse('plantas-piloto'))
        self.assertEqual({t.codigo for t in plantas.context['tipos_laboratorio']}, {'maquila', 'docencia'})
        self.laboratorio.tipos_laboratorio.add(general)
        laboratorios = self.client.get(reverse('hublab'))
        self.assertEqual({t.codigo for t in laboratorios.context['tipos_laboratorio']}, {'docencia'})

        exclusiva.tipologias = ['inexistente']
        with self.assertRaises(ValidationError):
            exclusiva.full_clean()

    def test_eliminar_solo_sin_unidades_y_el_admin_lo_refleja(self):
        usada = Categoria.objects.create(nombre='Alimentos')
        libre = Categoria.objects.create(nombre='Sin uso')
        self.laboratorio.categorias.add(usada)
        registro = admin.site._registry[Categoria]
        peticion = RequestFactory().get('/')
        peticion.user = self.usuario

        with self.assertRaises(ValidationError):
            usada.delete()
        self.assertFalse(registro.has_delete_permission(peticion, usada))
        self.assertTrue(registro.has_delete_permission(peticion, libre))
        libre.delete()
        self.assertFalse(Categoria.objects.filter(nombre='Sin uso').exists())
        self.assertTrue(Categoria.objects.filter(nombre='Alimentos').exists())

    def test_el_admin_ordena_por_orden_y_muestra_unidades(self):
        Categoria.objects.create(nombre='Zeta', orden=1)
        Categoria.objects.create(nombre='Alfa', orden=2)
        respuesta = self.client.get(reverse('admin:directorio_unidades_categoria_changelist'))
        contenido = respuesta.content.decode()
        self.assertLess(contenido.index('Zeta'), contenido.index('Alfa'))
        self.assertContains(respuesta, 'Unidades')
        alta = self.client.get(reverse('admin:directorio_unidades_categoria_add'))
        self.assertContains(alta, 'name="tipologias"')
        self.assertContains(alta, 'value="plantas_piloto"')
