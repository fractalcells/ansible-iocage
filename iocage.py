#!/usr/bin/python
# -*- coding: utf-8 -*-

# Copyright 2015, Perceivon Hosting Inc.
#
# Redistribution and use in source and binary forms, with or without
# modification, are permitted provided that the following conditions are met:
#
# 1. Redistributions of source code must retain the above copyright notice, this
#    list of conditions and the following disclaimer.
#
# 2. Redistributions in binary form must reproduce the above copyright notice,
#    this list of conditions and the following disclaimer in the documentation
#    and/or other materials provided with the distribution.
#
# THIS SOFTWARE IS PROVIDED BY [COPYRIGHT HOLDER] AND CONTRIBUTORS "AS IS" AND
# ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE IMPLIED
# WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE ARE
# DISCLAIMED. IN NO EVENT SHALL [COPYRIGHT HOLDER] OR CONTRIBUTORS BE LIABLE FOR
# ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES
# (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES;
# LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND ON
# ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT
# (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE OF THIS
# SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.

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
    module.fail_json(msg="%s\ncmd: '%s' return: %s\nstdout: '%s'\nstderr: '%s')"
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
        cmd = "%s %s" % (iocage_path, opt[argument])
    else:
        module.fail_json(msg="_get_iocage_facts(%s): argument not understood" % (argument))

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
                module.fail_json(msg="_get_iocage_facts():\nUnreadable stdout line from cmd '%s': '%s'"
                                 % (cmd, line))
    except ValueError:
        module.fail_json(msg="unable to parse %s" % (state))

    if name is not None:
        if name in _jails:
            return _jails[name]
        else:
            return {}

    return _jails


def _jail_started(module, iocage_path, name):

    cmd = "%s list -h" % (iocage_path)
    rc, state, err = module.run_command(to_bytes(cmd, errors='surrogate_or_strict'),
                                        errors='surrogate_or_strict')
    if rc != 0:
        _command_fail(module, "jail_started(%s)" % (name), cmd, rc, state, err)

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
                module.fail_json(msg="Jail %s unknown state: %s" % (name, line))

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
        module.fail_json(msg="Jail %s exists." % (argument))

    return name.strip()


def jail_start(module, iocage_path, name):

    cmd = "%s start %s" % (iocage_path, name)
    rc = 1
    out = ""
    _msg = ""
    _changed = True
    if not module.check_mode:
        rc, out, err = module.run_command(to_bytes(cmd, errors='surrogate_or_strict'),
                                          errors='surrogate_or_strict')
        if not rc == 0:
            _command_fail(module,
                          "Jail %s could not be started." % (name),
                          cmd, rc, out, err)
        _msg = "Jail %s was started.\n%s" % (name, out)
    else:
        _msg = "Jail %s would have been started." % (name)

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
            argstr += '%s=1 ' % (_prop)
        elif _val in ['no', 'off', False]:
            argstr += '%s=0 ' % (_prop)
        elif _val in ['-', 'none']:
            argstr += '%s=%s ' % (_prop, _val)
        else:
            argstr += '%s="%s" ' % (_prop, str(_val))

    return argstr


def release_fetch(module, iocage_path, update=False, release="NO-RELEASE", components=None, args=""):

    if not module.check_mode:
        if update:
            args += " -U"
        if components is not None:
            for _component in components:
                if _component != "":
                    args += " -F %s" % (_component)
        cmd = "%s fetch -r %s %s" % (iocage_path, release, args)
        rc = 1
        rc, out, err = module.run_command(to_bytes(cmd, errors='surrogate_or_strict'),
                                          errors='surrogate_or_strict')
        if not rc == 0:
            _command_fail(module,
                          "Release %s could not be fetched." % (release),
                          cmd, rc, out, err)
        _changed = True
        if update:
            _msg = "Release %s was successfully updated." % (release)
        else:
            _msg = "Release %s was successfully fetched." % (release)
    else:
        _changed = True
        _msg = "Release %s would have been fetched." % (release)

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
                          "Jail %s could not be restarted." % (name),
                          cmd, rc, out, err)
        _msg = "Jail %s was restarted.\n%s" % (name, out)
    else:
        _msg = "Jail %s would have been restarted." % (name)

    return _changed, _msg


def jail_stop(module, iocage_path, name):

    cmd = "%s stop %s" % (iocage_path, name)
    _changed = False
    rc = 1
    out = ""
    _msg = ""

    if not module.check_mode:
        rc, out, err = module.run_command(to_bytes(cmd, errors='surrogate_or_strict'),
                                          errors='surrogate_or_strict')
        if not rc == 0:
            _command_fail(module,
                          "Jail %s could not be stopped." % (name),
                          cmd, rc, out, err)
        _msg = "Jail %s was stopped.\n" % (name)
    else:
        _msg = "Jail %s would have been stopped" % (name)

    return _changed, _msg


def jail_exec(module, iocage_path, name, user="root", _cmd='/usr/bin/true'):

    rc = 1
    out = ""
    err = ""
    _msg = ""
    _changed = True
    if not module.check_mode:
        cmd = "%s exec -u %s %s -- %s" % (iocage_path, user, name, _cmd)
        rc, out, err = module.run_command(to_bytes(cmd, errors='surrogate_or_strict'),
                                          errors='surrogate_or_strict')
        if not rc == 0:
            _command_fail(module,
                          "Command '%s' could not be executed in jail '%s'." % (_cmd, name),
                          cmd, rc, out, err)
        _msg = ("Command '%s' was executed in jail '%s'.\nrc: %s\nstdout:\n%s\nstderr:\n%s"
                % (cmd, name, rc, out, err))
    else:
        _msg = "Command '%s' would have been executed in jail '%s'." % (_cmd, name)

    return _changed, _msg, out, err


def jail_pkg(module, iocage_path, name, _cmd='info'):

    rc = 1
    out = ""
    err = ""
    _msg = ""
    _changed = True
    if not module.check_mode:
        cmd = "%s pkg %s %s" % (iocage_path, name, _cmd)
        rc, out, err = module.run_command(to_bytes(cmd, errors='surrogate_or_strict'),
                                          errors='surrogate_or_strict')
        if not rc == 0:
            _command_fail(module,
                          "pkg '%s' could not be executed in jail '%s'." % (_cmd, name),
                          cmd, rc, out, err)
        _msg = ("pkg '%s' was executed in jail '%s'.\nstdout:\n%s\nstderr:\n%s"
                % (_cmd, name, out, err))
    else:
        _msg = "pkg '%s' would have been executed in jail '%s'." % (_cmd, name)

    return _changed, _msg, out, err


def _jail_get_properties(module, iocage_path, name):

    rc = 1
    out = ""
    if name is not None and name != "":
        properties = {}
        cmd = "%s get all %s" % (iocage_path, name)
        rc, out, err = module.run_command(to_bytes(cmd, errors='surrogate_or_strict'),
                                          errors='surrogate_or_strict')
        if rc == 0:
            _properties = [line.strip() for line in out.strip().split('\n')]
            for p in _properties:
                for _property in [p.split(':', 1)]:
                    if len(_property) == 2:
                        properties[_property[0]] = _property[1]
                    else:
                        module.fail_json(msg="error parsing property %s from %s" % (p, str(properties)))
        else:
            _command_fail(module,
                          "_jail_get_properties(%s)" % (name),
                          cmd, rc, out, err)
    elif module.check_mode and name == "CHECK_MODE_FAKE_UUID":
        properties = {"CHECK_NEW_JAIL": True}
    else:
        module.fail_json(msg="jail %s not found." % (name))

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
                propval = '%s' % (_val)
        else:
            module.fail_json(msg="Unable to set attribute %s to %s for jail %s"
                             % (_property, str(_val).replace("'", "'\\''"), name))

        if 'CHECK_NEW_JAIL' in _existing_props or \
           (property in _existing_props.keys() and str(_existing_props[_property]) != str(propval)) and \
           propval is not None:
            _props_to_be_changed[_property] = propval

    if len(_props_to_be_changed) > 0:
        need_restart = False
        for p in _props_to_be_changed.keys():
            if p in ['ip4_addr', 'ip6_addr', 'template', 'interfaces', 'vnet', 'host_hostname']:
                need_restart = _jail_started(module, iocage_path, name)

        cmd = '%s set %s %s' % (iocage_path, _props_to_str(_props_to_be_changed), name)

        if not module.check_mode:
            if need_restart:
                jail_stop(module, iocage_path, name)
            rc, out, err = module.run_command(cmd)
            if need_restart:
                jail_start(module, iocage_path, name)
            if not rc == 0 or (rc == 1 and "is already a jail!" in err):
                _command_fail(module,
                              "Attributes could not be set on jail '%s'." % (name),
                              cmd, rc, out, err)
            _msg = ("properties %s were set on jail '%s' with cmd=%s."
                    % (str(_props_to_be_changed.keys()), name, cmd))
        else:
            _msg = ("properties %s would have been changed for jail %s with command %s"
                    % (str(_props_to_be_changed.keys()), name, cmd))
            _msg += str(_props_to_be_changed)
        _changed = True

    else:
        _changed = False
        _msg = "properties %s already set for jail %s" % (properties.keys(), name)

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
            cmd = "%s create -b -r %s -n %s" % (iocage_path, name, release)

        elif thickjail:
            cmd = "%s create -T -r %s -n %s %s" % (iocage_path, name, release, _props_to_str(properties))

        else:
            cmd = "%s create -r %s -n %s %s" % (iocage_path, name, release, _props_to_str(properties))

        if pkglist:
            cmd += " --pkglist=" + pkglist

    elif clone_from_name:
        cmd = "%s clone %s -n %s %s" % (iocage_path, clone_from_name, name, _props_to_str(properties))
    elif clone_from_template:
        cmd = "%s create -t %s -n %s %s" % (iocage_path, clone_from_template, name, _props_to_str(properties))

    if not module.check_mode:
        rc, out, err = module.run_command(cmd)
        if not rc == 0:
            _command_fail(module,
                          "Jail '%s' could not be created." % (name),
                          cmd, rc, out, err)
        _msg += "Jail '%s' was created with properties %s.\n\n%s" % (name, str(properties), cmd)
        name = jail_exists(module, iocage_path, name)
        if not name:
            module.fail_json(msg="Jail '%s' not created ???\ncmd: %s\nstdout:\n%s\nstderr:\n%s" % (name, cmd, out, err))

    else:
        _msg += "Jail %s would be created with command:\n%s\n" % (name, cmd)
        name = "CHECK_MODE_FAKE_UUID_FOR_%s" % (name)

    return name, True, _msg


def jail_update(module, iocage_path, name):

    rc = 1
    out = ""
    _msg = ""
    _changed = False
    cmd = "%s update %s" % (iocage_path, name)
    if not module.check_mode:
        rc, out, err = module.run_command(to_bytes(cmd, errors='surrogate_or_strict'),
                                          errors='surrogate_or_strict')
        if not rc == 0:
            _command_fail(module,
                          "Jail '%s' not updated." % (name),
                          cmd, rc, out, err)
        if "No updates needed" in out:
            _changed = False
        elif "updating to" in out:
            nv = re.search(r' ([^ ]*):$', filter((lambda x: 'updating to' in x), out.split('\n'))[0]).group(1)
            _msg = "jail %s updated to %s" % (name, nv)
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
        cmd = "%s destroy -f %s" % (iocage_path, name)
        rc, out, err = module.run_command(to_bytes(cmd, errors='surrogate_or_strict'),
                                          errors='surrogate_or_strict')
        if not rc == 0:
            _command_fail(module,
                          "Jail '%s' could not be destroyed." % (name),
                          cmd, rc, out, err)
        _msg = "Jail '%s' was destroyed." % (name)
        jail_exists(module, iocage_path, name, True)
    else:
        _msg = "Jail %s would have been destroyed." % (name)

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
        result = dict(changed=changed,
                      msg=", ".join(msgs),
                      ansible_facts=facts,
                      stdout=out,
                      stderr=err,
                      )
        if module._debug:
            result['module_args'] = f"{(json.dumps(module.params, indent=4))}"
        module.exit_json(**result)

    # Input validation

    # states that need name of jail
    if name is None and p["state"] in ["started", "stopped", "restarted", "exists", "set", "exec", "pkg", "absent"]:
        module.fail_json(msg="name needed for state %s" % (p["state"]))

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
                module.fail_json(msg="Release not recognised: %s" % (out))

    # need existing jail
    if p["state"] in ["started", "stopped", "restarted", "set", "exec", "pkg", "exists"]:
        if name not in facts["iocage_jails"] and name not in facts["iocage_templates"]:
            module.fail_json(msg="Jail '%s' doesn't exist" % (name))

    # states that need running jail
    if p["state"] in ["exec", "pkg"] and facts["iocage_jails"][name]["state"] != "up":
        module.fail_json(msg="Jail '%s' not running" % (name))

    if p["state"] == "started":
        if jails[name]["state"] != "up":
            changed, _msg = jail_start(module, iocage_path, name)
            msgs.append(_msg)
            jails[name] = _get_iocage_facts(module, iocage_path, "jails", name)
            if jails[name]["state"] != "up" and not module.check_mode:
                module.fail_json(msg="Starting jail %s failed with %s :(" % (name, _msg))
        else:
            msgs.append("Jail %s already started" % (name))

    elif p["state"] == "stopped":
        if jails[name]["state"] == "up":
            changed, _msg = jail_stop(module, iocage_path, name)
            msgs.append(_msg)
            if not module.check_mode:
                jails[name] = _get_iocage_facts(module, iocage_path, "jails", name)
                if jails[name]["state"] != "down":
                    module.fail_json(msg="Stopping jail %s failed with %s :(" % (name, _msg))
        else:
            msgs.append("Jail %s already stopped" % (name))

    elif p["state"] == "restarted":
        changed, _msg = jail_restart(module, iocage_path, name)
        jails[name] = _get_iocage_facts(module, iocage_path, "jails", name)
        if jails[name]["state"] != "up":
            module.fail_json(msg="Starting jail %s failed with %s :(" % (name, _msg))
        msgs.append(_msg)

    elif p["state"] == "exec":
        changed, _msg, out, err = jail_exec(module, iocage_path, name, user, cmd)
        msgs.append(_msg)

    elif p["state"] == "pkg":
        changed, _msg, out, err = jail_pkg(module, iocage_path, name, cmd)
        msgs.append(_msg)

    elif p["state"] == "exists":
        msgs.append("Jail %s exists" % (name))

    elif p["state"] == "fetched":
        if update or release not in facts["iocage_releases"]:
            rel, changed, _msg = release_fetch(module, iocage_path, update, release, components, args)
            msgs.append(_msg)
            facts["iocage_releases"] = _get_iocage_facts(module, iocage_path, "releases")
            if release not in facts["iocage_releases"] or update:
                module.fail_json(msg="Fetching release %s failed with %s" % (release, _msg))
        else:
            msgs.append("Release %s already fetched" % (release))

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
                    msgs.append("Jail %s would have been cloned from (nonexisting) jail or template %s" % (name, clone_from))
                else:
                    module.fail_json(msg="unable to create jail %s\nbasejail %s doesn't exist" % (name, clone_from))

        if name not in facts["iocage_templates"] and name not in facts["iocage_jails"]:
            name, changed, _msg = jail_create(module, iocage_path, name, properties, clone_from_name,
                                              clone_from_template, release, do_basejail, do_thickjail, pkglist)
            msgs.append(_msg)
        else:
            changed, _msg = jail_set(module, iocage_path, name, properties)
            msgs.append("%s already exists" % (name))
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
            _msg = "Jail %s is already absent." % (name)
            msgs.append(_msg)
        if name in facts["iocage_jails"]:
            del(facts["iocage_jails"][name])
            _msg = "Jail %s removed from iocage_jails." % (name)
            msgs.append(_msg)
        if name in facts["iocage_templates"]:
            del(facts["iocage_templates"][name])
            _msg = "Jail %s removed from iocage_templates." % (name)
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
