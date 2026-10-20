#ifndef BAYES_H
#define BAYES_H

#include <stddef.h>


typedef struct {
	size_t count;
	double *probabilities;
}BayesModel;

BayesModel *bayes_create(
		const double *prior,
		size_t count
);

int bayes_update(
		BayesModel *model,
		const double *likelihood
);

int bayes_predict(
		const BayesModel *model,
		size_t *ranking
);

void bayes_free(
		BayesModel *model
);

void print_topk(BayesModel *model,size_t *ranking);

#endif
