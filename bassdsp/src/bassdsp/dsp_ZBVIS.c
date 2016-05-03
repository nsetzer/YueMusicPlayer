

#include "bassdsp.h"
#include "common.h"
#include "filter/zbfilter.h"
#include "core/oFloatVector.h"

void CALLBACK DSPFUNC DSP_ZBVIS_Proc(HDSP handle, DWORD channel, void *buffer, DWORD length, void *user) {
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
	float v=0,v2=0;
	DWORD i,j;
	ZB_Block * zbbp_block = (ZB_Block *) user;
	if (zbbp_block==NULL)
		return;
	//float test[32];	
	for (i=0;i<length/4;i+=2){
		v = (d[i]+d[i+1])*0.5;
		for (j=0; j < zbbp_block->N;j++){
			// note recent changes to this filter function
			v2 = oTDF1_3_IIR(&zbbp_block->df[j],v);
			v2 = (v - v2)*0.5; // this comes from the zbfilter paper
							   // and implements the band pass filter.
			//test[j] += v2*v2;
			oMovingAvg_insertRMS( &zbbp_block->rmsavg[j],v2);
		}
	}
	//for (j=0; j < zbbp_block->N;j++)
	//	test[j]= sqrt(test[j]/(length/4));
	//printf("test zbvis: %f %f %f %f\n",test[0],test[2],test[4],test[6]);
		
	
	return;
}
void CALLBACK DSPFUNC DSP_ZBVIS_Proc_Mono(HDSP handle, DWORD channel, void *buffer, DWORD length, void *user) {
	float *d=(float*)buffer;
	float v=0,v2=0;
	DWORD i,j;
	ZB_Block * zbbp_block = (ZB_Block *) user;
	if (zbbp_block==NULL)
		return;
	for (i=0;i<length/4;i++){
		for (j=0; j < zbbp_block->N;j++){
			v2 = oTDF1_3_IIR(&zbbp_block->df[j],d[i]);
			v2 = (v - v2)*0.5;
			oMovingAvg_insertRMS( &zbbp_block->rmsavg[j],v2);
		}
	}
	return;
}

void * DSP_ZBVIS_New(int sampleRate,int num_filters,double * fclst,double *bwlst,int filter_delay) {
	// filter_delay : 4410 : 1/10*SR : sample period to take an average over.
	int i;
	
	ZB_Block * zbbp_block = NewZBFilterBlock(num_filters);
	
	if ( zbbp_block == NULL)
		return NULL;

    for( i=0; i < zbbp_block->N; i++){
	
		oMovingAvg_init(&zbbp_block->rmsavg[i],filter_delay);

		ZBFilterBlockInit(zbbp_block,i,fclst[i],sampleRate,bwlst[i],0);
	}
	

	return (void*) zbbp_block;
}

int DSPFUNC DSP_ZBVIS_Settings(void) {
	// return a set of enums, te
	return DSP_CHAN_STEREO|DSP_CHAN_MONO;
}

void DSPFUNC DSP_ZBVIS_Delete(void * ozbvis) {
	ZB_Block * zbbp_block = (ZB_Block *) ozbvis;
	ZB_Block_Delete( zbbp_block );
}

int DSPFUNC DSP_ZBVIS_GetData(void * ozbvis, double * buffer, int bufferlength) {
	int i;
	ZB_Block * zbbp_block = (ZB_Block *) ozbvis;
	if (zbbp_block == NULL)
		return 0;
	for (i=0;i<bufferlength&&i<zbbp_block->N;i++) {
		buffer[i] = oMovingAvg_getRMS(&zbbp_block->rmsavg[i]);
	}
	//printf("DSP ZBVIS get data::%f %f %f\n",buffer[0],buffer[1],buffer[6]);
	return i;
}


