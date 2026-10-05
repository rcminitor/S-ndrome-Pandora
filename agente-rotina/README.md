# Agente de rotina (WhatsApp)

Avisa no WhatsApp, via [CallMeBot](https://www.callmebot.com/), os blocos de tese (leitura, escrita, revisão), atividade física, outro estudo/hobby e descanso. Também manda um resumo às 7h. Lê o cofre da tese só para leitura: a próxima atividade do Índice, o capítulo em aberto e o balanço da semana.

Roda no GitHub Actions (`.github/workflows/avisos-rotina.yml`) a cada 10 min. A rotina (horários e mensagens) **não fica no repositório**: ela vem do secret `ROTINA_JSON`.

## Secrets (Settings → Secrets and variables → Actions)
| Nome | Conteúdo |
|---|---|
| `ROTINA_JSON` | o conteúdo de `rotina.json` (cópia local, fora do git) |
| `CALLMEBOT_APIKEY` | (opcional, WhatsApp) a chave enviada pelo CallMeBot |
| `WHATSAPP_PHONE` | +55… |
| `TELEGRAM_TOKEN` | (opcional) token do bot criado no @BotFather |
| `TELEGRAM_CHAT_ID` | (opcional) seu chat_id — `python avisar.py --telegram-chat-id` mostra |
| `COFRE_TOKEN` | token *fine-grained*, só leitura de *Contents* no repositório privado `sindrome-de-pandora` |

**Pausa (férias/feriado):** crie a *variable* `AGENTE_PAUSA_ATE` com uma data (`2026-12-31`), na aba *Variables*, e apague-a para voltar. Funciona pelo celular.

**Teste:** Actions → "Avisos da rotina" → Run workflow → marcar "teste".

**Falhas:** com 3 envios seguidos com erro, a execução fica vermelha e o GitHub manda e-mail.

Comandos locais: `python avisar.py --previa | --hoje | --teste | --pausar N | --retomar`.

Canais: configure WhatsApp, Telegram ou os dois (a mensagem vai para todos os configurados).
