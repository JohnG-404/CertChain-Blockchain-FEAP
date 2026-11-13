# -*- coding: utf-8 -*-
"""
CertChain - bateria completa de testes (CP3 + CP4): T01 a T19

Executa o contrato numa EVM local (py-evm, via eth-tester), na mesma ordem
do roteiro do README, e compara o resultado observado com o esperado.
Complementa a demonstracao no Remix VM (caminho oficial da trilha).

Requer Python 3.8+ e:
    pip install web3 "eth-tester[py-evm]" py-solc-x
Uso (na pasta que contem src/):
    python src/executar_testes.py                                  # contrato atual (CP4)
    python src/executar_testes.py --contrato src/historico/CertChain_CP3.sol   # versao do CP3
    python src/executar_testes.py --csv testes/resultado_local.csv # tambem grava um CSV

Opcoes:
    --contrato ARQUIVO.sol   contrato a testar (padrao: src/CertChain.sol)
    --artefato ARQUIVO.json  usa ABI e bytecode ja compilados, sem baixar o solc
    --csv ARQUIVO.csv        grava id, categoria, esperado, observado e status

Os resultados ESPERADOS sao as regras do grupo (CP2, refinadas no CP4). Rodar
contra a versao do CP3 mostra as falhas T18 e T19 que motivaram o ajuste.
"""
import csv
import hashlib
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

from web3 import Web3, EthereumTesterProvider

SRC = Path(__file__).resolve().parent
PDFS = SRC / "certificados_ficticios"
ESTADOS = {0: "Inexistente", 1: "Valido", 2: "Revogado"}
SITUACOES = {0: "NaoCadastrado", 1: "Ativo", 2: "Inativo"}
VERSAO_SOLC = "0.8.28"
ZERO_ADDR = "0x" + "00" * 20
ZERO_HASH = "0x" + "00" * 32


def opcao(nome, padrao=None):
    return sys.argv[sys.argv.index(nome) + 1] if nome in sys.argv else padrao


def compilar(caminho_sol):
    artefato = opcao("--artefato")
    if artefato:
        dados = json.loads(Path(artefato).read_text(encoding="utf-8"))
        return dados["abi"], dados["bytecode"], dados.get("compilador", "artefato informado")
    import solcx
    if VERSAO_SOLC not in [str(v) for v in solcx.get_installed_solc_versions()]:
        solcx.install_solc(VERSAO_SOLC)
    saida = solcx.compile_files([str(caminho_sol)], output_values=["abi", "bin"],
                                solc_version=VERSAO_SOLC, evm_version="cancun")
    contrato = next(v for k, v in saida.items() if k.endswith(":CertChain"))
    return contrato["abi"], contrato["bin"], "solc " + VERSAO_SOLC


def sha256_arquivo(nome):
    return "0x" + hashlib.sha256((PDFS / nome).read_bytes()).hexdigest()


def sha256_texto(texto):
    return "0x" + hashlib.sha256(texto.encode("utf-8")).hexdigest()


def main():
    caminho_sol = Path(opcao("--contrato", str(SRC / "CertChain.sol")))
    abi, bytecode, compilador = compilar(caminho_sol)
    w3 = Web3(EthereumTesterProvider())
    c1, c2, c3, c4, c5 = w3.eth.accounts[:5]  # equivalem as Accounts 1 a 5 do Remix VM
    nomes = {c1: "Account 1 (administrador)", c2: "Account 2 (Emissor A)", c3: "Account 3 (Emissor B)",
             c4: "Account 4 (sem permissao)", c5: "Account 5 (verificador)"}

    print("=== CertChain - bateria de testes T01 a T19 (EVM local py-evm via eth-tester) ===")
    print("Data/hora (UTC):", datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S"))
    try:
        exibido = caminho_sol.resolve().relative_to(SRC.parent).as_posix()
    except ValueError:
        exibido = caminho_sol.name
    print("Contrato:", exibido, "| compilador:", compilador)
    for conta, nome in nomes.items():
        print(f"  {nome}: {conta}")
    print()

    def enviar(conta, funcao):
        try:
            tx = funcao.transact({"from": conta})
            rec = w3.eth.wait_for_transaction_receipt(tx)
            return (rec.status == 1), None, rec.gasUsed
        except Exception as erro:
            msg = str(erro.args[0]) if erro.args else str(erro)
            return False, msg.replace("execution reverted: ", ""), None

    rec = w3.eth.wait_for_transaction_receipt(w3.eth.contract(abi=abi, bytecode=bytecode)
                                              .constructor().transact({"from": c1}))
    cc = w3.eth.contract(address=rec.contractAddress, abi=abi)
    f = cc.functions
    print(f"[Prep] Account 1 implanta o contrato em {rec.contractAddress}")
    for conta, nome in ((c2, "Semana de Tecnologia FEAP (ficticia)"), (c3, "Empresa Parceira X (ficticia)")):
        ok, _, _ = enviar(c1, f.credenciarEmissor(conta, nome))
        print(f"[Prep] Account 1 credenciarEmissor({nomes[conta]}, \"{nome}\") -> {'aceita' if ok else 'FALHA'}")
    print()

    H1, H2, H3 = (sha256_arquivo(n) for n in ("CERT-0001.pdf", "CERT-0002.pdf", "CERT-0003.pdf"))
    H2A = sha256_arquivo("CERT-0002_adulterado.pdf")
    H4, H5 = sha256_texto("CERT-0004 (teste CP4)"), sha256_texto("CERT-0005 (teste CP4)")
    print("Hashes usados:")
    for rot, h in (("CERT-0001.pdf", H1), ("CERT-0002.pdf", H2), ("CERT-0003.pdf", H3),
                   ("CERT-0002_adulterado.pdf", H2A), ('texto "CERT-0004 (teste CP4)"', H4),
                   ('texto "CERT-0005 (teste CP4)"', H5)):
        print(f"  {rot:32s} {h}")
    print()

    estado = lambda h: ESTADOS[f.estadoDoCertificado(h).call()]
    situacao = lambda conta: SITUACOES[f.emissores(conta).call()[1]]
    resultados = []

    def teste(id_t, categoria, descricao, conta, chamada, funcao, esperado_msg, checar, estado_txt):
        """esperado_msg = None -> deve ser aceita; texto -> deve ser rejeitada com essa mensagem."""
        if funcao is None:
            aceita, motivo, gas = True, None, None
        else:
            aceita, motivo, gas = enviar(conta, funcao)
        observado = "aceita" + (f" ({gas} gas)" if gas else "") if aceita else f'rejeitada: "{motivo}"'
        esperado = "aceita" if esperado_msg is None else f'rejeitada: "{esperado_msg}"'
        ok_resultado = aceita if esperado_msg is None else (not aceita and motivo == esperado_msg)
        ok_estado, estado_obs = checar()
        status = "PASSOU" if (ok_resultado and ok_estado) else "FALHOU"
        resultados.append({"id": id_t, "categoria": categoria, "descricao": descricao,
                           "conta": nomes[conta], "chamada": chamada, "esperado": f"{esperado}; {estado_txt}",
                           "observado": f"{observado}; {estado_obs}", "status": status})
        print(f"{id_t} [{categoria}] {descricao}")
        print(f"     conta: {nomes[conta]}")
        print(f"     chamada: {chamada}")
        print(f"     esperado: {esperado}; {estado_txt}")
        print(f"     observado: {observado}; {estado_obs}")
        print(f"     status: {status}")
        print()

    def est(h, alvo):
        return lambda: (estado(h) == alvo, f"estado = {estado(h)}")

    # ---------------- CP3: fluxo principal (regressao) ----------------
    print("--- Testes do CP3 (regressao) ---\n")
    teste("T01", "Fluxo (positivo)", "Emissor A emite o CERT-0001", c2, "emitirCertificado(CERT-0001)",
          f.emitirCertificado(H1), None, est(H1, "Valido"), "estado = Valido")
    teste("T02", "Fluxo (positivo)", "Emissor A revoga o CERT-0001 (motivo 1)", c2, "revogarCertificado(CERT-0001, 1)",
          f.revogarCertificado(H1, 1), None, est(H1, "Revogado"), "estado = Revogado")
    enviar(c2, f.emitirCertificado(H2))
    print(f"[Prep] Account 2 emite o CERT-0002 -> estado {estado(H2)}\n")
    teste("T03", "Permissoes", "Emissor B tenta revogar o CERT-0002 do Emissor A", c3,
          "revogarCertificado(CERT-0002, 2)", f.revogarCertificado(H2, 2),
          "Somente o emissor do certificado", est(H2, "Valido"), "estado = Valido")
    teste("T04", "Permissoes", "Conta nao credenciada tenta emitir o CERT-0003", c4, "emitirCertificado(CERT-0003)",
          f.emitirCertificado(H3), "Emissor nao autorizado", est(H3, "Inexistente"), "estado = Inexistente")
    teste("T05", "Verificacao", "Hash da copia adulterada do CERT-0002 nao e reconhecido", c5,
          "verificarCertificado(CERT-0002_adulterado)", None, None,
          lambda: (estado(H2A) == "Inexistente" and estado(H2) == "Valido",
                   f"adulterado = {estado(H2A)}, original = {estado(H2)}"),
          "adulterado = Inexistente, original = Valido")

    # ---------------- CP4: permissoes ----------------
    print("--- CP4: permissoes ---\n")
    teste("T06", "Permissoes", "Emissor A (nao administrador) tenta credenciar a Account 4", c2,
          'credenciarEmissor(Account 4, "Entidade Indevida (ficticia)")',
          f.credenciarEmissor(c4, "Entidade Indevida (ficticia)"), "Somente o administrador",
          lambda: (situacao(c4) == "NaoCadastrado", f"Account 4 = {situacao(c4)}"), "Account 4 = NaoCadastrado")
    teste("T07", "Permissoes", "Emissor B tenta descredenciar o Emissor A", c3, "descredenciarEmissor(Account 2)",
          f.descredenciarEmissor(c2), "Somente o administrador",
          lambda: (situacao(c2) == "Ativo", f"Account 2 = {situacao(c2)}"), "Account 2 = Ativo")
    teste("T08", "Permissoes", "Conta sem permissao tenta se tornar administradora", c4,
          "transferirAdministracao(Account 4)", f.transferirAdministracao(c4), "Somente o administrador",
          lambda: (f.administrador().call() == c1, f"administrador = {nomes.get(f.administrador().call())}"),
          "administrador = Account 1")

    # ---------------- CP4: entradas invalidas ----------------
    print("--- CP4: entradas invalidas ---\n")
    total = lambda: f.totalCertificados().call()
    t0 = total()
    teste("T09", "Entradas invalidas", "Emissor A tenta emitir um hash vazio (bytes32 zero)", c2,
          "emitirCertificado(0x000...000)", f.emitirCertificado(ZERO_HASH), "Hash vazio",
          lambda: (total() == t0, f"totalCertificados = {total()}"), f"totalCertificados = {t0}")
    teste("T10", "Entradas invalidas", "Emissor A tenta revogar o CERT-0002 com motivo 0", c2,
          "revogarCertificado(CERT-0002, 0)", f.revogarCertificado(H2, 0), "Motivo invalido",
          est(H2, "Valido"), "estado = Valido")
    teste("T11", "Entradas invalidas", "Emissor A tenta revogar o CERT-0002 com motivo 4", c2,
          "revogarCertificado(CERT-0002, 4)", f.revogarCertificado(H2, 4), "Motivo invalido",
          est(H2, "Valido"), "estado = Valido")
    teste("T12", "Entradas invalidas", "Administrador tenta credenciar o endereco zero", c1,
          'credenciarEmissor(0x000...000, "Entidade X (ficticia)")',
          f.credenciarEmissor(ZERO_ADDR, "Entidade X (ficticia)"), "Conta invalida",
          lambda: (situacao(ZERO_ADDR) == "NaoCadastrado", f"endereco zero = {situacao(ZERO_ADDR)}"),
          "endereco zero = NaoCadastrado")
    teste("T13", "Entradas invalidas", "Administrador tenta credenciar a Account 4 com nome vazio", c1,
          'credenciarEmissor(Account 4, "")', f.credenciarEmissor(c4, ""), "Nome da entidade vazio",
          lambda: (situacao(c4) == "NaoCadastrado", f"Account 4 = {situacao(c4)}"), "Account 4 = NaoCadastrado")

    # ---------------- CP4: falhas e estado indevido ----------------
    print("--- CP4: falhas e estado indevido ---\n")
    emissor_antes, data_antes = f.certificados(H2).call()[0:2]
    teste("T14", "Falhas/estado", "Emissor A tenta emitir de novo o CERT-0002 (ja Valido)", c2,
          "emitirCertificado(CERT-0002)", f.emitirCertificado(H2), "Certificado ja registrado",
          lambda: (tuple(f.certificados(H2).call()[0:2]) == (emissor_antes, data_antes),
                   "emissor e emitidoEm do CERT-0002 inalterados" if tuple(f.certificados(H2).call()[0:2]) ==
                   (emissor_antes, data_antes) else "emissor ou data ALTERADOS"),
          "emissor e emitidoEm do CERT-0002 inalterados")
    teste("T15", "Falhas/estado", "Emissor A tenta revogar de novo o CERT-0001 (ja Revogado)", c2,
          "revogarCertificado(CERT-0001, 1)", f.revogarCertificado(H1, 1), "Certificado nao esta valido",
          est(H1, "Revogado"), "estado = Revogado")
    teste("T16", "Falhas/estado", "Emissor A tenta revogar o CERT-0003, que nao existe", c2,
          "revogarCertificado(CERT-0003, 1)", f.revogarCertificado(H3, 1), "Certificado nao esta valido",
          est(H3, "Inexistente"), "estado = Inexistente")

    enviar(c3, f.emitirCertificado(H3))
    enviar(c3, f.emitirCertificado(H4))
    enviar(c1, f.descredenciarEmissor(c3))
    print(f"[Prep] Account 3 emite o CERT-0003 ({estado(H3)}) e o CERT-0004 ({estado(H4)}); "
          f"Account 1 descredencia a Account 3 -> {situacao(c3)}\n")
    teste("T17", "Falhas/estado", "Emissor B descredenciado tenta emitir o CERT-0005", c3,
          "emitirCertificado(CERT-0005)", f.emitirCertificado(H5), "Emissor nao autorizado",
          lambda: (estado(H5) == "Inexistente" and estado(H3) == "Valido",
                   f"CERT-0005 = {estado(H5)}, CERT-0003 = {estado(H3)}"),
          "CERT-0005 = Inexistente, CERT-0003 = Valido")
    teste("T18", "Falhas/estado", "Emissor B descredenciado tenta revogar o CERT-0003 que emitiu antes", c3,
          "revogarCertificado(CERT-0003, 2)", f.revogarCertificado(H3, 2), "Emissor nao autorizado",
          est(H3, "Valido"), "estado = Valido")
    teste("T19", "Permissoes", "Administrador revoga o CERT-0004 do emissor descredenciado (motivo 2 = fraude)",
          c1, "revogarCertificado(CERT-0004, 2)", f.revogarCertificado(H4, 2), None,
          est(H4, "Revogado"), "estado = Revogado")

    resumo = ", ".join(f"{r['id']} {r['status']}" for r in resultados)
    falhas = [r["id"] for r in resultados if r["status"] == "FALHOU"]
    print("Resumo:", resumo)
    print(f"Total: {len(resultados)} testes, {len(resultados) - len(falhas)} PASSOU, {len(falhas)} FALHOU"
          + (f" ({', '.join(falhas)})" if falhas else ""))

    destino = opcao("--csv")
    if destino:
        Path(destino).parent.mkdir(parents=True, exist_ok=True)
        with open(destino, "w", newline="", encoding="utf-8") as arq:
            escritor = csv.DictWriter(arq, fieldnames=list(resultados[0].keys()))
            escritor.writeheader()
            escritor.writerows(resultados)
        print("CSV gravado em", destino)
    return 0 if not falhas else 1


if __name__ == "__main__":
    sys.exit(main())
