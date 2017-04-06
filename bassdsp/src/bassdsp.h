
#ifndef CP_BASS_DSP_H
#define CP_BASS_DSP_H

#include "alien/bass/bass.h"
#include "common.h"

#ifdef __linux__
// empty define of symbol for linux
#	define DSPFUNC
#elif __APPLE__
#   define DSPFUNC
#else
#   ifdef bassdsp_EXPORTS
#       define DSPFUNC __declspec(dllexport)
#   else
#       define DSPFUNC __declspec(dllimport)
#   endif
#endif

#undef CALLBACK
#define CALLBACK

// enum for set of required channel parameters.
// These are hints a DSP can give to ensure correct performance.
#define DSP_CHAN_MONO   0x01
#define DSP_CHAN_STEREO 0x02
#define DSP_CHAN_undef1 0x04
#define DSP_CHAN_undef2 0x08

void CALLBACK DSPFUNC DSP_ZBPEQ_Proc(HDSP handle, DWORD channel, void *buffer, DWORD length, void *user);
DSPFUNC void *  DSP_ZBPEQ_New(int num_filters,double * fclst,double *bwlst,double * gdb);
void DSPFUNC DSP_ZBPEQ_Delete(void * ozbpeq);
int DSPFUNC DSP_ZBPEQ_GetGain(void * ozbvis , double * gdblist, int length);
void DSPFUNC DSP_ZBPEQ_SetGain(void * ozbvis, double * gdblist, int length);

/*
	ZBVIS
	this DSP block applies N band pass filters. The GetData function
	can be used to get the RMS average of these filters.
*/
void CALLBACK DSPFUNC DSP_ZBVIS_Proc(HDSP handle, DWORD channel, void *buffer, DWORD length, void *user);
void CALLBACK DSPFUNC DSP_ZBVIS_Proc_Mono(HDSP handle, DWORD channel, void *buffer, DWORD length, void *user);
DSPFUNC void *  DSP_ZBVIS_New(int sampleRate,int num_filters,double * fclst,double *bwlst,int filter_delay);
void   DSPFUNC DSP_ZBVIS_Delete(void *);
int   DSPFUNC DSP_ZBVIS_Settings(void);
int DSPFUNC DSP_ZBVIS_GetData(void * ozbvis, double * buffer, int bufferlength);

void CALLBACK DSPFUNC DSP_ZBLOG_Proc(HDSP handle, DWORD channel, void *buffer, DWORD length, void *user);
void CALLBACK DSPFUNC DSP_ZBLOG_Proc_Mono(HDSP handle, DWORD channel, void *buffer, DWORD length, void *user);
DSPFUNC void *  DSP_ZBLOG_New(int sampleRate,int num_filters,double * fclst,double *bwlst,int filter_delay,int log_delay);
void   DSPFUNC DSP_ZBLOG_Delete(void *);
void DSPFUNC DSP_ZBLOG_Reset(void * oZBLOG);
int   DSPFUNC DSP_ZBLOG_Settings(void);
int DSPFUNC DSP_ZBLOG_GetMean(void * oZBLOG,int index,double **buffer);
int DSPFUNC DSP_ZBLOG_GetMaximum(void * oZBLOG,float *pos,float *neg);

void CALLBACK DSPFUNC DSP_ZBVEQ_Proc(HDSP handle, DWORD channel, void *buffer, DWORD length, void *user);
DSPFUNC void *  DSP_ZBVEQ_New(int sampleRate);
void   DSPFUNC DSP_ZBVEQ_Delete(void *);
int   DSPFUNC DSP_ZBVEQ_Settings(void);
int DSPFUNC DSP_ZBVEQ_GetVX(void * oZBVEQ,double **buffer);
int DSPFUNC DSP_ZBVEQ_GetVC(void * oZBVEQ,double **buffer);

void CALLBACK DSPFUNC DSP_VOLEQ_Proc(HDSP handle, DWORD channel, void *buffer, DWORD length, void *user);
DSPFUNC void *  DSP_VOLEQ_New(void);
int DSPFUNC DSP_VOLEQ_Settings(void);
void DSPFUNC DSP_VOLEQ_Delete(void * ozbvis);
void DSPFUNC DSP_VOLEQ_SetScale(void * ozbvis, float scale);

DSPFUNC void *  DSP_AudioIngest_New(ULONG Fs_in,ULONG Fs_out, BOOL inputIsStereo);
int32 DSPFUNC DSP_AudioIngest_fromChannel(void * ingest, DWORD channel, float* output, int32 out_length);
ULONG DSPFUNC DSP_AudioIngest_fromSignal(void * ingest, float* input,ULONG in_length, float* output, ULONG out_length);
void DSPFUNC DSP_AudioIngest_Delete(void * ingest);

DSPFUNC void * DSP_FEATGEN_new(uint32 Fs_in);
DSPFUNC void * DSP_FEATGEN_newMFCC(uint32 Fs_in);
DSPFUNC void * DSP_FEATGEN_newMIDI(uint32 Fs_in);
DSPFUNC void * DSP_FEATGEN_newSpectrogram(uint32 Fs_in);
void DSPFUNC DSP_FEATGEN_setLogOutput(void * vpfg,int useLogOutput, double add, double mul, double tiny);
void DSPFUNC DSP_FEATGEN_setFFTOptions(void * vpfg,int logN,int window_shift);
void DSPFUNC DSP_FEATGEN_setMFCCOptions(void * vpfg,int useDCT,int SaveZeroBin,int numFilter,int numFilterSave, double minf, double maxf);
void DSPFUNC DSP_FEATGEN_setMIDIOptions(void * vpfg,int numFilter);
int DSPFUNC DSP_FEATGEN_init(void * vpfg);
void DSPFUNC DSP_FEATGEN_delete(void * vpfg);
void DSPFUNC DSP_FEATGEN_reset(void * vpfg);

void DSPFUNC DSP_FEATGEN_outputSize(void * vpfg,int *size);
long DSPFUNC DSP_FEATGEN_pushSample(void * vpfg,double * x, ULONG x_size);
long DSPFUNC DSP_FEATGEN_nextFrame(void * vpfg, double * y, ULONG y_size);


//void* DSPFUNC DSP_Transcode_new(const char * inFile,int bitrate,int quality,float scale);
DSPFUNC void*  DSP_Transcode_new(DWORD channel,int bitrate,int quality,float scale);
int32 DSPFUNC DSP_Transcode_setArtist(void * transcoder, const char * artist);
int32 DSPFUNC DSP_Transcode_setAlbum(void * transcoder, const char * album);
int32 DSPFUNC DSP_Transcode_setTitle(void * transcoder, const char * title);
int32 DSPFUNC DSP_Transcode_do(void * transcoder,const char * outFile);

#endif