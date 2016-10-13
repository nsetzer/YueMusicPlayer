
#ifndef oMovingAvg_H
#define oMovingAvg_H

#include "common.h"

typedef struct oMovingAvg_t {
	// the numbers inside of data are RMS power-squared.
	// RMS power is sqrt(x^2). therefore the value is just x^2.
	// set length to how much memory you want
	// 		a length of 441 is 100ms of memory. at 44.1KHz Fs.
	// the true average is sqrt(total) / count;
	// index starts at zero.
	//	increment with index = (index+1)%length
	double * data;	// an array of elements of size L
	double  total;	// sum of all elements in data
	ULONG   count;   // number of items in data
	ULONG  length;	// length of data
	ULONG   index;   // next index to place data
	double  insert_total;	// sum of all elements inserted since last reset
	double  insert_count;	// count of all elements inserted since last reset
	double max_value;
	double min_value;

} oMovingAvg;

int oMovingAvg_init( oMovingAvg * avgstore , ULONG length);
void oMovingAvg_free( oMovingAvg * avgstore);
void oMovingAvg_insert( oMovingAvg * avgstore, double value);
void oMovingAvg_insertRMS( oMovingAvg * avgstore, double value);
double oMovingAvg_get( oMovingAvg * avgstore );
double oMovingAvg_getRMS( oMovingAvg * avgstore );
double oMovingAvg_getTotal( oMovingAvg * avgstore );
double oMovingAvg_getRMSTotal( oMovingAvg * avgstore );
void oMovingAvg_reset( oMovingAvg * avgstore  );
#endif