

#include "bassdsp.h"
#include "common.h"
#include "filter/zbfilter.h"
#include "core/oFloatVector.h"

typedef struct veqData_t {
	int N;
	oMovingAvg ma_scale;
	oMovingAvg ma_max;
	oMovingAvg * rmsavg;
	double max;
	double rmsmax; // = max*max
	int samplecount;
	oFloatVector vx;
	oFloatVector vc;
	
} veqData;

void CALLBACK DSPFUNC DSP_ZBVEQ_Proc(HDSP handle, DWORD channel, void *buffer, DWORD length, void *user) {
	/*
		HDSP handle - the handle of the DSP
		channel - channel that the dsp is being applied to
		buffer  - pointer to sample data to apple the DSP to,
			8  bit       - unsigned
			16 bit       - signed
			32 bit float - range from -1 to +1 (unclipped so value can be outside this range)
		length  - number of bytes in buffer
				- for FLOAT DSP, there are 4 bytes per sample.
				- therefore there are LENGTH/8 samples passed to this function
				-
		void * user, information given when BASS_ChannelSetDSP was called
	*/
	float *d=(float*)buffer;
	float l=0,x=0,c=0,s=0;

	oTDF1_3 * filter;
	DWORD i,j;
	
	veqData * veq = (veqData *) user;
	
	if (veq==NULL)
		return;
	for (i=0;i<length/4;i+=2) {
		l = (d[i]*0.5) + (d[i+1]*0.5);	
		
		
		oMovingAvg_insertRMS(&veq->ma_max,l);
		
		x = 0;
		for (j=0; j < veq->N;j++){
			oMovingAvg_insertRMS(&veq->rmsavg[j],l);
			x += (veq->rmsmax / oMovingAvg_getRMS( &veq->rmsavg[j] ))/veq->N;
		}

		c = oMovingAvg_getRMS( &veq->ma_max );
		c = veq->rmsmax / (c<0.001?0.001:c) ;
		if (c>10.0)c=10.0;
		
		s = ((double)veq->rmsavg[0].count/(double)veq->rmsavg[0].length);
		x = (1-s) + s*x; // slowly ramp up the effect of X;
		
		if (x < veq->max) x = veq->max;
		oMovingAvg_insert(&veq->ma_scale,x);
		x = oMovingAvg_get(&veq->ma_scale);

		if (x > c) { 
			x=.9*c;
			for (j=0;j<veq->ma_scale.length;j++) {
				veq->ma_scale.data[j]=x;	
			}
			veq->ma_scale.total = x * veq->ma_scale.length;
			
		}

		d[i]*=x;
		d[i+1]*=x;
		
		if ( (veq->samplecount+i) % 4410 == 0) {
			oFloatVector_append(&veq->vx,x);
			oFloatVector_append(&veq->vc,c);
		}
		
	}
	//veq->samplecount += length/4;
	return;
}

void * DSP_ZBVEQ_New(int sampleRate) {
	// filter_delay : 4410 : 1/10*SR : sample period to take an average over.
	int i;
	
	// create the main data structure
	veqData * veq = malloc(sizeof(veqData));
	if (veq == NULL) {
		return NULL;
	}
	veq -> N = 2;
	veq -> max = 0.5;
	veq -> rmsmax = veq -> max * veq -> max;
	veq -> rmsavg = malloc(  sizeof(oMovingAvg) * veq -> N  );

	oMovingAvg_init(&veq->ma_scale,sampleRate);
	oMovingAvg_init(&veq->ma_max,sampleRate*5);
	oMovingAvg_init(&veq->rmsavg[0],sampleRate*10);
	oMovingAvg_init(&veq->rmsavg[1],sampleRate*5);
	
	veq->samplecount = 0;
	oFloatVector_init(&veq->vx,-1,-1);
	oFloatVector_init(&veq->vc,-1,-1);

	// by enforcing a starting max, the ramp is slightly controlled.
	// also some maximum is needed to prevent a 0 starting max
	for (i=0;i<veq->N;i++) {
		veq->rmsavg[i].max_value=.1;
	}
	
	return (void*) veq;
}

int DSPFUNC DSP_ZBVEQ_Settings(void) {
	// return a set of enums, te
	return DSP_CHAN_STEREO;
}

void DSPFUNC DSP_ZBVEQ_Delete(void * oZBVEQ) {
	int i;
	veqData * veq = (veqData *) oZBVEQ;
	
	if (veq != NULL) {
	
		for (i=0;i<veq->N;i++) {
			oMovingAvg_free(&veq->rmsavg[i]);
		}
		free(veq -> rmsavg);
		oMovingAvg_free(&veq->ma_max);
		oMovingAvg_free(&veq->ma_scale);
	}
	free(veq);
}

int DSPFUNC DSP_ZBVEQ_GetVX(void * oZBVEQ,double **buffer) {
	veqData * veq = (veqData *) oZBVEQ;
	if (veq !=NULL) {
		*buffer = veq->vx.data;
		return veq->vx.size;
	}
	return 0;
}
int DSPFUNC DSP_ZBVEQ_GetVC(void * oZBVEQ,double **buffer) {
	veqData * veq = (veqData *) oZBVEQ;
	if (veq !=NULL) {
		*buffer = veq->vc.data;
		return veq->vc.size;
	}
	return 0;
}

