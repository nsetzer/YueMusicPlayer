
# https://labs.spotify.com/2014/02/28/how-to-shuffle-songs/
# Fisher-Yates
import math
import random

class ShuffleElement(object):

    def __init__( self, ref , index ):
        self.ref = ref
        self.index = index
        self.score = 0

def fisher_yates(data):
    N = len(data)
    for i in range(N):
        j = random.randint(i,N-1)
        data[i],data[j] = data[j],data[i]

def binshuffle(data,group_mapping=lambda x:x):
    # count the number of each artist
    # assign each element an index
    # n : number of elements
    # i : index of an element in a group
    # ngrp : number of elements in a group
    # ngrps: number of groups
    # n*i/ngrp +/- log(ngrps)+1
    # sort elements by there index

    # determine the number of groups, and the number of elements in that group

    grpcounts = {}
    grpoffset = {}
    temp = []

    fisher_yates(data)

    for elem in data:
        k = group_mapping(elem)
        if k not in grpcounts:
            grpcounts[k] = 1
        else:
            grpcounts[k] += 1
        temp.append(ShuffleElement(elem,grpcounts[k] - 1))

    # generate an initial offset for each group
    for grp in grpcounts.keys():
        t = (math.log(len(grpcounts),2)+1)
        # if there are more of a group, should i weight then lower?
        offset = random.random() * t - t
        grpoffset[grp] = offset

    # calculate a score for each element
    for i,elem in enumerate(temp):
        k = group_mapping(elem.ref)
        ngrp = grpcounts[k]
        ngrps = len(grpcounts)
        # TODO: the random offset added here should
        # be equal to half the width to the next element of this grp
        # int(N/ngrp/2)
        h = int(len(temp) / ngrp / 2)
        #offset = (random.random() - .5) + grpoffset[k]
        offset = random.random()*h - h/2 + grpoffset[k]
        elem.score = len(temp)*elem.index/float(ngrp) + offset

    temp = sorted(temp,key=lambda x:x.score)

    return [x.ref for x in temp]


def main():

    colors = "rgby"
    counts = [3,3,3,3]

    data = sum([ [c,]*n for c,n in zip(colors,counts) ],[])
    print(data)
    data = shuffle(data)
    print([x for x in data])

if __name__ == '__main__':
    main()