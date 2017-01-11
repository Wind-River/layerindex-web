#!/usr/bin/env python

# Test script
#
# Copyright (C) 2012 Intel Corporation
# Author: Paul Eggleton <paul.eggleton@linux.intel.com>

import sys
import os.path
import logging
import subprocess
from datetime import datetime
import fnmatch
from distutils.version import LooseVersion


logger = None


def sanitise_path(inpath):
    outpath = ""
    for c in inpath:
        if c in '/ .=+?:':
            outpath += "_"
        else:
            outpath += c
    return outpath

def main():
    # Get access to our Django model
    newpath = os.path.abspath(os.path.dirname(os.path.abspath(sys.argv[0])) + '/..')
    sys.path.append(newpath)
    os.environ['DJANGO_SETTINGS_MODULE'] = 'settings'

    from django.core.management import setup_environ
    from django.conf import settings
    from layerindex.models import LayerItem, Recipe
    from django.db import transaction
    import settings

    setup_environ(settings)

    # Set path to bitbake lib dir
    basepath = os.path.abspath(sys.argv[1])
    bitbakedir_env = os.environ.get('BITBAKEDIR', '')
    if bitbakedir_env and os.path.exists(bitbakedir_env + '/lib/bb'):
        bitbakepath = bitbakedir_env
    elif os.path.exists(basepath + '/bitbake/lib/bb'):
        bitbakepath = basepath + '/bitbake'
    elif os.path.exists(basepath + '/../bitbake/lib/bb'):
        bitbakepath = os.path.abspath(basepath + '/../bitbake')
    else:
        # look for bitbake/bin dir in PATH
        bitbakepath = None
        for pth in os.environ['PATH'].split(':'):
            if os.path.exists(os.path.join(pth, '../lib/bb')):
                bitbakepath = os.path.abspath(os.path.join(pth, '..'))
                break
        if not bitbakepath:
            print("Unable to find bitbake by searching BITBAKEDIR, specified path '%s' or its parent, or PATH" % basepath)
            sys.exit(1)

    # Skip sanity checks
    os.environ['BB_ENV_EXTRAWHITE'] = 'DISABLE_SANITY_CHECKS'
    os.environ['DISABLE_SANITY_CHECKS'] = '1'

    sys.path.extend([bitbakepath + '/lib'])
    import bb.tinfoil
    tinfoil = bb.tinfoil.Tinfoil()
    tinfoil.prepare(config_only = True)

    logger = logging.getLogger('BitBake')

    fetchdir = settings.LAYER_FETCH_DIR
    if not fetchdir:
        logger.error("Please set LAYER_FETCH_DIR in settings.py")
        sys.exit(1)

    for layer in LayerItem.objects.filter(status='P'):
        urldir = sanitise_path(layer.vcs_url)
        repodir = os.path.join(fetchdir, urldir)
        layerrecipes = Recipe.objects.filter(layer=layer)
        for recipe in layerrecipes:
            fullpath = str(os.path.join(repodir, layer.vcs_subdir, recipe.filepath, recipe.filename))
            print(fullpath)
            try:
                envdata = bb.cache.Cache.loadDataFull(fullpath, [], tinfoil.config_data)
                print("DESCRIPTION = \"%s\"" % envdata.getVar("DESCRIPTION", True))
            except Exception as e:
                logger.info("Unable to read %s: %s", fullpath, str(e))

    tinfoil.shutdown()
    sys.exit(0)


if __name__ == "__main__":
    main()
