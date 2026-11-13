# CertChain — CP4 (validação e ajustes)

Protótipo do Projeto Integrador de Blockchain e Criptomoedas (FEAP 2026.2). O CP4 testou permissões, entradas inválidas e situações de falha do contrato entregue no CP3, corrigiu as duas falhas encontradas (T18 e T19) e repetiu todos os testes.

## 1. Identificação

| Item | Resposta |
|---|---|
| Código do grupo | Não há (o grupo não recebeu código) |
| Título | CertChain: registro e verificação de certificados de atividades complementares com blockchain |
| Disciplina | Blockchain e Criptomoedas — FEAP 2026.2 |
| Caminho | Trilha fundamental: contrato-base RastreioLote adaptado, executado no **Remix VM** |
| Representante | João Gabriel Pereira Cardozo |
| Repositório | https://github.com/JohnG-404/CertChain-Blockchain-FEAP |
| Manifesto | `manifesto.json` (grupo, integrantes, trilha e arquivo principal) |

## 2. O que funciona?

Fluxo sobre o **mesmo registro** (o certificado identificado pelo hash SHA-256 do PDF):

1. `constructor` — a conta que implanta vira **administradora** (governança).
2. `credenciarEmissor(conta, nomeEntidade)` / `descredenciarEmissor(conta)` — o administrador controla quem emite.
3. `emitirCertificado(hash)` — **cria o registro**: Inexistente → **Valido**. Só emissor Ativo.
4. `revogarCertificado(hash, motivo)` — **muda o estado**: Valido → **Revogado**. Regra ajustada no CP4: o emissor que emitiu, **desde que ainda esteja Ativo**, ou o **administrador**.
5. `estadoDoCertificado(hash)` e `verificarCertificado(hash)` — **consultas** que mostram o antes e o depois.
6. `transferirAdministracao(novo)` e `calcularHash(texto)` (SHA-256 de um texto, para testes).

### Ajuste do CP4 (antes × depois)

| Teste | Situação | Contrato do CP3 (`src/historico/CertChain_CP3.sol`) | Contrato do CP4 (`src/CertChain.sol`) |
|---|---|---|---|
| T18 | Emissor B **descredenciado** tenta revogar um certificado que emitiu antes | Aceitava: o certificado virava Revogado (**FALHOU**) | Rejeita com `Emissor nao autorizado`; continua Valido (**PASSOU**) |
| T19 | Administrador revoga, por fraude, um certificado do emissor descredenciado | Rejeitava com `Somente o emissor do certificado`: ninguém conseguia revogar (**FALHOU**) | Aceita; o certificado vira Revogado (**PASSOU**) |

Mudanças no código: dois `require` em `revogarCertificado` e o evento `CertificadoRevogado`, que passou a registrar **quem revogou** (`revogadoPor`) em vez do emissor. O resto do contrato não mudou.

## 3. O que é preciso para executar?

| Item | Detalhe |
|---|---|
| Ferramenta | Navegador com https://app.remix.live (remix.ethereum.org redireciona para lá) |
| Ambiente | Deploy & Run → Environment: **Remix VM** (usamos Remix VM (Osaka)) |
| Compilador | Solidity **0.8.24 ou superior** (testado com 0.8.28), otimização desligada |
| Arquivo principal | `src/CertChain.sol` (versão do CP4); versão do CP3 em `src/historico/CertChain_CP3.sol` |
| Dados de teste | `src/certificados_ficticios/*.pdf` (fictícios, sem dados reais) |
| Testes automatizados | Python 3.8+ e `pip install web3 "eth-tester[py-evm]" py-solc-x` para `src/executar_testes.py` |

Não há carteiras nem chaves: só as contas de teste do Remix VM.

## 4. Como repetir a demonstração (Remix VM)

### 4.1 Contas e papéis

No campo **Account** do Remix VM, as contas aparecem sempre na mesma ordem. Usem:

| Conta do Remix | Endereço (normalmente) | Papel |
|---|---|---|
| Conta 1 | `0x5B38Da6a701c568545dCfcB03FcB875f56beddC4` | Administrador (implanta o contrato) |
| Conta 2 | `0xAb8483F64d9C6d1EcF9b849Ae677dD3315835cb2` | Emissor A — Semana de Tecnologia FEAP (fictícia) |
| Conta 3 | `0x4B20993Bc481177ec7E8f571ceCaE8A9e22C02db` | Emissor B — Empresa Parceira X (fictícia) |
| Conta 4 | `0x78731D3Ca6b7E34aC0F824c42a7cC18A495cabaB` | Conta sem permissão |
| Conta 5 | `0x617F2E2fD72FD9D5503197092aC168c91465E7f2` | Verificador (só consulta) |

Se os endereços forem diferentes, copiem pelo ícone ao lado de Account.

### 4.2 Hashes dos certificados fictícios

Os valores abaixo são o SHA-256 dos PDFs que estão no ZIP. Para conferir: `python src/gerar_hash.py "src/certificados_ficticios/*.pdf"`.
Usem os PDFs do ZIP. Se rodarem `gerar_certificados_ficticios.py` em outro computador, outra versão do reportlab pode gerar outros bytes e outros hashes.

| Arquivo | Hash SHA-256 (bytes32) |
|---|---|
| CERT-0001.pdf | `0xc8817a6e76282cd93ce4975dd11454ecbab71d6087a1704d42c94ae5acc5bec1` |
| CERT-0002.pdf | `0xc04f00c77193d987e0de79a6ad72b576819f03cc7cb28f43636de00e64e20dc2` |
| CERT-0003.pdf | `0xa89e7aa3dc0fbe6cf3f061ae6c62ffd4a6aca7b5333740368183654da1dd0a11` |
| CERT-0002_adulterado.pdf (carga horária 12 h → 120 h) | `0x40aea5f7f903668e2622d6feb608b9f7e6df8a0da5f77e4a485986fcbfc274d8` |

### 4.3 Passo a passo

> Dica: para funções com mais de um parâmetro, cliquem na seta ao lado do nome da função para abrir um campo por parâmetro. Assim o texto pode ser digitado sem aspas.

**Preparação**

1. Abram o Remix, criem o arquivo `CertChain.sol` e colem o conteúdo de `src/CertChain.sol`.
2. **Solidity Compiler** → versão 0.8.24 ou superior → **Compile CertChain.sol**, sem erros.
3. **Deploy & Run Transactions** → Environment **Remix VM** → Account **Conta 1** → Contract **CertChain** → **Deploy**.
4. Em *Deployed Contracts*, abram o contrato e cliquem em `administrador`: deve aparecer o endereço da Conta 1.
5. Ainda com a **Conta 1**: `credenciarEmissor(conta = endereço da Conta 2, nomeEntidade = Semana de Tecnologia FEAP (ficticia))` → **transact**.
6. Ainda com a **Conta 1**: `credenciarEmissor(conta = endereço da Conta 3, nomeEntidade = Empresa Parceira X (ficticia))` → **transact**.
7. Conferência: `emissores(endereço da Conta 2)` retorna o nome e `situacao: 1` (Ativo).

**T01 — criação do registro (positivo)**

8. `estadoDoCertificado(hash CERT-0001)` → **0** (Inexistente). Este é o "antes".
9. Account **Conta 2** → `emitirCertificado(0xc8817a6e…bec1)` (hash completo do CERT-0001) → **transact**.
10. Esperado: transação aceita (✔ no terminal). `estadoDoCertificado(hash CERT-0001)` → **1** (Valido). `verificarCertificado(hash CERT-0001)` mostra o emissor = Conta 2 e o nome da entidade.
11. Capturas: `evidencias/T01_1_antes.png` a `T01_4_depois.png` (Account, função, valor, terminal e consulta).

**T02 — mudança de estado do mesmo registro (positivo)**

12. Account **Conta 2** → `revogarCertificado(hashCertificado = hash CERT-0001, motivo = 1)` → **transact**.
13. Esperado: aceita. `estadoDoCertificado(hash CERT-0001)` → **2** (Revogado). `verificarCertificado` mostra `revogadoEm` preenchido e `motivo = 1`.
14. Capturas: `evidencias/T02_1_transacao.png` e `T02_2_depois.png`.

**T03 — conta sem permissão tenta revogar (negativo)**

15. Preparação: Account **Conta 2** → `emitirCertificado(hash CERT-0002)` → estado **1** (Valido). O T03 usa um **segundo** certificado ainda válido; se usasse o CERT-0001, já revogado, a rejeição viria do estado e não da permissão.
16. Account **Conta 3** (Emissor B, credenciado, mas não emitiu o CERT-0002) → `revogarCertificado(hash CERT-0002, 2)` → **transact**.
17. Esperado: transação **revertida** com `Somente o emissor do certificado`. `estadoDoCertificado(hash CERT-0002)` continua **1**.
18. Capturas: `evidencias/T03_1_preparacao.png` a `T03_3_depois.png`.

**T04 — conta não credenciada tenta emitir (negativo)**

19. Account **Conta 4** → `emitirCertificado(hash CERT-0003)` → **transact**.
20. Esperado: **revertida** com `Emissor nao autorizado`. `estadoDoCertificado(hash CERT-0003)` continua **0**.
21. Capturas: `evidencias/T04_1_rejeicao.png` e `T04_2_depois.png`.

**T05 — documento adulterado (verificação)**

22. Account **Conta 5** → `verificarCertificado(hash CERT-0002_adulterado)` → retorna estado **0** (Inexistente), enquanto o CERT-0002 original retorna **1**.
23. Capturas: `evidencias/T05_1_adulterado.png` e `T05_2_original.png`.

Se a página do Remix for recarregada, o contrato e os dados somem. O código fica salvo, mas é preciso repetir a partir do passo 3.

### 4.4 Testes do CP4 no Remix (continuação da mesma sessão)

Depois do T05, sem recarregar a página, continuem com as mesmas contas. Dois hashes extras são de textos fictícios (no Remix, `calcularHash` com o texto exato dá o mesmo valor):

| Texto | Hash SHA-256 (bytes32) |
|---|---|
| `CERT-0004 (teste CP4)` | `0xc76c97a1531928a0609ea173eef4ff74d8209d9b328830362bc0e495ef397fa5` |
| `CERT-0005 (teste CP4)` | `0x867c729de9f12ffb3600160c264ffac1c9c07149b693f850c012e5fb6ef63bf9` |

| ID | Conta | Chamada | Esperado (contrato do CP4) | Captura sugerida |
|---|---|---|---|---|
| T06 | Conta 2 | `credenciarEmissor(Conta 4, "Entidade Indevida (ficticia)")` | revert `Somente o administrador` | `evidencias/CP4/T06_rejeicao.png` |
| T07 | Conta 3 | `descredenciarEmissor(Conta 2)` | revert `Somente o administrador` | `evidencias/CP4/T07_rejeicao.png` |
| T08 | Conta 4 | `transferirAdministracao(Conta 4)`; depois `administrador` | revert `Somente o administrador`; administrador = Conta 1 | `evidencias/CP4/T08_rejeicao.png` |
| T09 | Conta 2 | `emitirCertificado(0x` + 64 zeros`)` | revert `Hash vazio` | `evidencias/CP4/T09_rejeicao.png` |
| T10 | Conta 2 | `revogarCertificado(CERT-0002, 0)` | revert `Motivo invalido`; CERT-0002 continua 1 | `evidencias/CP4/T10_rejeicao.png` |
| T11 | Conta 2 | `revogarCertificado(CERT-0002, 4)` | revert `Motivo invalido` | `evidencias/CP4/T11_rejeicao.png` |
| T12 | Conta 1 | `credenciarEmissor(0x0000000000000000000000000000000000000000, "Entidade X (ficticia)")` | revert `Conta invalida` | `evidencias/CP4/T12_rejeicao.png` |
| T13 | Conta 1 | `credenciarEmissor(Conta 4, "")` (nome em branco) | revert `Nome da entidade vazio` | `evidencias/CP4/T13_rejeicao.png` |
| T14 | Conta 2 | `emitirCertificado(CERT-0002)` (já Valido) | revert `Certificado ja registrado` | `evidencias/CP4/T14_rejeicao.png` |
| T15 | Conta 2 | `revogarCertificado(CERT-0001, 1)` (já Revogado) | revert `Certificado nao esta valido` | `evidencias/CP4/T15_rejeicao.png` |
| T16 | Conta 2 | `revogarCertificado(CERT-0003, 1)` (não existe) | revert `Certificado nao esta valido` | `evidencias/CP4/T16_rejeicao.png` |
| Prep. | Conta 3, depois Conta 1 | Conta 3 emite o CERT-0003 e o `CERT-0004 (teste CP4)`; Conta 1 `descredenciarEmissor(Conta 3)` | tudo aceito; Conta 3 fica Inativa (situacao 2) | `evidencias/CP4/T17_preparacao.png` |
| T17 | Conta 3 | `emitirCertificado(CERT-0005 (teste CP4))` | revert `Emissor nao autorizado`; CERT-0003 continua 1 | `evidencias/CP4/T17_rejeicao.png` |
| T18 | Conta 3 | `revogarCertificado(CERT-0003, 2)` | revert `Emissor nao autorizado`; CERT-0003 continua 1 | `evidencias/CP4/T18_depois_CP4.png` |
| T19 | Conta 1 | `revogarCertificado(CERT-0004 (teste CP4), 2)` | aceita; CERT-0004 vira 2 (Revogado) | `evidencias/CP4/T19_depois_CP4.png` |

Para mostrar o **antes** do ajuste: implantem `src/historico/CertChain_CP3.sol` (Deploy de novo, pela Conta 1), credenciem a Conta 3, emitam com ela o CERT-0003 e o CERT-0004, descredenciem-na e repitam T18 e T19. No contrato do CP3, o T18 é aceito e o T19 é rejeitado (capturas `evidencias/CP4/T18_antes_CP3.png` e `T19_antes_CP3.png`).

### 4.5 Execução automatizada (todos os testes, T01 a T19)

`src/executar_testes.py` repete o fluxo e os 19 testes numa EVM local (py-evm), na mesma ordem da tabela acima, e compara o observado com o esperado:

```
pip install web3 "eth-tester[py-evm]" py-solc-x
python src/executar_testes.py                                        # contrato do CP4
python src/executar_testes.py --contrato src/historico/CertChain_CP3.sol   # contrato do CP3 (antes)
python src/executar_testes.py --csv testes/resultado_local.csv       # também grava um CSV
```

Na primeira execução, o py-solc-x baixa o compilador solc 0.8.28. As saídas registradas estão em `evidencias/CP4/CP4_depois_contrato_CP4.txt` (19 PASSOU) e `evidencias/CP4/CP4_antes_contrato_CP3.txt` (17 PASSOU, T18 e T19 FALHOU). Os endereços das contas na EVM local são diferentes dos do Remix, mas os papéis são os mesmos.

## 5. Testes executados

O detalhamento de cada teste (conta, função, entradas, estado inicial, esperado, observado, status e evidência) está em **`testes/casos.csv`**.

| Etapa | Testes | Onde | Resultado | Evidências |
|---|---|---|---|---|
| CP3 | T01 a T05 (fluxo, permissões, documento adulterado) | Remix VM, 09/11/2026 | 5 PASSOU | `evidencias/P1`–`P3`, `T01_*` a `T05_*` (.png) |
| CP4, antes do ajuste | T01 a T19 no contrato do CP3 | EVM local, 13/11/2026 | 17 PASSOU, **T18 e T19 FALHOU** | `evidencias/CP4/CP4_antes_contrato_CP3.txt` |
| CP4, depois do ajuste | T01 a T19 no contrato do CP4 (inclui a regressão de T01 a T05) | EVM local, 13/11/2026 | **19 PASSOU** | `evidencias/CP4/CP4_depois_contrato_CP4.txt` |

| Categoria | Testes do CP4 |
|---|---|
| Permissões | T06 (credenciar sem ser administrador), T07 (descredenciar sem ser administrador), T08 (tomar a administração), T19 (administrador revoga por fraude) |
| Entradas inválidas | T09 (hash vazio), T10 e T11 (motivo 0 e 4), T12 (endereço zero), T13 (nome vazio) |
| Falhas / estado indevido | T14 (emitir hash já registrado), T15 (revogar duas vezes), T16 (revogar hash inexistente), T17 (emissor descredenciado emite), T18 (emissor descredenciado revoga) |

Nota sobre o CP3: as capturas `P1` a `P3` foram feitas depois dos testes, numa segunda implantação na mesma sessão (contrato `0xD7ACd2a9FD159E69Bb102A1ca21C9a3e3A5F771B`); a preparação do contrato usado nos testes aparece no terminal da captura `T01_2_transacao.png`.

## 6. Limitações e pendências para o CP5

- **Remix VM** é uma blockchain simulada num único navegador: não tem rede P2P nem consenso, e o estado some ao recarregar.
- A blockchain garante que o certificado **não foi alterado depois do registro**, mas não que o conteúdo é verdadeiro.
- **Governança centralizada:** o administrador credencia, descredencia e, desde o CP4, pode revogar qualquer certificado. Restringir a revogação pelo administrador a fraude (motivo 2) ou exigir mais de uma assinatura fica como discussão para o CP5.
- **Transferência da administração em uma etapa:** se o administrador digitar um endereço errado em `transferirAdministracao`, perde o controle sem volta. A correção usual (o novo administrador aceitar a transferência) fica registrada como limitação conhecida.
- O hash é de um arquivo PDF; gerar o mesmo PDF em outro programa produz outro hash.
- **CP5 (23/11):** comparação blockchain × banco de dados (versão SQLite com as mesmas regras, prevista desde o CP2), relatório final e pitch.

## 7. Fontes e uso de IA

- **Contrato-base RastreioLote** (Aula 6, FEAP 2026.2): ponto de partida. O grupo manteve a organização (papéis e estados em enum, padrão verificações → efeitos → evento, função de hash e consulta de estado) e trocou o domínio: lote → certificado identificado por hash, papéis fixos → cadastro de emissores Ativo/Inativo, `administrador` imutável → transferível, keccak256 → **SHA-256**.
- **Simulação rastreio_lote_sim.py** (Aula 6): o formato da saída dos testes segue o da função `teste(...)`.
- **Bibliotecas:** reportlab (PDFs fictícios), web3.py, eth-tester/py-evm e py-solc-x (execução local).
- **IA generativa:** Claude (Anthropic) apoiou a escrita do contrato, dos scripts, dos testes do CP4 e deste README, e conferiu as capturas do CP3. Os testes do CP4 e a comparação antes/depois foram executados com `src/executar_testes.py`. Os detalhes estão na seção 6 do formulário do CP4.

## 8. Estrutura do pacote

```
manifesto.json                     grupo, integrantes, trilha e arquivo principal
README.md                          este arquivo
src/CertChain.sol                  contrato atual (CP4)
src/historico/CertChain_CP3.sol    contrato entregue no CP3 (para o antes/depois)
src/executar_testes.py             bateria automatizada T01 a T19
src/gerar_hash.py                  SHA-256 dos PDFs (formato bytes32)
src/gerar_certificados_ficticios.py e src/certificados_ficticios/   certificados fictícios
src/historico/teste_local_CP3.py   script de testes do CP3 (T01 a T05), mantido como histórico
testes/casos.csv                   todos os testes, com esperado, observado, status e evidência
evidencias/                        capturas do Remix (CP3) e saídas do CP4 em evidencias/CP4/
```
