#include "bayes.h"
#include <stdlib.h>
#include <stdio.h>
#include <math.h>





BayesModel *bayes_create(const double *prior, size_t count)
{


	BayesModel *model = malloc(sizeof(BayesModel));
	if(model == NULL){
		return NULL;
	}
	model->count = count;
	model->probabilities = malloc(sizeof(double) * count);
	if(prior != NULL){//Если не знаем вероятности то делаем равновероятными
		for(size_t i = 0 ; i < count;i++){
			model->probabilities[i] = prior[i];
		}
	}
	else{
		for(size_t i =0;i<count;i++){
			model->probabilities[i] = 1.0/count;
		}
	}

	return model;
}


int bayes_update(BayesModel *model,const double *likelihood)
{
	double sum = 0.0;
	double check_norm = 0;
	if (model->count == 0 || likelihood<0)
		return -2;
	for (size_t i = 0; i < model->count;i++){
		sum += model->probabilities[i] * likelihood[i];
	}
	if(sum <= 0)
		return -1;
	for(size_t i = 0 ;i < model->count;i++){
		model->probabilities[i] = model->probabilities[i] * likelihood[i]/sum;
		check_norm += model->probabilities[i];
	}
	return 0;
}

int bayes_predict(const BayesModel *model,size_t *ranking){
	if(!model || !ranking || !model->probabilities || model->count == 0)
		return -1;

	for(size_t i = 0;i<model->count;i++){
		ranking[i] = i;
	}
	for(size_t i = 1;i<model->count;i++){
		size_t key = ranking[i];
		size_t j = i;

		while(j > 0 && model->probabilities[ranking[j-1]] < model->probabilities[key]){
			ranking[j] = ranking[j-1];
			j--;
		}
		ranking[j] = key;
	}
	return 0;

}

void print_topk(BayesModel *model, size_t *ranking){
	for(size_t i = 0; i< model->count;i++){
		printf("H_%lli = %.2f%%\n",i,model->probabilities[ranking[i]]*100);
	}
}

void bayes_free(BayesModel *model){
	free(model->probabilities);
	free(model);
}
void bayseci_test_failure(void) {

	int x = ;
}
