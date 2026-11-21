# Exemplos do MVP com inputs mínimos

Perfis, custo de R$ 7 e preço praticado de R$ 12 são fictícios. A referência de mercado é observada: Coca-Cola 2 L, sete redes, 01/10/2026. Tributação estimada e margem usam as premissas configuradas; não representam uma empresa real.

| Regime | Caminho | Preço avaliado | Margem de contribuição | Price index |
|---|---|---:|---:|---:|
| simples_nacional | Preço praticado | R$ 12.00 | R$ 3.22 (26.85%) | 100.08 |
| simples_nacional | Cenário pela referência | R$ 11.99 | R$ 3.21 (26.80%) | 100.00 |
| lucro_presumido | Preço praticado | R$ 12.00 | R$ 1.38 (11.51%) | 100.08 |
| lucro_presumido | Cenário pela referência | R$ 11.99 | R$ 1.37 (11.45%) | 100.00 |
| lucro_real | Preço praticado | R$ 12.00 | R$ 1.18 (9.83%) | 100.08 |
| lucro_real | Cenário pela referência | R$ 11.99 | R$ 1.17 (9.78%) | 100.00 |

Faixa inicial observada para teste: R$ 11,99 a R$ 12,96 em centavos. Pontos iguais foram eliminados. Não é preço ótimo nem recomendação validada.

Execução offline: o endereço RTC foi intencionalmente configurado como indisponível. Os resultados preservam esse estado; não há chamada fiscal real bem-sucedida nova nessa execução. Os 50 testes reais do motor atualizado estão preservados nas evidências anteriores.

Validação atual: 77 testes aprovados, pylint 10/10, mypy sem erros em 20 arquivos. A suíte inclui os 50 SKUs nos três perfis, com o RTC simulado como indisponível.
