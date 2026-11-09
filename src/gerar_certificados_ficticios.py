# -*- coding: utf-8 -*-
"""
Gera os certificados FICTICIOS usados na demonstracao do CertChain (CP3).
Nenhum dado pessoal real: alunos, entidades e codigos sao inventados.

Os PDFs sao gerados de forma deterministica (invariant=1): rodar de novo
produz exatamente os mesmos bytes e, portanto, o mesmo hash SHA-256.

Requer: pip install reportlab
Uso (na pasta que contem src/):  python src/gerar_certificados_ficticios.py
"""
from pathlib import Path
from reportlab.lib.pagesizes import A4, landscape
from reportlab.pdfgen import canvas

PASTA = Path(__file__).resolve().parent / "certificados_ficticios"

CERTIFICADOS = [
    # arquivo, codigo, aluno, atividade, entidade, carga horaria
    ("CERT-0001.pdf", "CERT-0001-7F3A9C", "Aluno Ficticio A", "Palestra: Contratos inteligentes na pratica",
     "Semana de Tecnologia FEAP (entidade ficticia)", "8 horas"),
    ("CERT-0002.pdf", "CERT-0002-B41E07", "Aluno Ficticio B", "Minicurso: Introducao ao Solidity",
     "Semana de Tecnologia FEAP (entidade ficticia)", "12 horas"),
    ("CERT-0003.pdf", "CERT-0003-0C9D52", "Aluno Ficticio C", "Workshop: Seguranca de dados",
     "Empresa Parceira X (entidade ficticia)", "4 horas"),
    # Copia ADULTERADA do CERT-0002: so a carga horaria mudou (12 -> 120 horas).
    ("CERT-0002_adulterado.pdf", "CERT-0002-B41E07", "Aluno Ficticio B", "Minicurso: Introducao ao Solidity",
     "Semana de Tecnologia FEAP (entidade ficticia)", "120 horas"),
]


def gerar(arquivo, codigo, aluno, atividade, entidade, carga):
    c = canvas.Canvas(str(PASTA / arquivo), pagesize=landscape(A4), invariant=1)
    c.setTitle(f"Certificado {codigo} (FICTICIO)")
    largura, altura = landscape(A4)
    c.setFont("Helvetica-Bold", 30)
    c.drawCentredString(largura / 2, altura - 120, "CERTIFICADO")
    c.setFont("Helvetica", 15)
    linhas = [
        f"Certificamos que {aluno} participou da atividade",
        f'"{atividade}",',
        f"promovida por {entidade},",
        f"com carga horaria de {carga}.",
    ]
    y = altura - 200
    for linha in linhas:
        c.drawCentredString(largura / 2, y, linha)
        y -= 28
    c.setFont("Helvetica", 11)
    c.drawCentredString(largura / 2, 110, f"Codigo de verificacao: {codigo}")
    c.setFont("Helvetica-Oblique", 10)
    c.drawCentredString(largura / 2, 80, "DOCUMENTO FICTICIO - Projeto Integrador FEAP 2026.2 - sem validade")
    c.save()


if __name__ == "__main__":
    PASTA.mkdir(exist_ok=True)
    for dados in CERTIFICADOS:
        gerar(*dados)
        print("gerado:", PASTA / dados[0])
