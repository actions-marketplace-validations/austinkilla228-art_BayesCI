#include <stdio.h>
#include "bayes.h"



int main(void){
	double prior[] = {0.2,0.5,0.3};
	double likelihoods[] = {0.1,0.8,0.4};
	size_t count = 3;
	size_t ranking[3];
	BayesModel *model = bayes_create(prior,count);
	printf("%.2f\n",model->probabilities[2]);

	bayes_update(model,likelihoods);
	size_t result = bayes_predict(model,ranking);

	print_topk(model,ranking);
	return 0;
}
