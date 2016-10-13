
#ifndef DSP_COMMON_H
#define DSP_COMMON_H

#include <stdio.h>
#include <stdlib.h>
#include <string.h>

#include <math.h>


#undef PI
#define PI (3.14159265358979323846)

#undef TWOPI
#define TWOPI (2.0*PI)

#undef TRUE
#define TRUE 1

#undef FALSE
#define FALSE 0


// DSP normalized sinc function
#define sinc(x) ( (x==0.0)?1.0:sin(PI*x)/(PI*x) )


#ifdef DIAG_SIGPROC
#define diag(fmt,...) printf(fmt "\r\n", ##__VA_ARGS__)
#else
#define diag(fmt,...) ;
#endif

#ifdef USE_DOUBLE_PRECISION
#define floatDSP double
#else
#define floatDSP float
#endif

#undef uint64
#define uint64 unsigned long long

#undef int64
#define int64 signed long long

#undef uint32
#define uint32 unsigned long

#undef int32
#define int32 signed long

#undef uint16
#define uint16 unsigned short

#undef int16
#define int16 signed short

#undef uint8
#define uint8 unsigned char

#undef int8
#define int8 unsigned char

// deprecated
#undef USHORT
#define USHORT unsigned short

#undef SSHORT
#define SSHORT short

#undef ULONG
#define ULONG unsigned long

#undef SLONG
#define SLONG long

#undef BYTE
#define BYTE char

#undef BOOL
#define BOOL char

#define check_float(expected,value,eps) ( fabs(expected-value) < eps )

#endif