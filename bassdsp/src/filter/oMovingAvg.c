#include <stdlib.h>
#include <stdio.h>
#include <math.h>

#include "filter/oMovingAvg.h"

#define oma_INT_MAX 100
/*
	File: oMovingAvg.c
	Description:
		This file defines an object that can efficiently calculate 
		a moving avg of a series of values.
		Allocate memory for the structure and then call the init function
		Define how long of a moving average you want to calculate.
		
		the helper method insert is used to add a value to the moving average
		filter. Insert replaces the oldest value in memory and updates the
		running total.
		
		Use the get function to return the average value.
		
		Two functions insertRMS and getRMS are provided for convenience.
		RMS power, or Root Mean Square power is the average power of
		a signal after taking the average of the sum of the square of each input
		and finally taking the square root.
		RMS power gives you the average magnitude if the values can exist below zero

*/
int oMovingAvg_init( oMovingAvg * avgstore , ULONG length) { 
	int i;
	avgstore -> data = (double *) malloc( sizeof(double) * length );
	if (avgstore -> data == NULL) 
		return 1;
	
	avgstore -> length = length;
	avgstore -> count = 0;
	avgstore -> total = 0;
	avgstore -> index = 0;
	
	avgstore -> min_value = oma_INT_MAX;
	avgstore -> max_value = -oma_INT_MAX;

	for (i=0; i < length; i ++ ) {
		avgstore -> data[i] = 0;
	}
	return 0;
}

void oMovingAvg_free( oMovingAvg * avgstore) { 
	if (avgstore != NULL) {
		free( avgstore->data );
	}
}

void oMovingAvg_insert( oMovingAvg * avgstore, double value) {
	if (avgstore==NULL)
		return;

	avgstore->total -= avgstore->data[avgstore->index];
	avgstore->total += value;
	
	avgstore->data[avgstore->index] = value;
	
	avgstore->index = ( avgstore->index+1 ) % avgstore->length;
	
	if (avgstore->count < avgstore->length) {
		avgstore->count++;
	}
	avgstore->max_value = (value>avgstore->max_value)?value:avgstore->max_value;
	
	avgstore->insert_total += value;
	avgstore->insert_count++;

}
void oMovingAvg_insertRMS( oMovingAvg * avgstore, double value) {
	// insert the value squared
	oMovingAvg_insert(avgstore, value*value );
	
}
double oMovingAvg_get( oMovingAvg * avgstore ) {
	// return the simple average
	return avgstore->total / (double) avgstore->count;
}

double oMovingAvg_getRMS( oMovingAvg * avgstore ) {
	// return the square root of the average
	// assumes insertRMS was used to place values in the table
	double v = sqrt( avgstore->total / (double) (avgstore->count) );
	if (v!=v) // if inner value is -0 or smaller, such that sqrt(v)==nan
		return 0;
	return v;
}

double oMovingAvg_getTotal( oMovingAvg * avgstore ) {
	// return the simple average
	return avgstore->insert_total / (double) avgstore->insert_count;
}

double oMovingAvg_getRMSTotal( oMovingAvg * avgstore ) {
	// return the square root of the average
	// assumes insertRMS was used to place values in the table
	return sqrt( avgstore->insert_total / (double) (avgstore->insert_count) );
}

void oMovingAvg_reset( oMovingAvg * avgstore  ) { 
	int i;
	avgstore -> count = 0;
	avgstore -> total = 0;
	avgstore -> index = 0;
	
	avgstore->insert_total=0;
	avgstore->insert_count=0;
	
	avgstore -> min_value =  oma_INT_MAX;
	avgstore -> max_value = -oma_INT_MAX;
	
	
	for (i=0; i < avgstore->length; i ++ ) {
		avgstore -> data[i] = 0;
	}
}
