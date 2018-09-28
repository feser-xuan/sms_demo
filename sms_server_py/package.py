#! /usr/bin/env python
# -----------------------------------------------------------------------------
# Copyright (c) 2013, PyInstaller Development Team.
#
# Distributed under the terms of the GNU General Public License with exception
# for distributing bootloader.
#
# The full license is in the file COPYING.txt, distributed with this software.
# -----------------------------------------------------------------------------
"""
Main command-line interface to PyInstaller.
"""
# from  PyInstaller import  *
import os
import sys
import ConfigParser

if __name__ == '__main__':
    from PyInstaller.__main__ import run

    # opts=['src/mainwindow.py','-F','-w','--icon=favicon.ico' ,'-p src']
    os.system('rm -rf dist/')
    opts = [
        # '-p', 'D:/Python27/Lib/',
        # '-p', 'D:/Python27/Lib/site-packages/PyQt4',
        # '-p', 'D:/Python27/Lib/site-packages',
        # '-p','D:/Python27/Lib/site-packages/win32com',
        # '-p','D:/Python27/Lib/site-packages/win32',
        # '-p','D:/Python27/Lib/site-packages/pyttsx',
        # '--hidden-import','os',
        # '--hidden-import','os.path',
        # '--hidden-import','path',
        # '--hidden-import','traceback',
        # '--additional-hooks-dir','D:/Python27/Lib/site-packages/PyInstaller/hooks',
        '-D',
        '-c',
        '-y',
        '--add-data','conf/config.ini;conf',
        # '--add-data','logs;logs',
        # '--add-data','src/img/*.png;img',
        # '--add-data','src/img/*.jpg;img',
        '--uac-admin',
        '--distpath','dist',
        '--clean',
        'sms_server.py']
    run(opts)
    os.chdir('dist/sms_server/')
    os.makedirs('logs')