#! /usr/bin/python3

from os import system
import sys
system(f'disable-puppet "{sys.argv[1]}"')
input('press enter to re-enable puppet')
system('enable-puppet')
