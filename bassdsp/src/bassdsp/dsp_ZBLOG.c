


#include "bassdsp.h"
#include "common.h"
#include "filter/zbfilter.h"
#include "core/oFloatVector.h"

typedef struct logdata_t {
	//FILE * logfile;
	ZB_Block * zbbp_block;
	oFloatVector * fvec_block;
	int N;
	int lograte; // write to log fiole every N samples.
	int samplecount;
	float max_p; // maximum positive number found
	float max_n; // maximum negative number found
			     // peak-to-peak max is max_p - max_n
				 // for stereo, these values are the maximum from either 
				 // channel (and peak-to-peak may not be well defined there)
} logdata;

void zblog_proc_main(logdata * data,float l) {
	float vl,tl;
	DWORD j;
	oTDF1_3 * filter;
	ZB_Block * zbbp_block = data -> zbbp_block;
	if (l!=l)
		printf(".");
	// first one is unfiltered
	oMovingAvg_insertRMS( &zbbp_block->rmsavg[0],l);
	// push each sample in to each filter	
	for (j=1; j < (unsigned)zbbp_block->N;j++){

		//------------------------------------
		filter = &zbbp_block->df[j];
		
		vl = filter->ZA1 + l;
		tl = vl*filter->B[0] + filter->ZB1;
		
		filter->ZA1 = vl*filter->A[1] + filter->ZA2;
		filter->ZA2 = vl*filter->A[2];
		
		filter->ZB1 = vl*filter->B[1] + filter->ZB2;
		filter->ZB2 = vl*filter->B[2];	
		//------------------------------------
		// apply the band pass filter to l.
		oMovingAvg_insertRMS( &zbbp_block->rmsavg[j],(l - tl)*0.5);

	}
	
}

void CALLBACK DSPFUNC DSP_ZBLOG_Proc(HDSP handle, DWORD channel, void *buffer, DWORD length, void *user) {
	float *d=(float*)buffer;
	float l=0;

	DWORD i,j;
	
	logdata * data = (logdata *) user;

	if (data==NULL)
		return;

	for (i=0;i<length/4;i+=2){
		// combine left and right channels
		l = (d[i]*0.5) + (d[i+1]*0.5);	
		
		zblog_proc_main(data,l);
		
		if ( (data->samplecount+i) % data->lograte == 0) {
			for (j=0; j < data->zbbp_block->N;j++){
				l = oMovingAvg_getRMS( &data->zbbp_block->rmsavg[j] );
				oFloatVector_append(&data->fvec_block[j], l );
			}
		}	
		
		data->max_p = (data->max_p>d[i]  )?data->max_p:d[i];
		data->max_p = (data->max_p>d[i+1])?data->max_p:d[i+1];
		data->max_n = (data->max_n<d[i]  )?data->max_n:d[i];
		data->max_n = (data->max_n<d[i+1])?data->max_n:d[i+1];
	}

	data->samplecount += length/4;
	
	return;
}

void CALLBACK DSPFUNC DSP_ZBLOG_Proc_Mono(HDSP handle, DWORD channel, void *buffer, DWORD length, void *user) {
	float *d=(float*)buffer;
	float l=0;

	oTDF1_3 * filter;
	DWORD i,j;
	
	logdata * data = (logdata *) user;

	if (data==NULL)
		return;

	for (i=0;i<length/4;i++){
		zblog_proc_main(data,d[i]);
		
		if ( (data->samplecount+i) % data->lograte == 0) {
			for (j=0; j < data->zbbp_block->N;j++){
				oFloatVector_append(&data->fvec_block[j], \
					oMovingAvg_getRMS( &data->zbbp_block->rmsavg[j] ) );
			}
		}	
		
		data->max_p = (data->max_p>d[i]  )?data->max_p:d[i];
		data->max_n = (data->max_n<d[i]  )?data->max_n:d[i];
	}

	data->samplecount += length/4;
	
	return;
}



void * DSP_ZBLOG_New(int sampleRate,int num_filters,double * fclst,double *bwlst,int filter_delay,int log_delay) {
	// filter_delay : 4410 : 1/10*SR : sample period to take an average over.
	int i;
	num_filters++;// filter[0] is always the entire signal
	// create the main data structure
	logdata * data = malloc(sizeof(logdata));
	if (data == NULL) {
		return NULL;
	}
	data -> samplecount = 0;
	data -> lograte = log_delay;
	data -> N = num_filters;
	
	data -> max_p = 0.0;
	data -> max_n = 0.0;
		
	// create the AB blocks, or roll back any changes.
	ZB_Block * zbbp_block = NewZBFilterBlock(num_filters);
	data -> zbbp_block = zbbp_block;
	
	if ( zbbp_block == NULL) {
		free(data);
		return NULL;
	}
	
	oFloatVector * fvec_block = malloc( sizeof(oFloatVector) * (num_filters) );
	data -> fvec_block = fvec_block;
	
	if ( fvec_block == NULL) {
		free(zbbp_block);
		free(data);
		return NULL;
	}
	
	// init all averagers to be the same
    for( i=0; i < num_filters; i++){
		oMovingAvg_init(&zbbp_block->rmsavg[i],filter_delay);
		oFloatVector_init(&fvec_block[i],-1,-1);
		fvec_block[i].size=0;
	}
	
	// only init 1:N zbblocks, the first one (index 0) will not be used.
	// ( first one is only used for RMS average of the whole signal. )
	for( i=0; i < zbbp_block->N - 1; i++){
		ZBFilterBlockInit(zbbp_block,i+1,fclst[i],sampleRate,bwlst[i],0);
	}
	

	return (void*) data;
}

int DSPFUNC DSP_ZBLOG_Settings(void) {
	return DSP_CHAN_STEREO|DSP_CHAN_MONO;
}

void DSPFUNC DSP_ZBLOG_Delete(void * oZBLOG) {
	logdata * data = (logdata *) oZBLOG;
	
	ZB_Block_Delete( data -> zbbp_block );
}

void DSPFUNC DSP_ZBLOG_Reset(void * oZBLOG) {
	int i;
	logdata * data = (logdata *) oZBLOG;
	
	if (data !=NULL) {
		data -> max_p = 0.0;
		data -> max_n = 0.0;
		for( i=0; i < data->N; i++){
		
			data->fvec_block[i].size = 0;
			
			oMovingAvg_reset(&data->zbbp_block->rmsavg[i]);
			
			data->zbbp_block->df[i].ZB1 = 0;
			data->zbbp_block->df[i].ZB2 = 0;
			data->zbbp_block->df[i].ZA1 = 0;
			data->zbbp_block->df[i].ZA2 = 0;
		}
	}
}

int DSPFUNC DSP_ZBLOG_GetMean(void * oZBLOG,int index,double **buffer) {
	logdata * data = (logdata *) oZBLOG;
	if (data !=NULL) {
		*buffer = data->fvec_block[index].data;
		return data->fvec_block[index].size;
	}
	return 0;
}

int DSPFUNC DSP_ZBLOG_GetMaximum(void * oZBLOG,float *pos,float *neg) {
	logdata * data = (logdata *) oZBLOG;
	if (data !=NULL) {
		*pos = data->max_p;
		*neg = data->max_n;
		return 0;
	}
	return -1;
}

