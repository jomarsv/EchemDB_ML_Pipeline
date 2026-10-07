# Avaliacao congelada da particao balanceada

Os modelos foram treinados e selecionados somente no desenvolvimento da
particao balanceada por fonte. As 22 curvas do teste externo permaneceram
separadas e foram usadas apenas uma vez para a avaliacao final desta etapa.

Os resultados continuam sendo candidatos: a particao ainda depende da
revisao final das referencias e da redigitalizacao da curva anomala de
Nishihara.

Resultado observado no teste externo (22 curvas; Ag=4, Au=8, Pt=10):

| pacote congelado | acuracia | acuracia balanceada | macro-F1 |
|---|---:|---:|---:|
| fold 1: ensemble completo | 90,9% | 83,3% | 85,2% |
| fold 2: k-NN | 86,4% | 80,0% | 80,3% |
| fold 3: ensemble top-3 | 81,8% | 71,7% | 70,7% |

As métricas por classe estão em `selected_class_metrics.csv` e as predições
individuais em `selected_predictions.csv`. A variação entre os três pacotes
mostra que a seleção ainda é sensível à composição das fontes; por isso não
deve ser apresentada como uma única acurácia definitiva.
