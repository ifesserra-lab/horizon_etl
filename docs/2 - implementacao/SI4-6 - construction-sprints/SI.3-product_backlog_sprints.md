# Product Backlog – ConectaFapes
**Última atualização:** <DD/MM/AAAA>  
**Responsável (PO):** <Nome>  
**Versão do Documento:** 1.0  

---

# 1. Visão Geral

Este Product Backlog reúne todas as **User Stories (US)** priorizadas para o ConectaFapes, servindo como base para:

- Planejamento de Releases (PM1.3)  
- Planejamento de Sprints  
- Geração de Tasks no Sprint Backlog  
- Rastreabilidade ISO 29110 (SI.1 → SI.3)  
- Automação de criação de cards no GitHub Projects  

Cada US deve conter **título, prioridade, critérios de aceitação, notas técnicas, origem SI.1–SI.3, e os metadados necessários para futura decomposição**.

---

# 2. Convenções

| Campo | Descrição |
|-------|-----------|
| `ID` | Identificador único (US-001) |
| `Título` | Nome curto da funcionalidade |
| `Milestone` | Release (R1, R2, etc.) |
| `Prioridade` | Alta / Média / Baixa |
| `Tamanho` | Pontos (estimativa inicial) |
| `Origem` | SI.1 (Requisitos) / SI.2 (Processos) / SI.3 (Design) |
| `Descrição` | Contexto e objetivo da US |
| `Critérios de Aceitação` | Lista testável |
| `Dependencies` | Dependências técnicas ou funcionais |
| `Notas Técnicas` | Restrições, ADRs, módulos afetados |
| `Tags` | tipo:us, area:backend, area:frontend etc. |

> Os metadados são escritos em **bloco YAML**, fácil de detectar por scripts.

---

# 3. User Stories

Abaixo está o template oficial para cada US.

---

## US-001 – <Título da User Story>

```yaml
id: US-001
milestone: R1
prioridade: Alta
tamanho: 5
origem:
  - SI1_requisitos
  - SI2_processos
  - SI3_design
tags:
  - type:us
  - area:frontend
  - area:backend
dependencias:
  - US-000 (opcional)
modulos_afetados:
  - autenticação
  - perfis
```

### Descrição  
<Explique o problema, o objetivo e o valor gerado para o usuário.>

### Critérios de Aceitação (BDD/Gherkin)

```
Dado que <situação inicial>
Quando <ação do usuário>
Então <resultado esperado>
```

- [ ] Critério 1  
- [ ] Critério 2  
- [ ] Critério 3  

### Notas Técnicas  
- <Regra de negócio importante>  
- <Possível impacto em integrações>  
- <Referência ADR se existir>  

---

## US-002 – <Título da US>

```yaml
id: US-002
milestone: R1
prioridade: Média
tamanho: 3
origem:
  - SI1_requisitos
tags:
  - type:us
  - area:frontend
dependencias: []
modulos_afetados:
  - dashboard
```

### Descrição  
<Descrição da funcionalidade.>

### Critérios de Aceitação  
- [ ] Critério 1  
- [ ] Critério 2  

### Notas Técnicas  
- Este módulo depende de autorização centralizada.  
- Deve seguir o padrão visual definido no design system.  

---

## US-003 – <Título>

```yaml
id: US-003
milestone: R2
prioridade: Baixa
tamanho: 8
origem:
  - SI1_requisitos
  - SI2_processos
tags:
  - type:us
  - area:backend
dependencias:
  - US-001
modulos_afetados:
  - workflow
```

### Descrição  
<Descrição da funcionalidade.>

### Critérios de Aceitação  
- [ ] Critério 1  
- [ ] Critério 2  
- [ ] Critério 3  

### Notas Técnicas  
- Impacta o fluxo BPMN.  

---

# 4. Backlog Refinado por Prioridade

| ID | Título | Milestone | Tamanho | Prioridade | Status |
|----|--------|-----------|---------|-------------|--------|
| US-001 | <Título> | R1 | 5 | Alta | Pendente |
| US-002 | <Título> | R1 | 3 | Média | Pendente |
| US-003 | <Título> | R2 | 8 | Baixa | Pendente |

---

# 5. Preparação para Sprint Planning

Cada US deve estar **pronta para entrar na Sprint** se:

## DoR – Definition of Ready
- [ ] US tem descrição clara  
- [ ] Critérios de aceitação testáveis  
- [ ] Impactos e dependências conhecidos  
- [ ] Tamanho estimado  
- [ ] Tags definidas  
- [ ] Impactos SI.1 → SI.3 identificados  

> Se um script estiver processando este arquivo, ele pode checar automaticamente o DoR para liberar a US para planejamento da sprint.

---

# 6. Como migrar do Product Backlog → Sprint Backlog

### A conversão é direta:

Cada US possui metadados em YAML como:

```yaml
id: US-001
milestone: R1
prioridade: Alta
tamanho: 5
tags: [type:us, area:backend]
```

E no Sprint Backlog vira:

```
## US-001 – <Título>
### Subtasks da Sprint
- [ ] DEV-001 – <Descrição> (Resp: @devX, Tipo: dev, US: US-001...)
- [ ] TEST-001 – <Descrição> (...)
- [ ] DOC-001 – <Descrição> (...)
```

O **parser** pode:

1. Ler cada bloco YAML  
2. Criar uma Issue / Card para a US  
3. Criar labels, milestone e assignee padrão  
4. Permitir ao facilitador quebrar em tasks durante a Planning  
5. Popular automaticamente o Sprint Backlog

---

# 7. Benefícios desse modelo

### ✔ 100% compatível com automação (GitHub Projects/API)
- YAML facilita parsing  
- IDs previsíveis (US-XXX)  
- Tags e Milestones prontos para card creation  

### ✔ Coerente com Sprint Backlog
- Campos idênticos: US, Tipo, Dependências  
- Já carrega tudo que as tasks devem “herdar”

### ✔ Aderente à ISO 29110
- SI.1 alimenta requisitos  
- SI.2 alimenta regras de processo  
- SI.3 alimenta notas técnicas  
- PM1.2 e PM1.3 são respeitados via prioridade/milestone

### ✔ Fácil de editar manualmente
- Markdown simples  
- Estrutura clara  
- Repetível para qualquer projeto


