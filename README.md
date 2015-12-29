ansible-iocage
==============

iocage module for ansible.

Usecases:
---------

create basejail:
```
iocage: state=basejail tag="foo"
```
create template:
```
iocage: state=template tag="foo" clone_from="basejail_10.2-BETA1" properties="ip4_addr='lo1|10.1.0.5' boot=on allow_sysvipc=1 pkglist=/path/to/pkglist.txt defaultrouter='10.1.0.1'"
```
clone existing jail:
```
iocage: state=cloned tag="foo" uuid="05a32718-2de2-11e5-ad68-a710c4a2a00f" properties="ip4_addr='lo1|10.1.0.5' boot=on allow_sysvipc=1 pkglist=/path/to/pkglist.txt defaultrouter='10.1.0.1'
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
iocage: state=set uuid="05a32718-2de2-11e5-ad68-a710c4a2a00f" properties="template=yes"
```

Expected results of ansible\_test.yml
-------------------------------------

PLAY RECAP ********************************************************
<host>             : ok=19   changed=12   unreachable=0    failed=0 
