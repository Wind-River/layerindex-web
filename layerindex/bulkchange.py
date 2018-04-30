#!/usr/bin/env python

# layerindex-web - bulk change implementation
#
# Copyright (C) 2013, 2016, 2018 Intel Corporation
#
# Licensed under the MIT license, see COPYING.MIT for details

import sys
import os
import tempfile
import tarfile
import recipeparse
import utils
import shutil

logger = utils.logger_create('LayerIndexImport')

def generate_patches(tinfoil, fetchdir, changeset, outputdir):
    import oe.recipeutils
    tmpoutdir = tempfile.mkdtemp(dir=outputdir)
    last_layer = None
    patchname = ''
    patches = []
    outfile = None
    try:
        for change in changeset.recipechange_set.all().order_by('recipe__layerbranch'):
            fields = change.changed_fields(mapped=True)
            if fields:
                layerbranch = change.recipe.layerbranch
                layer = layerbranch.layer
                if last_layer != layer:
                    patchname = "%s.patch" % layer.name
                    patches.append(patchname)
                    layerfetchdir = os.path.join(fetchdir, layer.get_fetch_dir())
                    utils.checkout_layer_branch(layerbranch, layerfetchdir)
                    layerdir = os.path.join(layerfetchdir, layerbranch.vcs_subdir)
                    config_data_copy = recipeparse.setup_layer(tinfoil.config_data, fetchdir, layerdir, layer, layerbranch)
                    if outfile:
                        outfile.close()
                    outfile = open(os.path.join(tmpoutdir, patchname), 'w')
                    last_layer = layer
                recipefile = str(os.path.join(layerfetchdir, layerbranch.vcs_subdir, change.recipe.filepath, change.recipe.filename))
                patchdatalist = oe.recipeutils.patch_recipe(config_data_copy, recipefile, fields, patch=True, relpath=layerfetchdir)
                for patchdata in patchdatalist:
                    for line in patchdata:
                        outfile.write(line)
    finally:
        if outfile:
            outfile.close()

    # If we have more than one patch, tar it up, otherwise just return the single patch file
    ret = None
    if len(patches) > 1:
        (tmptarfd, tmptarname) = tempfile.mkstemp('.tar.gz', 'bulkchange-', outputdir)
        tmptarfile = os.fdopen(tmptarfd, "wb")
        tar = tarfile.open(None, "w:gz", tmptarfile)
        for patch in patches:
            patchfn = os.path.join(tmpoutdir, patch)
            tar.add(patchfn, arcname=patch)
        tar.close()
        ret = tmptarname
    elif len(patches) == 1:
        (tmppatchfd, tmppatchname) = tempfile.mkstemp('.patch', 'bulkchange-', outputdir)
        tmppatchfile = os.fdopen(tmppatchfd, "wb")
        with open(os.path.join(tmpoutdir, patches[0]), "rb") as patchfile:
            shutil.copyfileobj(patchfile, tmppatchfile)
        tmppatchfile.close()
        ret = tmppatchname

    shutil.rmtree(tmpoutdir)
    return ret

def get_changeset(pk):
    from layerindex.models import RecipeChangeset
    res = list(RecipeChangeset.objects.filter(pk=pk)[:1])
    if res:
        return res[0]
    return None

def usage():
    print("Usage: bulkchange.py <id> <outputdir>")

def main():
    if '--help' in sys.argv:
        usage()
        sys.exit(0)
    if len(sys.argv) < 3:
        usage()
        sys.exit(1)

    utils.setup_django()
    import settings

    branch = utils.get_branch('master')
    fetchdir = settings.LAYER_FETCH_DIR
    bitbakepath = os.path.join(fetchdir, 'bitbake')

    lockfn = os.path.join(fetchdir, "layerindex.lock")
    lockfile = utils.lock_file(lockfn)
    if not lockfile:
        sys.stderr.write("Layer index lock timeout expired\n")
        sys.exit(1)
    try:
        (tinfoil, tempdir) = recipeparse.init_parser(settings, branch, bitbakepath, True)

        changeset = get_changeset(sys.argv[1])
        if not changeset:
            sys.stderr.write("Unable to find changeset with id %s\n" % sys.argv[1])
            sys.exit(1)

        utils.setup_core_layer_sys_path(settings, branch.name)

        outp = generate_patches(tinfoil, fetchdir, changeset, sys.argv[2])
    finally:
        tinfoil.shutdown()
        utils.unlock_file(lockfile)

    if outp:
        print(outp)
    else:
        sys.stderr.write("No changes to write\n")
        sys.exit(1)

    shutil.rmtree(tempdir)
    sys.exit(0)


if __name__ == "__main__":
    main()
