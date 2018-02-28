ansible-iocage
==============

[iocage](https://github.com/iocage/iocage) module for ansible. Based on https://github.com/fractalcells/ansible-iocage

Works with new python3 iocage, not anymore with shell version

release is host's one if not specified

release is automatically fetched if missing

Usecases:
---------

fetch 11.0-RELEASE:
```
iocage: state=fetched release=11.0-RELEASE
```

fetch host's RELEASE:
```
iocage: state=fetched
```
create basejail:
```
iocage: state=basejail name="foo" release=11.0-RELEASE
```

create template:
```
iocage: state=template name=mytemplate properties={ip4_addr: 'lo0|10.1.0.1', resolver: 'nameserver 127.0.0.1'}
```

clone existing jail:
```
iocage: state=present name="foo" clone_from="mytemplate" properties={ ip4_addr='lo0|10.1.0.5', boot: on, allow_sysvipc: 1, pkglist: /path/to/pkglist.txt, defaultrouter: '10.1.0.1', host_hostname: 'myjail.my.domain' }
```

create jail (without cloning):
```
iocage: state=present name="foo" properties={ ip4_addr='lo0|10.1.0.5', boot: on, allow_sysvipc: 1, pkglist: /path/to/pkglist.txt, defaultrouter: '10.1.0.1', host_hostname: 'myjail.my.domain' }
```

ensure jail is started:
```
iocage: state=started name="foo"
```

ensure jail is stopped:
```
iocage: state=stopped name="foo"
```

restart existing jail:
```
iocage: state=restarted name="myjail"
```

execute command in (running) jail:
```
iocage: state=exec name="myjail" user="root" cmd="service sshd start"
```

destroy jail:
```
iocage: state=absent name="myjail"
```

set attributes on jail:
```
iocage: state=set name="myjail" properties={template: yes}
```

Expected results of ansible\_test.yml
-------------------------------------

PLAY RECAP ********************************************************
<host>             : ok=28   changed=18   unreachable=0    failed=0 
