

#include "alien/bass/bass_util.h"

int bassutil_init(void) {
	BASS_SetConfig(BASS_CONFIG_FLOATDSP,1);
	//BASS_SetConfig(BASS_CONFIG_DEV_DEFAULT,1);
	return !!BASS_Init(-1,44100,0,0,0);
}

HSTREAM bassutil_decode(const char * input_file) {
	// TOOD no unicode flag on linux
	return BASS_StreamCreateFile(0,input_file,0,0,BASS_UNICODE|BASS_STREAM_DECODE|BASS_SAMPLE_FLOAT);
}

void bassutil_close(HSTREAM channel) {
	BASS_StreamFree(channel);
}
void bassutil_free(void) {
	BASS_Free();
}

int bassutil_channel_get_data(HSTREAM channel,float *buffer,long bufsize) {
	int bytes;
	bytes = BASS_ChannelGetData(channel,(void*)buffer,(sizeof(float)*bufsize)|BASS_DATA_FLOAT);
	if (bytes < 0)
		return bytes;
	return bytes/sizeof(float);
}
