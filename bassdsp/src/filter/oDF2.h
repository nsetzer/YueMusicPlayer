#ifndef oDF2_H
#define oDF2_H

typedef struct DF2Node_t {
	/*
		delay nodes maintain 2 values, for stereo audio
		only one delay line is then required.
	*/
	struct DF2Node_t * prev;
	struct DF2Node_t * next;
	double value;
	double value2;
} DF2Node;

typedef struct DelayLine_t {
	struct DF2Node_t * root;
	struct DF2Node_t * last;
	long N;
} DelayLine;

typedef struct oDF2_t {
	double * B;	// zeros
	double * A;	// poles A[0] is always 1
	DelayLine * delayline;
	long N;
} oDF2;

typedef struct oDF1_t {
	double * B;	// zeros
	double * A;	// poles
	DelayLine * delaylineB;
	DelayLine * delaylineA;
	long NB;
	long NA;
} oDF1;

typedef struct oTDF2_t {
	double * B;	// zeros
	double * A;	// poles A[0] is always 1
	double * Z; // delay blocks as an array
	long N;
} oTDF2;

typedef struct oTDF1_t {
	double * B;	// zeros
	double * A;	// poles
	double * ZB; // delay blocks
	double * ZA;
	long NB;
	long NA;
} oTDF1;

typedef struct oTDF1_3_t {
	// extreme special case. no insert function
	// mean for exactly 3 coeffcients
	/* for an input value x, output y is :
	
		v = filter->ZA1 + r;
		y = v*filter->B[0] + filter->ZB1;
		
		filter->ZA1 = v*filter->A[1] + filter->ZA2;
		filter->ZA2 = v*filter->A[2];

		filter->ZB1 = v*filter->B[1] + filter->ZB2;
		filter->ZB2 = v*filter->B[2];
		
	*/
	double B[3];	// zeros
	double A[3];	// poles
	double ZB1; // only need 4 delays 
	double ZA1; 
	double ZB2; 
	double ZA2;
} oTDF1_3;


oDF2 * newDirectForm2(double *B, double *A, long N);
void DelayLine_init(DelayLine * delayline, long N);
void DelayLine_free(DelayLine * delayline);
void DelayLine_insert(DelayLine * delayline, double value);
void DelayLine_insertStereo(DelayLine * delayline, double L,double R);

int oDF2_init(oDF2 * filter,double * A, double * B,long N);

double oDF2_FIR(oDF2 * filter,double value);
void   oDF2_FIR2(double * r1,double * r2, oDF2 * filter,double value,double value2);
double oDF2_IIR(oDF2 * filter,double value);
void   oDF2_IIR2(double * r1,double * r2, oDF2 * filter,double value,double value2);

void oDF2_flush(oDF2 * filter);
void oDF2_free(oDF2 * filter);

//todo rename TDF1_3 to TDF
// && create a generalized TDF_BIQUAD which
// holds a chain of TDF_3
oTDF1_3 * newTDF1_3(double * A,double * B);
void oTDF1_3_init(oTDF1_3 * filter,double * A, double * B);
void oTDF1_3_flush(oTDF1_3 * filter);
void oTDF1_3_free(oTDF1_3 * filter);
// insert a value using transposed direct form 1 method
double oTDF1_3_IIR(oTDF1_3 * filter,double v);
// insert a value using transposed direct form 2 method.
double oTDF2_3_IIR(oTDF1_3 * filter,double v);

#endif
