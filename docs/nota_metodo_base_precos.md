# Nota de método: base de preços (Rodrigo, 07/11/2026)

**Objetivo:** aumentar as ocorrências utilizáveis de cada um dos 50 SKUs, com identidade conferida e método explicável. A meta é mais observações do mesmo produto, não mais SKUs.

## 1. Regras de limpeza (código: `mercado/base_precos.py`, branch `base-precos`)
- **Vínculo:** EAN exato do catálogo (50 SKUs). Resultado: 16.185 linhas.
- **Filtro:** `preco_regular > 0`. Restam 16.020, igual ao relatório do Pedro.
- **Deduplicação** pela chave produto + id_empresa + endereço + data_pesquisa, mantendo o primeiro arquivo: 281 pares removidos. Todos tinham preços idênticos, em arquivos mensais consecutivos, só em 29/02 e 30/04/2024.
- **Exclusão por produto diferente sob o mesmo EAN:** 9 linhas de Sorriso 90 g gravadas no EAN do Sorriso 70 g (2026-05).
- **Resultado: 15.730 observações únicas.**
- **Eixo do tempo:** `__mes` identifica a rodada de coleta (cada arquivo cobre 0 a 1 dia). `data_pesquisa` é a data real. 35,6% das observações têm mês da data diferente do `__mes`, porque a coleta cai na virada do mês. Trocar o eixo partiria uma rodada em dois meses.
- O arquivo 2024-05 só repete a coleta de 30/04. São **33 meses** de cobertura, não 34.

## 2. Tamanho do universo (medido, antes da exclusão do Sorriso 90 g)
Nos 12 grupos (busca pelo início da descrição, sem preço zerado e sem repetições): **52.498 linhas**.
- 15.739 (30%) são do nosso catálogo.
- 23.343 (44%) têm EAN válido, mas são outros produtos (190 códigos de outras marcas, versões e embalagens).
- 11.349 (22%) são genéricos "( + ) BARATO".
- 2.067 (4%) não têm EAN válido: códigos internos antigos.
- O argumento "13% de 112 mil" não vale: as categorias 1, 6 e 9 incluem produtos de outros grupos, e nossos grupos também aparecem nos códigos 0, 2, 3 e 5. A legenda dos códigos é **inferida**.

## 3. Candidatos a mesmo SKU sob outro código
**Critério:** mesma marca, volume e embalagem; **nenhum mês em comum** com o EAN do catálogo; preço da mesma loja estável na troca de código (set para out/2024).

| Origem | Registros | Meses | Evidência |
|---|---|---|---|
| Refrigerante 2 L (3 códigos internos aprovados: Coca, Guaraná Antártica, Pepsi; jan a set/2024) | +444 | 25 -> 33 | 0 meses em comum; mediana nas lojas comuns 0,0% |
| Cerveja 350 ml (4 códigos internos aprovados, jan a set/2024) | +569 | 17 -> 25 | 0 meses em comum; mediana nas lojas comuns 0,0% |

**Total: +1.013 candidatos aprovados (444 + 569). Observado 15.730 + candidato = 16.743.** Status: 7 aprovados pelo Pedro em 07/11; o Guaraná Cini (+155 linhas) foi rejeitado e fica só como observado. Camadas separadas (`cobertura_por_camada.csv`).

**Feijão Reserva (EAN 7896050600269): classificado como conflito e excluído.** Coexiste com o EAN do catálogo em 39 lojas e datas (38 com preço igual); não está no SI5; o Cosmos (não auditado) o descreve como "FEIJAO CARIOCA/PRETO 1KG"; o prefixo do código difere do fabricante. Informação insuficiente para somar.

## 4. Precisão da referência (`dados/precisao_por_sku.csv`)
- Para cada SKU: mediana por loja na janela, IC95% por bootstrap (semente fixa por SKU) e largura relativa.
- Coca 2 L (ago a out/2026): mediana R$ 11,64, IC 11,48 a 11,99, 28 lojas, 15 redes.
- Regra proposta (limiar de 10% é escolha, não validada): janela de 3 meses se IC <= 10%; senão 6 meses; senão selo "baixa precisão". Resultado: 23 SKUs com 3 meses, 18 com 6 meses, 9 com baixa precisão.
- O IC mede lojas distintas e dispersão real de preço; mais linhas antigas não o melhoram.

## 5. Erro fora da amostra (`dados/mae_por_sku.csv`)
- Para cada mês, a mediana dos 3 meses anteriores (ou só o mês anterior) prevendo a mediana do mês.
- Erro médio: 5,6% do preço com janela de 3 meses; 5,1% com o último mês (melhor em 29 de 50 SKUs).
- Leitura: a janela serve para estabilizar a referência, não para prever. Mostrar data e janela na tela.

## 6. Testes e decisões
- **Preço zerado:** 196 linhas (165 no catálogo, 31 nos candidatos) sem preço regular, todas com promoção ou fidelidade. Não entram na série regular; no máximo, camada separada.
- **Outros 190 EANs:** produtos diferentes. Com normalização melhor, só o Feijão Reserva tinha descrição igual a um SKU. Não somam à série; servem só de contexto de grupo.
- **RapidFuzz e TF-IDF não foram executados neste recorte.** O que restava de "mesmo produto sob outro código" foi resolvido por regra determinística e auditável. Não há comparação medida entre métodos.
- **Teto realista:** cerca de 17 mil observações do mesmo produto. O limite é a coleta da fonte (rodízio de lojas).

## 7. Limites e pendências
- Evidência dos candidatos: 7 a 11 lojas comuns por marca, em um único par de meses. Quedas individuais de até 26% não investigadas.
- Sucessão de período e preço estável não provam identidade; confirmação definitiva seria externa.
- Cerveja: última observação em 2026-02 (referência antiga). "LATA" na descrição dos códigos internos é hipótese.
- IC por bootstrap trata lojas como independentes (otimista). Mix de lojas e atacado x varejo não testados. Mediana por rede e janela de 6 meses não testadas no erro fora da amostra.
- O script lê o catálogo dos 37 de `dados/ncm_rastreabilidade_37.csv` (PR #6, já mesclado na `main`).
- Decisão do Pedro (07/11): 7 candidatos aprovados (Coca, Guaraná Antártica, Pepsi, Skol, Antártica, Kaiser, Brahma); Guaraná Cini rejeitado (queda de preço sem alta, padrão de produto diferente ou reembalagem). Os 7 seguem em camada separada do observado.

## 8. Teste com coletas diárias de outubro (Pedro, 07/11) - NÃO integrado
- Entrega: 7.546 linhas, 18 datas (02 a 29/10/2026), 46 dos 50 SKUs. Validação: todas com preço positivo, todas de códigos do catálogo, 0 duplicatas internas, 0 sobreposição com a base mensal (que tem só 01/10).
- **Linhas do catálogo:** observado 15.730 -> 23.276 (+7.546). Candidatos aprovados: 1.013 (sem mudança: são de 2024 e as 4 cervejas não receberam dados novos). Total com candidatos: 16.743 -> 24.289.
- **Universo dos 12 grupos:** era 52.498 na base mensal. Sobe no mínimo para 60.044 (+7.546). O valor real é maior e não foi medido, porque o arquivo diário traz só os 50 SKUs. Logo, a proporção 23.276 / 60.044 = 39% é um piso do denominador; o percentual verdadeiro é menor que 39%.
- Lojas: 60 na janela de 6 meses da base mensal; 73 no adicional; 53 em comum; 20 novas; 80 somando.
- Método do teste: uma linha por loja no mês (mediana das coletas), mês do adicional derivado da data real, IC95% por bootstrap com semente fixa.
- Resultado: SKUs com IC de 6 meses > 10%: 9 -> 6 (4 resolvidos, 1 piorou: Café 3 Corações). 44 de 50 com referência confiável. Lojas por SKU na janela de 6 meses: 40 -> 55 em média.
- Regra completa recalculada: 43 SKUs com 3 meses, 1 com 6 meses, 6 com baixa precisão.
- Ressalvas: a janela de 3 meses fica concentrada em outubro (18 coletas contra 1 dos outros meses), então é uma referência de outubro; mais lojas e preço mais recente não foram separados; as 4 cervejas não receberam dados novos; o mês vir da data real é adaptação de teste, a validar com o Edu; o IC trata lojas como independentes (otimista); limiar de 10% é escolha do grupo. O ganho que importa é em lojas distintas, não em linhas.
- Os 6 fracos: Arroz Tio João, Arroz Parboilizado Urbano, Café 3 Corações (perto do limiar); Macarrão Orquídea pena e as duas águas (dispersão real de preço).
