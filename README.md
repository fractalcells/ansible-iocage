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

The project comes with set of tests stored in the directory test/tasks. Run
the complete collection of the tests at localhost

```
shell> cd test
shell> ansible-playbook -M . iocage_test.yml
```

This should display a report similar to this one

```sh
PLAY RECAP ***********************************************************************
localhost: ok=158 changed=17 unreachable=0 failed=0 skipped=65 rescued=6 ignored=0
```

Custom stats will provide you with more details if you run the tests
on multiple nodes. See *ansible.builtin.set_stats*. For example run
the complete collection of the tests on two nodes *test_23* and
*test_29*

```sh
shell> ANSIBLE_SHOW_CUSTOM_STATS=true ansible-playbook iocage_test.yml -M . -e my_hosts=test_23,test_29
```

This should display a report similar to this one

```sh
PLAY RECAP *********************************************************************
test_23: ok=207 changed=17 unreachable=0 failed=0 skipped=28 rescued=6 ignored=0
test_29: ok=207 changed=17 unreachable=0 failed=0 skipped=28 rescued=6 ignored=0

CUSTOM STATS: ******************************************************************
       test_23:   a1: Aug 29 21:46:23  a2: Aug 29 21:52:12  ok: 35
       test_29:   a1: Aug 29 21:46:23  a2: Aug 29 22:03:57  ok: 35
```


Advanced tests
--------------

Most of the tests and groups are generated from templates (see
directory templates) by the dictionaries *iocage_test_db* and
*iocage_group_db* stored in the files in directory vars. Do not edit
the tasks and groups manually. Modify or create new templates and
dictionaries, and run the playbook *configure.yml*. For example, add
new group of tests in *vars/groups.d/group_present_absent_restart.yml*

```yaml
---
group_present_absent_restart:
  template: group
  tests:
    - test: test_present
    - test: test_absent
    - test: test_restart_crash
```

Run playbook *configure.yml* and create the group *group_present_absent_restart*

```sh
shell> ansible-playbook configure.yml -e my_groups=group_present_absent_restart -t create_groups,create_iocage_test
...
TASK [Create group files in directory tasks] *********************************
ok: [localhost] => (item=group_present_absent_restart)

TASK [Create playbook iocage_test.yml] ***************************************
ok: [localhost]
```

Create file with the parameters of the tests, e.g. run the tests on
the nodes *test_23,test_29*, use jail *test_31*, enable debug, and set
strategy *free*

```yaml
shell> cat extra_vars/test_31-debug-n2.yml
---
my_hosts: test_23,test_29
my_jname: test_31
my_debug: true
my_strategy: free
```

Run the tests and display custom stats

```sh
shell> ANSIBLE_SHOW_CUSTOM_STATS=true ansible-playbook iocage_test.yml -M . -e @extra_vars/test_31-debug-n2.yml -t group_present_absent_restart
```

This should display a report similar to this abridged one

```yaml

PLAY [test_23,test_29] *****************************************************************

TASK [>>> TEST START: test_present: Check if test_31 can be created] *******************
ok: [test_23] =>
  result.msg: |-
    Jail 'test_31' was created with properties {}.
    /usr/local/bin/iocage create -n test_31 -r 13.0-RELEASE
ok: [test_29] =>
  result.msg: |-
    Jail 'test_31' was created with properties {}.
    /usr/local/bin/iocage create -n test_31 -r 13.0-RELEASE

ok: [test_23] => changed=false
  msg: |-
    [OK]  test_present: Passed: Jail 'test_31' was created with properties {}.
ok: [test_29] => changed=false
  msg: |-
    [OK]  test_present: Passed: Jail 'test_31' was created with properties {}.

TASK [>>> TEST START: test_absent: Check if jail test_31 can be destroyed] *************
ok: [test_23] =>
  result.msg: Jail 'test_31' was destroyed., Jail test_31 removed from iocage_jails.
ok: [test_29] =>
  result.msg: Jail 'test_31' was destroyed., Jail test_31 removed from iocage_jails.

ok: [test_23] => changed=false
  msg: '[OK]  test_absent: Passed: Jail ''test_31'' was destroyed., Jail test_31 removed from iocage_jails.'
ok: [test_29] => changed=false
  msg: '[OK]  test_absent: Passed: Jail ''test_31'' was destroyed., Jail test_31 removed from iocage_jails.'

TASK [>>> TEST START: test_restart_crash: Check if jail test_31 can not be restarted] **
fatal: [test_23]: FAILED! => changed=false
  msg: Jail 'test_31' doesn't exist
fatal: [test_29]: FAILED! => changed=false
  msg: Jail 'test_31' doesn't exist

ok: [test_23] => changed=false
  msg: '[OK]  test_restart_crash: Passed: Jail ''test_31'' doesn''t exist'
ok: [test_29] => changed=false
  msg: '[OK]  test_restart_crash: Passed: Jail ''test_31'' doesn''t exist'


CUSTOM STATS: **************************************************************************
        test_23:   a1: Aug 25 23:26:31  a2: Aug 25 23:27:01  ok: 3
        test_29:   a1: Aug 25 23:26:31  a2: Aug 25 23:28:06  ok: 3
```


Variables and parameters of the tests
-------------------------------------

In this framework, there are three sources of the tests' parameters

* Hard-coded parameters in the test files and group files. If you want
  to customize them change the data in vars/ and run the playbook
  *configure.yml*. You can also add you own test and group files
  preferably in the form of the data in vars/ and templates. Add
  templates if needed.

* Defaults in the playbook iocage_test.yml. If you want to customize
  them change the template *iocage_test.yml.j2* and run the playbook
  *configure.yml*.

* Extra vars on the command line. See examples in the directory
  extra_vars/ on how to create files with extra variables.

Except of this you can customize the variables at any other precedence
you want to, of course.


See also
--------

* [iocage - A FreeBSD Jail Manager - iocage documentation at readthedocs.io](https://iocage.readthedocs.io/en/latest/)
* [iocage - Jail manager using ZFS and VNET - FreeBSD System Manager's Manual](https://www.freebsd.org/cgi/man.cgi?query=iocage)
