"""Tarifas de referencia para validar el costo de las corridas de las plantas.

Sirven para probar el cálculo con cifras plausibles mientras cada planta no
declara las suyas; el cargador solo las pone donde no hay valor, así que una
tarifa fijada por la planta no se pisa. Se reemplazan en los permisos
operativos de cada planta cuando se pase a datos reales.

- Energía: orden de magnitud de la tarifa eléctrica comercial e industrial
  en media tensión del Ecuador, en USD por kWh.
- Hora-persona: el salario básico unificado con sus cargas patronales
  (aporte al IESS, décimos, vacaciones y fondos de reserva) repartido en las
  160 horas del mes, en USD por hora.
"""
from decimal import Decimal

TARIFA_ENERGIA_KWH = Decimal('0.0950')
COSTO_HORA_PERSONA = Decimal('4.50')
