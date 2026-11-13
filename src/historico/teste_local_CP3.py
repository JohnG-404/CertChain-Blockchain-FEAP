# -*- coding: utf-8 -*-
"""
CertChain - execucao automatizada do fluxo e dos testes T01 a T05 (CP3)

COMPLEMENTO da demonstracao no Remix VM (caminho oficial, ver README.md).
Executa o MESMO contrato src/CertChain.sol em uma EVM local (py-evm, via
eth-tester), com as mesmas contas, valores e ordem descritos no README,
e imprime o resultado de cada teste.

Requer Python 3.8+ e:
    pip install web3 "eth-tester[py-evm]" py-solc-x
Uso (na pasta que contem src/):
    python src/historico/teste_local_CP3.py
    python src/historico/teste_local_CP3.py > evidencias/execucao_testes_local.txt

Na primeira execucao, o py-solc-x baixa o compilador solc 0.8.28.
Opcao: --artefato ARQUIVO.json usa ABI e bytecode ja compilados
(campos "abi" e "bytecode"), sem baixar o compilador.
"""
import hashlib
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

from web3 import Web3, EthereumTesterProvider

SRC = Path(__file__).resolve().parent.parent  # pasta src/ (script movido para src/historico no CP4)
PDFS = SRC / "certificados_ficticios"
ESTADOS = {0: "Inexistente", 1: "Valido", 2: "Revogado"}
VERSAO_SOLC = "0.8.28"


def compilar():
    if "--artefato" in sys.argv:
        caminho = sys.argv[sys.argv.index("--artefato") + 1]
        dados = json.loads(Path(caminho).read_text(encoding="utf-8"))
        return dados["abi"], dados["bytecode"], dados.get("compilador", "artefato informado")
    import solcx
    if VERSAO_SOLC not in [str(v) for v in solcx.get_installed_solc_versions()]:
        solcx.install_solc(VERSAO_SOLC)
    saida = solcx.compile_files([str(SRC / "historico" / "CertChain_CP3.sol")], output_values=["abi", "bin"],
                                solc_version=VERSAO_SOLC, evm_version="cancun")
    contrato = next(v for k, v in saida.items() if k.endswith(":CertChain"))
    return contrato["abi"], contrato["bin"], "solc " + VERSAO_SOLC


def sha256_arquivo(nome):
    return "0x" + hashlib.sha256((PDFS / nome).read_bytes()).hexdigest()


def curto(conta):
    return conta[:6] + "..." + conta[-4:]


def main():
    abi, bytecode, compilador = compilar()
    w3 = Web3(EthereumTesterProvider())
    c1, c2, c3, c4, c5 = w3.eth.accounts[:5]  # equivalem as 5 primeiras contas do Remix VM
    nomes = {c1: "Conta 1 (administrador)", c2: "Conta 2 (Emissor A)", c3: "Conta 3 (Emissor B)",
             c4: "Conta 4 (sem permissao)", c5: "Conta 5 (verificador)"}

    print("=== CertChain - execucao local do CP3 (EVM py-evm via eth-tester) ===")
    print("Data/hora (UTC):", datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S"))
    print("Compilador:", compilador, "| contrato: src/CertChain.sol")
    for conta, nome in nomes.items():
        print(f"  {nome}: {conta}")
    print()

    def enviar(conta, funcao):
        """Envia a transacao. Retorna (aceita, detalhe)."""
        try:
            tx = funcao.transact({"from": conta})
            rec = w3.eth.wait_for_transaction_receipt(tx)
            return rec.status == 1, f"aceita | tx {tx.hex()[:18]}... | gas usado {rec.gasUsed}"
        except Exception as erro:  # revert: a EVM rejeita e nada muda
            msg = str(erro.args[0]) if erro.args else str(erro)
            return False, "rejeitada (revert): " + msg

    # ------------------------------------------------------------------
    # Passo 1 - implantacao pela Conta 1
    Contrato = w3.eth.contract(abi=abi, bytecode=bytecode)
    rec = w3.eth.wait_for_transaction_receipt(Contrato.constructor().transact({"from": c1}))
    cert = w3.eth.contract(address=rec.contractAddress, abi=abi)
    print(f"[Passo 1] Conta 1 implanta CertChain em {rec.contractAddress} (gas {rec.gasUsed})")
    print("          administrador() =", cert.functions.administrador().call())

    # Passo 2 - governanca: credenciar emissores
    for conta, nome_ent in ((c2, "Semana de Tecnologia FEAP (ficticia)"),
                            (c3, "Empresa Parceira X (ficticia)")):
        ok, det = enviar(c1, cert.functions.credenciarEmissor(conta, nome_ent))
        print(f'[Passo 2] Conta 1 credenciarEmissor({curto(conta)}, "{nome_ent}") -> {det}')
        nome, situacao = cert.functions.emissores(conta).call()
        print(f"          emissores({curto(conta)}) = ('{nome}', situacao {situacao} = Ativo)")
    print()

    h1 = sha256_arquivo("CERT-0001.pdf")
    h2 = sha256_arquivo("CERT-0002.pdf")
    h3 = sha256_arquivo("CERT-0003.pdf")
    h2_adulterado = sha256_arquivo("CERT-0002_adulterado.pdf")
    print("Hashes SHA-256 dos certificados ficticios (src/certificados_ficticios/):")
    for nome, h in (("CERT-0001.pdf", h1), ("CERT-0002.pdf", h2), ("CERT-0003.pdf", h3),
                    ("CERT-0002_adulterado.pdf", h2_adulterado)):
        print(f"  {nome:26s} {h}")
    print()

    def estado(h):
        return ESTADOS[cert.functions.estadoDoCertificado(h).call()]

    resultados = []

    def teste(id_teste, tipo, descricao, conta, chamada, funcao, h, esperado_aceita, estado_esperado):
        antes = estado(h)
        if funcao is None:  # teste de consulta: nao envia transacao
            aceita, det = True, f"consulta sem transacao; estado retornado = {estado(h)}"
        else:
            aceita, det = enviar(conta, funcao)
        depois = estado(h)
        passou = (aceita == esperado_aceita) and depois == estado_esperado
        status = "PASSOU" if passou else "FALHOU"
        resultados.append((id_teste, status))
        print(f"{id_teste} [{tipo}] {descricao}")
        print(f"     conta: {nomes[conta]}")
        print(f"     chamada: {chamada}")
        if funcao is None:
            print(f"     esperado: consulta retorna {estado_esperado}")
        else:
            print(f"     esperado: {'aceita' if esperado_aceita else 'rejeitada'}; estado final {estado_esperado}")
        print(f"     observado: {det}")
        print(f"     estadoDoCertificado: antes = {antes} | depois = {depois}")
        if depois != "Inexistente":
            e, emissor, nome_ent, emitido, revogado, motivo = cert.functions.verificarCertificado(h).call()
            print(f"     verificarCertificado: estado={ESTADOS[e]}, emissor={curto(emissor)} ('{nome_ent}'), "
                  f"emitidoEm={emitido}, revogadoEm={revogado}, motivo={motivo}")
        print(f"     status: {status}")
        print()

    # T01 - criacao do registro
    teste("T01", "POSITIVO", "Emissor A credenciado emite o certificado CERT-0001", c2,
          "emitirCertificado(hash CERT-0001.pdf)", cert.functions.emitirCertificado(h1), h1, True, "Valido")

    # T02 - mudanca de estado do MESMO registro
    teste("T02", "POSITIVO", "Emissor A revoga o CERT-0001 que ele emitiu (motivo 1 = erro de emissao)", c2,
          "revogarCertificado(hash CERT-0001.pdf, 1)", cert.functions.revogarCertificado(h1, 1), h1, True, "Revogado")

    # Preparacao do T03: um SEGUNDO certificado, ainda Valido. Se usassemos o CERT-0001
    # (ja Revogado), a rejeicao viria do estado e nao da permissao.
    ok, det = enviar(c2, cert.functions.emitirCertificado(h2))
    print(f"[Preparacao T03] Conta 2 emitirCertificado(hash CERT-0002.pdf) -> {det}")
    print(f"     estadoDoCertificado(CERT-0002) = {estado(h2)}")
    print()

    # T03 - conta credenciada, mas NAO e a emissora do certificado
    teste("T03", "NEGATIVO", "Emissor B tenta revogar o CERT-0002, emitido pelo Emissor A", c3,
          "revogarCertificado(hash CERT-0002.pdf, 2)", cert.functions.revogarCertificado(h2, 2), h2, False, "Valido")

    # T04 - conta nao credenciada tenta emitir
    teste("T04", "NEGATIVO", "Conta 4, nao credenciada, tenta emitir o CERT-0003", c4,
          "emitirCertificado(hash CERT-0003.pdf)", cert.functions.emitirCertificado(h3), h3, False, "Inexistente")

    # T05 - verificacao de documento adulterado (consulta)
    teste("T05", "VERIFICACAO", "Verificador consulta o hash da copia adulterada do CERT-0002 (12 h -> 120 h)", c5,
          "verificarCertificado(hash CERT-0002_adulterado.pdf)", None, h2_adulterado, True, "Inexistente")
    print(f"     comparacao: o CERT-0002 original continua {estado(h2)}; basta mudar a carga horaria")
    print("     para o hash mudar e o documento nao ser reconhecido.")
    print()

    # Checagem extra: calcularHash do contrato == SHA-256 do Python
    texto = "certificado-teste"
    no_contrato = Web3.to_hex(cert.functions.calcularHash(texto).call())
    no_python = "0x" + hashlib.sha256(texto.encode("utf-8")).hexdigest()
    print(f'Checagem extra: calcularHash("{texto}") no contrato = {no_contrato}')
    print(f'                SHA-256 no Python                     = {no_python}')
    print("                iguais:", no_contrato == no_python)
    print()
    print("Resumo:", ", ".join(f"{i} {s}" for i, s in resultados),
          "| totalCertificados =", cert.functions.totalCertificados().call())
    return 0 if all(s == "PASSOU" for _, s in resultados) else 1


if __name__ == "__main__":
    sys.exit(main())
