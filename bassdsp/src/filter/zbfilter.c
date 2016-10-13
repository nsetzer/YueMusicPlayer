

#include "zbfilter.h"

/*
	zbfilter creates a 2 pole IIR? band pass filter.
	B,A : double array of size 3.
	basize is the size of the array A and B. because this is a zb filter
	this value must always be 3.
	fc : center frequency of band pass filter
	fs : sample frequency (44100)
	bw : bandwidth of the band pass filter
	gdb : gain coefficient, in DB.
*/
double zbfilter(double* B,double* A,int basize,float fc, float fs, float bw, float gdb){
	/*
		places A2(z) from the paper into the
		given Df2 Block
		returns the value of h0/2
		h0 = v0-1.
	*/
	if ( basize != 3 )
		return 0;
		
	double v0 = pow(10.0,gdb/20.0);
	
	double h0 = v0 - 1.0;

	double ohmc = (2.0*PI*fc)/fs;
	double ohmw = (2.0*PI*bw)/fs;

	double d = -cos(ohmc);
	
	double ax;
	double tohm = tan(ohmw/2.0);
	if (v0 >= 1.0)
		ax = (tohm-1.0) / (tohm+1.0);
	else
		ax = (tohm-v0) / (tohm+v0);

	B[0] = -ax;
	B[1] = d * ( 1.0 - ax );
	B[2] = 1.0;
    
	A[0] = 1.0;
	A[1] = -d * ( 1.0 - ax ); // note i inverted
	A[2] = ax;				// A1 and A2
	
	//printf("%f %f %f\n",B[0],B[1],B[2]);
	//printf("%f %f %f\n\n",A[0],A[1],A[2]);
    //
	// alternate form
	//double e = d * ( 1.0 - ax );
	//double f = ( 1 + ax ) * h0 / 2.0;
	//
	//B[0] = 1.0 + f;
	//B[1] = e;
	//B[2] = (-ax - f);
	//
	//A[0] = 1.0;
	//A[1] = e;
	//A[2] = -ax;
		
	return h0/2.0;
}

ZB_Block * NewZBFilterBlock(int num_filters) {
	int i;
	ZB_Block * zbbp_block = malloc( sizeof(ZB_Block) );
	
	if (zbbp_block == NULL)
		return NULL;
		
	zbbp_block->N = num_filters; 
	
	zbbp_block->df     = malloc(  sizeof(oTDF1_3)    * num_filters  );
	zbbp_block->rmsavg = malloc(  sizeof(oMovingAvg) * num_filters  );
	zbbp_block->h02    = malloc(  sizeof(double)     * num_filters  );

	if ( zbbp_block->df==NULL || zbbp_block->rmsavg == NULL || zbbp_block->h02==NULL ) {
		free(zbbp_block->df);
		free(zbbp_block->rmsavg);
		free(zbbp_block->h02);
		free(zbbp_block);
		return NULL;
	}
	for (i=0;i<zbbp_block->N;i++) {
		zbbp_block->rmsavg->data = NULL;
	}
		
	return zbbp_block;
	
}

void ZB_Block_Delete( ZB_Block * zbbp_block ) {
	int i;
	if (zbbp_block == NULL)
		return;
	free(zbbp_block->df);
	//todo: INIT THESE TO NULLPTR just in case we accidentallt free unallocated mem
	for (i=0;i<zbbp_block->N;i++) {
		oMovingAvg_free(&zbbp_block->rmsavg[i]); 
	}
	free(zbbp_block->rmsavg);
	free(zbbp_block->h02); 
	free(zbbp_block); 
}

// initialize the ith filter in a block.
void ZBFilterBlockInit(ZB_Block * zbbp_block,int idx,float fc, float fs, float bw, float gdb) {
	double B[3];
	double A[3];
	
	zbbp_block->h02[idx] = zbfilter( 
									zbbp_block->df[idx].B,
									zbbp_block->df[idx].A,
									3,
									fc,
									fs,
									bw,
									gdb
								);						
	zbbp_block->df[idx].ZB1 = 0;
	zbbp_block->df[idx].ZB2 = 0;
	zbbp_block->df[idx].ZA1 = 0;
	zbbp_block->df[idx].ZA2 = 0;
}

ZB_Stereo_Block * NewZBStereoFilterBlock(int num_filters,double*fclst,double*bwlst,double*gdblst) {

	int i;
	ZB_Stereo_Block * zbbps = malloc( sizeof(ZB_Stereo_Block) );
	
	zbbps->zb1 = NewZBFilterBlock(num_filters);
	if ( zbbps->zb1==NULL ) {
		free( zbbps );
		return NULL;
	}
		
	zbbps->zb2 = NewZBFilterBlock(num_filters);
	if ( zbbps->zb1==NULL ) {
		ZB_Block_Delete(zbbps->zb1);
		free( zbbps );
		return NULL;
	}
		
	zbbps->N = num_filters;
	zbbps->update_gain = FALSE;
	zbbps->fc  = malloc(  sizeof(double) * num_filters );
	zbbps->bw  = malloc(  sizeof(double) * num_filters );
	zbbps->gdb = malloc(  sizeof(double) * num_filters );
	
	if ( zbbps->fc==NULL || zbbps->bw==NULL || zbbps->gdb==NULL) {
		free( zbbps->fc );
		free( zbbps->bw );
		free( zbbps->gdb );
		ZB_Block_Delete(zbbps->zb1);
		ZB_Block_Delete(zbbps->zb2);
		free( zbbps );
		return NULL;
	}
		
	//--------------------------
	for ( i=0; i < num_filters; i++ ) {
		zbbps->fc[i]  = fclst[i];
		zbbps->bw[i]  = bwlst[i];
		zbbps->gdb[i] = gdblst[i];
		ZBFilterBlockInit(zbbps->zb1,i,zbbps->fc[i], 44100, zbbps->bw[i], zbbps->gdb[i]);
		ZBFilterBlockInit(zbbps->zb2,i,zbbps->fc[i], 44100, zbbps->bw[i], zbbps->gdb[i]);
	}
	
	return zbbps;
	
}

void ZB_Stereo_Block_Delete( ZB_Stereo_Block * zbbps ) {
	if (zbbps == NULL)
		return
	free( zbbps->fc );
	free( zbbps->bw );
	free( zbbps->gdb );
	ZB_Block_Delete(zbbps->zb1); 
	ZB_Block_Delete(zbbps->zb2); 
	free( zbbps ); 
}

void ZB_Stereo_Block_UpdateGain( ZB_Stereo_Block * zbbps ) {
	int i;
	for ( i=0; i < zbbps->N; i++ ) {
		ZBFilterBlockInit(zbbps->zb1,i,zbbps->fc[i], 44100, zbbps->bw[i], zbbps->gdb[i]);
		ZBFilterBlockInit(zbbps->zb2,i,zbbps->fc[i], 44100, zbbps->bw[i], zbbps->gdb[i]);
	}
}