# -*- coding: utf-8 -*-
"""
CertChain - comparacao com banco de dados convencional (SQLite)

Implementa as MESMAS regras do contrato src/CertChain.sol numa aplicacao
comum com banco SQLite (o "backend" de uma secretaria academica) e:

  Parte A - repete os cenarios T01 a T19 e confere se as regras dao o
            mesmo resultado que o contrato (equivalencia funcional);
  Parte B - mostra o que muda quando quem administra o banco altera os
            dados diretamente (UPDATE/DELETE), sem passar pelas regras;
  Parte C - mede tempo por operacao, custo (gas) e espaco ocupado,
            comparando o SQLite com o contrato numa EVM local (py-evm).

Uso (na pasta que contem src/):
    python src/comparacao_sqlite.py                    # partes A e B (so biblioteca padrao)
    python src/comparacao_sqlite.py --medir            # tambem a parte C (requer web3 e eth-tester)
    python src/comparacao_sqlite.py --medir --artefato contrato.json   # ABI/bytecode ja compilados
    python src/comparacao_sqlite.py --medir --n 200    # quantidade de certificados na medicao

Somente dados ficticios. O banco e criado num arquivo temporario e apagado ao final.
"""
import hashlib
import os
import sqlite3
import statistics
import sys
import tempfile
import time
from datetime import datetime, timezone
from pathlib import Path

SRC = Path(__file__).resolve().parent
PDFS = SRC / "certificados_ficticios"
MOTIVO_MIN, MOTIVO_MAX = 1, 3


class RegraViolada(Exception):
    """Equivale ao revert do contrato: a operacao e recusada e nada muda."""


class CertChainDB:
    """Mesmas regras de src/CertChain.sol, aplicadas pela aplicacao sobre o SQLite."""

    def __init__(self, caminho, administrador):
        self.db = sqlite3.connect(caminho, isolation_level=None)
        self.db.executescript("""
            PRAGMA journal_mode = WAL;
            CREATE TABLE config (chave TEXT PRIMARY KEY, valor TEXT NOT NULL);
            CREATE TABLE emissores (conta TEXT PRIMARY KEY, nome TEXT NOT NULL,
                                    situacao TEXT NOT NULL CHECK (situacao IN ('Ativo','Inativo')));
            CREATE TABLE certificados (hash TEXT PRIMARY KEY, emissor TEXT NOT NULL,
                                       emitido_em INTEGER NOT NULL, revogado_em INTEGER NOT NULL DEFAULT 0,
                                       motivo INTEGER NOT NULL DEFAULT 0,
                                       estado TEXT NOT NULL CHECK (estado IN ('Valido','Revogado')));
            CREATE TABLE eventos (id INTEGER PRIMARY KEY AUTOINCREMENT, quando INTEGER NOT NULL,
                                  tipo TEXT NOT NULL, conta TEXT NOT NULL, detalhe TEXT NOT NULL);
        """)
        self.db.execute("INSERT INTO config VALUES ('administrador', ?)", (administrador,))
        self._evento("AdministracaoTransferida", administrador, "implantacao")

    # ---------- apoio ----------
    def _evento(self, tipo, conta, detalhe):
        self.db.execute("INSERT INTO eventos (quando, tipo, conta, detalhe) VALUES (?,?,?,?)",
                        (int(time.time()), tipo, conta, detalhe))

    def administrador(self):
        return self.db.execute("SELECT valor FROM config WHERE chave='administrador'").fetchone()[0]

    def situacao(self, conta):
        linha = self.db.execute("SELECT situacao FROM emissores WHERE conta=?", (conta,)).fetchone()
        return linha[0] if linha else "NaoCadastrado"

    def estado(self, h):
        linha = self.db.execute("SELECT estado FROM certificados WHERE hash=?", (h,)).fetchone()
        return linha[0] if linha else "Inexistente"

    def certificado(self, h):
        return self.db.execute("SELECT emissor, emitido_em, revogado_em, motivo, estado FROM certificados "
                               "WHERE hash=?", (h,)).fetchone()

    def total(self):
        return self.db.execute("SELECT COUNT(*) FROM certificados").fetchone()[0]

    def _exigir(self, condicao, mensagem):
        if not condicao:
            raise RegraViolada(mensagem)

    # ---------- governanca ----------
    def credenciar_emissor(self, chamador, conta, nome):
        self._exigir(chamador == self.administrador(), "Somente o administrador")
        self._exigir(conta not in (None, "", "0x" + "00" * 20), "Conta invalida")
        self._exigir(len(nome) > 0, "Nome da entidade vazio")
        self._exigir(self.situacao(conta) != "Ativo", "Emissor ja ativo")
        self.db.execute("INSERT INTO emissores VALUES (?,?, 'Ativo') ON CONFLICT(conta) DO UPDATE "
                        "SET nome=excluded.nome, situacao='Ativo'", (conta, nome))
        self._evento("EmissorCredenciado", conta, nome)

    def descredenciar_emissor(self, chamador, conta):
        self._exigir(chamador == self.administrador(), "Somente o administrador")
        self._exigir(self.situacao(conta) == "Ativo", "Emissor nao esta ativo")
        self.db.execute("UPDATE emissores SET situacao='Inativo' WHERE conta=?", (conta,))
        self._evento("EmissorDescredenciado", conta, "")

    def transferir_administracao(self, chamador, novo):
        self._exigir(chamador == self.administrador(), "Somente o administrador")
        self._exigir(novo not in (None, "", "0x" + "00" * 20), "Conta invalida")
        self.db.execute("UPDATE config SET valor=? WHERE chave='administrador'", (novo,))
        self._evento("AdministracaoTransferida", novo, f"anterior={chamador}")

    # ---------- operacoes do negocio ----------
    def emitir_certificado(self, chamador, h):
        self._exigir(self.situacao(chamador) == "Ativo", "Emissor nao autorizado")
        self._exigir(h != "0x" + "00" * 32, "Hash vazio")
        self._exigir(self.estado(h) == "Inexistente", "Certificado ja registrado")
        self.db.execute("INSERT INTO certificados (hash, emissor, emitido_em, estado) VALUES (?,?,?, 'Valido')",
                        (h, chamador, int(time.time())))
        self._evento("CertificadoEmitido", chamador, h)

    def revogar_certificado(self, chamador, h, motivo):
        cert = self.certificado(h)
        eh_admin = chamador == self.administrador()
        self._exigir(cert is not None and cert[4] == "Valido", "Certificado nao esta valido")
        self._exigir(eh_admin or chamador == cert[0], "Somente o emissor do certificado")
        self._exigir(eh_admin or self.situacao(chamador) == "Ativo", "Emissor nao autorizado")
        self._exigir(MOTIVO_MIN <= motivo <= MOTIVO_MAX, "Motivo invalido")
        self.db.execute("UPDATE certificados SET estado='Revogado', revogado_em=?, motivo=? WHERE hash=?",
                        (int(time.time()), motivo, h))
        self._evento("CertificadoRevogado", chamador, f"{h} motivo={motivo}")


def sha256_arquivo(nome):
    return "0x" + hashlib.sha256((PDFS / nome).read_bytes()).hexdigest()


def sha256_texto(texto):
    return "0x" + hashlib.sha256(texto.encode("utf-8")).hexdigest()


def opcao(nome, padrao=None):
    return sys.argv[sys.argv.index(nome) + 1] if nome in sys.argv else padrao


# Mesmas contas de teste do Remix VM (Account 1 a 5); aqui sao apenas identificadores.
A1, A2, A3, A4, A5 = ("0x5B38Da6a701c568545dCfcB03FcB875f56beddC4", "0xAb8483F64d9C6d1EcF9b849Ae677dD3315835cb2",
                      "0x4B20993Bc481177ec7E8f571ceCaE8A9e22C02db", "0x78731D3Ca6b7E34aC0F824c42a7cC18A495cabaB",
                      "0x617F2E2fD72FD9D5503197092aC168c91465E7f2")
NOMES = {A1: "Account 1 (administrador)", A2: "Account 2 (Emissor A)", A3: "Account 3 (Emissor B)",
         A4: "Account 4 (sem permissao)", A5: "Account 5 (verificador)"}


def parte_a(db, H):
    print("=== Parte A - mesmas regras, mesmos cenarios (T01 a T19) no SQLite ===\n")
    resultados = []

    def caso(id_t, conta, descricao, acao, esperado_msg, checar):
        try:
            acao()
            obs = "aceita"
            ok = esperado_msg is None
        except RegraViolada as e:
            obs = f'rejeitada: "{e}"'
            ok = (esperado_msg == str(e))
        ok_estado, txt = checar()
        status = "PASSOU" if ok and ok_estado else "FALHOU"
        esperado = "aceita" if esperado_msg is None else f'rejeitada: "{esperado_msg}"'
        resultados.append((id_t, status))
        print(f"{id_t} {descricao} | {NOMES[conta]} | esperado: {esperado} | observado: {obs}; {txt} | {status}")

    est = lambda h, alvo: (lambda: (db.estado(h) == alvo, f"estado = {db.estado(h)}"))
    db.credenciar_emissor(A1, A2, "Semana de Tecnologia FEAP (ficticia)")
    db.credenciar_emissor(A1, A3, "Empresa Parceira X (ficticia)")
    caso("T01", A2, "emitir CERT-0001", lambda: db.emitir_certificado(A2, H["1"]), None, est(H["1"], "Valido"))
    caso("T02", A2, "revogar CERT-0001 (motivo 1)", lambda: db.revogar_certificado(A2, H["1"], 1), None,
         est(H["1"], "Revogado"))
    db.emitir_certificado(A2, H["2"])
    caso("T03", A3, "Emissor B revoga CERT-0002 do Emissor A", lambda: db.revogar_certificado(A3, H["2"], 2),
         "Somente o emissor do certificado", est(H["2"], "Valido"))
    caso("T04", A4, "conta nao credenciada emite CERT-0003", lambda: db.emitir_certificado(A4, H["3"]),
         "Emissor nao autorizado", est(H["3"], "Inexistente"))
    caso("T05", A5, "verificar copia adulterada do CERT-0002", lambda: None, None,
         lambda: (db.estado(H["2a"]) == "Inexistente" and db.estado(H["2"]) == "Valido",
                  f"adulterado = {db.estado(H['2a'])}, original = {db.estado(H['2'])}"))
    sit = lambda c, alvo: (lambda: (db.situacao(c) == alvo, f"situacao = {db.situacao(c)}"))
    caso("T06", A2, "nao administrador credencia Account 4",
         lambda: db.credenciar_emissor(A2, A4, "Entidade Indevida (ficticia)"), "Somente o administrador",
         sit(A4, "NaoCadastrado"))
    caso("T07", A3, "nao administrador descredencia Emissor A", lambda: db.descredenciar_emissor(A3, A2),
         "Somente o administrador", sit(A2, "Ativo"))
    caso("T08", A4, "conta sem permissao toma a administracao", lambda: db.transferir_administracao(A4, A4),
         "Somente o administrador", lambda: (db.administrador() == A1, "administrador = Account 1"))
    t0 = db.total()
    caso("T09", A2, "emitir hash vazio", lambda: db.emitir_certificado(A2, "0x" + "00" * 32), "Hash vazio",
         lambda: (db.total() == t0, f"total = {db.total()}"))
    caso("T10", A2, "revogar com motivo 0", lambda: db.revogar_certificado(A2, H["2"], 0), "Motivo invalido",
         est(H["2"], "Valido"))
    caso("T11", A2, "revogar com motivo 4", lambda: db.revogar_certificado(A2, H["2"], 4), "Motivo invalido",
         est(H["2"], "Valido"))
    caso("T12", A1, "credenciar endereco zero",
         lambda: db.credenciar_emissor(A1, "0x" + "00" * 20, "Entidade X (ficticia)"), "Conta invalida",
         sit("0x" + "00" * 20, "NaoCadastrado"))
    caso("T13", A1, "credenciar com nome vazio", lambda: db.credenciar_emissor(A1, A4, ""),
         "Nome da entidade vazio", sit(A4, "NaoCadastrado"))
    antes = db.certificado(H["2"])[:2]
    caso("T14", A2, "emitir de novo o CERT-0002", lambda: db.emitir_certificado(A2, H["2"]),
         "Certificado ja registrado", lambda: (db.certificado(H["2"])[:2] == antes, "emissor e data inalterados"))
    caso("T15", A2, "revogar de novo o CERT-0001", lambda: db.revogar_certificado(A2, H["1"], 1),
         "Certificado nao esta valido", est(H["1"], "Revogado"))
    caso("T16", A2, "revogar CERT-0003 inexistente", lambda: db.revogar_certificado(A2, H["3"], 1),
         "Certificado nao esta valido", est(H["3"], "Inexistente"))
    db.emitir_certificado(A3, H["3"]); db.emitir_certificado(A3, H["4"]); db.descredenciar_emissor(A1, A3)
    caso("T17", A3, "emissor descredenciado emite CERT-0005", lambda: db.emitir_certificado(A3, H["5"]),
         "Emissor nao autorizado", est(H["5"], "Inexistente"))
    caso("T18", A3, "emissor descredenciado revoga CERT-0003", lambda: db.revogar_certificado(A3, H["3"], 2),
         "Emissor nao autorizado", est(H["3"], "Valido"))
    caso("T19", A1, "administrador revoga CERT-0004 (fraude)", lambda: db.revogar_certificado(A1, H["4"], 2),
         None, est(H["4"], "Revogado"))
    passou = sum(1 for _, s in resultados if s == "PASSOU")
    print(f"\nParte A: {passou} de {len(resultados)} cenarios com o mesmo resultado do contrato.\n")
    return passou, len(resultados)


def parte_b(db, H):
    print("=== Parte B - alteracao direta por quem administra o banco (fora das regras) ===\n")
    print("Antes:  CERT-0001 =", db.estado(H["1"]), "| CERT-0002 emissor =", NOMES[db.certificado(H["2"])[0]],
          "| eventos registrados =", db.db.execute("SELECT COUNT(*) FROM eventos").fetchone()[0])
    # 1) "Ressuscita" um certificado revogado e troca o emissor de outro, sem chamar nenhuma regra.
    db.db.execute("UPDATE certificados SET estado='Valido', revogado_em=0, motivo=0 WHERE hash=?", (H["1"],))
    db.db.execute("UPDATE certificados SET emissor=? WHERE hash=?", (A4, H["2"]))
    # 2) Apaga do log os eventos que denunciariam a revogacao.
    apagados = db.db.execute("DELETE FROM eventos WHERE tipo='CertificadoRevogado' AND detalhe LIKE ?",
                             (H["1"] + "%",)).rowcount
    print("SQL executado: UPDATE certificados SET estado='Valido' ... (CERT-0001); "
          "UPDATE certificados SET emissor=Account 4 (CERT-0002); "
          f"DELETE FROM eventos ... ({apagados} evento apagado)")
    print("Depois: CERT-0001 =", db.estado(H["1"]), "| CERT-0002 emissor =", NOMES[db.certificado(H["2"])[0]],
          "| eventos registrados =", db.db.execute("SELECT COUNT(*) FROM eventos").fetchone()[0])
    print("Resultado: o verificador passa a ver o CERT-0001 como Valido e o CERT-0002 como emitido pela "
          "Account 4. Nenhuma regra da aplicacao foi acionada e o log nao guarda rastro da mudanca.")
    print("No contrato nao existe operacao que leve um certificado de Revogado para Valido nem que troque o "
          "emissor; o historico de transacoes e os eventos ficam no bloco. Numa rede real (varios nos e "
          "consenso), reescrever isso exigiria controlar a maioria da rede. No Remix VM (um unico no, no "
          "navegador) essa garantia NAO e demonstrada: quem controla o navegador pode reiniciar a cadeia.\n")


def parte_c(n):
    print(f"=== Parte C - desempenho, custo e espaco (n = {n} certificados) ===\n")
    hashes = [sha256_texto(f"CERT-MED-{i:05d} (ficticio)") for i in range(n)]

    # ---- SQLite em arquivo, uma transacao (commit) por operacao ----
    pasta = tempfile.mkdtemp(prefix="certchain_")
    arq = os.path.join(pasta, "certchain.db")
    db = CertChainDB(arq, A1)
    db.credenciar_emissor(A1, A2, "Semana de Tecnologia FEAP (ficticia)")
    t_emit, t_rev, t_cons = [], [], []
    for h in hashes:
        t = time.perf_counter(); db.emitir_certificado(A2, h); t_emit.append(time.perf_counter() - t)
    for h in hashes[: n // 2]:
        t = time.perf_counter(); db.revogar_certificado(A2, h, 1); t_rev.append(time.perf_counter() - t)
    for h in hashes:
        t = time.perf_counter(); db.estado(h); t_cons.append(time.perf_counter() - t)
    db.db.execute("PRAGMA wal_checkpoint(TRUNCATE)")
    tamanho = os.path.getsize(arq)
    db.db.close()
    for nome in os.listdir(pasta):
        os.remove(os.path.join(pasta, nome))
    os.rmdir(pasta)
    ms = lambda v: statistics.mean(v) * 1000
    print(f"SQLite (arquivo local, commit por operacao): emitir {ms(t_emit):.3f} ms | revogar {ms(t_rev):.3f} ms | "
          f"consultar {ms(t_cons):.4f} ms | arquivo {tamanho / 1024:.1f} KiB ({tamanho / n:.0f} bytes/certificado, "
          "com indices e log)")

    # ---- Contrato numa EVM local (py-evm) ----
    import json
    from web3 import Web3, EthereumTesterProvider
    artefato = opcao("--artefato")
    if artefato:
        dados = json.loads(Path(artefato).read_text(encoding="utf-8"))
        abi, bytecode = dados["abi"], dados["bytecode"]
    else:
        import solcx
        if "0.8.28" not in [str(v) for v in solcx.get_installed_solc_versions()]:
            solcx.install_solc("0.8.28")
        saida = solcx.compile_files([str(SRC / "CertChain.sol")], output_values=["abi", "bin"],
                                    solc_version="0.8.28", evm_version="cancun")
        c = next(v for k, v in saida.items() if k.endswith(":CertChain"))
        abi, bytecode = c["abi"], c["bin"]
    w3 = Web3(EthereumTesterProvider())
    c1, c2 = w3.eth.accounts[:2]
    rec = w3.eth.wait_for_transaction_receipt(w3.eth.contract(abi=abi, bytecode=bytecode).constructor()
                                              .transact({"from": c1}))
    f = w3.eth.contract(address=rec.contractAddress, abi=abi).functions
    gas_deploy = rec.gasUsed
    w3.eth.wait_for_transaction_receipt(f.credenciarEmissor(c2, "Semana de Tecnologia FEAP (ficticia)")
                                        .transact({"from": c1}))
    e_emit, e_rev, e_cons, g_emit, g_rev = [], [], [], [], []
    for h in hashes:
        t = time.perf_counter()
        r = w3.eth.wait_for_transaction_receipt(f.emitirCertificado(h).transact({"from": c2}))
        e_emit.append(time.perf_counter() - t); g_emit.append(r.gasUsed)
    for h in hashes[: n // 2]:
        t = time.perf_counter()
        r = w3.eth.wait_for_transaction_receipt(f.revogarCertificado(h, 1).transact({"from": c2}))
        e_rev.append(time.perf_counter() - t); g_rev.append(r.gasUsed)
    for h in hashes:
        t = time.perf_counter(); f.estadoDoCertificado(h).call(); e_cons.append(time.perf_counter() - t)
    print(f"Contrato na EVM local (py-evm, 1 no, sem rede): emitir {ms(e_emit):.1f} ms | revogar {ms(e_rev):.1f} ms | "
          f"consultar {ms(e_cons):.2f} ms")
    print(f"Gas: implantacao {gas_deploy} | emitir {statistics.mean(g_emit):.0f} (min {min(g_emit)}, max {max(g_emit)}) "
          f"| revogar {statistics.mean(g_rev):.0f} | consultar 0 (leitura view)")
    print("  (a primeira emissao custa mais porque grava totalCertificados pela primeira vez: "
          "escrever num slot zerado custa mais que atualizar um slot ja usado)")
    print(f"Armazenamento on-chain: 2 slots de 32 bytes por certificado (64 bytes), replicados em todos os nos "
          f"de uma rede real.")
    for gwei in (1, 10):
        eth_emit = statistics.mean(g_emit) * gwei * 1e-9
        print(f"Custo ilustrativo a {gwei} gwei/gas: emitir = {eth_emit:.6f} ETH por certificado; "
              f"{n} certificados = {eth_emit * n:.4f} ETH (o preco do gas e do ETH variam; Remix VM e gratis)")
    print("Observacao: a EVM local executa sem rede, sem mineracao e sem consenso. Numa rede publica, cada "
          "transacao ainda espera a inclusao num bloco (no Ethereum, um bloco a cada 12 s) e a finalizacao.\n")
    return {"sqlite_emit_ms": ms(t_emit), "evm_emit_ms": ms(e_emit), "gas_emit": statistics.mean(g_emit)}


def main():
    print("=== CertChain - blockchain (contrato) x banco de dados convencional (SQLite) ===")
    print("Data/hora (UTC):", datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S"),
          "| SQLite", sqlite3.sqlite_version, "| Python", sys.version.split()[0], "\n")
    H = {"1": sha256_arquivo("CERT-0001.pdf"), "2": sha256_arquivo("CERT-0002.pdf"),
         "3": sha256_arquivo("CERT-0003.pdf"), "2a": sha256_arquivo("CERT-0002_adulterado.pdf"),
         "4": sha256_texto("CERT-0004 (teste CP4)"), "5": sha256_texto("CERT-0005 (teste CP4)")}
    db = CertChainDB(":memory:", A1)
    passou, total = parte_a(db, H)
    parte_b(db, H)
    db.db.close()
    if "--medir" in sys.argv:
        parte_c(int(opcao("--n", "200")))
    else:
        print("(Parte C omitida: rode com --medir para medir desempenho e gas.)")
    return 0 if passou == total else 1


if __name__ == "__main__":
    sys.exit(main())
