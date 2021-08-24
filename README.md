ansible-iocage
==============

[![license](https://img.shields.io/badge/license-BSD-red.svg)](https://www.freebsd.org/doc/en/articles/bsdl-gpl/article.html)

[iocage](https://github.com/iocage/iocage) module for Ansible.

Home on https://github.com/fractalcells/ansible-iocage


Description
-----------

This module is an Ansible 'wrapper' of the iocage command.

* Works with new Python3 iocage, not anymore with shell version

* Release is host's one if not specified

* Release is automatically fetched if missing


Requirements (on the node)
--------------------------

* lang/python >= 3.6

* sysutils/iocage


Install
-------

Put the module to DEFAULT_MODULE_PATH

```
shell> ansible-config dump|grep DEFAULT_MODULE_PATH
DEFAULT_MODULE_PATH(default) = ['/home/admin/.ansible/plugins/modules', '/usr/share/ansible/plugins/modules']
```


Documentation
-------------

Only the inline documentation of the module is available. Run the command

```
shell> ansible-doc -t module iocage
```

Read the [iocage documentation at readthedocs.io](https://iocage.readthedocs.io/en/latest/)


Example
-------

No option of the module is required. Without any option the module
gathers facts about the jails. For example the play below

```yaml
shell> cat playbook.yml
- hosts: srv.example.net
  tasks:
    - iocage:
    - debug:
        msg: |-
          iocage_releases = {{ ansible_facts.iocage_releases }}
          iocage_templates.keys() = {{ ansible_facts.iocage_templates.keys()|list }}
          iocage_jails.keys() = {{ ansible_facts.iocage_jails.keys()|list }}
```

gives

```yaml

shell> ansible-playbook playbook.yml
  ...
  msg: |-
    iocage_releases = ['13.0-RELEASE']
    iocage_templates.keys() = []
    iocage_jails.keys() = ['NewJail', 'test_31', 'test_basejail_13_0_RELEASE']
```


Use-cases
---------

* Fetch 11.0-RELEASE

```
iocage: state=fetched release=11.0-RELEASE
```

* Fetch host's RELEASE

```
iocage: state=fetched
```

* Fetch just the base component of host's RELEASE

```
iocage: state=fetched components=base.txz
```

* Fetch host's RELEASE, limited to base and doc components

```
iocage: state=fetched components=base.txz,doc.txz
```

* Create basejail
```
iocage: state=basejail name="foo" release=11.0-RELEASE
```

* Create template

```
iocage:
  state: template
  name: mytemplate
  properties:
    ip4_addr: 'lo0|10.1.0.1'
    resolver: 'nameserver 127.0.0.1'
```

* Clone existing jail

```
iocage:
  state: present
  name: "foo"
  clone_from: "mytemplate"
  pkglist: /path/to/pkglist.json
  properties:
    ip4_addr: 'lo0|10.1.0.5'
    boot: "on"
    allow_sysvipc: 1
    defaultrouter: '10.1.0.1'
    host_hostname: 'myjail.my.domain'
```

* Create jail (without cloning)

```
iocage:
  state: present
  name: "foo"
  pkglist: /path/to/pkglist.json
  properties:
    ip4_addr: 'lo0|10.1.0.5'
    boot: "on"
    allow_sysvipc: 1
    defaultrouter: '10.1.0.1'
    host_hostname: 'myjail.my.domain'
```

* Ensure jail is started

```
iocage: state=started name="foo"
```

* Ensure jail is stopped

```
iocage: state=stopped name="foo"
```

* Restart existing jail

```
iocage: state=restarted name="myjail"
```

* Execute command in (running) jail

```
iocage: state=exec name="myjail" user="root" cmd="service sshd start"
```

* Destroy jail

```
iocage: state=absent name="myjail"
```

* Set attributes on jail

```
iocage:
  state: set
  name: "myjail"
  properties:
    template: "yes"
```


Tests
-----

The project comes with set of tests stored in the directory
tasks. Most of the tasks are generated from templates (see directory
templates) by the dictionary iocage_task_db stored in
vars/iocage_task_db.yml. Do not edit such tasks manually. Modify or
create new template, modify iocage_task_db, and run the playbook
configure.yml if you want to modify tasks or add new ones.

The complete collection of the tests at localhost

```
shell> ansible-playbook -M . iocage_test.yml
```

should show something similar to

```sh
PLAY RECAP ***********************************************************************
localhost: ok=124 changed=12 unreachable=0 failed=0 skipped=53 rescued=5 ignored=0
```

Custom stats will provide you with more details if you run the tests
on multiple nodes. See ansible.builtin.set_stats

```sh
shell> ANSIBLE_SHOW_CUSTOM_STATS=true ansible-playbook iocage_test.yml -M . -e test_iocage=test_23
```

should show something similar to

```sh
PLAY RECAP *********************************************************************
test_23: ok=124 changed=12 unreachable=0 failed=0 skipped=53 rescued=5 ignored=0

CUSTOM STATS: ******************************************************************
       test_23:   test_pass: 28
```

See also
--------

* [iocage - A FreeBSD Jail Manager - iocage documentation at readthedocs.io](https://iocage.readthedocs.io/en/latest/)

* [iocage - Jail manager using ZFS and VNET - FreeBSD System Manager's Manual](https://www.freebsd.org/cgi/man.cgi?query=iocage)
