// SPDX-License-Identifier: MIT
pragma solidity ^0.8.24;

/*
 * =====================================================================
 *  CertChain — registro e verificação de certificados de atividades
 *  complementares
 *  Projeto Integrador • Blockchain e Criptomoedas • FEAP 2026.2
 *
 *  BASE: contrato-base RastreioLote (Aula 6), ADAPTADO PELO GRUPO.
 *  Mantivemos a organização do contrato-base (papéis, estados,
 *  padrão verificações -> efeitos -> evento, funções de apoio aos
 *  testes) e trocamos o domínio "lote de resina" pelo domínio do
 *  projeto: emissores credenciados registram o hash de certificados.
 *
 *  HISTÓRICO
 *  - CP3 (09/11/2026): primeira versão funcional (src/historico/CertChain_CP3.sol).
 *  - CP4 (13/11/2026): ajuste em revogarCertificado após os testes T18 e T19:
 *    emissor descredenciado não revoga mais; o administrador pode revogar.
 *
 *  USO EXCLUSIVAMENTE EDUCACIONAL
 *  - Executar somente no Remix VM (blockchain simulada no navegador).
 *  - Usar apenas contas de teste do Remix e certificados fictícios.
 *  - Nenhum dado pessoal vai para a cadeia: só o hash do documento.
 *
 *  ESTADOS DO CERTIFICADO (registro principal)
 *      Inexistente -> Valido -> Revogado   (Revogado é final)
 *  SITUAÇÃO DO EMISSOR (registro de governança)
 *      NaoCadastrado -> Ativo <-> Inativo
 *
 *  PARTICIPANTES (CP2, seção 4.2)
 *  - Administrador (governança): credencia e descredencia emissores.
 *  - Emissor credenciado (Ativo): emite e revoga os próprios certificados.
 *  - Administrador também pode revogar qualquer certificado válido (CP4).
 *  - Verificador / aluno / empresa: apenas consultam (funções view).
 * =====================================================================
 */
contract CertChain {
    // -----------------------------------------------------------------
    // 1. ESTADOS
    // -----------------------------------------------------------------

    // O valor padrão de um enum é o primeiro item: um hash nunca
    // registrado aparece como Inexistente (mesma ideia do RastreioLote).
    enum Estado { Inexistente, Valido, Revogado }

    // Situação do emissor. NaoCadastrado = 0 (valor padrão).
    enum SituacaoEmissor { NaoCadastrado, Ativo, Inativo }

    // Códigos de motivo da revogação (CP2, seção 4.4).
    uint8 public constant MOTIVO_ERRO_EMISSAO = 1;
    uint8 public constant MOTIVO_FRAUDE = 2;
    uint8 public constant MOTIVO_CANCELAMENTO = 3;

    // -----------------------------------------------------------------
    // 2. DADOS REGISTRADOS (on-chain)
    //    Apenas o que alguma regra do contrato usa. O PDF do certificado,
    //    o nome do aluno, a carga horária e a atividade ficam FORA da
    //    cadeia; aqui vai só o hash SHA-256 do arquivo.
    // -----------------------------------------------------------------

    struct Emissor {
        string nomeEntidade;        // nome institucional (fictício no protótipo)
        SituacaoEmissor situacao;   // regra: só emissor Ativo emite
    }

    struct Certificado {
        address emissor;     // regra: só quem emitiu pode revogar
        uint64 emitidoEm;    // data da emissão (block.timestamp)
        uint64 revogadoEm;   // data da revogação (0 se válido)
        uint8 motivo;        // 0 = nenhum; 1, 2 ou 3 após revogação
        Estado estado;       // controla a sequência das operações
    }

    // Conta que governa o cadastro de emissores. Começa com quem
    // implantou o contrato e pode ser transferida (governança).
    address public administrador;

    // Cadastro de emissores, consultado pelo endereço.
    mapping(address => Emissor) public emissores;

    // Certificados, consultados pelo hash do documento.
    mapping(bytes32 => Certificado) public certificados;

    // Quantidade de certificados emitidos.
    uint256 public totalCertificados;

    // -----------------------------------------------------------------
    // 3. EVENTOS
    // -----------------------------------------------------------------

    event AdministracaoTransferida(address indexed anterior, address indexed novo);
    event EmissorCredenciado(address indexed emissor, string nomeEntidade);
    event EmissorDescredenciado(address indexed emissor);
    event CertificadoEmitido(bytes32 indexed hashCertificado, address indexed emissor);
    event CertificadoRevogado(bytes32 indexed hashCertificado, address indexed revogadoPor, uint8 motivo);

    // -----------------------------------------------------------------
    // 4. IMPLANTAÇÃO
    // -----------------------------------------------------------------

    constructor() {
        administrador = msg.sender;
        emit AdministracaoTransferida(address(0), msg.sender);
    }

    modifier somenteAdministrador() {
        require(msg.sender == administrador, "Somente o administrador");
        _;
    }

    // -----------------------------------------------------------------
    // 5. GOVERNANÇA: quem pode emitir
    // -----------------------------------------------------------------

    /// Credencia (ou reativa) uma conta como emissora. Somente o administrador.
    function credenciarEmissor(address conta, string calldata nomeEntidade) external somenteAdministrador {
        require(conta != address(0), "Conta invalida");
        require(bytes(nomeEntidade).length > 0, "Nome da entidade vazio");
        require(emissores[conta].situacao != SituacaoEmissor.Ativo, "Emissor ja ativo");

        emissores[conta] = Emissor({nomeEntidade: nomeEntidade, situacao: SituacaoEmissor.Ativo});
        emit EmissorCredenciado(conta, nomeEntidade);
    }

    /// Descredencia um emissor. Os certificados que ele já emitiu
    /// continuam consultáveis e válidos. Somente o administrador.
    function descredenciarEmissor(address conta) external somenteAdministrador {
        require(emissores[conta].situacao == SituacaoEmissor.Ativo, "Emissor nao esta ativo");

        emissores[conta].situacao = SituacaoEmissor.Inativo;
        emit EmissorDescredenciado(conta);
    }

    /// Transfere a administração para outra conta. Somente o administrador.
    function transferirAdministracao(address novoAdministrador) external somenteAdministrador {
        require(novoAdministrador != address(0), "Conta invalida");

        emit AdministracaoTransferida(administrador, novoAdministrador);
        administrador = novoAdministrador;
    }

    // -----------------------------------------------------------------
    // 6. OPERAÇÕES DO NEGÓCIO
    //    Padrão: verificações -> efeitos (estado) -> evento
    // -----------------------------------------------------------------

    /// Emissor credenciado registra o hash de um certificado novo.
    /// Estado: Inexistente -> Valido
    function emitirCertificado(bytes32 hashCertificado) external {
        // Verificações
        require(emissores[msg.sender].situacao == SituacaoEmissor.Ativo, "Emissor nao autorizado");
        require(hashCertificado != bytes32(0), "Hash vazio");
        require(certificados[hashCertificado].estado == Estado.Inexistente, "Certificado ja registrado");

        // Efeitos
        certificados[hashCertificado] = Certificado({
            emissor: msg.sender,
            emitidoEm: uint64(block.timestamp),
            revogadoEm: 0,
            motivo: 0,
            estado: Estado.Valido
        });
        totalCertificados++;

        emit CertificadoEmitido(hashCertificado, msg.sender);
    }

    /// Revoga um certificado válido, informando o motivo
    /// (1 = erro de emissão, 2 = fraude, 3 = cancelamento).
    /// Quem pode revogar (regra ajustada no CP4, testes T18 e T19):
    ///  - o emissor que emitiu o certificado, desde que ainda esteja Ativo;
    ///  - o administrador (governança), por exemplo para revogar um
    ///    certificado fraudulento de um emissor já descredenciado.
    /// Estado: Valido -> Revogado
    function revogarCertificado(bytes32 hashCertificado, uint8 motivo) external {
        Certificado storage cert = certificados[hashCertificado];
        bool ehAdministrador = msg.sender == administrador;

        // A verificação de estado também rejeita hash inexistente e revogação repetida.
        require(cert.estado == Estado.Valido, "Certificado nao esta valido");
        require(ehAdministrador || msg.sender == cert.emissor, "Somente o emissor do certificado");
        // CP4: um emissor descredenciado não altera mais o registro (antes ele conseguia revogar).
        require(
            ehAdministrador || emissores[msg.sender].situacao == SituacaoEmissor.Ativo,
            "Emissor nao autorizado"
        );
        require(motivo >= MOTIVO_ERRO_EMISSAO && motivo <= MOTIVO_CANCELAMENTO, "Motivo invalido");

        cert.estado = Estado.Revogado;
        cert.revogadoEm = uint64(block.timestamp);
        cert.motivo = motivo;

        emit CertificadoRevogado(hashCertificado, msg.sender, motivo);
    }

    // -----------------------------------------------------------------
    // 7. CONSULTAS E APOIO AOS TESTES (somente leitura, sem custo)
    // -----------------------------------------------------------------

    /// Consulta completa usada pelo verificador. Para hash nunca
    /// registrado, retorna estado 0 (Inexistente) e campos vazios.
    function verificarCertificado(bytes32 hashCertificado)
        external
        view
        returns (
            Estado estado,
            address emissor,
            string memory nomeEntidade,
            uint64 emitidoEm,
            uint64 revogadoEm,
            uint8 motivo
        )
    {
        Certificado storage cert = certificados[hashCertificado];
        return (
            cert.estado,
            cert.emissor,
            emissores[cert.emissor].nomeEntidade,
            cert.emitidoEm,
            cert.revogadoEm,
            cert.motivo
        );
    }

    /// Retorna o estado como número: 0 Inexistente, 1 Valido, 2 Revogado.
    function estadoDoCertificado(bytes32 hashCertificado) external view returns (Estado) {
        return certificados[hashCertificado].estado;
    }

    /// Gera o hash SHA-256 de um texto, para testes no Remix sem precisar
    /// de arquivo. Para um arquivo PDF, use src/gerar_hash.py (mesmo algoritmo).
    function calcularHash(string calldata texto) external pure returns (bytes32) {
        return sha256(bytes(texto));
    }
}
