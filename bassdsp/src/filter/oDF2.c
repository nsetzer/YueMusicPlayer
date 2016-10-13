
#include <stdlib.h>
#include <stdio.h>
#include <math.h>

#include "oDF2.h"

void DelayLine_init(DelayLine * delayline, long N) {

	DF2Node * last;
	DF2Node * temp;
	long i=1;
	
	delayline->N = N;
	
	delayline->root = (DF2Node*) malloc(sizeof(DF2Node));
	delayline->root->prev = NULL;
	delayline->root->value = 0;
	delayline->root->value2 = 0;
	
	last = delayline->root;
	// build the linked list of nodes
	while (i < N) {
		temp = (DF2Node*) malloc(sizeof(DF2Node));
		
		temp->value = 0;
		temp->value2 = 0;
		
		temp->prev = last;
		last->next = temp;
		
		last = temp;
		
		i++;
		
	}
	
	delayline->last = last;
	delayline->last->next = NULL;

}
void DelayLine_insert(DelayLine * delayline, double value){
	// swap the last node to the front
	// insert the new value into the node which
	// will now occupy the front
	DF2Node * temp;
	
	delayline->last->value = value;
	
	temp = delayline->last;

	delayline->last = temp->prev;
	temp->prev = NULL;
	
	delayline->last->next = NULL;
	
	temp->next = delayline->root;
	delayline->root->prev = temp;
	
	delayline->root = temp;
	
}
void DelayLine_insertStereo(DelayLine * delayline, double L,double R){

	delayline->last->value2 = R;
	DelayLine_insert(delayline,L);
	
}
void DelayLine_free(DelayLine * delayline) {

	DF2Node * temp;
	DF2Node * temp2;
	
	temp=delayline->root;
	
	while (temp!=NULL) {
		temp2 = temp;
		temp = temp->next;
		
		free(temp2);
	}
	
	free(delayline);
	
}


oDF2 * newDirectForm2(double *B, double *A, long N) {
	oDF2 * df = malloc(sizeof(oDF2));
	if (!df) 
		return NULL;
	if (oDF2_init(df,A,B,N)!=0) {
		free(df);
	}
	return df;
	
}
int oDF2_init(oDF2 * filter,double * A, double * B,long N) {
	// if using FIR, A can be NULL
	// otherwise A[0] must always be 1
	// and len(A) == len(B) == N
	// copies of both A and B are made.
	int i;
	filter->delayline = (DelayLine *) malloc(sizeof(DelayLine));
	
	DelayLine_init(filter->delayline,N);
	
	filter->A = (double *) malloc(N*sizeof(double));
	filter->B = (double *) malloc(N*sizeof(double));
	
	
	
	for (i=0;i<N;i++) {
		//in director form 2 the multiplicative constant
		// for feedback is negative the pole value
		filter->B[i] =  B[i];
		if (A != NULL)
			filter->A[i] = -A[i];
	}
	// TODO: instead of setting A0 to 1 figure 
	//       out the scale factor and apply it
	if (A != NULL)
		filter->A[0] = 1;
	else
		filter->A = NULL;
	return 0;
}	
double oDF2_FIR(oDF2 * filter,double value){
	//implement an FIR filter that enters a single value into
	//the delay line, and returns the most recent result.
	double _b=0;
	long i = 1;
	DF2Node * temp;
	// _b stores the result of the delayed values
	// multiplied with there coefficients.
	for (temp=filter->delayline->root;temp!=NULL;temp=temp->next,i++) {
		_b += filter->B[i] * temp->value;
	}

	DelayLine_insert(filter->delayline,value);
	
	return value * filter->B[0] + _b;
}
void oDF2_FIR2(double * r1,double * r2, oDF2 * filter,double value,double value2){
	// like oDF2_FIR, however allows to enter 2 values into the delay line
	// becuase C cannot return 2 value, two double containers must be passed in
	// their values will be over-written with the result 
	double _b=0;
	double _b2=0;
	long i = 1;
	DF2Node * temp;
	
	for (temp=filter->delayline->root;temp!=NULL;temp=temp->next,i++) {
		_b += filter->B[i] * temp->value;
		_b2 += filter->B[i] * temp->value2;
	}

	DelayLine_insertStereo(filter->delayline,value,value2);
	
	// todo return 2 doubles
	(*r1) = value * filter->B[0] + _b;
	(*r2) = value2 * filter->B[0] + _b2;
}
double oDF2_IIR(oDF2 * filter,double value){
	// implement an IIR filter with a delay line
	// apply the feedback and then insert the new value into the 
	// delay line. The output is then returned
	double _a=0,_b=0;
	double new_value; // new value to insert
	long i = 1;
	DF2Node * temp;
	
	for (temp=filter->delayline->root;temp!=NULL;temp=temp->next,i++) {
		_a += filter->A[i] * temp->value;
		_b += filter->B[i] * temp->value;
	}
	//printf("%f %f %f \r\n",_a,value);
	new_value = _a + value;
	
	DelayLine_insert(filter->delayline,new_value);
	
	return new_value * filter->B[0] + _b;
}
void oDF2_IIR2(double * r1,double * r2, oDF2 * filter,double value,double value2){
	// see oDF2_FIR2 and oDF2_IIR
	double _a=0,_b=0;
	double _a2=0,_b2=0;
	double new_value; // new value to insert
	double new_value2; // new value to insert
	long i = 1;
	DF2Node * temp;
	
	for (temp=filter->delayline->root;temp!=NULL;temp=temp->next,i++) {
		_a  += filter->A[i] * temp->value;
		_a2 += filter->A[i] * temp->value2;
		_b  += filter->B[i] * temp->value;
		_b2 += filter->B[i] * temp->value2;
	}
	
	new_value = _a + value;
	new_value2 = _a + value;
	
	DelayLine_insertStereo(filter->delayline,new_value,new_value2);
	
	(*r1) = new_value * filter->B[0] + _b;
	(*r2) = new_value2 * filter->B[0] + _b2;
}
void oDF2_flush(oDF2 * filter) {
	// flush the delay line
	// set all values to zero.
	DF2Node * temp;
	for (temp=filter->delayline->root;temp!=NULL;temp=temp->next) {
		temp->value = 0;
		temp->value2 = 0;
	}
}
void oDF2_free(oDF2 * filter) {

	if (!filter)
		return;
	DelayLine_free(filter->delayline);
	
	if (filter->A != NULL)
		free(filter->A);
	free(filter->B);
}

oTDF1_3 * newTDF1_3(double * A,double * B) {
	oTDF1_3 * filter = malloc(sizeof(oTDF1_3));
	if (!filter)
		return NULL;
	oTDF1_3_init( filter, A, B);
	return filter;
}

void oTDF1_3_init(oTDF1_3 * filter,double * A, double * B){

	int i;
	//A[0] should always equal 1.0
	//https://ccrma.stanford.edu/~jos/fp/Transposed_Direct_Forms.html
	// negate A because that link says so.
	for (i=0;i<3;i++) {
		filter->B[i] =  B[i];
		if (A != NULL)
			filter->A[i] = -A[i];
	}
	if (A != NULL)
		filter->A[0] = 1;

}
void oTDF1_3_flush(oTDF1_3 * filter) {
	filter->ZB1 = 0;
	filter->ZB2 = 0;
	filter->ZA1 = 0;
	filter->ZA2 = 0;
}
void oTDF1_3_free(oTDF1_3 * filter) {
	if (filter->A != NULL)
		free(filter->A);
	free(filter->B);
	free(filter);
}
double oTDF1_3_IIR(oTDF1_3 * filter,double v) {
	double y1,v1;
	v1 = filter->ZA1 + v;
	y1 = v1*filter->B[0] + filter->ZB1;
	
	filter->ZA1 = v1*filter->A[1] + filter->ZA2;
	filter->ZA2 = v1*filter->A[2];
	
	filter->ZB1 = v1*filter->B[1] + filter->ZB2;
	filter->ZB2 = v1*filter->B[2];		
	return y1;
}

double oTDF2_3_IIR(oTDF1_3 * filter,double v) {
	double y1;

	y1 = v*filter->B[0] + filter->ZB1;
	// TDF2 only needs one set of state registers.
	filter->ZB1 = y1*filter->A[1] + v*filter->B[1] + filter->ZB2;
	filter->ZB2 = y1*filter->A[2] + v*filter->B[2];

	return y1;
}