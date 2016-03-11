
# #########################################################
# #########################################################
# File: Qt_CustomStyle
#
# Description:
#       This File provides 1 main method:
#  style_set_custom_theme - for loading a custom style and setting css of a Qt Application object
#
# What is a style?:
#   Qt allows for custom styles by using cascading style sheets (css)
#   This module requires a specific file structure, described below to work
#   But normal CSS can be used to describe all of the PyQt widgets.
#   A special syntax is used, where variables can be declared in a dictionary (*.dict)
#   These values can then be accessed by using %var_name% in a CSS file.
#   These variables can be used to replace entire lines of  css, or entire classes
#
# style_directory is the path to a folder which contains two folders
#    /<style_directory>/images/         default image location for images missing in a style's image folder
#    /<style_directory>/style/          contains folders corresponding to different styles
#    this is the layout used in ConsolePlayer
#
# A Style is located in:
#    /<style_directory>/style/<style_name>/
#   it is required that a Main.css file is found here
#
# A Style contains one sub folder (optional):
#    /<style_directory>/style/<style_name>/images/      primary location to find images for the style.
#
# example dictionary: theme.dict
#   font_size           => 12
#   font_family         => Verdana
#
# example of a css file: Main.css
#
#   * {
#       font-family: "%font_family%";
#       font-style:normal;
#       font-size:%font_size%px;
#   }
#
#   QPlainTextEdit {
#       font-family: "Lucida Console";
#       font-style:normal;
#       font-size:%font_size%px;
#   }
#
# the above to files will set the font for all Qt widgets to Verdana
# and then Plain Text Edit will use Lucida console. All fonts will be 12 point.
#
# #########################################################
import os,sys

from SystemPathMethods import *

from PyQt5.QtCore import *
from PyQt5.QtWidgets import *
from PyQt5.QtGui import *


class StyleError(Exception):
    pass

# ######################################################
# Style Theme CSS
# ######################################################
current_style = None


def style_set_custom_theme(style_directory,style_name):
    #loadUserDict=False
    theme_path = os.path.join( style_directory,style_name);

    if not os.path.exists(theme_path):
        raise StyleError(theme_path)

    theme_dict = os.path.join(theme_path,"theme.dict")
    dict_vars = style_read_dictionary(theme_dict,{})
    # when loadUserDict is set to true update the main dictionary with user defined values
    #if loadUserDict:
    #    dict_vars = style_read_dictionary(fpath+"user.dict",dict_vars)

    dict_vars["IMAGE"]  = os.path.join( style_directory,style_name,"img",""); # ensure final slash
    dict_vars["STYLE"]  = os.path.join( style_directory,style_name,"");

    # URLS are funny in that they require foward slashes, even on windows
    dict_vars["IMAGE"] = dict_vars["IMAGE"].replace("\\","/");
    dict_vars["STYLE"] = dict_vars["STYLE"].replace("\\","/");

    R = os.listdir(theme_path)

    css = ""

    # load the main css file first, if one exists

    if "Main.css" in R:
        css += read_css_file(dict_vars, theme_path,"Main")
        R.remove("Main.css")
    # load all remaining css files
    for file in R:
        if fileGetExt(file) == "css":
            fname = fileGetName(file)
            if fname[:1] != 'x':
                css += read_css_file(dict_vars, theme_path,fname)

    global current_style
    current_style = css_to_qt_color_dict(dict_vars)
    return css, dict_vars

def clearStyle():
    global current_style
    current_style = None

def currentStyle():
    return current_style

def read_css_file(dict_vars,fpath,name):
    """
        reads in a css file into a string buffer
        comments ( /* ... */ ) are removed, as well
        as empty lines
    """
    fname = name + ".css"

    css = ""
    l = " "

    rf = open(os.path.join(fpath,fname),"r")
    lc = 0
    while len(l) != 0:
        l  = rf.readline()
        e = l.strip()
        # allow for comments, ignore empty lines
        if len(e) > 0: # not empty
            if e[:2] != "/*": # not a comment
                # 3/2016: support for images per theme is disabled currently
                for key in dict_vars: # replace all %key% in the text with value
                    e = e.replace("%%%s%%"%key,dict_vars[key])
                lc += 1
                css += e+"\n"
    rf.close()

    return css

def css_to_qt_color_dict(cdict):
    qdct = cdict.copy()
    for key in ["theme_p_light", "theme_p_mid", "theme_p_dark", "theme_p_vdark",
                "theme_s_light", "theme_s_mid", "theme_s_dark", "theme_s_vdark",
                "theme_bg_color",
                "theme_very_light",
                "theme_neutral",
                "theme_very_dark",
                "text_color",
                "text_light",
                "text_dark",
                "text_important1",
                "text_important2",
                "color_highlight",
                "color_highlightOOF",
                "color_special1",
                "color_special2",
                "color_special3",
                "color_invalid" ]:
        if key in cdict:
            qdct[key] = css_to_qt_color(cdict[key])
    return qdct

def setApplicationPallete(app,dict_vars):
    """
    app : QApplication.instance()
    """
    p = app.palette();

    CG   = [QPalette.Disabled,QPalette.Active,QPalette.Inactive]
    c1   = css_to_qt_color( dict_vars["theme_p_light"] )
    c2   = css_to_qt_color( dict_vars["theme_p_mid"] )
    c3   = css_to_qt_color( dict_vars["theme_p_dark"] )
    c4   = css_to_qt_color( dict_vars["theme_p_vdark"] )
    cbg  = css_to_qt_color( dict_vars["theme_bg_color"] )
    t1   = css_to_qt_color( dict_vars["text_color"] )

    c2a = color_avg_rgb(c1,c2)
    c2b = color_avg_rgb(c2,c3)

    for cg in CG:
        p.setColor( cg, QPalette.Light    , c1   )
        p.setColor( cg, QPalette.Midlight , c2a  )
        p.setColor( cg, QPalette.Button   , c2   )
        p.setColor( cg, QPalette.Mid      , c2b  )
        p.setColor( cg, QPalette.Dark     , c3   )
        p.setColor( cg, QPalette.Shadow   , c4   )
        p.setColor( cg, QPalette.Window   , cbg  )
        p.setColor( cg, QPalette.Text     , t1   )

    app.setPalette(p);

    return p

def css_to_qt_color(string):
    #TODO this function looks un-neccessary
    hex = {'0':0, '1':1, '2':2, '3':3, '4':4,
           '5':5, '6':6, '7':7, '8':8, '9':9,
           'A':10, 'B':11,'C':12, 'D':13, 'E':14, 'F':15,
           'a':10, 'b':11,'c':12, 'd':13, 'e':14, 'f':15 }
    hex_template = "#RRGGBB"
    r=0;
    g=0;
    b=0;
    a=1.0;
    if len(string) == len(hex_template):
        r = hex[string[1]]*16 + hex[string[2]]
        g = hex[string[3]]*16 + hex[string[4]]
        b = hex[string[5]]*16 + hex[string[6]]
    elif string[:4] == 'rgba':   #rgba(YYX,YYX,YYX,A)
        # for css alpha is in range 0 to 1.
        (i,j,k,a) = string[5:-1].split(',')
        r = int(i)
        g = int(j)
        b = int(k)
        a = float(a)
    elif string[:3] == 'rgb':   #rgb(YYX,YYX,YYX)
        (i,j,k) = string[4:-1].split(',')
        r = int(i)
        g = int(j)
        b = int(k)
    return QColor(r,g,b,int(255*a))

def color_avg_rgb(c1,c2):
    """ return a color midpoint between two colors """
    # TODO: THIS IS WRONG AND YOU SHOULD FEEL BAD
    # CONVERT TO ANOTHER COLOR SPACE, HSL/HSV
    r = (c1.red()+c2.red())/2
    g = (c1.green()+c2.green())/2
    b = (c1.blue()+c2.blue())/2
    a = (c1.alpha()+c2.alpha())/2
    return QColor(r,g,b,a)

# ######################################################
# Dictionary Files
# ######################################################

def style_read_dictionary(fpath,dict_vars=None):
    """
       reads a css theme color dictionary
       a color dictionary stores color information for the theme

       a dictionary of variables can be passed to this function with initial values
       that will be overwritten if they exist in the file
       use this when there are a set of defualt values required, then call this function
       to set any values that are from a previous session.
    """

    if dict_vars == None:
        dict_vars = {}

    if os.path.exists(fpath):
        l = " "

        rf = open(fpath,"r")

        while len(l) != 0:
            l  = rf.readline()
            e = l.strip()
            try:
                if len(e) > 0: # not empty
                    if e[0] != "#": # not a comment

                        # allow continuation to a new line by having the last character in a line
                        # a back slash '\'
                        while e[-1] == '\\':
                            l = rf.readline().strip();
                            e = e[:-1]+" "+l

                        (k,v) = e.split('=>')
                        k = k.strip()
                        v = v.strip()
                        # replace variables that have already been defined in the new variables
                        # as they are read. this allows among other features, the ability to define
                        # one variable use it to expand into others, then redefine it to expand into other
                        # variables. , also the construct, a=red; a=%a%,%a%,%a%;
                        #   a now equals "red,red,red"
                        for key in dict_vars:
                            v = v.replace("%%%s%%"%key,dict_vars[key]);
                        dict_vars[k] = v
            except:
                pass

        rf.close()


    return dict_vars

def style_save_dictionary(style_directory,style_name,fname,dict_vars):
    """
        save a color dictionary
        sort the values for user convenience
        it is not recommeneded to use this for theme.dict
        the default themes may contain values beyond the standard set
    """
    #style_directory = MpGlobal.installPath;

    fpath = os.path.join(style_directory,"style",style_name,fname+".dict")

    k = lambda x: x[0]
    R = sorted(dict_vars.items(), key = k)

    wf = open(fpath,"w")
    for key,value in R :
        wf.write( "%-20s=> %s\n"%(key,value) )
    wf.close()

