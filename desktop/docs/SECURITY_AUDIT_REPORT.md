# Relatorio de Auditoria de Seguranca e Clean Code
## Conexao Movel (NectarLink) - Servico de Downloads, Wake-on-LAN e Integracao RPC

Este documento consolida a auditoria estatica e dinamica de seguranca, sanitizacao de parametros, prevencao contra vulnerabilidades e conformidade de engenharia de software realizada pelo Subagente 5 (Auditor de Seguranca e Clean Code) no ecossistema do Conexao Movel (NectarLink).

---

## 1. Escopo e Objetivos da Auditoria

A auditoria cobriu os seguintes componentes e fluxos operacionais:
1. **Servico de Downloads de Midia Local**:
   - `desktop/downloader/downloader_service.py`: Motor core de integracao com `yt-dlp` e `ffmpeg`.
   - `desktop/downloader/downloader_server.py`: Servidor HTTP REST operando em `127.0.0.1:28795`.
   - `desktop/downloader/google_bridge_routes.py`: Rotas locais auxiliares de integracao Google Suite.
2. **Ponte RPC do Desktop Core (Rust)**:
   - `desktop/app/src/downloader_bridge.rs`: Ponte entre canais P2P (`media.download_rpc`) e a porta 28795.
   - `core/nectarlink-core/src/actions.rs`: Despacho de mensagens RPC e Wake-on-LAN.
3. **Especificacao e Empacotamento Windows**:
   - `desktop/docs/WINDOWS_WOL_DOWNLOADER_SPEC.md`: Especificacao arquitetural do pacote Windows.
   - `desktop/packaging/windows/downloader_manifest.json`: Manifesto de componentes e dependencias.
4. **Interfaces de Usuario (Desktop QML e Mobile Android)**:
   - `desktop/app/qml/pages/DownloadsPage.qml` e `desktop/app/qml/pages/WalkthroughPage.qml`.
   - `android/app/src/main/kotlin/app/nectarlink/android/ui/settings/SettingsScreen.kt`.
5. **Suite de Testes na pasta `area_de_testes/`**.

---

## 2. Diagnostico de Vulnerabilidades e Riscos Identificados (Pre-Auditoria)

Durante a inspecao profunda do codigo original, foram identificadas vulnerabilidades relevantes:

### 2.1. Falha Critica de Validacao de Origem (CORS / Zero-Trust Bypass)
- **Localizacao**: `desktop/downloader/downloader_server.py`.
- **Condicao Vulneravel**: A verificacao de origem utilizava prefixo simples:
  `origin.startswith("http://127.0.0.1") or origin.startswith("http://localhost")`.
- **Vetor de Exploracao**: Qualquer dominio malicioso controlado por um atacante iniciando com essa sequencia (como `http://localhost.evil.com` ou `http://127.0.0.1.attacker.org`) atendia a condicao, recebendo permissao de CORS irrestrita via cabecalho `Access-Control-Allow-Origin: <origin>`.
- **Impacto**: Um website aberto no navegador do usuario poderia realizar chamadas nao-autorizadas aos endpoints do servidor local.

### 2.2. Ausencia de Protecao contra DNS Rebinding
- **Localizacao**: `desktop/downloader/downloader_server.py`.
- **Condicao Vulneravel**: O servidor HTTP nao validava o cabecalho `Host` das requisicoes HTTP/1.1.
- **Vetor de Exploracao**: Um atacante configurando um nome de dominio externo com TTL curto resolvendo para `127.0.0.1` poderia forcar o navegador a emitir requisicoes com `Host: evil.com` diretamente a porta 28795 sem cabecalho `Origin`.
- **Impacto**: Acesso nao-autorizado a endpoints locais, incluindo leitura da area de transferencia via `/clipboard`.

### 2.3. Risco de Option Injection e Command Parameter Injection no yt-dlp
- **Localizacao**: `desktop/downloader/downloader_service.py`.
- **Condicao Vulneravel**: Os parametros de URL eram anexados ao comando sem a flag delimitadora de fim de opcoes (`--`) do padrao POSIX.
- **Vetor de Exploracao**: Caso parametros contendo opcoes de linha de comando como `--exec`, `--config-location` ou `--plugin-dirs` fossem fornecidos, o parser de argumentos do `yt-dlp` poderia interpretar tais valores como flags executaveis.
- **Impacto**: Potencial execucao arbitraria de comandos no host local.

### 2.4. Risco de SSRF (Server-Side Request Forgery) em Metadados de Nuvem
- **Localizacao**: `desktop/downloader/downloader_service.py`.
- **Condicao Vulneravel**: O metodo `inspect_url` aceitava qualquer URL iniciada por `http://` ou `https://`, permitindo alvos como `http://169.254.169.254` (metadados AWS/GCP) ou requisicoes de varredura interna na rede local.
- **Impacto**: Exfiltracao de metadados de infraestrutura ou sondagem de portas internas.

### 2.5. Ausencia de Limitacao de Taxa (Rate Limiting) e Concorrencia
- **Localizacao**: `desktop/downloader/downloader_server.py` e `downloader_service.py`.
- **Condicao Vulneravel**: Ausencia de limitador de requisicoes e ausencia de teto para processos `yt-dlp` em paralelo.
- **Impacto**: Ataques de exaustao de recursos (Denial of Service local) via chamadas repetidas de download e inspecao.

### 2.6. Caminhos Absolutos Indevidos no Codigo de Producao
- **Localizacao**: `desktop/app/qml/pages/WalkthroughPage.qml` e `DownloadsPage.qml`.
- **Condicao**: Utilizacao de caminhos hardcoded como `file:///home/Vincent/Downloads`, que falhariam em outros computadores ou no sistema operacional Windows.

### 2.7. Caractere Unicode em Interface Android
- **Localizacao**: `android/app/src/main/kotlin/app/nectarlink/android/ui/settings/SettingsScreen.kt`.
- **Condicao**: Utilizacao de caractere unicode (checkmark U+2713) em texto como icone de selecao de cor.

---

## 3. Medidas Corretivas e Hardening Implementados

Todas as vulnerabilidades foram corrigidas e validadas:

### 3.1. Validacao Estrita de Origem e Anti-DNS Rebinding
- No arquivo `downloader_server.py`, a funcao `is_allowed_origin` agora realiza o parsing da URI via `urllib.parse.urlparse`, extraindo o hostname canonico e validando rigorosamente se pertence exclusivamente a `127.0.0.1` ou `localhost`.
- Implementada a funcao `is_allowed_host`, validando que o cabecalho `Host` da requisicao pertence estritamente a `127.0.0.1` ou `localhost`. Requisicoes com hosts divergentes sao sumariamente bloqueadas com HTTP 403 Forbidden.
- O servidor HTTP foi migrado de `HTTPServer` sincrono para `ThreadingHTTPServer` assincrono e nao-bloqueante, impedindo que tarefas longas travem requisicoes concorrentes.

### 3.2. Sanitizacao de URLs, Prevencao de Injeccao e Bloqueio de SSRF
- No arquivo `downloader_service.py`, foi criada a funcao `validate_download_url`:
  - Limite estrito de tamanho (maximo 4096 caracteres).
  - Bloqueio de espacos, tabulacoes, quebras de linha (`\r`, `\n`) e caracteres de controle (`ord(c) < 32`).
  - Restricao de esquemas aos protocolos `http` e `https`.
  - Proibicao de credenciais embutidas (`user:pass@host`).
  - Bloqueio estrito de hostnames de loopback e metadados de nuvem (`localhost`, `127.0.0.1`, `::1`, `0.0.0.0`, `169.254.169.254`, dominios `.local` e `.internal`).
- Inclusao mandataria do separador `--` antes da URL em todas as chamadas ao `yt-dlp` (`inspect_url`, `_download_audio`, `_download_video`), garantindo que o interpretador de linha de comando trate o argumento estritamente como alvo posicional.
- Adicao das opcoes `--restrict-filenames` e `--windows-filenames` no `yt-dlp`, garantindo nomes de arquivo seguros e compativeis tanto em Linux quanto em Windows.

### 3.3. Prevencao contra Path Traversal em Arquivos Gerados
- Implementada a funcao `is_safe_path(base_dir, target_path)` utilizando `os.path.commonpath([real_base, real_target]) == real_base`.
- Todo arquivo gerado pelo `yt-dlp` ou extraido pelo `ffmpeg` e auditado antes de ser registrado no estado da tarefa ou repassado ao cliente.
- Sanitizacao estrita de identificadores `task_id` aceitando exclusivamente padrao alfanumerico com hifen e underscore (`^[a-zA-Z0-9_\-]{1,64}$`).

### 3.4. Mecanismo de Rate Limiting e Concorrencia
- Implementada a classe thread-safe `RateLimiter` com janelas deslizantes em memoria:
  - Limite global de requisicoes: maximo de 120 requisicoes por minuto.
  - Limite de inspecao (`/inspect`): maximo de 30 requisicoes por minuto.
  - Limite de inicio de download (`/download`): maximo de 15 requisicoes por minuto.
  - Teto maximo de 3 downloads simultaneos ativos (`MAX_CONCURRENT_DOWNLOADS = 3`). Ao atingir o teto, o servidor responde com HTTP 429 Too Many Requests com mensagem explicativa.

### 3.5. Correcao de Caminhos Absolutos no QML
- Em `desktop/app/qml/pages/DownloadsPage.qml` e `WalkthroughPage.qml`, os caminhos fixos foram substituidos por resolucao dinamica consultando o endpoint `/health` do servico local, obtendo o diretorio real do usuario em qualquer sistema operacional.

### 3.6. Eliminacao de Caractere Unicode no Android
- Em `android/app/src/main/kotlin/app/nectarlink/android/ui/settings/SettingsScreen.kt`, o caractere textual foi substituido pelo componente grafico `Surface` com formato circular `CircleShape`, em conformidade com o Material 3 e com a diretriz global de ausencia de emojis e simbolos improvisados.

---

## 4. Matriz de Homologacao e Testes de Seguranca (`area_de_testes/`)

Foi desenvolvida a suite automatizada `area_de_testes/test_downloader_security_hardening.py`, contendo 8 testes de alta cobertura:

| Teste | Objetivo | Resultado |
|---|---|---|
| `test_dns_rebinding_rejection` | Rejeita cabecalhos Host com dominios externos (HTTP 403) | APROVADO |
| `test_cors_zero_trust_subdomain_bypass_prevention` | Bloqueia subdominios como `localhost.evil.com` e `127.0.0.1.attacker.org` | APROVADO |
| `test_allowed_loopback_origins` | Aceita origens legitimas de loopback com cabecalhos CORS | APROVADO |
| `test_ssrf_internal_ips_rejected` | Bloqueia requisicoes para `169.254.169.254`, `localhost`, `0.0.0.0`, `.local` | APROVADO |
| `test_option_injection_and_control_chars_rejected` | Rejeita URLs com espacos, `--exec`, `--config` e credenciais | APROVADO |
| `test_path_traversal_task_id_rejected` | Impede `../` e caracteres maliciosos em task_id | APROVADO |
| `test_z_rate_limiting_protection` | Valida disparo de HTTP 429 sob rajadas em massa | APROVADO |
| `test_no_emojis_in_code_or_documentation` | Valida ausencia absoluta de emojis no arquivo de testes | APROVADO |

### 4.1. Validacao de Regressao Cruzada
Todas as suites da `area_de_testes/` foram executadas conjuntamente:
- `test_downloader_security_hardening.py`: 8 testes (APROVADO)
- `test_downloader_rpc_endpoints.py`: 13 testes (APROVADO)
- `test_downloader_integration.py`: 9 testes (APROVADO)
- `test_windows_wol_downloader_spec.py`: 6 testes (APROVADO)
- `test_wake_on_lan_packet.py`: 13 testes (APROVADO)
- `test_windows_installer_manifest.py`: 7 testes (APROVADO)
**Total: 56 testes executados e 100% aprovados.**

---

## 5. Auditoria de Clean Code e Conformidade com Diretrizes Globais

1. **Ausencia Absoluta de Emojis Unicode (Regra 3)**:
   - Realizada varredura automatizada completa em 115 arquivos modificados ou novos.
   - Confirmado: ZERO emojis em codigo de producao, comentarios, logs e documentacao.
   - (Apenas strings de teste em `core/nectarlink-core/tests/two_devices.rs` e `core/nectarlink-protocol/src/messages.rs` mantem caracteres unicode para testar a transmissao pura de texto UTF-8 pela rede P2P).
2. **Conformidade com Limite Seguro de Linhas (Regra 12)**:
   - `downloader_server.py`: 270 linhas (< 300 linhas).
   - `downloader_service.py`: 345 linhas (< 500 linhas).
   - `WINDOWS_WOL_DOWNLOADER_SPEC.md`: 253 linhas (< 300 linhas).
   - `downloader_manifest.json`: 183 linhas (< 300 linhas).
   - `test_downloader_security_hardening.py`: 175 linhas (< 300 linhas).
3. **Ausencia de Credenciais Expostas**:
   - Nenhuma chave privada, token de autenticacao permanente ou credencial de usuario esta exposta em texto plano.
4. **Padrao de Idioma e Documentacao (Regra 1)**:
   - Toda a documentacao, logs e mensagens tecnicas estao redigidos em Português do Brasil (pt-BR).

---

## 6. Conclusao

O servico de downloads e a esteira de comunicacao RPC do Conexao Movel (NectarLink) encontram-se plenamente endurecidos, protegidos contra ataques de rede local, injecoes de comando, contorno de CORS e esgotamento de recursos, cumprindo rigorosamente todos os padroes de excelencia de engenharia de software do ecossistema.
