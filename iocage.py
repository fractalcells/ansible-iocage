#!/usr/bin/python
# -*- coding: utf-8 -*-

# Copyright 2015, Perceivon Hosting Inc.
# Copyright 2021, Vladimir Botka <vbotka@gmail.com>
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

from __future__ import (absolute_import, division, print_function)
__metaclass__ = type

DOCUMENTATION = r'''
---
module: iocage

short_description: FreeBSD iocage jail handling

description:
    - The M(iocage) module allows several iocage commands to be executed through ansible.
    - document use-cases here
options:
    state:
      description:
          - I(state) of the desired result.
      type: str
      choices: [basejail, thickjail, template, present, cloned, started,
                stopped, restarted, fetched, exec, pkg, exists, absent,
                set, facts]
      default: facts
    name:
      description:
          - I(name) of the jail (former uuid).
      type: str
    pkglist:
      description:
          - Path to a JSON file containing packages to install. Only applicable when creating a jail.
      type: path
    properties:
      description:
          - I(properties) of the jail.
      type: dict
    args:
      description:
          - Additional arguments.
      type: dict
    user:
      description:
        - I(user) who runs the command I(cmd).
      type: str
      default: root
    cmd:
      description:
        - Execute the command I(cmd) inside the specified jail I(name).
      type: str
    clone_from:
      description:
        - Clone the jail I(clone_from) to I(name). Use I(properties) to configure the clone.
      type: str
    release:
      description:
        - Specify which RELEASE to fetch, update, or create a jail.
      type: str
    update:
      description:
        - Update the fetch to the latest patch level.
      type: bool
      default: False
    components:
      description:
        - Uses a local file directory for the root directory instead
          of HTTP to downloads and/or updates releases.
      type: list
      elements: path
      aliases: [files, component]
requirements:
  - py38-iocage >= 1.2_9
notes:
  - Supports C(check_mode).
seealso:
  - name: iocage - A FreeBSD Jail Manager
    description: iocage 1.2 documentation
    link: https://iocage.readthedocs.io/en/latest/
  - name: iocage -- jail manager using ZFS and VNET
    description: FreeBSD System Manager's Manual
    link: https://www.freebsd.org/cgi/man.cgi?query=iocage
author:
  - Johannes Meixner (@xmj)
  - Vladimir Botka (@vbotka)
'''

EXAMPLES = '''
- name: Create jail without cloning
  iocage:
    name: foo
    state: present
    pkglist: /path/to/pkglist.json
    properties:
      ip4_addr: 'lo1|10.1.0.5'
      boot: true
      allow_sysvipc: true
      defaultrouter: '10.1.0.1'

- name: Create template
  iocage:
    name: tplfoo
    state: template
    pkglist: /path/to/pkglist.json
    properties:
      ip4_addr: 'lo1|10.1.0.5'
      boot: true
      allow_sysvipc: true
      defaultrouter: '10.1.0.1'

- name: Create a cloned jail. Creates basejail if needed.
  iocage:
    name: foo
    state: present
    clone_from: tplfoo
    pkglist: /path/to/pkglist.json
    properties:
      ip4_addr: 'lo1|10.1.0.5'
      boot: true
      allow_sysvipc: true
      defaultrouter: '10.1.0.1'

- name: Start existing jail
  iocage:
    name: foo
    state: started

- name: Stop existing jail
  iocage:
    name: foo
    state: stopped

- name: Restart existing jail
  iocage:
    name: foo
    state: restarted

- name: Execute command in running jail
  iocage:
    name: foo
    state: exec
    cmd: service sshd start

- name: Destroy jail
  iocage:
    name: foo
    state: absent
'''

RETURN = r'''
'''

import re

from ansible.module_utils.basic import AnsibleModule
from ansible.module_utils._text import to_bytes


def _command_fail(module, label, cmd, rc, stdout, stderr):
    module.fail_json(msg="{0}\ncmd: '{1}' return: {2}\nstdout: '{3}'\nstderr: '{4}')"
                     .format(label, cmd, rc, stdout, stderr))


def _get_iocage_facts(module, iocage_path, argument="all", name=None):

    opt = dict(jails="list -hl",
               templates="list -hlt",
               releases="list -hr",
               init="list -h")

    if argument == "all":
        # local variable '_init' is assigned to but never used [F841]
        # _init = _get_iocage_facts(module, iocage_path, "init")
        _jails = _get_iocage_facts(module, iocage_path, "jails")
        _templates = _get_iocage_facts(module, iocage_path, "templates")
        _releases = _get_iocage_facts(module, iocage_path, "releases")
        return dict(iocage_jails=_jails,
                    iocage_templates=_templates,
                    iocage_releases=_releases)
    elif argument in opt:
        cmd = "{0} {1}".format(iocage_path, opt[argument])
    else:
        module.fail_json(msg="_get_iocage_facts({0}): argument not understood".format(argument))

    rc, state, err = module.run_command(to_bytes(cmd, errors='surrogate_or_strict'),
                                        errors='surrogate_or_strict')
    if rc != 0 and argument != "init":
        _command_fail(module, "_get_iocage_facts()", cmd, rc, state, err)
    elif argument == "init":
        return {}

    if argument == 'releases':
        _releases = []
        for line in state.split('\n'):
            if re.match(r'\s*\d', line):
                _releases.append(line.strip())
        return _releases

    _jails = {}
    # module.fail_json(msg=state)
    try:
        for line in state.split('\n'):
            if line == "":
                continue
            _jid = line.split('\t')[0]
            if _jid == '---':
                # non-iocage jails: skip all
                break
            elif re.match(r'(\d+|-)', _jid):
                _fragments = line.split('\t')
                if len(_fragments) == 10:
                    (_jid, _name, _boot, _state, _type, _release, _ip4, _ip6, _template, _basejail) = _fragments
                else:
                    (_jid, _name, _boot, _state, _type, _release, _ip4, _ip6, _template) = _fragments
                if _name != "":
                    _properties = _jail_get_properties(module, iocage_path, _name)
                    _jails[_name] = {"jid": _jid, "name": _name, "state": _state, "properties": _properties}
            else:
                module.fail_json(msg="_get_iocage_facts():\nUnreadable stdout line from cmd '{0}': '{1}'"
                                 .format(cmd, line))
    except ValueError:
        module.fail_json(msg="unable to parse {0}".format(state))

    if name is not None:
        if name in _jails:
            return _jails[name]
        else:
            return {}

    return _jails


def _jail_started(module, iocage_path, name):

    cmd = "{0} list -h".format(iocage_path)
    rc, state, err = module.run_command(to_bytes(cmd, errors='surrogate_or_strict'),
                                        errors='surrogate_or_strict')
    if rc != 0:
        _command_fail(module, "jail_started({0})".format(name), cmd, rc, state, err)

    st = None
    for line in state.split('\n'):
        u = line.split('\t')[1]
        if u == name:
            s = line.split('\t')[2]
            if s == 'up':
                st = True
                break
            elif s == 'down':
                st = False
                break
            else:
                module.fail_json(msg="Jail {0} unknown state: {1}".format(name, line))

    return st


def jail_exists(module, iocage_path, argument=None, assume_absent=False):

    cmd = "%s get host_hostuuid %s" % (iocage_path, argument)
    rc, name, err = module.run_command(to_bytes(cmd, errors='surrogate_or_strict'),
                                       errors='surrogate_or_strict')
    if not rc == 0:
        name = ""

    # local variable '_msg' is assigned to but never used [F841]
    # _msg = ""

    if name != "" and assume_absent:
        module.fail_json(msg="Jail {0} exists.".format(argument))

    return name.strip()


def jail_start(module, iocage_path, name):

    cmd = "{0} start {1}".format(iocage_path, name)
    rc = 1
    out = ""
    _msg = ""
    _changed = True
    if not module.check_mode:
        rc, out, err = module.run_command(to_bytes(cmd, errors='surrogate_or_strict'),
                                          errors='surrogate_or_strict')
        if not rc == 0:
            _command_fail(module,
                          "Jail {0} could not be started.".format(name),
                          cmd, rc, out, err)
        _msg = "Jail {0} was started.\n{1}".format(name, out)
    else:
        _msg = "Jail {0} would have been started.".format(name)

    return _changed, _msg


def _props_to_str(props):

    argstr = ""
    # local variable 'minargs' is assigned to but never used [F841]
    # minargs = ""
    for _prop in props:
        _val = props[_prop]
        if _val == '-' or _val == '' or not _val:
            continue
        if _val in ['yes', 'on', True]:
            argstr += '{0}=1 '.format(_prop)
        elif _val in ['no', 'off', False]:
            argstr += '{0}=0 '.format(_prop)
        elif _val in ['-', 'none']:
            argstr += '{0}={1} '.format(_prop, _val)
        else:
            argstr += '{0}="{1}" '.format(_prop, str(_val))

    return argstr


def release_fetch(module, iocage_path, update=False, release="NO-RELEASE", components=None, args=""):

    if not module.check_mode:
        if update:
            args += " -U"
        if components is not None:
            for _component in components:
                if _component != "":
                    args += " -F {0}".format(_component)
        cmd = "{0} fetch -r {1} {2}".format(iocage_path, release, args)
        rc = 1
        rc, out, err = module.run_command(to_bytes(cmd, errors='surrogate_or_strict'),
                                          errors='surrogate_or_strict')
        if not rc == 0:
            _command_fail(module,
                          "Release {0} could not be fetched.".format(release),
                          cmd, rc, out, err)
        _changed = True
        if update:
            _msg = "Release {0} was successfully updated.".format(release)
        else:
            _msg = "Release {0} was successfully fetched.".format(release)
    else:
        _changed = True
        _msg = "Release {0} would have been fetched.".format(release)

    return release, _changed, _msg


def jail_restart(module, iocage_path, name):

    cmd = "%s restart %s" % (iocage_path, name)
    rc = 1
    out = ""
    _msg = ""
    _changed = True
    if not module.check_mode:
        rc, out, err = module.run_command(to_bytes(cmd, errors='surrogate_or_strict'),
                                          errors='surrogate_or_strict')
        if not rc == 0:
            _command_fail(module,
                          "Jail {0} could not be restarted.".format(name),
                          cmd, rc, out, err)
        _msg = "Jail {0} was restarted.\n{1}".format(name, out)
    else:
        _msg = "Jail {0} would have been restarted.".format(name)

    return _changed, _msg


def jail_stop(module, iocage_path, name):

    cmd = "{0} stop {1}".format(iocage_path, name)
    _changed = False
    rc = 1
    out = ""
    _msg = ""

    if not module.check_mode:
        rc, out, err = module.run_command(to_bytes(cmd, errors='surrogate_or_strict'),
                                          errors='surrogate_or_strict')
        if not rc == 0:
            _command_fail(module,
                          "Jail {0} could not be stopped.".format(name),
                          cmd, rc, out, err)
        _msg = "Jail {0} was stopped.\n".format(name)
    else:
        _msg = "Jail {0} would have been stopped".format(name)

    return _changed, _msg


def jail_exec(module, iocage_path, name, user="root", _cmd='/usr/bin/true'):

    rc = 1
    out = ""
    err = ""
    _msg = ""
    _changed = True
    if not module.check_mode:
        cmd = "{0} exec -u {1} {2} -- {3}".format(iocage_path, user, name, _cmd)
        rc, out, err = module.run_command(to_bytes(cmd, errors='surrogate_or_strict'),
                                          errors='surrogate_or_strict')
        if not rc == 0:
            _command_fail(module,
                          "Command '{0}' could not be executed in jail '{1}'.".format(_cmd, name),
                          cmd, rc, out, err)
        _msg = ("Command '{0}' was executed in jail '{1}'.\nrc: {2}\nstdout:\n{3}\nstderr:\n{4}"
                .format(cmd, name, rc, out, err))
    else:
        _msg = "Command '{0}' would have been executed in jail '{1}'.".format(_cmd, name)

    return _changed, _msg, out, err


def jail_pkg(module, iocage_path, name, _cmd='info'):

    rc = 1
    out = ""
    err = ""
    _msg = ""
    _changed = True
    if not module.check_mode:
        cmd = "{0} pkg {1} {2}".format(iocage_path, name, _cmd)
        rc, out, err = module.run_command(to_bytes(cmd, errors='surrogate_or_strict'),
                                          errors='surrogate_or_strict')
        if not rc == 0:
            _command_fail(module,
                          "pkg '{0}' could not be executed in jail '{1}'.".format(_cmd, name),
                          cmd, rc, out, err)
        _msg = ("pkg '{0}' was executed in jail '{1}'.\nstdout:\n{2}\nstderr:\n{3}"
                .format(_cmd, name, out, err))
    else:
        _msg = "pkg '{0}' would have been executed in jail '{1}'.".format(_cmd, name)

    return _changed, _msg, out, err


def _jail_get_properties(module, iocage_path, name):

    rc = 1
    out = ""
    if name is not None and name != "":
        properties = {}
        cmd = "{0} get all {1}".format(iocage_path, name)
        rc, out, err = module.run_command(to_bytes(cmd, errors='surrogate_or_strict'),
                                          errors='surrogate_or_strict')
        if rc == 0:
            _properties = [line.strip() for line in out.strip().split('\n')]
            for p in _properties:
                for _property in [p.split(':', 1)]:
                    if len(_property) == 2:
                        properties[_property[0]] = _property[1]
                    else:
                        module.fail_json(msg="error parsing property {0} from {1}".format(p, str(properties)))
        else:
            _command_fail(module,
                          "_jail_get_properties({0})".format(name),
                          cmd, rc, out, err)
    elif module.check_mode and name == "CHECK_MODE_FAKE_UUID":
        properties = {"CHECK_NEW_JAIL": True}
    else:
        module.fail_json(msg="jail {0} not found.".format(name))

    return properties


def jail_set(module, iocage_path, name, properties=None):

    if properties is None:
        properties = {}

    rc = 1
    out = ""
    _msg = ""
    _changed = False
    cmd = ""
    _existing_props = _jail_get_properties(module, iocage_path, name)
    _props_to_be_changed = {}
    for _property in properties:
        if _property not in _existing_props:
            continue
        if _existing_props[_property] == '-' and not properties[_property]:
            continue
        if _property == "template":
            continue

        propval = None
        _val = properties[_property]
        _oval = _existing_props[_property]
        if _val in [0, 'no', 'off', False]:
            propval = 0
        elif _val in [1, 'yes', 'on', True]:
            propval = 1
        elif isinstance(_oval, str):
            if _val == '':
                propval = 'none'
            else:
                propval = '{0}'.format(_val)
        else:
            module.fail_json(msg="Unable to set attribute {0} to {1} for jail {2}"
                             .format(_property, str(_val).replace("'", "'\\''"), name))

        if 'CHECK_NEW_JAIL' in _existing_props or \
           (property in _existing_props.keys() and str(_existing_props[_property]) != str(propval)) and \
           propval is not None:
            _props_to_be_changed[_property] = propval

    if len(_props_to_be_changed) > 0:
        need_restart = False
        for p in _props_to_be_changed.keys():
            if p in ['ip4_addr', 'ip6_addr', 'template', 'interfaces', 'vnet', 'host_hostname']:
                need_restart = _jail_started(module, iocage_path, name)

        cmd = '{0} set {1} {2}'.format(iocage_path, _props_to_str(_props_to_be_changed), name)

        if not module.check_mode:
            if need_restart:
                jail_stop(module, iocage_path, name)
            rc, out, err = module.run_command(cmd)
            if need_restart:
                jail_start(module, iocage_path, name)
            if not rc == 0 or (rc == 1 and "is already a jail!" in err):
                _command_fail(module,
                              "Attributes could not be set on jail '{0}'.".format(name),
                              cmd, rc, out, err)
            _msg = ("properties {0} were set on jail '{1}' with cmd={2}."
                    .format(str(_props_to_be_changed.keys()), name, cmd))
        else:
            _msg = ("properties {0} would have been changed for jail {1} with command {2}"
                    .format(str(_props_to_be_changed.keys()), name, cmd))
            _msg += str(_props_to_be_changed)
        _changed = True

    else:
        _changed = False
        _msg = "properties {0} already set for jail {1}".format(properties.keys(), name)

    return _changed, _msg


def jail_create(module, iocage_path, name=None, properties=None, clone_from_name=None,
                clone_from_template=None, release=None, basejail=False, thickjail=False, pkglist=None):

    if properties is None:
        properties = {}

    rc = 1
    out = ""
    _msg = ""

    if clone_from_name is None and clone_from_template is None:
        if basejail:
            cmd = "{0} create -b -r {2} -n {1}".format(iocage_path, name, release)

        elif thickjail:
            cmd = "{0} create -T -r {2} -n {1} {3}".format(iocage_path, name, release, _props_to_str(properties))

        else:
            cmd = "{0} create -r {2} -n {1} {3}".format(iocage_path, name, release, _props_to_str(properties))

        if pkglist:
            cmd += " --pkglist=" + pkglist

    elif clone_from_name:
        cmd = "{0} clone {1} -n {2} {3}".format(iocage_path, clone_from_name, name, _props_to_str(properties))
    elif clone_from_template:
        cmd = "{0} create -t {1} -n {2} {3}".format(iocage_path, clone_from_template, name, _props_to_str(properties))

    if not module.check_mode:
        rc, out, err = module.run_command(cmd)
        if not rc == 0:
            _command_fail(module,
                          "Jail '{0}' could not be created.".format(name),
                          cmd, rc, out, err)
        _msg += "Jail '{0}' was created with properties {1}.\n\n{2}".format(name, str(properties), cmd)
        name = jail_exists(module, iocage_path, name)
        if not name:
            module.fail_json(msg="Jail '{0}' not created ???\ncmd: {1}\nstdout:\n{2}\nstderr:\n{3}".format(name, cmd, out, err))

    else:
        _msg += "Jail {0} would be created with command:\n{1}\n".format(name, cmd)
        name = "CHECK_MODE_FAKE_UUID_FOR_{0}".format(name)

    return name, True, _msg


def jail_update(module, iocage_path, name):

    rc = 1
    out = ""
    _msg = ""
    _changed = False
    cmd = "{0} update {1}".format(iocage_path, name)
    if not module.check_mode:
        rc, out, err = module.run_command(to_bytes(cmd, errors='surrogate_or_strict'),
                                          errors='surrogate_or_strict')
        if not rc == 0:
            _command_fail(module,
                          "Jail '{0}' not updated.".format(name),
                          cmd, rc, out, err)
        if "No updates needed" in out:
            _changed = False
        elif "updating to" in out:
            nv = re.search(r' ([^ ]*):$', filter((lambda x: 'updating to' in x), out.split('\n'))[0]).group(1)
            _msg = "jail {0} updated to {1}".format(name, nv)
            _changed = True
    else:
        _msg = "Unable to check for updates in check_mode"

    return _changed, _msg


def jail_destroy(module, iocage_path, name):

    rc = 1
    out = ""
    _msg = ""
    _changed = True
    if not module.check_mode:
        cmd = "{0} destroy -f {1}".format(iocage_path, name)
        rc, out, err = module.run_command(to_bytes(cmd, errors='surrogate_or_strict'),
                                          errors='surrogate_or_strict')
        if not rc == 0:
            _command_fail(module,
                          "Jail '{0}' could not be destroyed.".format(name),
                          cmd, rc, out, err)
        _msg = "Jail '{0}' was destroyed.".format(name)
        jail_exists(module, iocage_path, name, True)
    else:
        _msg = "Jail {0} would have been destroyed.".format(name)

    return name, _changed, _msg


def run_module():

    module_args = dict(
        state=dict(type='str',
                   default="facts",
                   choices=["basejail", "thickjail", "template", "present", "cloned", "started",
                            "stopped", "restarted", "fetched", "exec", "pkg", "exists", "absent",
                            "set", "facts"],),
        name=dict(type='str'),
        pkglist=dict(type='path'),
        properties=dict(type='dict'),
        args=dict(type='dict'),
        user=dict(type='str', default="root"),
        cmd=dict(type='str'),
        clone_from=dict(type='str'),
        release=dict(type='str'),
        update=dict(type='bool', default=False,),
        components=dict(type='list', elements='path', aliases=["files", "component"],),)

    module = AnsibleModule(argument_spec=module_args,
                           supports_check_mode=True)

    iocage_path = module.get_bin_path('iocage', True)
    if not iocage_path:
        module.fail_json(msg='Utility iocage not found!')

    p = module.params
    name = p["name"]
    properties = p["properties"]
    cmd = p["cmd"]
    args = p["args"]
    clone_from = p["clone_from"]
    user = p["user"]
    release = p["release"]
    update = p["update"]
    components = p["components"]
    pkglist = p["pkglist"]

    msgs = []
    changed = False
    out = ""
    err = ""

    facts = _get_iocage_facts(module, iocage_path, "all")

    jails = {}
    for u in facts["iocage_jails"]:
        jails[u] = facts["iocage_jails"][u]
    for u in facts["iocage_templates"]:
        jails[u] = facts["iocage_templates"][u]

    if p["state"] == "facts":
        module.exit_json(changed=False, ansible_facts=facts)

    # Input validation

    # states that need name of jail
    if name is None and p["state"] in ["started", "stopped", "restarted", "exists", "set", "exec", "pkg", "absent"]:
        module.fail_json(msg="name needed for state {0}".format(p["state"]))

    # states that need release defined
    if p["state"] in ["basejail", "thickjail", "template", "fetched", "present"] or p["update"]:
        if release is None or release == "":
            # if name and not (upgrade):
            #     _jail_props = _jail_get_properties(module, iocage_path, name)
            #     release = _jail_props["release"]
            # else:
            rc, out, err = module.run_command("uname -r")
            if rc != 0:
                module.fail_json(msg="Unable to run uname -r ???")

            matches = re.match(r'(\d+\.\d+)\-(RELEASE|RC\d+).*', out.strip())
            if matches is not None:
                release = matches.group(1) + "-RELEASE"
            else:
                module.fail_json(msg="Release not recognised: {0}".format(out))

    # need existing jail
    if p["state"] in ["started", "stopped", "restarted", "set", "exec", "pkg", "exists"]:
        if name not in facts["iocage_jails"] and name not in facts["iocage_templates"]:
            module.fail_json(msg="Jail '{0}' doesn't exist".format(name))

    # states that need running jail
    if p["state"] in ["exec", "pkg"] and facts["iocage_jails"][name]["state"] != "up":
        module.fail_json(msg="Jail '{0}' not running".format(name))

    if p["state"] == "started":
        if jails[name]["state"] != "up":
            changed, _msg = jail_start(module, iocage_path, name)
            msgs.append(_msg)
            jails[name] = _get_iocage_facts(module, iocage_path, "jails", name)
            if jails[name]["state"] != "up" and not module.check_mode:
                module.fail_json(msg="Starting jail {0} failed with {1} :(".format(name, _msg))
        else:
            msgs.append("Jail {0} already started".format(name))

    elif p["state"] == "stopped":
        if jails[name]["state"] == "up":
            changed, _msg = jail_stop(module, iocage_path, name)
            msgs.append(_msg)
            if not module.check_mode:
                jails[name] = _get_iocage_facts(module, iocage_path, "jails", name)
                if jails[name]["state"] != "down":
                    module.fail_json(msg="Stopping jail {0} failed with {1} :(".format(name, _msg))
        else:
            msgs.append("Jail {0} already stopped".format(name))

    elif p["state"] == "restarted":
        changed, _msg = jail_restart(module, iocage_path, name)
        jails[name] = _get_iocage_facts(module, iocage_path, "jails", name)
        if jails[name]["state"] != "up":
            module.fail_json(msg="Starting jail {0} failed with {1} :(".format(name, _msg))
        msgs.append(_msg)

    elif p["state"] == "exec":
        changed, _msg, out, err = jail_exec(module, iocage_path, name, user, cmd)
        msgs.append(_msg)

    elif p["state"] == "pkg":
        changed, _msg, out, err = jail_pkg(module, iocage_path, name, cmd)
        msgs.append(_msg)

    elif p["state"] == "exists":
        msgs.append("Jail {0} exists".format(name))

    elif p["state"] == "fetched":
        if update or release not in facts["iocage_releases"]:
            rel, changed, _msg = release_fetch(module, iocage_path, update, release, components, args)
            msgs.append(_msg)
            facts["iocage_releases"] = _get_iocage_facts(module, iocage_path, "releases")
            if release not in facts["iocage_releases"] or update:
                module.fail_json(msg="Fetching release {0} failed with {1}".format(release, _msg))
        else:
            msgs.append("Release {0} already fetched".format(release))

    elif p["state"] == "set":
        changed, _msg = jail_set(module, iocage_path, name, properties)
        msgs.append(_msg)
        jails[name] = _get_iocage_facts(module, iocage_path, "jails", name)

    elif p["state"] in ["present", "cloned", "template", "basejail", "thickjail"]:

        do_basejail = False
        do_thickjail = False
        clone_from_name = None
        clone_from_template = None
        # local variable 'jail_exists' is assigned to but never used [F841]
        # jail_exists = False

        if p["state"] != "cloned" and release not in facts["iocage_releases"]:
            release, _release_changed, _release_msg = release_fetch(module, iocage_path, update, release, components, args)
            if _release_changed:
                facts["iocage_releases"] = _get_iocage_facts(module, iocage_path, "releases")
                msgs.append(_release_msg)

        if p["state"] == "template":
            if properties is None:
                properties = {}
            properties["template"] = "true"
            properties["boot"] = "false"
            if name in facts["iocage_templates"]:
                # local variable 'jail_exists' is assigned to but never used [F841]
                # jail_exists = True
                pass

        elif p["state"] == "basejail":
            properties = {}
            do_basejail = True

        elif p["state"] == "thickjail":
            do_thickjail = True

        elif clone_from:
            if clone_from in facts["iocage_jails"]:
                clone_from_name = clone_from
            elif clone_from in facts["iocage_templates"]:
                clone_from_template = clone_from
            else:
                if module.check_mode:
                    # todo: use facts to check if basejail would have been created before
                    msgs.append("Jail {0} would have been cloned from (nonexisting) jail or template {1}".format(name, clone_from))
                else:
                    module.fail_json(msg="unable to create jail {0}\nbasejail {1} doesn't exist".format(name, clone_from))

        if name not in facts["iocage_templates"] and name not in facts["iocage_jails"]:
            name, changed, _msg = jail_create(module, iocage_path, name, properties, clone_from_name,
                                              clone_from_template, release, do_basejail, do_thickjail, pkglist)
            msgs.append(_msg)
        else:
            changed, _msg = jail_set(module, iocage_path, name, properties)
            msgs.append("{0} already exists".format(name))
            if changed:
                msgs.append(_msg)

        if p["update"]:
            if release not in facts["iocage_releases"]:
                release, _release_changed, _release_msg = release_fetch(module, iocage_path, update, release, components, args)
                if _release_changed:
                    _msg += _release_msg
                    facts["iocage_releases"] = _get_iocage_facts(module, iocage_path, "releases")

            release, changed, _msg = jail_update(module, iocage_path, name, release)
            msgs.append(_msg)

#        # re-set properties (iocage missing them on creation - iocage-sh bug)
#        if len(p["properties"]) > 0:
#            changed, _msg = jail_set(module, iocage_path, name, properties)
#            if changed:
#                msgs.append(_msg)

        if changed:
            if p["state"] == "template":
                facts["iocage_templates"][name] = _get_iocage_facts(module, iocage_path, "templates", name)
            else:
                facts["iocage_jails"][name] = _get_iocage_facts(module, iocage_path, "jails", name)

    elif p["state"] == "absent":
        if name in jails:
            if jails[name]['state'] == "up":
                changed, _msg = jail_stop(module, iocage_path, name)
                msgs.append(_msg)
            name, changed, _msg = jail_destroy(module, iocage_path, name)
            msgs.append(_msg)
            del(jails[name])
        else:
            _msg = "Jail {0} is already absent.".format(name)
            msgs.append(_msg)
        if name in facts["iocage_jails"]:
            del(facts["iocage_jails"][name])
            _msg = "Jail {0} removed from iocage_jails.".format(name)
            msgs.append(_msg)
        if name in facts["iocage_templates"]:
            del(facts["iocage_templates"][name])
            _msg = "Jail {0} removed from iocage_templates.".format(name)
            msgs.append(_msg)

    result = dict(changed=changed,
                  msg=", ".join(msgs),
                  name="",
                  ansible_facts=facts,
                  stdout=out,
                  stderr=err,
                  )
    module.exit_json(**result)


def main():
    run_module()


if __name__ == '__main__':
    main()
