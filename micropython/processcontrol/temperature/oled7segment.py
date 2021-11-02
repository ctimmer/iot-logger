##################################################################
# oled7segment.py - Display simulated 7 segment digits/characters
#   This module allows you to customize th size of 7 segment digits
#   to fit any OLED area.
#
# Inputs (__init__ or set_parameters with default values):
#   pixel_display - No default, pixel display function from gfx
#   digit_size="S" - Up to 4 lines, "M" up to 2 lines, "L" 1 line (128x64)
#   v_segment_length=4 - Vertical segment lingth in pixels
#   h_segment_length=4 - Horizontal segment lingth in pixels
#   segment_width=2 - Segment (all) width
#   spacing=1 - pixels between/below segments
#   color=1 - 1 for monochrome
# Methods:
#   display_string (xpos, ypos, chars)
#     Displays chars at x position, y position
#   display_character (xpos, ypos, char) # Called by display_string
#     Displays char at x position, y position
#     Only 1 character allowed
#     Unknown characters are displayed as '?'
#
# Typical imports:
# from machine import Pin, SoftI2C
# import ssd1306
# import gfx
#
#################################################################

class OLED7Segment :
    def __init__ (self,
                    pixel_display ,
                    digit_size="S" ,
                    v_segment_length=4 ,
                    h_segment_length=4 ,
                    segment_width=2,
                    spacing=1 ,
                    bold=False ,
                    color=1) :
        self.set_parameters  (pixel_display=pixel_display ,
                              digit_size="S" ,
                              v_segment_length=v_segment_length ,
                              h_segment_length=h_segment_length ,
                              segment_width=segment_width ,
                              spacing=spacing ,
                              bold=bold ,
                              color=color)
        self.segment_chars = {
            "0" : {
                "handler" : self.zero_seg
                } ,
            "1" : {
                "handler" : self.one_seg
                } ,
            "2" : {
                "handler" : self.two_seg
                } ,
            "3" : {
                "handler" : self.three_seg
                } ,
            "4" : {
                "handler" : self.four_seg
                } ,
            "5" : {
                "handler" : self.five_seg
                } ,
            "6" : {
                "handler" : self.six_seg
                } ,
            "7" : {
                "handler" : self.seven_seg
                } ,
            "8" : {
                "handler" : self.eight_seg
                } ,
            "9" : {
                "handler" : self.nine_seg
                } ,
            "." : {
                "handler" : self.decimal_point_seg
                } ,
            "+" : {
                "handler" : self.plus_seg
                } ,
            "-" : {
                "handler" : self.minus_seg
                } ,
            ":" : {
                "handler" : self.colon_seg
                } ,
            "?" : {
                "handler" : self.question_seg
                } ,
            " " : {
                "handler" : self.space_seg
                } ,
            "A" : {
                "handler" : self.a_seg
                } ,
            "a" : {
                "handler" : self.a_seg
                } ,
            "B" : {
                "handler" : self.b_seg
                } ,
            "b" : {
                "handler" : self.b_seg
                } ,
            "C" : {
                "handler" : self.c_seg
                } ,
            "c" : {
                "handler" : self.c_seg
                } ,
            "D" : {
                "handler" : self.d_seg
                } ,
            "d" : {
                "handler" : self.d_seg
                } ,
            "E" : {
                "handler" : self.e_seg
                } ,
            "e" : {
                "handler" : self.e_seg
                } ,
            "F" : {
                "handler" : self.f_seg
                } ,
            "f" : {
                "handlhttp://localhost:5010/er" : self.f_seg
                }
            }
    
    def set_parameters (self ,
                        pixel_display=None ,
                        digit_size=None ,
                        v_segment_length=None ,
                        h_segment_length=None ,
                        segment_width=None ,
                        spacing=None ,
                        bold=None ,
                        color=None) :
        if not pixel_display == None :
            self.pixel_display = pixel_display
        if not digit_size == None :
            if digit_size == "S" :        # Small digits
                self.v_segment_len = 4
                self.h_segment_len = 4
                self.segment_wid = 2
            elif digit_size == "M" :      # Medium digits
                self.v_segment_len = 11
                self.h_segment_len = 11
                self.segment_wid = 3
            elif digit_size == "L" :      # Large digits
                self.v_segment_len = 22
                self.h_segment_len = 22
                self.segment_wid = 6
                self.spacing = 2
        # These settings will override 'digit_size'
        if not v_segment_length == None :  # vertical segment lengths
            self.v_segment_len = v_segment_length
        if not h_segment_length == None :  # horizontal segment lengths
            self.h_segment_len = h_segment_length
        if not segment_width == None :     # all segment widths
            self.segment_wid = segment_width
        if not spacing == None :           # spacing between digits
            self.spacing = spacing
        if not bold == None :              # Bold (T/F)
            self.bold = bold
        if not color == None :             # Color
            self.color = color
        #---- char/digit width
        self.char_wid = self.segment_wid \
                        + self.h_segment_len \
                        + self.segment_wid \
                        + self.spacing
        #---- char/digit height
        self.char_height = self.segment_wid \
                        + self.v_segment_len \
                        + self.segment_wid \
                        + self.v_segment_len \
                        + self.segment_wid \
                        + self.spacing
        #---- sign segment length
        self.sign_seg_len = max (self.v_segment_len,
                                self.h_segment_len)
        if self.sign_seg_len < 5 :
            self.sign_seg_len = 5
        elif self.sign_seg_len % 2 != 0 :
            self.sign_seg_len -= 1

# end set_parameters #

    #----------------------------------------------------------------------------------
    # Segment identifiers:
    # bold=False    bold=True
    #  xxTOPxx      xxxTOPxxx
    # x       x     x       x
    # U       U     U       U
    # L       R     L       R
    # x       x     x       x
    #  xxMIDxx      xxxMIDxxx
    # x       x     x       x
    # L       L     L       L
    # L       R     L       R
    # x       x     x       x
    #  xxBOTxx      xxxBOTxxx
    #
    #------------------------------
    def TOP_seg (self, xpos_in, ypos_in, color_in=None) :
        if self.bold :
            xpos = xpos_in
            xlen = self.segment_wid + self.h_segment_len + self.segment_wid
        else :
            xpos = xpos_in + self.segment_wid
            xlen = self.h_segment_len
        ypos = ypos_in
        if not color_in == None :
            seg_color = color_in
        else :
            seg_color = self.color
        self.pixel_display.fill_rect (xpos ,
                                        ypos ,
                                        xlen ,
                                        self.segment_wid ,
                                        seg_color)
    def UL_seg (self, xpos_in, ypos_in, color_in=None) :
        xpos = xpos_in
        if self.bold :
            ypos = ypos_in
            ylen = self.segment_wid + self.v_segment_len + self.segment_wid
        else :
            ypos = ypos_in + self.segment_wid
            ylen = self.v_segment_len
        if not color_in == None :
            seg_color = color_in
        else :
            seg_color = self.color
        self.pixel_display.fill_rect (xpos ,
                                        ypos ,
                                        self.segment_wid ,
                                        ylen ,
                                        seg_color)
    def UR_seg (self, xpos_in, ypos_in, color_in=None) :
        xpos = xpos_in + self.segment_wid + self.h_segment_len
        if self.bold :
            ypos = ypos_in
            ylen = self.segment_wid + self.v_segment_len + self.segment_wid
        else :
            ypos = ypos_in + self.segment_wid
            ylen = self.v_segment_len
        if not color_in == None :
            seg_color = color_in
        else :
            seg_color = self.color
        self.pixel_display.fill_rect (xpos ,
                                        ypos ,
                                        self.segment_wid ,
                                        ylen ,
                                        seg_color)
    #-----------------------------------
    def MID_seg (self, xpos_in, ypos_in, color_in=None) :
        if self.bold :
            xpos = xpos_in
            xlen = self.segment_wid + self.h_segment_len + self.segment_wid
        else :
            xpos = xpos_in + self.segment_wid
            xlen = self.h_segment_len
        ypos = ypos_in + self.segment_wid + self.v_segment_len
        if not color_in == None :
            seg_color = color_in
        else :
            seg_color = self.color
        self.pixel_display.fill_rect (xpos ,
                                        ypos ,
                                        xlen ,
                                        self.segment_wid ,
                                        seg_color)
    def LL_seg (self, xpos_in, ypos_in, color_in=None) :
        xpos = xpos_in
        if self.bold :
            ypos = ypos_in + self.segment_wid + self.v_segment_len
            ylen = self.segment_wid + self.v_segment_len + self.segment_wid
        else :
            ypos = ypos_in + self.segment_wid + self.v_segment_len + self.segment_wid
            ylen = self.v_segment_len
        if not color_in == None :
            seg_color = color_in
        else :
            seg_color = self.color
        self.pixel_display.fill_rect (xpos ,
                                        ypos ,
                                        self.segment_wid ,
                                        ylen ,
                                        seg_color)
    def LR_seg (self, xpos_in, ypos_in, color_in=None) :
        xpos = xpos_in + self.segment_wid + self.h_segment_len
        if self.bold :
            ypos = ypos_in + self.segment_wid + self.v_segment_len
            ylen = self.segment_wid + self.v_segment_len + self.segment_wid
        else :
            ypos = ypos_in + self.segment_wid + self.v_segment_len + self.segment_wid
            ylen = self.v_segment_len
        if not color_in == None :
            seg_color = color_in
        else :
            seg_color = self.color
        self.pixel_display.fill_rect (xpos ,
                                        ypos ,
                                        self.segment_wid ,
                                        ylen ,
                                        seg_color)
    #-----------------------------------
    def BOT_seg (self, xpos_in, ypos_in, color_in=None) :
        if self.bold :
            xpos = xpos_in
            xlen = self.segment_wid + self.h_segment_len + self.segment_wid
        else :
            xpos = xpos_in + self.segment_wid
            xlen = self.h_segment_len
        ypos = ypos_in \
                + self.segment_wid \
                + self.v_segment_len \
                + self.segment_wid \
                + self.v_segment_len
        if not color_in == None :
            seg_color = color_in
        else :
            seg_color = self.color
        self.pixel_display.fill_rect (xpos ,
                                        ypos ,
                                        xlen ,
                                        self.segment_wid ,
                                        seg_color)
    #---------------------------------------------------------------------------------
    def nine_seg (self, xpos, ypos) :
        self.TOP_seg (xpos, ypos)
        self.UL_seg (xpos, ypos)
        self.UR_seg (xpos, ypos)
        self.MID_seg (xpos, ypos)
        #self.LL_seg (xpos, ypos)
        self.LR_seg (xpos, ypos)
        self.BOT_seg (xpos, ypos)
        return self.char_wid
    #---------------------------------------------------------------------------------
    def eight_seg (self, xpos, ypos) :
        self.TOP_seg (xpos, ypos)
        self.UL_seg (xpos, ypos)
        self.UR_seg (xpos, ypos)
        self.MID_seg (xpos, ypos)
        self.LL_seg (xpos, ypos)
        self.LR_seg (xpos, ypos)
        self.BOT_seg (xpos, ypos)
        return self.char_wid
    #---------------------------------------------------------------------------------
    def seven_seg (self, xpos, ypos) :
        self.TOP_seg (xpos, ypos)
        #self.UL_seg (xpos, ypos)
        self.UR_seg (xpos, ypos)
        #self.MID_seg (xpos, ypos)
        #self.LL_seg (xpos, ypos)
        self.LR_seg (xpos, ypos)
        #self.BOT_seg (xpos, ypos)
        return self.char_wid
    #---------------------------------------------------------------------------------
    def six_seg (self, xpos, ypos) :
        self.TOP_seg (xpos, ypos)
        self.UL_seg (xpos, ypos)
        #self.UR_seg (xpos, ypos)
        self.MID_seg (xpos, ypos)
        self.LL_seg (xpos, ypos)
        self.LR_seg (xpos, ypos)
        self.BOT_seg (xpos, ypos)
        return self.char_wid
    #---------------------------------------------------------------------------------
    def five_seg (self, xpos, ypos) :
        self.TOP_seg (xpos, ypos)
        self.UL_seg (xpos, ypos)
        #self.UR_seg (xpos, ypos)
        self.MID_seg (xpos, ypos)
        #self.LL_seg (xpos, ypos)
        self.LR_seg (xpos, ypos)
        self.BOT_seg (xpos, ypos)
        return self.char_wid
    #---------------------------------------------------------------------------------
    def four_seg (self, xpos, ypos) :
        #self.TOP_seg (xpos, ypos)
        self.UL_seg (xpos, ypos)
        self.UR_seg (xpos, ypos)
        self.MID_seg (xpos, ypos)
        #self.LL_seg (xpos, ypos)
        self.LR_seg (xpos, ypos)
        #self.BOT_seg (xpos, ypos)
        return self.char_wid
    #---------------------------------------------------------------------------------
    def three_seg (self, xpos, ypos) :
        self.TOP_seg (xpos, ypos)
        #self.UL_seg (xpos, ypos)
        self.UR_seg (xpos, ypos)
        self.MID_seg (xpos, ypos)
        #self.LL_seg (xpos, ypos)
        self.LR_seg (xpos, ypos)
        self.BOT_seg (xpos, ypos)
        return self.char_wid
    #---------------------------------------------------------------------------------
    def two_seg (self, xpos, ypos) :
        self.TOP_seg (xpos, ypos)
        #self.UL_seg (xpos, ypos)
        self.UR_seg (xpos, ypos)
        self.MID_seg (xpos, ypos)
        self.LL_seg (xpos, ypos)
        #self.LR_seg (xpos, ypos)
        self.BOT_seg (xpos, ypos)
        return self.char_wid
    #-----------------------------------------------
    def one_seg (self, xpos, ypos) :
        #self.TOP_seg (xpos, ypos)
        #self.UL_seg (xpos, ypos)
        self.UR_seg (xpos, ypos)
        #self.MID_seg (xpos, ypos)
        #self.LL_seg (xpos, ypos)
        self.LR_seg (xpos, ypos)
        #self.BOT_seg (xpos, ypos)
        return self.char_wid
    #---------------------------------------------------------------------------------
    def zero_seg (self, xpos, ypos) :
        self.TOP_seg (xpos, ypos)
        self.UL_seg (xpos, ypos)
        self.UR_seg (xpos, ypos)
        #self.MID_seg (xpos,ypos)
        self.LL_seg (xpos, ypos)
        self.LR_seg (xpos, ypos)
        self.BOT_seg (xpos, ypos)
        return self.char_wid
    #---------------------------------------------------------------------------------
    def a_seg (self, xpos, ypos) :
        self.TOP_seg (xpos, ypos)
        self.UL_seg (xpos, ypos)
        self.UR_seg (xpos, ypos)
        self.MID_seg (xpos, ypos)
        self.LL_seg (xpos, ypos)
        self.LR_seg (xpos, ypos)
        #self.BOT_seg (xpos, ypos)
        return self.char_wid
    #---------------------------------------------------------------------------------
    def b_seg (self, xpos, ypos) :
        #self.TOP_seg (xpos, ypos)
        self.UL_seg (xpos, ypos)
        #self.UR_seg (xpos, ypos)
        self.MID_seg (xpos, ypos)
        self.LL_seg (xpos, ypos)
        self.LR_seg (xpos, ypos)
        self.BOT_seg (xpos, ypos)
        return self.char_wid
    #---------------------------------------------------------------------------------
    def c_seg (self, xpos, ypos) :
        self.TOP_seg (xpos, ypos)
        self.UL_seg (xpos, ypos)
        #self.UR_seg (xpos, ypos)
        #self.MID_seg (xpos,ypos)
        self.LL_seg (xpos, ypos)
        #self.LR_seg (xpos, ypos)
        self.BOT_seg (xpos, ypos)
        return self.char_wid
    #---------------------------------------------------------------------------------
    def d_seg (self, xpos, ypos) :
        #self.TOP_seg (xpos, ypos)
        #self.UL_seg (xpos, ypos)
        self.UR_seg (xpos, ypos)
        self.MID_seg (xpos, ypos)
        self.LL_seg (xpos, ypos)
        self.LR_seg (xpos, ypos)
        self.BOT_seg (xpos, ypos)
        return self.char_wid
    #---------------------------------------------------------------------------------
    def e_seg (self, xpos, ypos) :
        self.TOP_seg (xpos, ypos)
        self.UL_seg (xpos, ypos)
        #self.UR_seg (xpos, ypos)
        self.MID_seg (xpos,ypos)
        self.LL_seg (xpos, ypos)
        #self.LR_seg (xpos, ypos)
        self.BOT_seg (xpos, ypos)
        return self.char_wid
    #---------------------------------------------------------------------------------
    def f_seg (self, xpos, ypos) :
        self.TOP_seg (xpos, ypos)
        self.UL_seg (xpos, ypos)
        #self.UR_seg (xpos, ypos)
        self.MID_seg (xpos,ypos)
        self.LL_seg (xpos, ypos)
        #self.LR_seg (xpos, ypos)
        #self.BOT_seg (xpos, ypos)
        return self.char_wid
    #---------------------------------------------------------------------------------
    def question_seg (self, xpos, ypos) :
        self.TOP_seg (xpos, ypos)
        #self.UL_seg (xpos, ypos)
        self.UR_seg (xpos, ypos)
        self.MID_seg (xpos,ypos)
        self.LL_seg (xpos, ypos)
        #self.LR_seg (xpos, ypos)
        #self.BOT_seg (xpos, ypos)
        return self.char_wid

    #---------------------------------------------------------------------------------
    def decimal_point_seg (self, xpos, ypos) :
        self.pixel_display.fill_rect (xpos ,
                            ypos + self.v_segment_len
                                    + self.v_segment_len
                                    + self.segment_wid
                                    + self.segment_wid ,
                            self.segment_wid ,
                            self.segment_wid ,
                            self.color)
        return self.segment_wid + self.spacing
    #---------------------------------------------------------------------------------
    def colon_seg (self, xpos, ypos) :
        self.decimal_point_seg (xpos, ypos)
        self.pixel_display.fill_rect (xpos ,
                            ypos + self.v_segment_len + self.segment_wid ,
                            self.segment_wid ,
                            self.segment_wid ,
                            self.color)
        return self.segment_wid + self.spacing
    #---------------------------------------------------------------------------------
    def minus_seg (self, xpos, ypos) :
        self.pixel_display.fill_rect (xpos , # + self.segment_wid,
                                        ypos + self.v_segment_len + self.segment_wid ,
                                        self.sign_seg_len ,
                                        self.segment_wid ,
                                        self.color)
        return self.sign_seg_len + self.spacing
    #---------------------------------------------------------------------------------
    def plus_seg (self, xpos, ypos) :
        self.minus_seg (xpos, ypos)
        vxpos = xpos + int (self.sign_seg_len / 2)
        vxpos -= int (self.segment_wid / 2)
        vypos = ypos + self.v_segment_len + self.segment_wid - int (self.sign_seg_len / 2) + 1
        self.pixel_display.fill_rect (vxpos ,
                                        vypos ,
                                        self.segment_wid ,
                                        self.sign_seg_len ,
                                        self.color)
        return self.sign_seg_len + self.spacing
    #---------------------------------------------------------------------------------
    def space_seg (self, xpos, ypos) :
        return self.char_wid

    #---------------------------------------------------------------------------------
    def get_character_width (self) :
        return self.char_wid
    def get_character_height (self) :
        return self.char_height
    #-----------------------------
    def display_character (self, xpos, ypos, char) :
        if char in self.segment_chars :
            return self.segment_chars[char]["handler"] (xpos, ypos)
        else :
            return self.question_seg (xpos, ypos)
    def display_string (self, xpos, ypos, chars) :
        x_display = xpos
        for char in chars :
            x_display += self.display_character (x_display, ypos, char)
        return x_display

# end Simple7Segment #

