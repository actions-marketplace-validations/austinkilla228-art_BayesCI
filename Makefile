
all:
	gcc -shared -O2 -I include/ -o bayes_engine.dll src/bayes.c
