# Guia de Templates — Gerador de Certificados

> Este guia é para a equipe de Treinamentos. Nenhum conhecimento técnico é necessário para seguir estas instruções.

---

## O que é um template?

O template é o arquivo PowerPoint (`.pptx`) ou Word (`.docx`) que serve de modelo para todos os certificados. Ele contém o visual completo — cores, fontes, logos, layout — e **marcadores especiais** nos lugares onde os dados de cada participante serão inseridos automaticamente. Este guia usa o PowerPoint como exemplo, mas as mesmas regras de variável valem para o Word.

---

## Como inserir variáveis no template

As variáveis são textos no formato `{{NOME_DA_VARIAVEL}}` inseridos diretamente no PowerPoint, **no lugar** onde você quer que apareça a informação do participante.

### Regras obrigatórias

| Regra | Correto | Errado |
|---|---|---|
| Sempre maiúsculo | `{{NOME}}` | `{{nome}}` |
| Sem espaços dentro | `{{NOME_COMPLETO}}` | `{{NOME COMPLETO}}` |
| Sem acentos na variável | `{{FUNCAO}}` | `{{FUNÇÃO}}` |
| Com duplas chaves | `{{NOME}}` | `{NOME}` ou `[NOME]` |
| Separar palavras com `_` | `{{DATA_CONCLUSAO}}` | `{{DATA-CONCLUSAO}}` |

### Exemplos de variáveis comuns

```
{{NOME}}           → Nome completo do participante
{{RG}}             → Número do RG
{{CPF}}            → CPF
{{CARGO}}          → Cargo ou função
{{TREINAMENTO}}    → Nome do treinamento
{{DATA_INICIO}}    → Data de início
{{DATA_CONCLUSAO}} → Data de conclusão
{{CARGA_HORARIA}}  → Carga horária em horas
```

### Como inserir no PowerPoint

1. Abra o template `.pptx` no PowerPoint
2. Clique na caixa de texto onde quer inserir a variável
3. Posicione o cursor no local exato
4. Digite a variável: `{{NOME}}`
5. **Importante:** Digite tudo de uma vez, sem apagar e redigitar partes — isso evita que o PowerPoint quebre a variável em pedaços internamente
6. Salve o arquivo

---

## Como preparar a planilha

A planilha (`.xlsx`, `.xls`, `.ods` ou `.csv`) deve ter:
- **Primeira linha**: nomes das colunas (cabeçalho)
- **Demais linhas**: um participante por linha

### Correspondência variável ↔ coluna

O aplicativo permite mapear cada variável do template para qualquer coluna da planilha — você não precisa nomear as colunas igual às variáveis. O app exibe um dropdown para cada variável onde você escolhe qual coluna corresponde.

**Dica:** Se o nome da coluna for igual ao nome da variável (sem chaves), o mapeamento é feito automaticamente. Exemplo: coluna `NOME` mapeia automaticamente para `{{NOME}}`.

### Valor fixo em vez de coluna ("Texto")

Ao lado de cada variável no painel de mapeamento existe um seletor **Planilha / Texto**. Use "Texto" quando o valor deve ser **igual em todos os certificados** — por exemplo, `{{TREINAMENTO}}` sempre igual a "Excelência no Atendimento", sem precisar repetir esse valor em toda linha da planilha.

### Gerando certificado só para alguns participantes

Depois de carregar a planilha, clique em **"Ver Tabela Completa"** dentro do app. Cada linha tem uma caixinha de seleção — desmarque a de um participante para que ele **não** receba certificado neste lote, sem precisar apagar a linha da planilha original. Há também botões para buscar por nome e ativar/desativar vários participantes de uma vez.

---

## Como adicionar uma nova variável

1. Edite o template `.pptx` e insira a nova variável (ex: `{{CPF}}`)
2. Adicione a coluna correspondente na planilha (ex: coluna `CPF`)
3. Abra o aplicativo — a nova variável aparecerá automaticamente no painel de mapeamento
4. Selecione a coluna correspondente no dropdown

**Nenhum desenvolvedor é necessário** para adicionar novas variáveis.

---

## Testando o template antes de processar o lote

1. Prepare uma planilha de teste com 2-3 linhas de dados fictícios
2. Selecione o template e a planilha de teste no aplicativo
3. Gere os certificados de teste
4. Abra um dos arquivos gerados no PowerPoint e verifique se os dados foram inseridos corretamente

---

## Limitações conhecidas

| Situação | Comportamento |
|---|---|
| Variável dentro de shape agrupado | Pode não ser detectada em alguns casos. Desagrupe as shapes antes de salvar o template. |
| Variável com mistura de formatações | Se parte de `{{NOME}}` estiver em negrito e outra parte não, a detecção pode falhar. Selecione toda a variável e aplique a formatação de uma vez. |
| Valores com `/` no nome do participante | O arquivo é gerado substituindo `/` por `_` no nome do arquivo. |
| Células vazias na planilha | O campo correspondente no certificado ficará em branco (sem texto). |

---

## Dúvidas frequentes

**O app disse "nenhuma variável detectada" mas eu coloquei variáveis no template.**
Verifique se as variáveis estão em maiúsculo e com duplas chaves. Abra o PowerPoint, clique na caixa de texto e confirme que está escrito exatamente `{{NOME}}` (sem espaços extras).

**Alguns certificados não foram gerados e aparece ✗ no log.**
O log mostra o motivo do erro. Os demais certificados são gerados normalmente — o lote não é cancelado por erros individuais.

**Quero usar o mesmo template para treinamentos diferentes.**
Basta selecionar uma planilha diferente no aplicativo. O mapeamento variável ↔ coluna é refeito automaticamente.

**Esqueci como algum passo funciona dentro do app.**
Clique no ícone **"?"** no canto superior direito do aplicativo — ele abre um tutorial com exemplos visuais de cada etapa. A maioria dos botões e campos também mostra uma dica ao passar o mouse por cima.

---

*Documento mantido pela equipe de Treinamentos — v1.1.0*
