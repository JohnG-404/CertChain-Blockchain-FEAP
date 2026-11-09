# -*- coding: utf-8 -*-
"""
Calcula o hash SHA-256 de arquivos (por exemplo, o PDF de um certificado)
no formato bytes32 aceito pelo Remix: 0x seguido de 64 caracteres hex.

O contrato CertChain usa o mesmo algoritmo (sha256) na funcao calcularHash,
entao o hash de um TEXTO calculado aqui e no Remix deve ser identico.

Uso (na pasta que contem src/):
    python src/gerar_hash.py src/certificados_ficticios/CERT-0001.pdf
    python src/gerar_hash.py src/certificados_ficticios/*.pdf
    python src/gerar_hash.py --texto "certificado-teste"
Nao usa bibliotecas externas (Python 3.8+).
"""
import glob
import hashlib
import sys


def hash_bytes(dados: bytes) -> str:
    return "0x" + hashlib.sha256(dados).hexdigest()


def main(args):
    if not args:
        print(__doc__)
        return 1
    if args[0] == "--texto":
        texto = " ".join(args[1:])
        print(f'{hash_bytes(texto.encode("utf-8"))}  texto="{texto}"')
        return 0
    caminhos = []
    for padrao in args:  # o terminal do Windows nao expande *.pdf sozinho
        caminhos.extend(sorted(glob.glob(padrao)) or [padrao])
    for caminho in caminhos:
        with open(caminho, "rb") as f:
            print(f"{hash_bytes(f.read())}  {caminho}")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
