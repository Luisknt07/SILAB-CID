"""El catálogo dice por qué una unidad va antes que otra, y las visitas se cuentan como visitas.

Por omisión las unidades se ordenan por visitas y la tarjeta muestra el contador; el
selector ofrece también por fecha de registro y por nombre. La visita cuenta una vez por
persona y sesión, y no cuenta cuando quien mira es quien gestiona la unidad o el sitio.
"""
from datetime import date

from django.contrib.auth import get_user_model
from django.test import Client, TestCase
from django.urls import reverse

from apps.directorio_unidades.models.core import Unidad


class CatalogoOrdenYVisitasTests(TestCase):
    def setUp(self):
        self.gestor = get_user_model().objects.create_user('gestor.visitas', 'g@example.org', 'clave')
        self.unidades = [
            Unidad.objects.create(nombre=nombre, slug=slug, descripcion='.', fecha_inicio=date(2026, 1, 1),
                                  dependencia='laboratorios', visitas=visitas)
            for nombre, slug, visitas in (('Zeta Lab', 'zeta-lab', 5), ('Alfa Lab', 'alfa-lab', 12),
                                          ('Beta Lab', 'beta-lab', 0))
        ]
        self.zeta, self.alfa, self.beta = self.unidades
        self.zeta.administrador = self.gestor
        self.zeta.save(update_fields=['administrador'])

    def nombres(self, **parametros):
        respuesta = self.client.get(reverse('laboratorios_unidades'), parametros)
        self.assertEqual(respuesta.status_code, 200)
        return respuesta, [unidad.nombre for unidad in respuesta.context['unidades']]

    def test_por_omision_van_primero_las_mas_visitadas_y_la_tarjeta_lo_muestra(self):
        respuesta, nombres = self.nombres()
        self.assertEqual(nombres, ['Alfa Lab', 'Zeta Lab', 'Beta Lab'])
        self.assertEqual(respuesta.context['orden'], 'visitadas')
        self.assertContains(respuesta, 'ordenadas por visitas: las más consultadas van primero')
        self.assertContains(respuesta, '<dd>12</dd>')
        self.assertContains(respuesta, 'Visitas</dt>')
        self.assertContains(respuesta, '<option value="visitadas" selected>')

    def test_los_otros_ordenes_se_explican_igual(self):
        _respuesta, nombres = self.nombres(orden='nombre')
        self.assertEqual(nombres, ['Alfa Lab', 'Beta Lab', 'Zeta Lab'])
        respuesta, nombres = self.nombres(orden='recientes')
        self.assertEqual(nombres, ['Beta Lab', 'Alfa Lab', 'Zeta Lab'])
        self.assertContains(respuesta, 'ordenadas por fecha de registro')
        # Un orden desconocido vuelve al de omisión.
        respuesta, nombres = self.nombres(orden='cualquiera')
        self.assertEqual(respuesta.context['orden'], 'visitadas')

    def test_la_visita_cuenta_una_vez_por_sesion_y_no_cuenta_a_quien_gestiona(self):
        ficha = reverse('laboratorio_detalle', args=[self.zeta.slug])
        visitante = Client()
        visitante.get(ficha)
        visitante.get(ficha)
        self.zeta.refresh_from_db()
        self.assertEqual(self.zeta.visitas, 6)
        otro = Client()
        otro.get(ficha)
        self.zeta.refresh_from_db()
        self.assertEqual(self.zeta.visitas, 7)
        # Quien gestiona la unidad la abre a diario: no es una visita.
        gestor = Client()
        gestor.force_login(self.gestor)
        gestor.get(ficha)
        superusuario = Client()
        superusuario.force_login(get_user_model().objects.create_superuser('super.visitas', 's@example.org', 'clave'))
        superusuario.get(ficha)
        self.zeta.refresh_from_db()
        self.assertEqual(self.zeta.visitas, 7)
        # El gestor de una unidad sí cuenta como visitante en las demás.
        gestor.get(reverse('laboratorio_detalle', args=[self.beta.slug]))
        self.beta.refresh_from_db()
        self.assertEqual(self.beta.visitas, 1)
