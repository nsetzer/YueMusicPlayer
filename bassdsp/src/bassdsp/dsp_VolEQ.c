


#include "bassdsp.h"

#include "common.h"

typedef struct VolEQ_t {
	float scale;
} VolEQ;

void CALLBACK DSPFUNC DSP_VOLEQ_Proc(HDSP handle, DWORD channel, void *buffer, DWORD length, void *user) {
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
	float scale;
	DWORD i;
	
	VolEQ * voleq = (VolEQ *) user;
	if (voleq==NULL)
		return;
	scale = voleq->scale;
	length /= 4;
	for (i=0;i<length;i++){
		d[i] *= scale;
	}
	return;
}

void *  DSP_VOLEQ_New(void) {
	// filter_delay : 4410 : 1/10*SR : sample period to take an average over.
	
	VolEQ * voleq = malloc( sizeof(VolEQ) );
	
	if ( voleq == NULL)
		return NULL;

    voleq->scale = 1.0F;

	return (void*) voleq;
}

int DSPFUNC DSP_VOLEQ_Settings(void) {
	return DSP_CHAN_STEREO|DSP_CHAN_MONO;
}

void DSPFUNC DSP_VOLEQ_Delete(void * oveq) {
	VolEQ * voleq = (VolEQ *) oveq;
	free(voleq);
}

void DSPFUNC DSP_VOLEQ_SetScale(void * oveq, float scale) {
	VolEQ * voleq = (VolEQ *) oveq;
	if (voleq != NULL)
		voleq->scale = scale;
}


