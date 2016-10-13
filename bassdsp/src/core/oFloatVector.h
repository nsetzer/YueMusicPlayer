
#ifndef OFLOATVECTOR_H
#define OFLOATVECTOR_H

typedef struct oFloatVector_t {
	long capacity;
	long size;
	double *data;
} oFloatVector;

int oFloatVector_init(oFloatVector * oFV,long size,long capacity); 
int oFloatVector_resize(oFloatVector * oFV,long capacity);
int oFloatVector_append(oFloatVector * oFV,double value);

#endif