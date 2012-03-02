#!/usr/bin/env python

def shell_quote(shellarg):
        return"'%s'"%shellarg.replace("'",r"'\''")
