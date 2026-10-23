CC = gcc
CFLAGS = -O2 -fPIC -Iinclude

ifeq ($(OS),Windows_NT)
    TARGET = bayes_engine.dll
else
    TARGET = libbayesci.so
endif

all:
	$(CC) -shared $(CFLAGS) -o $(TARGET) src/bayes.c -lm
