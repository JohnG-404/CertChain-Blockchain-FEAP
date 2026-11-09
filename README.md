# CertChain — CP3 (primeira versão funcional)

## 1. Identificação

| Item | Resposta |
|---|---|
| Código do grupo | Não há (o grupo não recebeu código) |
| Título | CertChain: registro e verificação de certificados de atividades complementares com blockchain |
| Disciplina | Blockchain e Criptomoedas — FEAP 2026.2 |
| Caminho | Trilha fundamental: contrato-base RastreioLote adaptado, executado no **Remix VM** |
| Representante | João Gabriel Pereira Cardozo |
| Repositório | https://github.com/JohnG-404/CertChain-Blockchain-FEAP |

## 2. O que já funciona?

Fluxo executado sobre o **mesmo registro** (o certificado identificado pelo hash SHA-256 do PDF):

1. `constructor` — a conta que implanta vira **administradora** (governança).
2. `credenciarEmissor(conta, nomeEntidade)` — o administrador credencia emissores.
3. `emitirCertificado(hash)` — **cria o registro**: Inexistente → **Valido**. Só emissor Ativo.
4. `revogarCertificado(hash, motivo)` — **muda o estado**: Valido → **Revogado**. Só o emissor que emitiu.
5. `estadoDoCertificado(hash)` e `verificarCertificado(hash)` — **consultas** que mostram o antes e o depois.

Também implementados (testes completos ficam para o CP4): `descredenciarEmissor`, `transferirAdministracao` e `calcularHash` (SHA-256 de um texto).

**Ainda não funciona ou não foi testado:** todos os testes de entradas inválidas e de governança (hash vazio, hash duplicado, motivo inválido, revogação repetida, emissor descredenciado, conta que não é a administradora). Isso fica para o CP4. A versão em banco de dados para comparação está prevista para o CP4.

## 3. O que é preciso para executar?

| Item | Detalhe |
|---|---|
| Ferramenta | Navegador com https://remix.ethereum.org |
| Ambiente | Deploy & Run → Environment: **Remix VM** (usamos Remix VM (Osaka); remix.ethereum.org hoje redireciona para app.remix.live) |
| Compilador | Solidity **0.8.24 ou superior** (testado com 0.8.28), otimização desligada |
| Arquivo principal | `src/CertChain.sol` |
| Dados de teste | `src/certificados_ficticios/*.pdf` (fictícios, sem dados reais) |
| Opcional | Python 3.8+ para `src/gerar_hash.py` (sem bibliotecas externas) e para `src/teste_local.py` (`pip install web3 "eth-tester[py-evm]" py-solc-x`) |

Não há dependências, carteiras nem chaves: só as contas de teste do Remix VM.

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
11. Captura: `evidencias/T01_emissao.png` (Account, função, valor, terminal e consulta).

**T02 — mudança de estado do mesmo registro (positivo)**

12. Account **Conta 2** → `revogarCertificado(hashCertificado = hash CERT-0001, motivo = 1)` → **transact**.
13. Esperado: aceita. `estadoDoCertificado(hash CERT-0001)` → **2** (Revogado). `verificarCertificado` mostra `revogadoEm` preenchido e `motivo = 1`.
14. Captura: `evidencias/T02_revogacao.png`.

**T03 — conta sem permissão tenta revogar (negativo)**

15. Preparação: Account **Conta 2** → `emitirCertificado(hash CERT-0002)` → estado **1** (Valido). O T03 usa um **segundo** certificado ainda válido; se usasse o CERT-0001, já revogado, a rejeição viria do estado e não da permissão.
16. Account **Conta 3** (Emissor B, credenciado, mas não emitiu o CERT-0002) → `revogarCertificado(hash CERT-0002, 2)` → **transact**.
17. Esperado: transação **revertida** com `Somente o emissor do certificado`. `estadoDoCertificado(hash CERT-0002)` continua **1**.
18. Captura: `evidencias/T03_rejeicao_permissao.png`.

**T04 — conta não credenciada tenta emitir (negativo)**

19. Account **Conta 4** → `emitirCertificado(hash CERT-0003)` → **transact**.
20. Esperado: **revertida** com `Emissor nao autorizado`. `estadoDoCertificado(hash CERT-0003)` continua **0**.
21. Captura: `evidencias/T04_rejeicao_nao_credenciado.png`.

**T05 — documento adulterado (verificação)**

22. Account **Conta 5** → `verificarCertificado(hash CERT-0002_adulterado)` → retorna estado **0** (Inexistente), enquanto o CERT-0002 original retorna **1**.
23. Captura: `evidencias/T05_documento_adulterado.png`.

Se a página do Remix for recarregada, o contrato e os dados somem. O código fica salvo, mas é preciso repetir a partir do passo 3.

### 4.4 Execução automatizada (complementar)

`src/teste_local.py` repete o mesmo fluxo e os testes T01 a T05 numa EVM local (py-evm), com o mesmo contrato:

```
pip install web3 "eth-tester[py-evm]" py-solc-x
python src/teste_local.py
```

A saída registrada está em `evidencias/execucao_testes_local.txt`. Os endereços das contas nessa EVM são diferentes dos do Remix, mas os papéis são os mesmos.

## 5. Testes executados

Executados no Remix em 08/11/2026 (Remix IDE 2.6.13, Remix VM (Osaka), solc 0.8.28). Todos tiveram o resultado esperado.

| ID | Tipo | O que testa | Evidência |
|---|---|---|---|
| Prep. | — | Deploy pela Account 1 e credenciamento dos emissores A e B | `00_preparacao_deploy_e_credenciamento.png` |
| T01 | Positivo | Emissor A emite o CERT-0001 (Inexistente → Valido) | `T01_emissao.png`, `terminal_remix.txt` |
| T02 | Positivo | Emissor A revoga o CERT-0001 (Valido → Revogado) | `T02_revogacao.png`, `terminal_remix.txt` |
| T03 | Negativo | Emissor B tenta revogar o CERT-0002 do Emissor A: rejeitado, continua Valido | `T03_rejeicao_permissao.png`, `terminal_remix.txt` |
| T04 | Negativo | Conta 4, não credenciada, tenta emitir: rejeitada, continua Inexistente | `T04_rejeicao_nao_credenciado.png`, `terminal_remix.txt` |
| T05 | Verificação | Hash do PDF adulterado não é reconhecido (Inexistente) | `T05_documento_adulterado.png`, `terminal_remix.txt` |

Complemento: `evidencias/execucao_testes_local.txt` traz os mesmos T01 a T05 executados automaticamente numa EVM local (`src/teste_local.py`). O custo do T01 (94106 gas) foi igual no Remix e na execução local.

## 6. Limitações e próximos passos

- **Remix VM** é uma blockchain simulada num único navegador: não tem rede P2P nem consenso entre nós, e o estado some ao recarregar.
- A blockchain garante que o certificado **não foi alterado depois do registro**, mas não que o conteúdo é verdadeiro.
- Governança centralizada num único administrador (simplificação do protótipo; ver CP2).
- O hash é de um arquivo PDF; gerar o mesmo PDF em outro programa produz outro hash.
- **CP4 (16/11):** testes de entradas inválidas e de governança (hash vazio, hash duplicado, motivo 0 e 4, revogar duas vezes, emissor descredenciado tentando emitir, conta comum credenciando ou transferindo a administração); versão em banco de dados (SQLite + Python) com as mesmas regras; medição de gas por operação.
- **CP5 (23/11):** comparação final blockchain × banco de dados, relatório e pitch.

## 7. Fontes e uso de IA

- **Contrato-base RastreioLote** (Aula 6, FEAP 2026.2): referência e ponto de partida. O grupo manteve a organização (papéis e estados em enum, padrão verificações → efeitos → evento, função de hash e consulta de estado para os testes) e trocou o domínio: lote → certificado identificado por hash, papéis fixos → cadastro de emissores com situação Ativo/Inativo, `administrador` imutável → transferível, keccak256 → **SHA-256** (o mesmo algoritmo usado para os PDFs).
- **Simulação rastreio_lote_sim.py** (Aula 6): o formato da saída de testes de `teste_local.py` segue o da função `teste(...)`.
- **Bibliotecas:** reportlab (geração dos PDFs fictícios), web3.py, eth-tester/py-evm e py-solc-x (execução local).
- **IA generativa:** Claude (Anthropic) apoiou a escrita do contrato adaptado, dos scripts Python e deste README. A IA também operou o Remix no navegador do computador do representante, com autorização dele, para executar T01 a T05 e capturar as evidências. O grupo conferiu as capturas e cada `require` com a tabela de permissões do CP2. Os detalhes estão nas seções 9 e 10 do formulário do CP3.
