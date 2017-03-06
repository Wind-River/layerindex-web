# Utilities for layerindex-web
#
# Copyright (C) 2013 Intel Corporation
# Author: Paul Eggleton <paul.eggleton@linux.intel.com>
#
# Licensed under the MIT license, see COPYING.MIT for details

import sys
import os
import tempfile
import subprocess
import logging
import time
import fcntl

def get_branch(branchname):
    from layerindex.models import Branch
    res = list(Branch.objects.filter(name=branchname)[:1])
    if res:
        return res[0]
    return None

def get_layer(layername):
    from layerindex.models import LayerItem
    res = list(LayerItem.objects.filter(name=layername)[:1])
    if res:
        return res[0]
    return None

def get_dependency_layer(depname, version_str=None, logger=None):
    from layerindex.models import LayerItem, LayerBranch

    # Get any LayerBranch with a layer that has a name that matches depmod, or
    # a LayerBranch that has the collection name depmod.
    res = list(LayerBranch.objects.filter(layer__name=depname)) + \
          list(LayerBranch.objects.filter(collection=depname))

    # Nothing found, return.
    if not res:
        return None

    # If there is no version constraint, return the first one found.
    if not version_str:
        return res[0].layer

    (operator, dep_version) = version_str.split()
    for layerbranch in res:
        layer_ver = layerbranch.version

        # If there is no version in the found layer, then don't use this layer.
        if not layer_ver:
            continue

        try:
            success = bb.utils.vercmp_string_op(layer_ver, version_str, operator)
        except bb.utils.VersionStringException as vse:
            raise vse

        if success:
            return layerbranch.layer

    return None

def add_dependencies(layerbranch, config_data, logger=None):
    _add_dependency("LAYERDEPENDS", 'dependency', layerbranch, config_data, logger=logger)

def add_recommends(layerbranch, config_data, logger=None):
    _add_dependency("LAYERRECOMMENDS", 'recommends', layerbranch, config_data, logger=logger, required=False)

def _add_dependency(var, name, layerbranch, config_data, logger=None, required=True):
    from layerindex.models import LayerBranch, LayerDependency

    layer_name = layerbranch.layer.name
    var_name = layer_name

    if layerbranch.collection:
        var_name = layerbranch.collection


    dep_list = config_data.getVar("%s_%s" % (var, var_name), True)

    if not dep_list:
        return

    try:
        dep_dict = bb.utils.explode_dep_versions2(dep_list)
    except bb.utils.VersionStringException as vse:
        logger.debug('Error parsing %s_%s for %s\n%s' % (var, var_name, layer_name, str(vse)))
        return

    for dep, ver_list in list(dep_dict.items()):
        ver_str = None
        if ver_list:
            ver_str = ver_list[0]

        try:
            dep_layer = get_dependency_layer(dep, ver_str, logger)
        except bb.utils.VersionStringException as vse:
            if logger:
                logger.error('Error getting %s %s for %s\n%s' %(name, dep. layer_name, str(vse)))
            continue

        # No layer found.
        if not dep_layer:
            if logger:
                logger.error('Cannot resolve %s %s (version %s) for %s' % (name, dep, ver_str, layer_name))
                continue

        # Skip existing entries.
        existing = list(LayerDependency.objects.filter(layerbranch=layerbranch).filter(dependency=dep_layer))
        if existing:
            logger.debug('Skipping %s - already a dependency for %s' % (dep, layer_name))
            continue

        if logger:
            logger.debug('Adding %s %s to %s' % (name, dep_layer.name, layer_name))

        layerdep = LayerDependency()
        layerdep.layerbranch = layerbranch
        layerdep.dependency = dep_layer
        layerdep.required = required
        layerdep.save()

def set_layerbranch_collection_version(layerbranch, config_data, logger=None):
    layerbranch.collection = config_data.getVar('BBFILE_COLLECTIONS', True)
    ver_str = "LAYERVERSION_"
    if layerbranch.collection:
        layerbranch.collection = layerbranch.collection.strip()
        ver_str += layerbranch.collection
        layerbranch.version = config_data.getVar(ver_str, True)

def setup_tinfoil(bitbakepath, enable_tracking):
    sys.path.insert(0, bitbakepath + '/lib')
    import bb.tinfoil
    import bb.cooker
    import bb.data
    try:
        tinfoil = bb.tinfoil.Tinfoil(tracking=enable_tracking)
    except TypeError:
        # old API
        tinfoil = bb.tinfoil.Tinfoil()
        if enable_tracking:
            tinfoil.cooker.enableDataTracking()
    tinfoil.prepare(config_only = True)

    return tinfoil

def checkout_layer_branch(layerbranch, repodir, logger=None):

    branchname = layerbranch.branch.name
    if layerbranch.actual_branch:
        branchname = layerbranch.actual_branch

    out = runcmd("git checkout origin/%s" % branchname, repodir, logger=logger)
    out = runcmd("git clean -f -x", repodir, logger=logger)

def is_layer_valid(layerdir):
    conf_file = os.path.join(layerdir, "conf", "layer.conf")
    if not os.path.isfile(conf_file):
        return False
    return True

def parse_layer_conf(layerdir, data, logger=None):
    conf_file = os.path.join(layerdir, "conf", "layer.conf")

    if not is_layer_valid(layerdir):
        if logger:
            logger.error("Cannot find layer.conf: %s"% conf_file)
        return

    data.setVar('LAYERDIR', str(layerdir))
    if hasattr(bb, "cookerdata"):
        # Newer BitBake
        data = bb.cookerdata.parse_config_file(conf_file, data)
    else:
        # Older BitBake (1.18 and below)
        data = bb.cooker._parse(conf_file, data)
    data.expandVarref('LAYERDIR')

def runcmd(cmd, destdir=None, printerr=True, logger=None):
    """
        execute command, raise CalledProcessError if fail
        return output if succeed
    """
    if logger:
        logger.debug("run cmd '%s' in %s" % (cmd, os.getcwd() if destdir is None else destdir))
    out = tempfile.TemporaryFile()
    try:
        subprocess.check_call(cmd, stdout=out, stderr=out, cwd=destdir, shell=True)
    except subprocess.CalledProcessError as e:
        out.seek(0)
        output = out.read()
        output = output.decode('ascii').strip()
        if printerr:
            if logger:
                logger.error("%s" % output)
            else:
                sys.stderr.write("%s\n" % output)
        e.output = output
        raise e

    out.seek(0)
    output = out.read()
    output = output.decode('ascii').strip()
    if logger:
        logger.debug("output: %s" % output.rstrip() )
    return output

def setup_django():
    import django
    # Get access to our Django model
    newpath = os.path.abspath(os.path.dirname(__file__) + '/..')
    sys.path.append(newpath)
    os.environ['DJANGO_SETTINGS_MODULE'] = 'settings'
    django.setup()

def logger_create(name):
    logger = logging.getLogger(name)
    loggerhandler = logging.StreamHandler()
    loggerhandler.setFormatter(logging.Formatter("%(levelname)s: %(message)s"))
    logger.addHandler(loggerhandler)
    logger.setLevel(logging.INFO)
    return logger

class ListHandler(logging.Handler):
    """Logging handler which accumulates formatted log records in a list, returning the list on demand"""
    def __init__(self):
        self.log = []
        logging.Handler.__init__(self, logging.WARNING)
    def emit(self, record):
        self.log.append('%s\n' % self.format(record))
    def read(self):
        log = self.log
        self.log = []
        return log


def lock_file(fn):
    starttime = time.time()
    while True:
        lock = open(fn, 'w')
        try:
            fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
            return lock
        except IOError:
            lock.close()
            if time.time() - starttime > 30:
                return None

def unlock_file(lock):
    fcntl.flock(lock, fcntl.LOCK_UN)

def chain_unique(*iterables):
    """Chain unique objects in a list of querysets, preserving order"""
    seen = set()
    for element in iterables:
        for item in element:
            k = item.id
            if k not in seen:
                seen.add(k)
                yield item
