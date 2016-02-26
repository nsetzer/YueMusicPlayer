#! python $this
"""
    FILE: zbpeq.py
    Description:
        Using "Parametric Digital Filter Structures" by
    Udo Zolzer and Thomas Boltze this file implements a
    set of functions for building filters suitable
    for a parametric EQUALIZER.

        Functions suffixed with '_param' return a
    zbparam object which contain B and A coefficients,
    these values are suitable for using in matlab. For example
    to see magnitude, frequncy respons, group delay and poles and zeroes.
    Mileage will vary for when they are used in a direct form block.
        Functions suffixed with 'A' are meant to be used with
    a direct form block. They do not completely implement
    the transfer function, and correspond to the A transform block
    in the relavent section of the paper. additional math will
    be requiered to implement the transfer function. see the doc string
    for those functions.
"""
import math,os,sys

def bw_from_q(fc,q): return fc / q;
def q_from_bw(fc,fbw): return fc / fbw;
def omega(f,fs): return (2.0 * math.pi * f) / fs;

def zb_ax(ohmw,v0):
    # boost case : v0 = 10^(gdb/20)
    # cut case   : v0 = 1
    # boost == cut when gdb = 0
    tohm = math.tan(ohmw/2.0);
    return (tohm-v0) / (tohm+v0);

def zb_hf_ax(ohmw,v0):
    tohm = math.tan(ohmw/2.0);
    return (v0*tohm-1) / (v0*tohm+1);

class zbparam(object):
    """
        C-style structure to hold information.
    """
    v0=0;
    h0=0;
    h02=0;
    ohmc=0;
    ohmw=0;
    d=0;    # only used in 2nd order filters
    ax=0;
    # when using a  directform filter, invert A coeffs.
    b_num = None;
    a_den = None;

def zbLFA(fs,fc,gdb):
    """
        A1l(z) All Pass filter for making
        LF shelving filters and low pass filters.
        if x[n] is the input signal, and t[n]
        is the output of a direct-form block using
        the coefficinents A,B given by this function
        then the final output y is :

        for LF shelf:
            y[n] = (t[n] + x[n]) * h0/2 + x[n]
        for LPF:
            y[n] = (t[n] + x[n])/2

        the above results are equivalent to:
            zbLFshelf_param
            zbLPF_param

    """
    p = zbparam()
    p.v0 = math.pow(10.0, gdb / 20.0);
    p.h0 = p.v0 - 1;
    p.h02 = p.h0/2.0
    p.ohmc = omega(fc,fs)
    p.ax = zb_ax(p.ohmc,p.v0)
    p.b_num = [p.ax,1.0]
    p.a_den = [1.0,p.ax]
    return p

def zbLFshelf_param(fs,fc,gdb):
    p = zbLFA(fs,fc,gdb); # 'boost' case when gdb != 0
    d = (1 + p.ax)*p.h02
    p.b_num = [1 + d,p.ax + d]
    p.a_den = [1,p.ax]
    return p

def zbLPF_param(fs,fc):
    p = zbLFA(fs,fc,0); # 'cut' case
    p.b_num = [.5*(1+p.ax),.5*(1+p.ax)]
    p.a_den = [1,p.ax]
    return p

def zbHFA(fs,fc,gdb):
    """
        A1h(z) All Pass filter for making
        HF shelving filters and High pass filters.
        if x[n] is the input signal, and t[n]
        is the output of a direct-form block using
        the coefficinents A,B given by this function
        then the final output y is :

        for HF shelf:
            y[n] = (x[n] - t[n]) * h0/2 + x[n]
        for HPF:
            y[n] = (x[n] - t[n])/2

        the above results are equivalent to:
            zbHFshelf_param
            zbHPF_param
    """
    p = zbparam()
    p.v0 = math.pow(10.0, gdb / 20.0);
    p.h0 = p.v0 - 1;
    p.h02 = p.h0/2.0
    p.ohmc = omega(fc,fs)
    p.ax = zb_hf_ax(p.ohmc,p.v0)
    p.b_num = [1,p.ax]
    p.a_den = [1,p.ax]
    return p

def zbHFshelf_param(fs,fc,gdb):
    p = zbHFA(fs,fc,gdb); # 'boost' case when gdb != 0
    d = (1.0 - p.ax)*p.h0/2.0
    e = (p.ax - 1.0)*p.h0/2.0
    p.b_num = [1.0+d,p.ax+e]
    p.a_den = [1.0,p.ax]
    return p

def zbHPF_param(fs,fc):
    # NOTES: there is a bug in the paper, A(z) is defined with a negative sign.
    # instead of -ax - z^-1 / 1 +axz^-1 use  ax + z^-1 / 1 +axz^-1
    # then solve .5 * (1 - A(z))
    # its obvious you should subtract at that point in the diagram,
    # but A(z) itself should not have been defined with a negative
    # - i was only able to solve this by using FilterDesign
    p = zbHFA(fs,fc,0); # 'cut' case
    p.b_num = [.5*(1-p.ax),.5*(p.ax-1)]
    p.a_den = [1.0,p.ax]
    return p

def zbpeakA(fs,fc,bw,gdb):
    """
        A2(z) All Pass filter for making
        Resonant peak filters and Band Pass filters.
        if x[n] is the input signal, and t[n]
        is the output of a direct-form block using
        the coefficinents A,B given by this function
        then the final output y is :

        for peak filter:
            y[n] = (x[n] - t[n]) * h0/2 + x[n]
        for bp filter:
            y[n] = (x[n] - t[n])/2

        the above results are equivalent to:
            zbpeak_param
            zbbp_param
    """
    p = zbparam()
    p.v0 = math.pow(10.0, gdb / 20.0);
    p.h0 = p.v0-1.0
    p.h02 = p.h0/2.0
    p.ohmc = omega(fc,fs)
    p.ohmw = omega(bw,fs)
    p.d = -math.cos(p.ohmc)

    if p.v0 > 1.0 :
        p.ax = zb_ax(p.ohmw,1.0)
    else:
        p.ax = zb_ax(p.ohmw,p.v0)

    e = p.d * ( 1 - p.ax )

    p.b_num = [-p.ax, e, 1]
    p.a_den = [ 1.0, e, -p.ax ];

    return p

def zbpeak_param(fs,fc,bw,gdb):
    p = zbpeakA(fs,fc,bw,gdb)

    e = p.d * ( 1 - p.ax )
    f = ( 1 + p.ax ) * p.h02

    p.b_num = [ (1 + f) , e , (-p.ax - f) ]
    p.a_den = [ 1.0, e, -p.ax ]

    return p

def zbbp_param(fs,fc,bw):
    p = zbpeakA(fs,fc,bw,0)

    e = ( 1 + p.ax ) / 2.0
    f = p.d * ( 1 - p.ax )

    p.b_num = [e,0,-e]
    p.a_den = [ 1.0, f, -p.ax ]

    return p

if __name__=="__main__":
    # http://as.reddit.com/r/DSP/comments/10c4un/z%C3%B6lzerboltze_zb_peaknotch_parametric_eq_in_c/
    # http://www.strauss-acoustics.ch/zb-peq.html
    # http://www.aes.org/e-lib/browse.cfm?elib=7667
    import sci
    # print the tranform coefficients for various band pass filters
    # just need a highpass and lowpass filter
    # low pass from < 69ish
    # and high pass from >8kish
    #n = [ 69 + 12*math.log(f/440.0,2) for f in (440,500,1000,2000,8000) ]
    #f = [math.pow(2,((d-69.0)/12.0))*440.0 for d in range(120) ]
    #print n
    #print f
    #fc_list = [1000,2000,3000,4000,5000,6000,7000]
    #bw_list = [1000,1000,1000,1000,1000,1000,1000]
    p = zbpeakA(44100,48,32,6)
    print("h02=",p.h02)
    print(p.b_num)
    print(p.a_den)

    # get mag
    #p = zbpeak_param(16000,4000,500,3)
    #print approx_mag(p.b_num,p.a_den,4000,16000)
    #print mag(p.b_num,p.a_den,4000)
    #w,h = signal.freqz(p.b_num,p.a_den)
    #h = abs(h)
    #hdb = 20.0 * log10 (abs(h))
    #print hdb[255], hdb[256], hdb[257]

    #fs=16000
    # fc = 7000
    # gdb = 3
    # bw = 500
    #p = zbLFshelf_param(fs,fc,gdb)
    #p = zbHFshelf_param(fs,fs/2.0 - fc,gdb)
    # p = zbpeak_param(fs,fc,bw,gdb)
    # for item in p.__dict__:
    #     print "%s = %s "%(item , p.__dict__[item])
    #[1.9286322257064175e-05, 0.08351048200372338, 0.4564042015620059, 1.884058158305
    #3839, 5.9969072455326291, 1.9718736137427284, 0.47730222192574173, 0.08941135668
    #7950305, 1.9286322257064175e-05]
    # print vzero(p.ax,d,p.ohmc) - 1
    #sci.assert_bw(p.b_num,p.a_den,250,fs)
    #sci.impz(p.b_num,p.a_den)
    #p = zbpeak_param(fs,400,50,12)
    #p = zbbp_param(fs,7951 ,98)
    #p = zbHPF_param(16000,6000)
    #p = zbHFshelf_param(16000,6000,3)
    #sci.mfreqz(p.b_num,p.a_den,-20,20)
    #fs = 16000
    #fc_list,bw_list = music_scale()
    ##bw_list = [ bw * 1 for bw in bw_list ]
    #print fc_list
    #gdb_list = [3,]*len(fc_list)
    #print "hey"
    #g_list = lt(fs,fc_list,bw_list,gdb_list)
    #print "gain list"
    #print g_list
    #pl = [zbpeak_param(fs,c,b,g) for c,b,g in zip(fc_list,bw_list,g_list)]
    #bl = [p.b_num for p in pl]
    #al = [p.a_den for p in pl]
    #sci.mfreqzl(bl,al,-9,9)

