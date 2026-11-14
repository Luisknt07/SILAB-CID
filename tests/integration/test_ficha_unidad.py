"""«Ficha de la unidad»: identidad, operación, creación, contacto y equipo, de un vistazo.

Cada dato aparece solo si está cargado, y el contacto se usa directamente:
llamar (con la extensión tras una pausa), escribir o abrir la página web.
Quien coordina va primero; las líneas de trabajo se ven con la presentación.
"""
from datetime import date

from django.contrib.auth import get_user_model
from django.urls import reverse

from apps.gestion_unidades.presentation.ficha_unidad import enlace_telefonico, equipo_de_la_unidad, iniciales
from apps.gestion_unidades.models.presentacion import LineaAccionUnidad, PresentacionUnidad
from apps.gestion_unidades.models.espacios import ResponsableUnidad
from apps.directorio_unidades.models.core import Unidad
from tests.integration.test_produccion_planta import BasePlantaProduce


class LaFichaDeLaUnidadTests(BasePlantaProduce):
    def ficha(self, usuario=None):
        if usuario is not None:
            self.client.force_login(usuario)
        return self.client.get(reverse('ficha_unidad', args=[self.unidad.slug]))

    def test_telefonos_e_iniciales(self):
        self.assertEqual(enlace_telefonico('(06) 2980 302 Ext. 2870'), 'tel:062980302,2870')
        self.assertEqual(enlace_telefonico('+57 (2) 339 32 48'), 'tel:+5723393248')
        self.assertEqual(iniciales('Ing. Patricia Chamorro'), 'PC')
        self.assertEqual(iniciales('Tlgo. Édison Cuasapaz'), 'ÉC')

    def test_el_contacto_aparece_solo_si_esta_cargado_y_se_usa_directo(self):
        pagina = self.ficha()
        self.assertEqual(pagina['X-Frame-Options'], 'SAMEORIGIN')
        self.assertNotContains(pagina, 'Página web')
        Unidad.objects.filter(pk=self.unidad.pk).update(
            telefono='(06) 2980 302 ext. 2870', celular='0991234567', sitio_web='https://upec.edu.ec/carnicos',
            contacto_email='planta@upec.edu.ec', resolucion_numero='Resolución 088-CU-2022',
            fecha_resolucion=date(2022, 4, 5),
        )
        pagina = self.ficha()
        for fragmento in ('href="tel:062980302,2870"', 'href="tel:0991234567"', 'href="mailto:planta@upec.edu.ec"',
                          'href="https://upec.edu.ec/carnicos" target="_blank" rel="noopener"',
                          'Resolución 088-CU-2022', '5 de abril de 2022'):
            self.assertContains(pagina, fragmento)

    def test_quien_coordina_va_primero_y_el_responsable_asignado_entra(self):
        Unidad.objects.filter(pk=self.unidad.pk).update(administrador=None)
        ResponsableUnidad.objects.filter(unidad=self.unidad).update(publico=False)
        ResponsableUnidad.objects.create(unidad=self.unidad, nombre='Tlgo. Ana Ruiz', rol='laboratorista', publico=True)
        ResponsableUnidad.objects.create(unidad=self.unidad, nombre='Ing. Luis Paz', rol='coordinacion', publico=True,
                                         email='coordina@upec.edu.ec')
        self.unidad.refresh_from_db()
        self.assertEqual([persona['nombre'] for persona in equipo_de_la_unidad(self.unidad)], ['Ing. Luis Paz', 'Tlgo. Ana Ruiz'])
        administrador = get_user_model().objects.create_user('jefe.planta', 'jefe@upec.edu.ec', 'Clave-segura-2026',
                                                             first_name='Marta', last_name='Ibarra')
        self.unidad.administrador = administrador
        equipo = equipo_de_la_unidad(self.unidad)
        self.assertEqual(equipo[0]['nombre'], 'Marta Ibarra')
        self.assertEqual(equipo[0]['iniciales'], 'MI')
        # El correo de coordinación se ofrece como contacto propio.
        self.assertContains(self.ficha(), 'href="mailto:coordina@upec.edu.ec"')

    def test_las_lineas_de_trabajo_se_ven_con_la_presentacion(self):
        LineaAccionUnidad.objects.create(unidad=self.unidad, titulo='Inocuidad alimentaria', icono='fa-shield-alt')
        presentacion = PresentacionUnidad.objects.create(unidad=self.unidad, areas_trabajo='Lácteos fermentados.')
        self.assertNotContains(self.ficha(), 'Inocuidad alimentaria')
        self.assertContains(self.ficha(self.coordinacion), 'Inocuidad alimentaria')
        self.client.logout()
        presentacion.publicada = True
        presentacion.save()
        pagina = self.ficha()
        self.assertContains(pagina, 'Inocuidad alimentaria')
        self.assertContains(pagina, 'Lácteos fermentados.')

    def test_la_ficha_la_abre_desde_la_unidad(self):
        ficha = self.client.get(self.unidad.get_absolute_url())
        self.assertContains(ficha, f'data-ui-arg0="{reverse("ficha_unidad", args=[self.unidad.slug])}"')
        self.assertContains(ficha, 'data-ui-arg1="ficha-unidad.html"')
        self.assertNotContains(ficha, 'data-seccion-integrada="datos-unidad"')
