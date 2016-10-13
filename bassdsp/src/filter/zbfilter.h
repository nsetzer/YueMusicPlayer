
#ifndef DSP_ZBFILTER_H
#define DSP_ZBFILTER_H

#include "oDF2.h"
#include "oMovingAvg.h"

#include "common.h"
// generic structure for holding N zbfilter instances.
typedef struct ZB_BLOCK_t {
	// ZB method uses 1st and 2nd order transfer functions
	BYTE N; // number of ZB DF2's to use
	oTDF1_3 * df; 
	oMovingAvg * rmsavg;		 
	double * h02;
} ZB_Block;

typedef struct ZB_STEREO_BLOCK_t {
	BYTE N;
	ZB_Block * zb1;
	ZB_Block * zb2;
	double * fc;  // array of N center frequency values
	double * bw;  // array of N bandwidth values
	double * gdb; // array of N gain values
	volatile BOOL update_gain;
} ZB_Stereo_Block;

double zbfilter(double* B,double* A,int basize,float fc, float fs, float bw, float gdb);

ZB_Block * NewZBFilterBlock(int num_filters);
void ZB_Block_Delete( ZB_Block * zbbp_block );
void ZBFilterBlockInit(ZB_Block * zbbp_block,int idx,float fc, float fs, float bw, float gdb);

ZB_Stereo_Block * NewZBStereoFilterBlock(int num_filters,double*fclst,double*bwlst,double*gdblst);
void ZB_Stereo_Block_Delete( ZB_Stereo_Block * zbbps );
void ZB_Stereo_Block_UpdateGain( ZB_Stereo_Block * zbbps );


#endif