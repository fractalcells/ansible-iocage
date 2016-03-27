ansible-iocage
==============

iocage module for ansible.

Usecases:
---------

fetch 10.2-RELEASE:
```
iocage: state=fetched release=10.2-RELEASE
```

create basejail:
```
iocage: state=basejail tag="foo" release=10.2-RELEASE
```

create template:
```
iocage: state=template tag=template release=10.2-RELEASE properties="ip4_addr=lo0|10.1.0.1' resolver='nameserver 127.0.0.1'"
```


clone existing jail:
```
iocage: state=cloned tag="foo" uuid="05a32718-2de2-11e5-ad68-a710c4a2a00f" properties="ip4_addr='lo1|10.1.0.5' boot=on allow_sysvipc=1 pkglist=/path/to/pkglist.txt defaultrouter='10.1.0.1'"
```
start existing jail:
```
iocage: state=started uuid="05a32718-2de2-11e5-ad68-a710c4a2a00f"
```
stop existing jail:
```
iocage: state=stopped uuid="05a32718-2de2-11e5-ad68-a710c4a2a00f" 
```
restart existing jail:
```
iocage: state=restarted uuid="05a32718-2de2-11e5-ad68-a710c4a2a00f" 
```
execute command in (running) jail:
```
iocage: state=exec uuid="05a32718-2de2-11e5-ad68-a710c4a2a00f" user="root" cmd="service sshd start"
```
force destroy jail:
```
iocage: state=absent uuid="05a32718-2de2-11e5-ad68-a710c4a2a00f"
```
set attributes on jail:
```
iocage: state=set uuid="05a32718-2de2-11e5-ad68-a710c4a2a00f" properties="istemplate=yes"
```

Expected results of ansible\_test.yml
-------------------------------------

PLAY RECAP ********************************************************
<host>             : ok=28   changed=18   unreachable=0    failed=0 
