
#include <stdlib.h>
#include <stdio.h>
#include <math.h>

#include "core/oFloatVector.h"

int oFloatVector_init(oFloatVector * oFV,long size,long capacity) {
	
	if (oFV == NULL)
		return 1;
	if (size < 0)
		size = 0;
	if (capacity < size)
		capacity = size;
	if (capacity <= 0)
		capacity = 1024;
		
	oFV->capacity = 0;	
	oFV->data = NULL;
	if (oFloatVector_resize(oFV,capacity) != 0) {
		oFV->size = 0;
		return 1;
	} else {
		oFV->size = size;	
	}
	
	return 0;
}

int oFloatVector_resize(oFloatVector * oFV,long capacity) {

	
	double * buffer = realloc(oFV->data,sizeof(double)*capacity);
	if (buffer!=NULL) {
		oFV->data = buffer;
		oFV->capacity = capacity;
		return 0;
	}
	return 1;
}

int oFloatVector_append(oFloatVector * oFV,double value) {
	
	if (oFV==NULL)
		return 1;
	if (oFV->size >= oFV->capacity) {
		if (oFloatVector_resize(oFV,oFV->capacity*2)!=0) {
			return 1;
		}
	}
	if (oFV->data==NULL)
		return 1;
	oFV->data[oFV->size++] = value;

	return 0;
}

