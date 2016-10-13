

#ifndef ALIEN_BASS_UTIL_H
#define ALIEN_BASS_UTIL_H

#include "alien/bass/bass.h"

int bassutil_init(void);
HSTREAM bassutil_decode(const char * input_file);
void bassutil_close(HSTREAM channel);
void bassutil_free(void);


int bassutil_channel_get_data(HSTREAM channel,float *buffer,long bufsize);

#endif