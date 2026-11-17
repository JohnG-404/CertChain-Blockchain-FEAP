# CertChain — entrega final (CP5)

Protótipo do Projeto Integrador de Blockchain e Criptomoedas (FEAP 2026.2). Um contrato Solidity registra o **hash SHA-256** de certificados de atividades complementares emitidos por entidades credenciadas, permite revogá-los com motivo e deixa qualquer pessoa verificar se um PDF é autêntico e ainda válido. Este README traz tudo para executar o protótipo, repetir os testes e conferir as evidências.

## 1. Identificação

| Item | Resposta |
|---|---|
| Código do grupo | Não há (o grupo não recebeu código GXX) |
| Título | CertChain: registro e verificação de certificados de atividades complementares com blockchain |
| Disciplina | Blockchain e Criptomoedas — Engenharia da Computação — FEAP 2026.2 |
| Trilha | Fundamental: contrato-base RastreioLote adaptado, executado no **Remix VM** |
| Representante | João Gabriel Pereira Cardozo |
| Integrantes | 8 (nomes e termos em `manifesto.json`) |
| Repositório | https://github.com/JohnG-404/CertChain-Blockchain-FEAP (complementa o ZIP, não o substitui) |

## 2. Problema e solução

Alunos precisam comprovar horas de atividades complementares com certificados emitidos por eventos, empresas parceiras e pela própria faculdade. A secretaria, empresas e outras instituições precisam saber se um PDF é verdadeiro, quem o emitiu e se não foi cancelado. Hoje isso depende de conferência manual ou de confiar no sistema de um único emissor.

O CertChain guarda na cadeia **só o hash do PDF** e o estado do certificado. O PDF, o nome do aluno e a carga horária ficam **fora da cadeia** (com o aluno e com o emissor). Qualquer alteração no arquivo muda o hash, e o certificado deixa de ser reconhecido.

| On-chain (contrato) | Off-chain |
|---|---|
| hash SHA-256 do PDF, emissor, datas de emissão e revogação, motivo, estado | o PDF, nome e dados do aluno, atividade e carga horária |
| cadastro de emissores (nome da entidade e situação Ativo/Inativo), administrador | cálculo do hash (`src/gerar_hash.py` ou `calcularHash` para texto) |

## 3. O que funciona

Fluxo sobre o **mesmo registro** (o certificado identificado pelo hash):

1. `constructor` — a conta que implanta vira **administradora** (governança).
2. `credenciarEmissor(conta, nomeEntidade)` / `descredenciarEmissor(conta)` — o administrador controla quem emite.
3. `emitirCertificado(hash)` — **cria o registro**: Inexistente (0) → **Valido (1)**. Só emissor Ativo.
4. `revogarCertificado(hash, motivo)` — **muda o estado**: Valido → **Revogado (2)**, estado final. Pode revogar o emissor que emitiu, **enquanto estiver Ativo**, ou o **administrador**. Motivos: 1 erro de emissão, 2 fraude, 3 cancelamento.
5. `estadoDoCertificado(hash)` e `verificarCertificado(hash)` — **consultas** gratuitas (view) para o verificador.
6. `transferirAdministracao(novo)` e `calcularHash(texto)` (SHA-256 de um texto, para testes).

Todos os 19 testes passam no contrato final (`src/CertChain.sol`). O que **não** foi feito, por estar fora do escopo acordado: interface gráfica, rede pública ou de teste, armazenamento do PDF e assinatura com mais de um administrador.

### Ajuste feito no CP4 (antes × depois)

| Teste | Situação | Contrato do CP3 (`src/historico/CertChain_CP3.sol`) | Contrato final (`src/CertChain.sol`) |
|---|---|---|---|
| T18 | Emissor **descredenciado** tenta revogar um certificado que emitiu antes | Aceitava: o certificado virava Revogado (**FALHOU**) | Rejeita com `Emissor nao autorizado`; continua Valido (**PASSOU**) |
| T19 | Administrador revoga, por fraude, um certificado do emissor descredenciado | Rejeitava com `Somente o emissor do certificado`: ninguém conseguia revogar (**FALHOU**) | Aceita; o certificado vira Revogado (**PASSOU**) |

Mudanças no código: dois `require` em `revogarCertificado` e o evento `CertificadoRevogado`, que passou a registrar **quem revogou** (`revogadoPor`). Nada mudou no CP5.

## 4. Ambiente, versões e dependências

| Item | Detalhe |
|---|---|
| Demonstração | Navegador com https://app.remix.live (remix.ethereum.org redireciona para lá); usamos Remix IDE 2.6.13 (CP3) e 2.6.14 (CP4) |
| Ambiente | Deploy & Run → Environment: **Remix VM (Osaka)** |
| Compilador | Solidity **0.8.28** (aceita 0.8.24 ou superior), otimização desligada |
| Arquivo principal | `src/CertChain.sol`; versão do CP3 em `src/historico/CertChain_CP3.sol` |
| Dados de teste | `src/certificados_ficticios/*.pdf` (fictícios) e dois textos fictícios (seção 5.4) |
| Testes automatizados | Python 3.8+ e `pip install web3 "eth-tester[py-evm]" py-solc-x` |
| Comparação com banco | `src/comparacao_sqlite.py`: só biblioteca padrão (sqlite3) nas partes A e B; a parte C usa as mesmas bibliotecas acima |

Não há carteiras nem chaves: só as contas de teste do Remix VM.

## 5. Como implantar e executar (Remix VM)

Ordem: preparação → T01 a T05 (seção 5.3) → T06 a T19 (5.4) → antes do ajuste (5.5).

### 5.1 Contas e papéis

No campo **Account** do Remix VM, as contas aparecem sempre na mesma ordem. Usem:

| Conta do Remix | Endereço (normalmente) | Papel |
|---|---|---|
| Conta 1 | `0x5B38Da6a701c568545dCfcB03FcB875f56beddC4` | Administrador (implanta o contrato) |
| Conta 2 | `0xAb8483F64d9C6d1EcF9b849Ae677dD3315835cb2` | Emissor A — Semana de Tecnologia FEAP (fictícia) |
| Conta 3 | `0x4B20993Bc481177ec7E8f571ceCaE8A9e22C02db` | Emissor B — Empresa Parceira X (fictícia) |
| Conta 4 | `0x78731D3Ca6b7E34aC0F824c42a7cC18A495cabaB` | Conta sem permissão |
| Conta 5 | `0x617F2E2fD72FD9D5503197092aC168c91465E7f2` | Verificador (só consulta) |

Se os endereços forem diferentes, copiem pelo ícone ao lado de Account.

### 5.2 Hashes dos certificados fictícios

Os valores abaixo são o SHA-256 dos PDFs que estão no ZIP. Para conferir: `python src/gerar_hash.py "src/certificados_ficticios/*.pdf"`.
Usem os PDFs do ZIP. Se rodarem `gerar_certificados_ficticios.py` em outro computador, outra versão do reportlab pode gerar outros bytes e outros hashes.

| Arquivo | Hash SHA-256 (bytes32) |
|---|---|
| CERT-0001.pdf | `0xc8817a6e76282cd93ce4975dd11454ecbab71d6087a1704d42c94ae5acc5bec1` |
| CERT-0002.pdf | `0xc04f00c77193d987e0de79a6ad72b576819f03cc7cb28f43636de00e64e20dc2` |
| CERT-0003.pdf | `0xa89e7aa3dc0fbe6cf3f061ae6c62ffd4a6aca7b5333740368183654da1dd0a11` |
| CERT-0002_adulterado.pdf (carga horária 12 h → 120 h) | `0x40aea5f7f903668e2622d6feb608b9f7e6df8a0da5f77e4a485986fcbfc274d8` |

### 5.3 Passo a passo

> Dica: para funções com mais de um parâmetro, cliquem na seta ao lado do nome da função para abrir um campo por parâmetro. Assim o texto pode ser digitado sem aspas.

**Preparação**

1. Abram o Remix, criem o arquivo `CertChain.sol` e colem o conteúdo de `src/CertChain.sol`.
2. **Solidity Compiler** → versão 0.8.28 (0.8.24 ou superior funciona) → **Compile CertChain.sol**, sem erros.
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

### 5.4 Testes de validação T06 a T19 (continuação da mesma sessão)

Depois do T05, sem recarregar a página, continuem com as mesmas contas. Dois hashes extras são de textos fictícios (no Remix, `calcularHash` com o texto exato dá o mesmo valor):

| Texto | Hash SHA-256 (bytes32) |
|---|---|
| `CERT-0004 (teste CP4)` | `0xc76c97a1531928a0609ea173eef4ff74d8209d9b328830362bc0e495ef397fa5` |
| `CERT-0005 (teste CP4)` | `0x867c729de9f12ffb3600160c264ffac1c9c07149b693f850c012e5fb6ef63bf9` |

| ID | Conta | Chamada | Esperado | Captura |
|---|---|---|---|---|
| T06 | Conta 2 | `credenciarEmissor(Conta 4, "Entidade Indevida (ficticia)")` | revert `Somente o administrador` | `evidencias/T06_rejeicao.png` |
| T07 | Conta 3 | `descredenciarEmissor(Conta 2)` | revert `Somente o administrador` | `evidencias/T07_rejeicao.png` |
| T08 | Conta 4 | `transferirAdministracao(Conta 4)`; depois `administrador` | revert `Somente o administrador`; administrador = Conta 1 | `evidencias/T08_rejeicao.png` |
| T09 | Conta 2 | `emitirCertificado(0x` + 64 zeros`)` | revert `Hash vazio` | `evidencias/T09_rejeicao.png` |
| T10 | Conta 2 | `revogarCertificado(CERT-0002, 0)` | revert `Motivo invalido`; CERT-0002 continua 1 | `evidencias/T10_rejeicao.png` |
| T11 | Conta 2 | `revogarCertificado(CERT-0002, 4)` | revert `Motivo invalido` | `evidencias/T11_rejeicao.png` |
| T12 | Conta 1 | `credenciarEmissor(0x0000000000000000000000000000000000000000, "Entidade X (ficticia)")` | revert `Conta invalida` | `evidencias/T12_rejeicao.png` |
| T13 | Conta 1 | `credenciarEmissor(Conta 4, "")` (digitar `""` no campo do nome) | revert `Nome da entidade vazio` | `evidencias/T13_1_campo_vazio_remix.png`, `T13_2_rejeicao.png` |
| T14 | Conta 2 | `emitirCertificado(CERT-0002)` (já Valido) | revert `Certificado ja registrado` | `evidencias/T14_rejeicao.png` |
| T15 | Conta 2 | `revogarCertificado(CERT-0001, 1)` (já Revogado) | revert `Certificado nao esta valido` | `evidencias/T15_rejeicao.png` |
| T16 | Conta 2 | `revogarCertificado(CERT-0003, 1)` (não existe) | revert `Certificado nao esta valido` | `evidencias/T16_rejeicao.png` |
| Prep. | Conta 3, depois Conta 1 | Conta 3 emite o CERT-0003 e o `CERT-0004 (teste CP4)`; Conta 1 `descredenciarEmissor(Conta 3)` | tudo aceito; Conta 3 fica Inativa (situacao 2) | `evidencias/T17_preparacao.png` |
| T17 | Conta 3 | `emitirCertificado(CERT-0005 (teste CP4))` | revert `Emissor nao autorizado` | `evidencias/T17_rejeicao.png` |
| T18 | Conta 3 | `revogarCertificado(CERT-0003, 2)`; depois `estadoDoCertificado` | revert `Emissor nao autorizado`; CERT-0003 continua 1 | `evidencias/T18_depois_CP4.png` |
| T19 | Conta 1 | `revogarCertificado(CERT-0004 (teste CP4), 2)`; depois `estadoDoCertificado` | aceita; CERT-0004 vira 2 (Revogado) | `evidencias/T19_depois_CP4.png` |

**Atenção no T13:** deixar o campo `nomeEntidade` em branco não envia a transação; o Remix acusa erro de codificação dos argumentos (`T13_1_campo_vazio_remix.png`). Para enviar uma string vazia, digitem `""`; aí o contrato rejeita com `Nome da entidade vazio` (`T13_2_rejeicao.png`).

### 5.5 Antes do ajuste (contrato do CP3)

Na mesma sessão, compilem e implantem `src/historico/CertChain_CP3.sol` pela Conta 1, credenciem a Conta 3, emitam com ela o CERT-0003 e o CERT-0004, descredenciem-na e repitam T18 e T19. No contrato do CP3, o T18 é **aceito** (estado vai a 2) e o T19 é **rejeitado** com `Somente o emissor do certificado` (capturas `evidencias/T18_T19_preparacao_CP3.png`, `T18_antes_CP3.png` e `T19_antes_CP3.png`).

As capturas do CP4 foram feitas em 13/11/2026 (Remix IDE 2.6.14, Remix VM Osaka, compilador 0.8.28). Contrato final em `0xd9145CCE52D386f254917e481eB44e9943F39138` e contrato do CP3 em `0x9D7f74d0C41E726EC95884E0e97Fa6129e3b5E99`, na mesma sessão. As capturas T01 a T05 são do CP3 (09/11/2026, contrato do CP3); esses cinco testes não dependem da regra alterada e foram repetidos com o contrato final na execução automatizada.

## 6. Repetir os testes automaticamente

```
pip install web3 "eth-tester[py-evm]" py-solc-x
python src/executar_testes.py                                             # contrato final: 19 PASSOU
python src/executar_testes.py --contrato src/historico/CertChain_CP3.sol  # contrato do CP3: T18 e T19 FALHOU
python src/comparacao_sqlite.py --medir                                   # comparação com SQLite
```

`executar_testes.py` repete o fluxo e os 19 testes numa EVM local (py-evm), na mesma ordem das seções 5.3 a 5.5, e compara o observado com o esperado. Na primeira execução, o py-solc-x baixa o solc 0.8.28; sem internet, usem `--artefato arquivo.json` com ABI e bytecode já compilados. Saídas registradas: `evidencias/execucao_local_contrato_final.txt` (19 PASSOU) e `evidencias/execucao_local_contrato_CP3.txt` (17 PASSOU; T18 e T19 FALHOU). Os endereços das contas na EVM local são diferentes dos do Remix, mas os papéis são os mesmos.

## 7. Testes e evidências

`testes/casos.csv` tem um teste por linha, em UTF-8, com o cabeçalho `id,categoria,papel_conta,funcao,entradas,estado_inicial,esperado,observado,status,evidencia`. Quando há mais de uma evidência, os caminhos são separados por `; `. Todos os caminhos existem em `evidencias/`. O CSV detalhado do CP3/CP4 (com uma linha por execução, inclusive as falhas de T18 e T19 antes do ajuste) foi preservado em `testes/historico/casos_CP3_CP4_detalhado.csv`.

| Categoria | Testes | Resultado no contrato final |
|---|---|---|
| positivo | T01 (criação), T02 (revogação do mesmo registro), T05 (verificação de cópia adulterada) | 3 PASSOU |
| permissao | T03, T04, T06, T07, T08, T19 | 6 PASSOU (T19 FALHOU antes do ajuste) |
| entrada_invalida | T09, T10, T11, T12, T13 | 5 PASSOU |
| estado_invalido | T14, T15, T16, T17, T18 | 5 PASSOU (T18 FALHOU antes do ajuste) |

| Etapa | Onde | Resultado | Evidências |
|---|---|---|---|
| CP3 — T01 a T05 | Remix VM, 09/11/2026 | 5 PASSOU | `evidencias/P1`–`P3` (preparação) e `T01_*` a `T05_*` |
| CP4 — T01 a T19, contrato do CP3 | EVM local, 13/11/2026 | 17 PASSOU, T18 e T19 FALHOU | `evidencias/execucao_local_contrato_CP3.txt` |
| CP4 — T01 a T19, contrato final | EVM local, 13/11/2026 | 19 PASSOU | `evidencias/execucao_local_contrato_final.txt` |
| CP4 — T06 a T19, contrato final | Remix VM, 13/11/2026 | 14 PASSOU | `evidencias/T06_*` a `T19_depois_CP4.png` |
| CP4 — T18 e T19, contrato do CP3 | Remix VM, 13/11/2026 | T18 e T19 FALHOU (confirma a EVM local) | `evidencias/T18_antes_CP3.png`, `T19_antes_CP3.png` |
| CP5 — comparação com SQLite | Python 3 + SQLite | mesmas regras: 19 de 19 cenários iguais | `evidencias/comparacao_sqlite_blockchain.txt` |

Nota: as capturas `P1` a `P3` foram feitas depois dos testes do CP3, numa segunda implantação na mesma sessão (contrato `0xD7ACd2a9FD159E69Bb102A1ca21C9a3e3A5F771B`); a preparação do contrato usado nos testes aparece no terminal da captura `T01_2_transacao.png`.

## 8. Comparação com banco de dados convencional

`src/comparacao_sqlite.py` implementa as mesmas regras numa aplicação comum com SQLite (como faria o sistema de uma secretaria). Saída registrada em `evidencias/comparacao_sqlite_blockchain.txt`:

- **Parte A — regras:** os 19 cenários dão o mesmo resultado no SQLite. As regras não dependem de blockchain; um banco bem programado também as aplica.
- **Parte B — quem controla o banco:** com três comandos SQL, o administrador do banco "ressuscitou" o CERT-0001 revogado, trocou o emissor do CERT-0002 e apagou do log o evento da revogação. O verificador passou a ver dados falsos, sem rastro. No contrato não existe operação que faça isso, e numa rede real alterar o histórico exigiria controlar a maioria dos nós.
- **Parte C — desempenho e custo (200 certificados):** SQLite ≈ 0,4 ms por emissão; contrato na EVM local ≈ 50 ms, sem rede. Emitir custa ≈ 77 mil gas (94.106 no primeiro certificado), revogar ≈ 37 mil gas, consultar é grátis. Numa rede pública cada transação ainda espera um bloco (12 s no Ethereum) e paga taxa.

| Critério | Banco de dados (SQLite/servidor da faculdade) | Blockchain (CertChain) |
|---|---|---|
| Participantes | um dono do banco; os demais confiam nele | vários emissores e verificadores usam o mesmo registro |
| Confiança | quem administra o banco pode alterar ou apagar registros (parte B) | regras no contrato; histórico verificável; numa rede real, sem dono único |
| Custo e complexidade | baixo; tecnologia conhecida | gas por escrita, operação de nós ou dependência de rede pública; contrato difícil de corrigir depois de implantado |
| Desempenho | ≈ 0,4 ms por escrita | dezenas de ms mesmo sem rede; segundos ou minutos com consenso real |
| Privacidade | controle de acesso por usuário | tudo on-chain é público; por isso só o hash vai para a cadeia |
| Governança | centralizada na instituição | no protótipo ainda há um administrador único (risco); o ideal seria um consórcio ou várias assinaturas |

**Conclusão:** para uma única instituição emitindo e verificando os próprios certificados, um banco de dados com assinatura digital dos PDFs seria mais simples e barato. A blockchain passa a valer a pena quando **várias entidades independentes** (faculdades, empresas, eventos) emitem e outras precisam verificar sem confiar em um só sistema; mesmo assim, a escolha realista seria uma rede permissionada de consórcio, com governança compartilhada.

## 9. Limitações, riscos e simulação × blockchain real

- **Remix VM é uma simulação:** um único nó no navegador, sem rede P2P, sem consenso, sem replicação e sem imutabilidade de rede. O estado some ao recarregar e quem controla o navegador pode reiniciar a cadeia. O protótipo demonstra **as regras**; a garantia de imutabilidade só existiria numa rede real.
- A blockchain garante que o registro não foi alterado depois de gravado, **não** que o conteúdo do certificado é verdadeiro: um emissor credenciado pode registrar um certificado falso (por isso existe a revogação com motivo 2, fraude).
- **Governança centralizada:** o administrador credencia, descredencia e pode revogar qualquer certificado; se a conta for comprometida, o sistema inteiro fica comprometido. **Transferência da administração em uma etapa:** um endereço digitado errado perde o controle sem volta.
- **Privacidade:** só o hash vai para a cadeia, mas em rede pública as datas e o endereço do emissor ficam visíveis para todos; o PDF precisa ser guardado pelo aluno, porque sem ele não há como verificar.
- O hash é de um arquivo PDF; gerar o mesmo certificado em outro programa produz outro hash.
- **Custo e sustentabilidade:** cada escrita paga gas numa rede pública; redes com prova de participação (como o Ethereum atual) consomem pouca energia, mas o custo por transação varia com a demanda.
- Contrato implantado não pode ser corrigido no lugar: uma nova versão exige novo endereço e migração dos registros (como fizemos entre o CP3 e o CP4, só no ambiente de teste).

## 10. Fontes e uso de IA

- **Contrato-base RastreioLote** (Aula 6, FEAP 2026.2): ponto de partida. O grupo manteve a organização (papéis e estados em enum, padrão verificações → efeitos → evento, função de hash e consulta de estado) e trocou o domínio: lote → certificado identificado por hash, papéis fixos → cadastro de emissores Ativo/Inativo, `administrador` imutável → transferível, keccak256 → **SHA-256**.
- **Simulação rastreio_lote_sim.py** (Aula 6): o formato da saída dos testes segue o da função `teste(...)`.
- **Bibliotecas:** reportlab (PDFs fictícios), web3.py, eth-tester/py-evm e py-solc-x (execução local), sqlite3 da biblioteca padrão (comparação).
- **IA generativa:** Claude (Anthropic) apoiou a escrita do contrato, dos scripts, dos testes, da comparação com SQLite e deste README; executou os testes do CP4 no Remix pelo navegador do representante (extensão Claude in Chrome, só com contas de teste) e conferiu as capturas. O grupo conferiu cada resultado com o código e com as evidências. Detalhes na seção 5 do formulário do CP5.

## 11. Estrutura do pacote

```
manifesto.json                     disciplina, checkpoint, grupo, projeto, representante, integrantes, trilha, ambiente, arquivo principal
README.md                          este arquivo
src/CertChain.sol                  contrato final (arquivo principal)
src/historico/CertChain_CP3.sol    contrato entregue no CP3 (para o antes/depois)
src/executar_testes.py             bateria automatizada T01 a T19 (EVM local)
src/comparacao_sqlite.py           mesmas regras em SQLite, adulteração direta e medições
src/gerar_hash.py                  SHA-256 dos PDFs (formato bytes32)
src/gerar_certificados_ficticios.py e src/certificados_ficticios/   certificados fictícios
src/historico/teste_local_CP3.py   script de testes do CP3 (T01 a T05), mantido como histórico
testes/casos.csv                   um teste por linha (T01 a T19), formato padrão do CP5
testes/historico/casos_CP3_CP4_detalhado.csv   registro detalhado das execuções do CP3 e do CP4
evidencias/                        capturas do Remix ([ID]_*.png), saídas da EVM local e da comparação com SQLite
```
