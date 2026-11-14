"""Modelo educativo determinista de capacidad de dos etapas en serie."""
from decimal import Decimal

from django import forms


class CapacidadForm(forms.Form):
    minutos = forms.IntegerField(label='Duración del turno (min)', min_value=1, max_value=1440, initial=480)
    disponibilidad = forms.DecimalField(label='Tiempo productivo del turno (%)', min_value=1, max_value=100, decimal_places=1, initial=85)
    demanda = forms.IntegerField(label='Demanda por turno (unidades)', min_value=1, max_value=1000000, initial=120)
    ciclo_ensamble = forms.DecimalField(label='Ensamble: minutos por unidad', min_value=Decimal('0.1'), max_value=10000, decimal_places=2, initial=4)
    puestos_ensamble = forms.IntegerField(label='Ensamble: puestos paralelos', min_value=1, max_value=100, initial=1)
    ciclo_inspeccion = forms.DecimalField(label='Inspección: minutos por unidad', min_value=Decimal('0.1'), max_value=10000, decimal_places=2, initial=3)
    puestos_inspeccion = forms.IntegerField(label='Inspección: puestos paralelos', min_value=1, max_value=100, initial=1)


def calcular_capacidad(datos):
    tiempo = Decimal(datos['minutos']) * datos['disponibilidad'] / 100
    ensamble = int(tiempo * datos['puestos_ensamble'] / datos['ciclo_ensamble'])
    inspeccion = int(tiempo * datos['puestos_inspeccion'] / datos['ciclo_inspeccion'])
    capacidad = min(ensamble, inspeccion)
    return {'tiempo': tiempo, 'ensamble': ensamble, 'inspeccion': inspeccion, 'capacidad': capacidad,
        'atendidas': min(capacidad, datos['demanda']), 'pendientes': max(0, datos['demanda'] - capacidad),
        'cuello': 'Ensamble' if ensamble < inspeccion else ('Inspección' if inspeccion < ensamble else 'Etapas equilibradas')}
