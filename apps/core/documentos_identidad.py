"""Reglas de documentos de identidad, sin formularios, modelos ni acceso a datos."""

def cedula_ecuatoriana_valida(numero):
    """Verifica el dígito verificador de una cédula ecuatoriana."""
    if not numero.isdigit() or len(numero) != 10:
        return False
    provincia = int(numero[:2])
    if provincia < 1 or (provincia > 24 and provincia != 30):
        return False
    if int(numero[2]) > 5:
        return False
    total = 0
    for posicion, digito in enumerate(numero[:9]):
        valor = int(digito) * (2 if posicion % 2 == 0 else 1)
        total += valor - 9 if valor > 9 else valor
    verificador = (10 - total % 10) % 10
    return verificador == int(numero[9])

