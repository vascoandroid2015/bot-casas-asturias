def es_ganga(precio, titulo):
    texto = titulo.lower()
    palabras = ["urge", "oportunidad", "rebajado", "chollo", "negociable"]
    score = 0

    if precio < 80000:
        score += 2
    if precio < 50000:
        score += 3

    for p in palabras:
        if p in texto:
            score += 2

    return score >= 3
