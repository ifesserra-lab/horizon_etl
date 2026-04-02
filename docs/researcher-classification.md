# Classificacao de Pesquisadores

Este documento explica a regra usada para preencher o campo `classification` no arquivo `data/exports/researchers_canonical.json`.

O export inclui tanto os registros base da tabela `researchers` quanto pessoas que aparecem como participantes em projetos, orientacoes e grupos de pesquisa, mesmo quando nao possuem linha propria em `researchers`.

A logica esta implementada em `src/core/logic/canonical_exporter.py`, no metodo `_build_classification_payload`.

## Campos relevantes no JSON

Cada pesquisador pode trazer os seguintes campos derivados:

- `classification`
- `classification_confidence`
- `classification_note`
- `role_evidence`
- `was_student`
- `was_staff`

Dentro de `role_evidence`, as evidencias usadas sao:

- `project_roles`
- `research_group_roles`
- `advisorship_roles`
- `has_institutional_email`
- `academic_reference_count`

## Regra de classificacao

### 1. `student`

Um pesquisador e classificado como `student` quando existe evidencia de aluno e nao existe evidencia forte de staff.

Papeis aceitos como aluno:

- `Student`
- `Estudante`
- `Estudante (Egresso)`

Casos que viram `student`:

- ha papel de aluno em projeto, grupo ou orientacao, sem papeis de staff
- ha papel de aluno com sinal forte em grupo ou orientacao, mesmo que apareca `Researcher` em projeto

Quando isso acontece, pode aparecer a nota:

- `student_signal_overrides_project_staff_role`

### 2. `researcher`

Um pesquisador e classificado como `researcher` quando existe evidencia forte de staff.

Sinais fortes de staff:

- papel de staff em grupo de pesquisa
- papel `Supervisor` em orientacao
- papel `Coordinator` ou `Researcher` em projeto junto com `has_institutional_email = true`

Papeis aceitos como staff:

- `Supervisor`
- `Coordinator`
- `Researcher`
- `Pesquisador`
- `Pesquisador (Egresso)`
- `Leader`
- `Lider`

### 3. `outside_ifes`

Um pesquisador e classificado como `outside_ifes` quando:

- aparece como `Coordinator` ou `Researcher` em projeto
- nao aparece em grupo de pesquisa
- nao aparece em orientacao
- nao tem e-mail institucional
- nao tem evidencia de aluno

Quando isso acontece, a nota e:

- `project_only_staff_without_institutional_signals`

### 4. `null`

O campo fica `null` quando nao ha evidencia suficiente para classificar a pessoa como `student`, `researcher` ou `outside_ifes`.

Um caso comum e:

- a pessoa so aparece como referencia academica em formacao, sem projeto, sem grupo, sem orientacao e sem e-mail institucional

Quando isso acontece, pode aparecer a nota:

- `academic_advisor_reference_only`

## Regra de precedencia

- `researcher` vence `student`
- `student` pode vencer um sinal fraco de staff em projeto se houver sinal forte de aluno em grupo ou orientacao
- `outside_ifes` so aparece quando a pessoa tem papel de staff apenas em projeto e sem sinais institucionais

## Distribuicao atual

Distribuicao observada no export atual:

- `student`: 4801
- `researcher`: 2362
- `outside_ifes`: 242
- `null`: 33

## Exemplos reais

### Exemplo `student`

```json
{
  "id": 500,
  "name": "Bernardo Ferri Schirmer",
  "classification": "student",
  "classification_confidence": "medium",
  "classification_note": "student_signal_overrides_project_staff_role",
  "was_student": true,
  "was_staff": false,
  "role_evidence": {
    "project_roles": ["Researcher", "Student"],
    "research_group_roles": [],
    "advisorship_roles": ["Student"],
    "has_institutional_email": false,
    "academic_reference_count": 0
  }
}
```

Leitura:

- ha evidencia de aluno em orientacao
- existe `Researcher` em projeto, mas sem sinal forte de staff
- por isso a classificacao final continua `student`

### Exemplo `researcher`

```json
{
  "id": 1,
  "name": "Carlos Roberto Pires Campos",
  "classification": "researcher",
  "classification_confidence": "high",
  "classification_note": null,
  "was_student": false,
  "was_staff": true,
  "role_evidence": {
    "project_roles": [],
    "research_group_roles": ["Leader", "Pesquisador (Egresso)"],
    "advisorship_roles": [],
    "has_institutional_email": true,
    "academic_reference_count": 0
  }
}
```

Leitura:

- ha papel forte de staff em grupo de pesquisa
- isso basta para classificar como `researcher`

### Exemplo `outside_ifes`

```json
{
  "id": 483,
  "name": "Kelly Assis De Souza",
  "classification": "outside_ifes",
  "classification_confidence": "medium",
  "classification_note": "project_only_staff_without_institutional_signals",
  "was_student": false,
  "was_staff": false,
  "role_evidence": {
    "project_roles": ["Researcher"],
    "research_group_roles": [],
    "advisorship_roles": [],
    "has_institutional_email": false,
    "academic_reference_count": 0
  }
}
```

Leitura:

- ha papel de staff apenas em projeto
- nao ha grupo, orientacao ou e-mail institucional
- por isso a classificacao final e `outside_ifes`

### Exemplo `null`

```json
{
  "id": 967,
  "name": "Monalessa Perini Barcellos",
  "classification": null,
  "classification_confidence": "low",
  "classification_note": "academic_advisor_reference_only",
  "was_student": false,
  "was_staff": false,
  "role_evidence": {
    "project_roles": [],
    "research_group_roles": [],
    "advisorship_roles": [],
    "has_institutional_email": false,
    "academic_reference_count": 1
  }
}
```

Leitura:

- nao ha evidencia de aluno ou staff
- existe apenas referencia academica
- por isso o campo `classification` fica `null`
