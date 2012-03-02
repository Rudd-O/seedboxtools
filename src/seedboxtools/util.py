#!/usr/bin/env python

from subprocess import Popen,PIPE,STDOUT,call

def shell_quote(shellarg):
        return"'%s'"%shellarg.replace("'",r"'\''")

def getstdout(cmdline):
        p = Popen(cmdline,stdout=PIPE)
        output = p.communicate()[0]
        if p.returncode != 0: raise Exception, "Command %s return code %s"%(cmdline,p.returncode)
        return output

def getstdoutstderr(cmdline,inp=None): # return stoud and stderr in a single string object
        p = Popen(cmdline,stdin=PIPE,stdout=PIPE,stderr=STDOUT)
        output = p.communicate(inp)[0]
        if p.returncode != 0: raise Exception, "Command %s return code %s"%(cmdline,p.returncode)
        return output

def passthru(cmdline): return call(cmdline) # return status code, pass the outputs thru
