#include "bassdsp.h"
#include "common.h"
#include "filter/zbfilter.h"
#include "core/oFloatVector.h"

void CALLBACK DSPFUNC DSP_ZBPEQ_Proc(HDSP handle, DWORD channel, void *buffer, DWORD length, void *user) {
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
	float l=0,tl=0,vl=0;
	float r=0,tr=0,vr=0;
	oTDF1_3 * filter;
	DWORD i,j;
	
	ZB_Stereo_Block * zbbps = (ZB_Stereo_Block *) user;
	if (zbbps==NULL)
		return;
		
	if (zbbps->update_gain!=FALSE) {
		zbbps->update_gain = FALSE;
		ZB_Stereo_Block_UpdateGain(zbbps);
	}
	for (i=0;i<length/4;i+=2){
		l = d[i];
		r = d[i+1];
		for (j=0; j < zbbps->N;j++){
			// perform the TDF1 convolution:


			filter = &zbbps->zb1->df[j];
			vl = filter->ZA1 + l;
			tl = vl*filter->B[0] + filter->ZB1;
			
			filter->ZA1 = vl*filter->A[1] + filter->ZA2;
			filter->ZA2 = vl*filter->A[2];
			
			filter->ZB1 = vl*filter->B[1] + filter->ZB2;
			filter->ZB2 = vl*filter->B[2];
			//------------------------------------

			filter = &zbbps->zb2->df[j];
			vr = filter->ZA1 + r;
			tr = vr*filter->B[0] + filter->ZB1;
			
			filter->ZA1 = vr*filter->A[1] + filter->ZA2;
			filter->ZA2 = vr*filter->A[2];
			
			filter->ZB1 = vr*filter->B[1] + filter->ZB2;
			filter->ZB2 = vr*filter->B[2];
			//------------------------------------		
			// apply the gain factor
			l = (l - tl)*zbbps->zb1->h02[j] + l;
			r = (r - tr)*zbbps->zb2->h02[j] + r;
			//l = tl;
			//r = tr;
			
		}
		d[i] = l;
		d[i+1] = r;
	}
	return;
}

void * DSP_ZBPEQ_New(int num_filters,double * fclst,double *bwlst,double * gdb) {
	ZB_Stereo_Block * zbbps = NewZBStereoFilterBlock( num_filters, fclst, bwlst, gdb );
	return zbbps;
}

void DSPFUNC DSP_ZBPEQ_Delete(void * ozbpeq) {
	ZB_Stereo_Block * zbbps = (ZB_Stereo_Block*) ozbpeq;
	if (zbbps == NULL)
		return;
	ZB_Stereo_Block_Delete(zbbps);
	return;
}

int DSPFUNC DSP_ZBPEQ_GetGain(void * ozbvis, double * gdblist, int length) {
	int i;
	ZB_Stereo_Block * zbbps = (ZB_Stereo_Block *) ozbvis;
	if (zbbps == NULL)
		return 0;
	for (i=0;i<length&&i<zbbps->N;i++) {
		gdblist[i] = zbbps->gdb[i];
	}
	return i;
}
void DSPFUNC DSP_ZBPEQ_SetGain(void * ozbvis, double * gdblist, int length) {
	int i;
	ZB_Stereo_Block * zbbps = (ZB_Stereo_Block *) ozbvis;
	if (zbbps == NULL)
		return;
	for (i=0;i<length&&i<zbbps->N;i++) {
		 zbbps->gdb[i] = gdblist[i];
	}
	zbbps->update_gain = TRUE;
	return;
}


